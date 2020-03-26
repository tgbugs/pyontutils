import re
from collections import defaultdict, Counter
from ttlser import natsort
from pyontutils.core import LabelsBase, Collector, Source, resSource, ParcOnt
from pyontutils.core import makePrefixes
from pyontutils.config import auth
from pyontutils.namespaces import nsExact
from pyontutils.namespaces import NIFRID, ilx, ilxtr, TEMP
from pyontutils.namespaces import NCBITaxon, UBERON
from pyontutils.namespaces import PAXMUS, PAXRAT, paxmusver, paxratver
from pyontutils.namespaces import rdf, rdfs, owl
from pyontutils.combinators import annotations
from nifstd_tools.parcellation import log
from nifstd_tools.parcellation import Atlas, Label, LabelRoot, LocalSource, parcCore
from nifstd_tools.parcellation import RegionRoot, RegionsBase

log = log.getChild('pax')


class DupeRecord:
    def __init__(self, alt_abbrevs=tuple(), structures=tuple(), figures=None, artiris=tuple()):
        self.alt_abbrevs = alt_abbrevs
        self.structures = structures
        self.artiris = artiris


class Artifacts(Collector):
    collects = Atlas
    class PaxMouseAt(Atlas):
        """ Any atlas artifact with Paxinos as an author for the adult rat. """
        iri = ilx['paxinos/uris/mouse']  # ilxtr.paxinosMouseAtlas
        class_label = 'Paxinos Mouse Atlas'

    PaxMouseAtlas = Atlas(iri=PaxMouseAt.iri,
                          species=NCBITaxon['10090'],
                          devstage=UBERON['0000113'],  # TODO this is 'Mature' which may not match... RnorDv:0000015 >10 weeks...
                          region=UBERON['0000955'],
                          )

    PaxMouse2 = PaxMouseAt(iri=paxmusver['2'],  # ilxtr.paxm2,
                           label='The Mouse Brain in Stereotaxic Coordinates 2nd Edition',
                           synonyms=('Paxinos Mouse 2nd',),
                           abbrevs=tuple(),
                           shortname='PAXMOUSE2',  # TODO upper for atlas lower for label?
                           copyrighted='2001',
                           version='2nd Edition',  # FIXME ??? delux edition??? what is this
                           citation='???????',)

    PaxMouse3 = PaxMouseAt(iri=paxmusver['3'],  # ilxtr.paxm3,
                           label='The Mouse Brain in Stereotaxic Coordinates 3rd Edition',
                           synonyms=('Paxinos Mouse 3rd',),
                           abbrevs=tuple(),
                           shortname='PAXMOUSE3',  # TODO upper for atlas lower for label?
                           copyrighted='2008',
                           version='3rd Edition',
                           citation='???????',)

    PaxMouse4 = PaxMouseAt(iri=paxmusver['4'],  # ilxtr.paxm4,
                           label='The Mouse Brain in Stereotaxic Coordinates 4th Edition',
                           synonyms=('Paxinos Mouse 4th',),
                           abbrevs=tuple(),
                           shortname='PAXMOUSE4',  # TODO upper for atlas lower for label?
                           copyrighted='2012',
                           version='4th Edition',
                           citation='???????',)

    class PaxRatAt(Atlas):
        """ Any atlas artifact with Paxinos as an author for the adult rat. """
        iri = ilx['paxinos/uris/rat']  # ilxtr.paxinosRatAtlas
        class_label = 'Paxinos Rat Atlas'

    PaxRatAtlas = Atlas(iri=PaxRatAt.iri,
                        species=NCBITaxon['10116'],
                        devstage=UBERON['0000113'],  # TODO this is 'Mature' which may not match... RnorDv:0000015 >10 weeks...
                        region=UBERON['0000955'],
                        citation=('Paxinos, George, Charles RR Watson, and Piers C. Emson. '
                                  '"AChE-stained horizontal sections of the rat brain '
                                  'in stereotaxic coordinates." Journal of neuroscience '
                                  'methods 3, no. 2 (1980): 129-149.'),)

    PaxRat4 = PaxRatAt(iri=ilx['paxinos/uris/rat/versions/4'],  # ilxtr.paxr4,
                       label='The Rat Brain in Stereotaxic Coordinates 4th Edition',
                       synonyms=('Paxinos Rat 4th',),
                       abbrevs=tuple(),
                       shortname='PAXRAT4',  # TODO upper for atlas lower for label?
                       copyrighted='1998',
                       version='4th Edition',)

    PaxRat6 = PaxRatAt(iri=ilx['paxinos/uris/rat/versions/6'],  # ilxtr.paxr6,
                       label='The Rat Brain in Stereotaxic Coordinates 6th Edition',
                       synonyms=('Paxinos Rat 6th',),
                       abbrevs=tuple(),
                       shortname='PAXRAT6',  # TODO upper for atlas lower for label?
                       copyrighted='2007',
                       version='6th Edition',)

    PaxRat7 = PaxRatAt(iri=ilx['paxinos/uris/rat/versions/7'],  # ilxtr.paxr7,
                       label='The Rat Brain in Stereotaxic Coordinates 7th Edition',
                       synonyms=('Paxinos Rat 7th',
                                 'Paxinos and Watson\'s The Rat Brain in Stereotaxic Coordinates 7th Edition',  # branding >_<
                                ),
                       abbrevs=tuple(),
                       shortname='PAXRAT7',  # TODO upper for atlas lower for label?
                       copyrighted='2014',
                       version='7th Edition',)


