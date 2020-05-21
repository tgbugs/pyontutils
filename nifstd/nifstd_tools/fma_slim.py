#!/usr/bin/env python3

import pathlib
from collections import Counter
from lxml import etree
from pyontutils.core import OntResIri, OntGraph, OntTerm
from pyontutils.utils import Async, deferred
from pyontutils.sheets import Sheet
from pyontutils.scigraph import Dynamic
from pyontutils.namespaces import PREFIXES as uPREFIXES
from nifstd_tools.chebi_slim import ChebiOntSrc, ChebiIdsSrc


def res_stats(res):
    hrm = [(o, n['id']) for o, r in res for n in r['nodes']]           
    hrmt = len(hrm)
    ntotal = len(set(hrm))
    assert hrmt == ntotal
    nunique = len(set(t for o, t in hrm))
    dupes = [(t, c) for t, c in Counter([t for o, t in hrm]).most_common() if c > 1]
    ndupes = len(dupes)
    total_extra = sum(c for t, c in dupes) - ndupes
    many = [(c, OntTerm(t)) for t, c in dupes if c > 2]       
    # the extra 7142 terms are the result of 6695 terms that
    # appear more than once across multiple organs
    breakpoint()


class FMAIdSrc(ChebiIdsSrc):
    source = None  # cypher query
    source_original = True
    @classmethod
    def loadData(cls):
        """ corresponds to the list of FMA ids from organParts
            for all organs in the sparc organsList """
        g = OntGraph()
        g.namespace_manager.populate_from(uPREFIXES)  # cls._ghead except fma doesn't define FMA:
        ol = cls.sgd.prod_sparc_organList()
        top_ids = [n['id'] for n in ol['nodes']]
        res = Async()(deferred(by_organ)(i, cls.sgd) for i in top_ids)
        #res = [by_organ(i, cls.sgd) for i in top_ids]
        #res_stats(res)  # why are there dupes? now we know!
        nodes = [n for o, r in res for n in r['nodes']]
        ids_raw = set(n['id'] for n in nodes if not n['id'].startswith('_:') and n['id'] != 'owl:Nothing')
        ids = set(g.namespace_manager.expand(id).toPython() for id in ids_raw)
        return ids_raw, ids


class FMAOntSrc(ChebiOntSrc):

    source = 'http://sig.biostr.washington.edu/share/downloads/fma/release/latest/fma.zip'
    _id_src = FMAIdSrc
    more = False

    @classmethod
    def loadData(cls):
        ori = OntResIri(cls.source)
        omi = ori.metadata()
        # omi.graph populates progenitors FIXME shouldn't have to do this explicitly?
        FMAIdSrc._ghead = omi.graph  # NOTE unused
        zp = omi.progenitor(type='path-compressed')

        with zp.open() as f:
            t = etree.parse(f)

        # FIXME zf should/needs to be closed
        # I think augpathlib has to deal with zip substreams like this
        # e.g. aug.LocalZipPath('file.zip/file.owl')
        # would check to see if file.zip exists and then just go on its
        # merry way to opening the streams, the makes more sense to me
        # the workflow is clearer as well and once ziphead is working
        # it should also work on remote zip files without the need to
        # pull the whole file, just the central directory and friends
        # <https://stackoverflow.com/questions/8543214/
        #  is-it-possible-to-download-just-part-of-a-zip-archive-e-g-one-file>
        # it looks like it is a bit more complicated in that I would need
        # a HttpIO ... https://pypi.org/project/httpio/
        # yep, there it is with my use case presented front and center!
        return t


def old():
    from sparcur.sheets import Organs
    from sparcur.utils import log

    class Terms(Sheet):
        name = 'sparc-terms'
        sheet_name = 'all-organs'
        index_columns = ('id',)

        def _lookup(self, index_column, value, fail=False, raw=True):
            try:
                row = self.byCol.searchIndex(index_column, value, raw=raw)
                return row
            except KeyError as e:
                # TODO update the sheet automatically
                log.critical(f'No match on {index_column} for: {value}')
                if fail:
                    raise e

        def _ic_row_index(self, row):
            # FIXME dict or cache this for performance
            icn = self.index_columns[0]
            index = self.values[0].index(icn)
            id = row[index]
            matching = self._lookup(icn, id, fail=True)
            return self.values.index(matching)

        def upsert(self, *rows):
            for row in rows:
                try:
                    row_index = self._ic_row_index(row)
                    row_object = self.row_object(row_index)
                    row_object.values = row
                except KeyError:
                    self._appendRow(row)


    def main():
        terms = Terms(readonly=False)
        sgd = Dynamic(cache=True)
        ol = sgd.prod_sparc_organList()
        ol['nodes']
        ids = [n['id'] for n in ol['nodes']]
        res = Async()(deferred(by_organ)(i, sgd) for i in ids)
        nodes = [n for o, r in res for n in r['nodes']]
        rows = [(o, n['id'], n['lbl'], '\n'.join(syn(n)), defn(n))
                for o, r in res for n in r['nodes']]
        terms.upsert(*rows)
        terms.commit()


def by_organ(i, sgd):
    return i, sgd.prod_sparc_organParts_id(i)


d = 'http://purl.org/sig/ont/fma/definition'
def defn(n):
    if d in n['meta']:
        dfn = n['meta'][d]
        if dfn:
            return dfn[0]

    if 'definition' in n['meta']:
        dfn = n['meta']['definition']
        if dfn:
            return dfn[0]


def syn(n):
    if 'synonym' in n['meta']:
        return n['meta']['synonym']
    else:
        return []


def main():
    # FMA -> subset
    sgd = Dynamic(cache=True)
    FMAIdSrc.sgd = sgd
    #d = FMAOntSrc.loadData()
    more, more_ids, g = FMAOntSrc()
    if FMAOntSrc.more:
        p = pathlib.Path('/tmp/fma-slim-big.ttl')
    else:
        p = pathlib.Path('/tmp/fma-slim.ttl')

    g.write(p)

    #breakpoint()

    # setting FMAOntSrc.more = False for now to avoid 5x expansion in term count

    # with the default chebi expansion rules
    # there are rougly 12k seed terms that produce a total about 60k classes
    # in fma full there are about 104k classes
    # slim is about an order of magnitude smaller in raw bytes
    # I think we need to tune the class inclusion rules to prevent overexpansion
    # because I'm pulling in ALL the restrictions
    # the more and more_ids lengths are around 48k and 58k respectively
    # which is ... not desireable, better to let these dangle probably?
    # would be fascinating to know what the other 40k we aren't hitting are though ...


if __name__ == '__main__':
    main()