class PaxSr_6(resSource):
    sourceFile = auth.get_path('resources') / 'paxinos09names.txt'
    artifact = Artifacts.PaxRat6

    @classmethod
    def loadData(cls):
        with open(cls.source, 'rt') as f:
            lines = [l.rsplit('#')[0].strip() for l in f.readlines() if not l.startswith('#')]
        return [l.rsplit(' ', 1) for l in lines]

    @classmethod
    def processData(cls):
        structRecs = []
        out = {}
        for structure, abrv in cls.raw:
            structRecs.append((abrv, structure))
            if abrv in out:
                out[abrv][0].append(structure)
            else:
                out[abrv] = ([structure], ())
        return structRecs, out

    @classmethod
    def validate(cls, structRecs, out):
        print(Counter(_[0] for _ in structRecs).most_common()[:5])
        print(Counter(_[1] for _ in structRecs).most_common()[:5])
        assert len(structRecs) == len([s for sl, _ in out.values() for s in sl]), 'There are non-unique abbreviations'
        errata = {}
        return out, errata


class PaxSrAr(resSource):
    artifact = None

    @classmethod
    def parseData(cls):
        a, b = cls.raw.split('List of Structures')
        if not a:
            los, loa = b.split('List of Abbreviations')
        else:
            los = b
            _, loa = a.split('List of Abbreviations')

        sr = []
        for l in los.split('\n'):
            if l and not l[0] == ';':
                if ';' in l:
                    l, *comment = l.split(';')
                    l = l.strip()
                    print(l, comment)

                #asdf = l.rsplit(' ', 1)
                #print(asdf)
                struct, abbrev = l.rsplit(' ', 1)
                sr.append((abbrev, struct))

        ar = []
        for l in loa.split('\n'):
            if l and not l[0] == ';':
                if ';' in l:
                    l, *comment = l.split(';')
                    l = l.strip()
                    print(l, comment)

                #asdf = l.rsplit(' ', 1)
                #print(asdf)
                abbrev, rest = l.split(' ', 1)
                parts = rest.split(' ')
                #print(parts)
                for i, pr in enumerate(parts[::-1]):
                    #print(i, pr)
                    z = pr[0].isdigit()
                    if not z or i > 0 and z and pr[-1] != ',':
                        break

                struct = ' '.join(parts[:-i])
                figs = tuple(tuple(int(_) for _ in p.split('-'))
                             if '-' in p
                             else (tuple(f'{nl[:-1]}{l}'
                                        for nl, *ls in p.split(',')
                                        for l in (nl[-1], *ls))
                                   if ',' in p or p[-1].isalpha()
                                   else int(p))
                             for p in (_.rstrip(',') for _ in parts[-i:]))
                figs = tuple(f for f in figs if f)  # zero marks abbrevs in index that are not in figures
                #print(struct)
                ar.append((abbrev, struct, figs))
        return sr, ar

    @classmethod
    def processData(cls):
        sr, ar = cls.parseData()
        out = {}
        achild = {}
        for a, s, f in ar:
            if ', layer 1' in s or s.endswith(' layer 1'):  # DTT1 ends in ' layer 1' without a comma
                achild[a[:-1]] = a
                continue  # remove the precomposed, we will deal with them systematically
            if a not in out:
                out[a] = ([s], f)
            else:
                if s not in out[a][0]:
                    print(f'Found new label from ar for {a}:\n{s}\n{out[a][0]}')
                    out[a][0].append(s)

        schild = {}
        for a, s in sr:
            if ', layer 1' in s or s.endswith(' layer 1'):
                schild[a[:-1]] = a
                continue # remove the precomposed, we will deal with them systematically
            if a not in out:
                out[a] = ([s], tuple())
            else:
                if s not in out[a][0]:
                    print(f'Found new label from sr for {a}:\n{s}\n{out[a][0]}')
                    out[a][0].append(s)
                    #raise TypeError(f'Mismatched labels on {a}: {s} {out[a][0]}')

        return sr, ar, out, achild, schild

    @classmethod
    def validate(cls, sr, ar, out, achild, schild):
        def missing(a, b):
            am = a - b
            bm = b - a
            return am, bm
        sabs = set(_[0] for _ in sr)
        aabs = set(_[0] for _ in ar)
        ssts = set(_[1] for _ in sr)
        asts = set(_[1] for _ in ar)
        ar2 = set(_[:2] for _ in ar)
        aam, sam = missing(aabs, sabs)
        asm, ssm = missing(asts, ssts)
        ar2m, sr2m = missing(ar2, set(sr))
        print('OK to skip')
        print(sorted(aam))
        print('Need to be created')
        print(sorted(sam))
        print()
        print(sorted(asm))
        print()
        print(sorted(ssm))
        print()
        #print(sorted(ar2m))
        #print()
        #print(sorted(sr2m))
        #print()

        assert all(s in achild for s in schild), f'somehow the kids dont match {achild} {schild}\n' + str(sorted(set(a) - set(s) | set(s) - set(a)
                                                                                               for a, s in ((tuple(sorted(achild.items())),
                                                                                                             tuple(sorted(schild.items()))),)))
        for k, (structs, figs) in out.items():
            for struct in structs:
                assert not re.match('\d+-\d+', struct) and not re.match('\d+$', struct), f'bad struct {struct} in {k}'

        errata = {'nodes with layers':achild}
        return out, errata


class PaxSrAr_4(PaxSrAr):
    sourceFile = auth.get_path('resources') / 'pax-4th-ed-indexes.txt'
    artifact = Artifacts.PaxRat4


class PaxSrAr_6(PaxSrAr):
    sourceFile = auth.get_path('resources') / 'pax-6th-ed-indexes.txt'
    artifact = Artifacts.PaxRat6


class PaxMSrAr_2(PaxSrAr):
    sourceFile = auth.get_path('resources') / 'paxm-2nd-ed-indexes.txt'
    artifact = Artifacts.PaxMouse2


class PaxMSrAr_3(PaxSrAr):
    sourceFile = auth.get_path('resources') / 'paxm-3rd-ed-indexes.txt'
    artifact = Artifacts.PaxMouse3


class PaxTree_6(Source):
    source = '~/ni/dev/nifstd/paxinos/tree.txt'
    artifact = Artifacts.PaxRat6

    @classmethod
    def loadData(cls):
        with open(os.path.expanduser(cls.source), 'rt') as f:
            return [l for l in f.read().split('\n') if l]

    @classmethod
    def processData(cls):
        out = {}
        recs = []
        parent_stack = [None]
        old_depth = 0
        layers = {}
        for l in cls.raw:
            depth, abbrev, _, name = l.split(' ', 3)
            depth = len(depth)

            if old_depth < depth:  # don't change
                parent = parent_stack[-1]
                parent_stack.append(abbrev)
                old_depth = depth
            elif old_depth == depth:
                if len(parent_stack) - 1 > depth:
                    parent_stack.pop()

                parent = parent_stack[-1]
                parent_stack.append(abbrev)
            elif old_depth > depth:  # bump back
                for _ in range(old_depth - depth + 1):
                    parent_stack.pop()

                parent = parent_stack[-1]
                parent_stack.append(abbrev)
                old_depth = depth

            struct = None if name == '-------' else name
            o = (depth, abbrev, struct, parent)
            if '-' in abbrev:
                # remove the precomposed, we will deal with them systematically
                maybe_parent, rest = abbrev.split('-', 1)
                if rest.isdigit() or rest == '1a' or rest == '1b':  # Pir1a Pir1b
                    if parent == 'Unknown':  # XXX special cases
                        if maybe_parent == 'Pi':  # i think this was probably caused by an ocr error from Pir3 -> Pi3
                            continue

                    assert maybe_parent == parent, f'you fall into a trap {maybe_parent} {parent}'
                    if parent not in layers:
                        layers[parent] = []

                    layers[parent].append((layer, o))  # FIXME where does layer come from here?
                    # I think this comes from the previous iteration of the loop?!
            elif struct is not None and ', layer 1' in struct:
                # remove the precomposed, we will deal with them systematically
                parent_, layer = abbrev[:-1], abbrev[-1]
                if parent_ == 'CxA' and parent == 'Amy':  # XXX special cases
                    parent = 'CxA'
                elif parent == 'Unknown':
                    if parent_ == 'LOT':
                        parent = 'LOT'
                    elif parent_ == 'Tu':
                        parent = 'Tu'

                assert parent_ == parent, f'wrong turn friend {parent_} {parent}'
                if parent not in layers:
                    layers[parent] = []

                layers[parent].append((layer, o))
            else:
                recs.append(o)
                out[abbrev] = ([struct], (), parent)

        errata = {'nodes with layers':layers}
        return recs, out, errata

    @classmethod
    def validate(cls, trecs, tr, errata):
        print(Counter(_[1] for _ in trecs).most_common()[:5])
        ('CxA1', 2), ('Tu1', 2), ('LOT1', 2), ('ECIC3', 2)
        assert len(tr) == len(trecs), 'Abbreviations in tr are not unique!'
        return tr, errata


class PaxFix4(LocalSource):
    artifact = Artifacts.PaxRat4
    _data = ({
        # 1-6b are listed in fig 19 of 4e, no 3/4, 5a, or 5b
        '1':(['layer 1 of cortex'], tuple()),
        '1a':(['layer 1a of cortex'], tuple()),
        '1b':(['layer 1b of cortex'], tuple()),
        '2':(['layer 2 of cortex'], tuple()),
        '3':(['layer 3 of cortex'], tuple()),
        '3/4':(['layer 3/4 of cortex'], tuple()),
        '4':(['layer 4 of cortex'], tuple()),
        '5':(['layer 5 of cortex'], tuple()),
        '5a':(['layer 5a of cortex'], tuple()),
        '5b':(['layer 5b of cortex'], tuple()),
        '6':(['layer 6 of cortex'], tuple()),
        '6a':(['layer 6a of cortex'], tuple()),
        '6b':(['layer 6b of cortex'], tuple()),
    }, {})


class PaxFix6(LocalSource):
    artifact = Artifacts.PaxRat6
    _data = ({
        '1':(['layer 1 of cortex'], tuple()),
        '1a':(['layer 1a of cortex'], (8,)),
        '1b':(['layer 1b of cortex'], (8,)),
        '2':(['layer 2 of cortex'], tuple()),
        '3':(['layer 3 of cortex'], tuple()),
        '3/4':(['layer 3/4 of cortex'], (94,)),
        '4':(['layer 4 of cortex'], tuple()),
        '5':(['layer 5 of cortex'], tuple()),
        '5a':(['layer 5a of cortex'], (52, 94)),
        '5b':(['layer 5b of cortex'], tuple()),
        '6':(['layer 6 of cortex'], tuple()),
        '6a':(['layer 6a of cortex'], tuple()),
        '6b':(['layer 6b of cortex'], tuple()),
    }, {})


class PaxFix(LocalSource):
    _data = ({
        '1':(['layer 1'], tuple()),
        '1a':(['layer 1a'], (8,)),
        '1b':(['layer 1b'], (8,)),
        '2':(['layer 2'], tuple()),
        '3':(['layer 3'], tuple()),
        '3/4':(['layer 3/4'], (94,)),
        '4':(['layer 4'], tuple()),
        '5':(['layer 5'], tuple()),
        '5a':(['layer 5a'], (52, 94)),
        '5b':(['layer 5b'], tuple()),
        '6':(['layer 6'], tuple()),
        '6a':(['layer 6a'], tuple()),
        '6b':(['layer 6b'], tuple()),
    }, {})


class PaxMFix(LocalSource):
    _data = ({}, {})


class PaxLabels(LabelsBase):
    """ Base class for processing paxinos indexes. """
    __pythonOnly = True
    path = 'ttl/generated/parcellation/'
    imports = parcCore,
    _fixes = []
    _dupes = {}
    _merge = {}

    @property
    def fixes_abbrevs(self):
        fixes_abbrevs = set()
        for f in self._fixes:
            fixes_abbrevs.add(f[0])
        for dupe in self._dupes.values():
            fixes_abbrevs.add(dupe.alt_abbrevs[0])
        return fixes_abbrevs

    @property
    def fixes_prov(self):
        _fixes_prov = {}
        for f in self._fixes:
            for l in f[1][0]:
                _fixes_prov[l] = [ParcOnt.wasGeneratedBy.format(line=getSourceLine(self.__class__))]  # FIXME per file
        return _fixes_prov

    @property
    def dupes_structs(self):
        ds = {'cerebellar lobules', 'cerebellar lobule'}
        for dupe in self._dupes.values():
            for struct in dupe.structures:
                ds.add(struct)
        return ds

    @property
    def fixes(self):
        _, _, collisions, _ = self.records()
        for a, (ss, f, arts) in self._fixes:
            if (a, ss[0]) in collisions:
                f.update(collisions[a, ss[1]])  # have to use 1 since we want "layer n" as the pref

            yield a, ([], ss, f, arts)

    def _prov(self, iri, abrv, struct, struct_prov, extras, alt_abbrevs, abbrev_prov):
        # TODO asssert that any triple for as ap at is actually in the graph...
        annotation_predicate = ilxtr.literalUsedBy
        definition_predicate = ilxtr.isDefinedBy  # TODO more like 'symbolization used in'
        for abbrev in [abrv] + alt_abbrevs:  # FIXME multiple annotations per triple...
            t = iri, Label.propertyMapping['abbrevs'], abbrev
            if t not in self._prov_dict:
                self._prov_dict[t] = []
            for s in [struct] + extras:
                if (abbrev, s) in abbrev_prov:
                    for artifact in abbrev_prov[abbrev, s]:
                        if 'github' in artifact:
                            continue
                        else:
                            predicate = annotation_predicate

                        self._prov_dict[t].append((predicate, artifact))

        if struct in struct_prov:
            t = iri, Label.propertyMapping['label'], struct
            if t not in self._prov_dict:
                self._prov_dict[t] = []
            for artifact in struct_prov[struct]:
                if 'github' in artifact:
                    predicate = definition_predicate
                else:
                    predicate = annotation_predicate

                self._prov_dict[t].append((predicate, artifact))

        for extra in extras:
            t = iri, Label.propertyMapping['synonyms'], extra
            if t not in self._prov_dict:
                self._prov_dict[t] = []
            for artifact in struct_prov[extra]:
                if 'github' in artifact:
                    predicate = definition_predicate
                else:
                    predicate = annotation_predicate

                self._prov_dict[t].append((predicate, artifact))

    def _makeIriLookup(self):
        # FIXME need to validate that we didn't write the graph first...
        g = Graph().parse(self._graph.filename, format='turtle')
        ids = [s for s in g.subjects(rdf.type, owl.Class) if self.namespace in s]
        index0 = Label.propertyMapping['abbrevs'],
        index1 = Label.propertyMapping['label'], Label.propertyMapping['synonyms']
        out = {}
        for i in ids:
            for p0 in index0:
                for o0 in g.objects(i, p0):
                    for p1 in index1:
                        for o1 in g.objects(i, p1):
                            key = o0, o1
                            value = i
                            if key in out:
                                raise KeyError(f'Key {key} already in output!')
                            out[key] = value
        return out

    def _triples(self):
        self._prov_dict = {}
        combined_record, struct_prov, _, abbrev_prov = self.records()
        for k, v in self.fixes_prov.items():
            if k in struct_prov:
                struct_prov[k].extend(v)
            else:
                struct_prov[k] = v
        for i, (abrv, (alts, (structure, *extras), figures, artifacts)) in enumerate(
                sorted(list(combined_record.items()) + list(self.fixes),
                       key=lambda d:natsort(d[1][1][0] if d[1][1][0] is not None else 'zzzzzzzzzzzzzzzzzzzz'))):  # sort by structure not abrev
            iri = self.namespace[str(i + 1)]  # TODO load from existing
            struct = structure if structure else 'zzzzzz'
            self._prov(iri, abrv, struct, struct_prov, extras, alts, abbrev_prov)
            yield from Label(labelRoot=self.root,
                             #ifail='i fail!',  # this indeed does fail
                             label=struct,
                             altLabel=None,
                             synonyms=extras,
                             abbrevs=(abrv, *alts),  # FIXME make sure to check that it is not a string
                             iri=iri,  # FIXME error reporint if you try to put in abrv is vbad
                             #extra_triples = str(processed_figures),  # TODO
                     )
            processed_figures = figures  # TODO these are handled in regions pass to PaxRegions
            if figures:
                for artifact in artifacts:
                    PaxRegion.addthing(iri, figures)  # artifact is baked into figures

        for t, pairs in self._prov_dict.items():
            if pairs:
                yield from annotations(pairs, *t)

    def validate(self):
        # check for duplicate labels
        labels = list(self.graph.objects(None, rdfs.label))
        assert len(labels) == len(set(labels)), f'There are classes with duplicate labels! {Counter(labels).most_common()[:5]}'

        # check for unexpected duplicate abbreviations
        abrevs = list(self.graph.objects(None, NIFRID.abbrev))
        # remove expected numeric/layer/lobule duplicates
        filt = [a for a in abrevs if not a.isdigit() and a.value not in ('6a', '6b')]
        assert len(filt) == len(set(filt)), f'DUPES! {Counter(filt).most_common()[:5]}'
        # check for abbreviations without corresponding structure ie 'zzzzzz'
        syns = list(self.graph.objects(None, NIFRID.synonym))
        for thing in labels + syns:
            trips = [(s, o) for s in self.graph.subjects(None, thing) for p, o in self.graph.predicate_objects(s)]
            assert 'zzzzzz' not in thing, f'{trips} has bad label/syn suggesting a problem with the source file'
        return self

    def records(self):
        combined_record = {}
        struct_prov = {}
        collisions = {}
        abbrev_prov = {}
        merge = {**self._merge, **{v:k for k, v in self._merge.items()}}
        fa = self.fixes_abbrevs
        ds = self.dupes_structs

        def do_struct_prov(structure, source=None, artiri=None):
            if artiri is None:
                artiri = source.artifact.iri
            if structure not in struct_prov:
                struct_prov[structure] = [artiri]
            elif artiri not in struct_prov[structure]:
                struct_prov[structure].append(artiri)

        def do_abbrev_prov(abbrev, primary_struct, source=None, artiri=None, overwrite=False):
            if artiri is None:
                artiri = source.artifact.iri
            if overwrite:
                abbrev_prov[abbrev, primary_struct] = artiri if isinstance(artiri, list) else [artiri]
            else:
                if (abbrev, primary_struct) not in abbrev_prov:
                    abbrev_prov[abbrev, primary_struct] = [artiri]
                elif artiri not in abbrev_prov[abbrev, primary_struct]:
                    abbrev_prov[abbrev, primary_struct].append(artiri)  # include all the prov we can

        for se in self.sources:
            source, errata = se
            for t in se.isVersionOf:
                self.addTrip(*t)
            for a, (ss, f, *_) in source.items():  # *_ eat the tree for now
                # TODO deal with overlapping layer names here
                if a in fa:  # XXX this is now just for dupes...
                    if ss[0] in ds:
                        print('TODO', a, ss, f)
                        collisions[a, ss[0]] = {se.artifact.iri:f}
                        continue  # skip the entries that we create manually TODO

                do_abbrev_prov(a, ss[0], se)
                for s in ss:
                    do_struct_prov(s, se)
                if a in combined_record:
                    _, structures, figures, artifacts = combined_record[a]
                    if f:
                        assert (se.artifact.iri not in figures or
                                figures[se.artifact.iri] == f), f'>1 figures {a} {figures} {bool(f)}'
                        figures[se.artifact.iri] = f
                    for s in ss:
                        if s is not None and s not in structures:
                            structures.append(s)
                    if se.artifact.iri not in artifacts:
                        artifacts.append(se.artifact.iri)
                elif a in merge and merge[a] in combined_record:
                    alt_abbrevs, structures, figures, artifacts = combined_record[merge[a]]
                    for struct in structures:  # allow merge of terms with non exact matching but warn
                        if struct not in ss:
                            if ss: log.warning(f'adding structure {struct} in merge of {a}')
                            ss.append(struct)
                    for aa in alt_abbrevs:
                        do_abbrev_prov(aa, ss[0], se)

                    alt_abbrevs.append(a)
                    figures[se.artifact.iri] = f
                    if se.artifact.iri not in artifacts:
                        artifacts.append(se.artifact.iri)
                else:
                    ss = [s for s in ss if s is not None]
                    alt_abbrevs = self._dupes[a].alt_abbrevs if a in self._dupes else []
                    for aa in alt_abbrevs:
                        for artiri in self._dupes[a].artiris:  # TODO check if matches current source art iri?
                            do_abbrev_prov(aa, ss[0], artiri=artiri)
                    if ss:  # skip terms without structures
                        combined_record[a] = alt_abbrevs, ss, {se.artifact.iri:f}, [se.artifact.iri]
                    if alt_abbrevs:  # TODO will need this for some abbrevs too...
                        artiris = self._dupes[a].artiris
                        for s in self._dupes[a].structures:
                            if s not in ss:
                                ss.append(s)
                            for artiri in artiris:
                                artifacts = combined_record[a][-1]
                                if artiri not in artifacts:
                                    artifacts.append(artiri)

                                do_struct_prov(s, artiri=artiri)
                        #abbrev_prov[a, ss[0]] = [se.artifact.iri]  # FIXME overwritten?
                        do_abbrev_prov(a, ss[0], se)
                        for alt in alt_abbrevs:
                            if alt not in abbrev_prov:
                                for artiri in artiris:
                                    do_abbrev_prov(alt, ss[0], artiri=artiri)

                            # TODO elif...

        return combined_record, struct_prov, collisions, abbrev_prov


class PaxMouseLabels(PaxLabels):
    """ Compilation of all labels used to name mouse brain regions
        in atlases created using Paxinos and Franklin\'s methodology."""

    # TODO FIXME align indexes where possible to paxrat???

    filename = 'paxinos-mus-labels'
    name = 'Paxinos & Franklin Mouse Parcellation Labels'
    shortname = 'paxmus'
    namespace = PAXMUS

    prefixes = {**makePrefixes('NIFRID', 'ilxtr', 'prov', 'dcterms'),
                'PAXMUS':str(PAXMUS),
                'paxmusver':str(paxmusver),
    }
    sources = PaxMFix, PaxMSrAr_2, PaxMSrAr_3
    root = LabelRoot(iri=nsExact(namespace),  # PAXMUS['0'],
                     label='Paxinos mouse parcellation label root',
                     shortname=shortname,
                     definingArtifactsS=(Artifacts.PaxMouseAt.iri,),
    )

    _merge = {
        '4/5Cb':'4&5Cb',
        '5N':'Mo5',
        '12N':'12',
        'AngT':'Ang',
        'ANS':'Acc',
        'ASt':'AStr',
        'hif':'hf',
        'MnM':'MMn',
        'MoDG':'Mol',
        'och':'ox',
        'PHA':'PH',  # FIXME PH is reused in 3rd
        'ST':'BST',
        'STIA':'BSTIA',
        'STLD':'BSTLD',
        'STLI':'BSTLI',
        'STLJ':'BSTLJ',
        'STLP':'BSTLP',
        'STLV':'BSTLV',
        'STMA':'BSTMA',
        'STMP':'BSTMP',
        'STMPI':'BSTMPI',
        'STMPL':'BSTMPL',
        'STMPM':'BSTMPM',
        'STMV':'BSTMV',
        'STS':'BSTS',
    }


class PaxRatLabels(PaxLabels):
    """ Compilation of all labels used to name rat brain regions
        in atlases created using Paxinos and Watson\'s methodology."""

    filename = 'paxinos-rat-labels'
    name = 'Paxinos & Watson Rat Parcellation Labels'
    shortname = 'paxrat'
    namespace = PAXRAT

    prefixes = {**makePrefixes('NIFRID', 'ilxtr', 'prov', 'dcterms'),
                'PAXRAT':str(PAXRAT),
                'paxratver':str(paxratver),
    }
    # sources need to go in the order with which we want the labels to take precedence (ie in this case 6e > 4e)
    sources = PaxFix, PaxSrAr_6, PaxSr_6, PaxSrAr_4, PaxFix6, PaxFix4 #, PaxTree_6()  # tree has been successfully used for crossreferencing, additional terms need to be left out at the moment (see in_tree_not_in_six)
    root = LabelRoot(iri=nsExact(namespace),  # PAXRAT['0'],
                     label='Paxinos rat parcellation label root',
                     shortname=shortname,
                     #definingArtifactsS=None,#Artifacts.PaxRatAt.iri,
                     definingArtifactsS=(Artifacts.PaxRatAt.iri,),
    )

    _fixes = []

    _dupes = {
        # for 4e the numbers in the index are to the cranial nerve nuclei entries
        '3N':DupeRecord(alt_abbrevs=['3'], structures=['oculomotor nucleus'], figures={}, artiris=[Artifacts.PaxRat4.iri]),
        '4N':DupeRecord(alt_abbrevs=['4'], structures=['trochlear nucleus'],  figures={}, artiris=[Artifacts.PaxRat4.iri]),
        '6N':DupeRecord(alt_abbrevs=['6'], structures=['abducens nucleus'],   figures={}, artiris=[Artifacts.PaxRat4.iri]),
        '7N':DupeRecord(alt_abbrevs=['7'], structures=['facial nucleus'],     figures={}, artiris=[Artifacts.PaxRat4.iri]),
        '10N':DupeRecord(alt_abbrevs=['10'], structures=['dorsal motor nucleus of vagus'], figures={}, artiris=[Artifacts.PaxRat4.iri]),

        # FIXME need comments about the index entries
        '1Cb':DupeRecord(alt_abbrevs=['1'], structures=['cerebellar lobule 1'], figures={}, artiris=[Artifacts.PaxRat4.iri]),
        '2Cb':DupeRecord(alt_abbrevs=['2'], structures=['cerebellar lobule 2'], figures={}, artiris=[Artifacts.PaxRat4.iri]),
        '2/3Cb':DupeRecord(alt_abbrevs=['2&3'], structures=['cerebellar lobules 2&3'], figures={}, artiris=[Artifacts.PaxRat4.iri]),
        '3Cb':DupeRecord(alt_abbrevs=['3'], structures=['cerebellar lobule 3'], figures={}, artiris=[Artifacts.PaxRat4.iri]),
        '4Cb':DupeRecord(alt_abbrevs=['4'], structures=['cerebellar lobule 4'], figures={}, artiris=[Artifacts.PaxRat4.iri]),
        '4/5Cb':DupeRecord(alt_abbrevs=['4&5'], structures=['cerebellar lobules 4&5'], figures={}, artiris=[Artifacts.PaxRat4.iri]),
        '5Cb':DupeRecord(alt_abbrevs=['5'], structures=['cerebellar lobule 5'], figures={}, artiris=[Artifacts.PaxRat4.iri]),
        '6Cb':DupeRecord(alt_abbrevs=['6'], structures=['cerebellar lobule 6'], figures={}, artiris=[Artifacts.PaxRat4.iri]),
        '6aCb':DupeRecord(alt_abbrevs=['6a'], structures=['cerebellar lobule 6a'], figures={}, artiris=[Artifacts.PaxRat4.iri]),
        '6bCb':DupeRecord(alt_abbrevs=['6b'], structures=['cerebellar lobule 6b'], figures={}, artiris=[Artifacts.PaxRat4.iri]),
        '6cCb':DupeRecord(alt_abbrevs=['6c'], structures=['cerebellar lobule 6c'], figures={}, artiris=[Artifacts.PaxRat4.iri]),
        '7Cb':DupeRecord(alt_abbrevs=['7'], structures=['cerebellar lobule 7'], figures={}, artiris=[Artifacts.PaxRat4.iri]),
        '8Cb':DupeRecord(alt_abbrevs=['8'], structures=['cerebellar lobule 8'], figures={}, artiris=[Artifacts.PaxRat4.iri]),
        '9Cb':DupeRecord(alt_abbrevs=['9'], structures=['cerebellar lobule 9'], figures={}, artiris=[Artifacts.PaxRat4.iri]),
        '10Cb':DupeRecord(alt_abbrevs=['10'], structures=['cerebellar lobule 10'], figures={}, artiris=[Artifacts.PaxRat4.iri]),
    }

    _merge = {  # abbrevs that have identical structure names
        '5N':'Mo5',
        '12N':'12',
        'ANS':'Acc',
        'ASt':'AStr',
        'AngT':'Ang',
        'MnM':'MMn',
        'MoDG':'Mol',
        'PDPO':'PDP',
        'PTg':'PPTg',
        'STIA':'BSTIA',
        'STL':'BSTL',
        'STLD':'BSTLD',
        'STLI':'BSTLI',
        'STLJ':'BSTLJ',
        'STLP':'BSTLP',
        'STLV':'BSTLV',
        'STM':'BSTM',
        'STMA':'BSTMA',
        'STMP':'BSTMP',
        'STMPI':'BSTMPI',
        'STMPL':'BSTMPL',
        'STMPM':'BSTMPM',
        'STMV':'BSTMV',
        'hif':'hf',
        'och':'ox',
    }

    def curate(self):
        fr, err4 = PaxSrAr_4()
        sx, err6 = PaxSrAr_6()
        sx2, _ = PaxSr_6()
        tr, err6t = PaxTree_6()

        sfr = set(fr)
        ssx = set(sx)
        ssx2 = set(sx2)
        str_ = set(tr)
        in_four_not_in_six = sfr - ssx
        in_six_not_in_four = ssx - sfr
        in_tree_not_in_six = str_ - ssx
        in_six_not_in_tree = ssx - str_
        in_six2_not_in_six = ssx2 - ssx
        in_six_not_in_six2 = ssx - ssx2

        print(len(in_four_not_in_six), len(in_six_not_in_four),
              len(in_tree_not_in_six), len(in_six_not_in_tree),
              len(in_six2_not_in_six), len(in_six_not_in_six2),
        )
        tr_struct_abrv = {}
        for abrv, ((struct, *extra), _, parent) in tr.items():
            tr_struct_abrv[struct] = abrv
            if abrv in sx:
                #print(abrv, struct, parent)
                if struct and struct not in sx[abrv][0]:
                    print(f'Found new label from tr for {abrv}:\n{struct}\n{sx[abrv][0]}\n')

        # can't run these for tr yet
        #reduced = set(tr_struct_abrv.values())
        #print(sorted(_ for _ in tr if _ not in reduced))
        #assert len(tr_struct_abrv) == len(tr), 'mapping between abrvs and structs is not 1:1 for tr'

        sx2_struct_abrv = {}
        for abrv, ((struct, *extra), _) in sx2.items():
            sx2_struct_abrv[struct] = abrv
            if abrv in sx:
                if struct and struct not in sx[abrv][0]:
                    print(f'Found new label from sx2 for {abrv}:\n{struct}\n{sx[abrv][0]}\n')

        reduced = set(sx2_struct_abrv.values())
        print(sorted(_ for _ in reduced if _ not in sx2))  # ah inconsistent scoping rules in class defs...
        assert len(sx2_struct_abrv) == len(sx2), 'there is a duplicate struct'

        sx_struct_abrv = {}
        for abrv, ((struct, *extra), _) in sx.items():
            sx_struct_abrv[struct] = abrv

        reduced = set(sx_struct_abrv.values())
        print(sorted(_ for _ in reduced if _ not in sx))
        assert len(sx_struct_abrv) == len(sx), 'there is a duplicate struct'

        # TODO test whether any of the tree members that were are going to exclude have children that we are going to include

        names_match_not_abbervs = {}

        tree_no_name = {_:tr[_] for _ in sorted(in_tree_not_in_six) if not tr[_][0][0]}
        tree_with_name = {_:tr[_] for _ in sorted(in_tree_not_in_six) if tr[_][0][0]}
        not_in_tree_with_figures = {_:sx[_] for _ in sorted(in_six_not_in_tree) if sx[_][-1]}
        a = f'{"abv":<25} | {"structure name":<60} | parent abv\n' + '\n'.join(f'{k:<25} | {v[0][0]:<60} | {v[-1]}' for k, v in tree_with_name.items())
        b = f'{"abv":<25} | {"structure name":<15} | parent abv\n' + '\n'.join(f'{k:<25} | {"":<15} | {v[-1]}' for k, v in tree_no_name.items())
        c = f'abv    | {"structure name":<60} | figures (figure ranges are tuples)\n' + '\n'.join(f'{k:<6} | {v[0][0]:<60} | {v[-1]}' for k, v in not_in_tree_with_figures.items())
        with open(os.path.expanduser('~/ni/dev/nifstd/paxinos/tree-with-name.txt'), 'wt') as f: f.write(a)
        with open(os.path.expanduser('~/ni/dev/nifstd/paxinos/tree-no-name.txt'), 'wt') as f: f.write(b)
        with open(os.path.expanduser('~/ni/dev/nifstd/paxinos/not-in-tree-with-figures.txt'), 'wt') as f: f.write(c)
        #match_name_not_abrev = set(v[0][0] for v in tree_with_name.values()) & set(v[0][0] for v in sx.values())

        _match_name_not_abrev = {}
        for a, (alts, (s, *extra), f, *_) in PaxRatLabels().records()[0].items():
            if s not in _match_name_not_abrev:
                _match_name_not_abrev[s] = [a]
            elif a not in _match_name_not_abrev[s]:
                _match_name_not_abrev[s].append(a)

        match_name_not_abrev = {k:v for k, v in _match_name_not_abrev.items() if len(v) > 1}

        abrv_match_not_name = {k:v[0] for k, v in PaxRatLabels().records()[0].items() if len(v[0]) > 1}
        _ = [print(k, *v[0]) for k, v in PaxRatLabels().records()[0].items() if len(v[0]) > 1]
        breakpoint()

        #self.in_tree_not_in_six = in_tree_not_in_six  # need for skipping things that were not actually named by paxinos


class PaxRecord:
    # TODO collisions
    def __init__(self, source, abbreviation, structure, artifacts,
                 figures=tuple(),
                 synonyms=tuple(),
                 altAbbrevs=tuple()):
        self.source = source
        self.abbreviation = abbreviation
        self.structure = structure
        self.artifacts = artifacts

    def __iter__(self):
        pass

    def __hash__(self):
        return hash(self.abbreviation)


class PaxRegion(RegionsBase):
    __pythonOnly = True  # TODO
    path = 'ttl/generated/parcellation/'
    filename = 'paxinos-rat-regions'
    name = 'Paxinos & Watson Rat Parcellation Regions'
    shortname = 'paxratr'
    comment = ('Intersection between labels and atlases for all regions '
               'delineated using Paxinos and Watson\'s methodology.')

    prefixes = {**makePrefixes('NIFRID', 'ilxtr', 'prov', 'ILXREPLACE')}
    # sources need to go in the order with which we want the labels to take precedence (ie in this case 6e > 4e)
    #sources = PaxSrAr_6(), PaxSr_6(), PaxSrAr_4(), PaxTree_6()  # tree has been successfully used for crossreferencing, additional terms need to be left out at the moment (see in_tree_not_in_six)
    root = RegionRoot(iri=TEMP['FIXME'],  # FIXME these should probably be EquivalentTo Parcellation Region HasLabel some label HasAtlas some atlas...
                      label='Paxinos rat parcellation region root',
                      shortname=shortname,
    )
    # atlas version
    # label identifier
    # figures

    things = {}

    @classmethod
    def addthing(cls, thing, value):
        cls.things[thing] = value
