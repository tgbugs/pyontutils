""" update ontology definitions

Usage:
    defs [options]

Options:
    -u --update    push updates to google sheet
    -d --debug     enable various debug options

"""
import rdflib
from ttlser import natsort
from pyontutils import clifun as clif
from pyontutils.core import OntGraph
from pyontutils.sheets import Sheet
from pyontutils.config import auth
from pyontutils.namespaces import (
    ilxtr,
    NIFRID,
    rdf,
    rdfs,
    owl,
    definition,
    editorNote)


class Defs(Sheet):
    name = 'estim-terms'
    sheet_name = 'stimulation.ttl definitions'
    index_columns = 'id',


def exorcise(g, s, p, join=None):
    try:
        if join is not None:
            l = [o.toPython() for o in g[s:p]]
            if l:
                return join.join(l)
            else:
                return None
        else:
            o = next(g[s:p])

        if isinstance(o, rdflib.Literal):
            return o.toPython()
        elif isinstance(o, rdflib.URIRef):
            return g.qname(o)
        else:
            raise NotImplementedError(f'wat: {type(o)} {o}') 

    except StopIteration:
        return None


funs = [
    lambda g, s: exorcise(g, s, rdfs.domain),
    lambda g, s: exorcise(g, s, rdfs.range),
    lambda g, s: exorcise(g, s, rdfs.label),
    lambda g, s: exorcise(g, s, NIFRID.synonym, join='\n'),
    lambda g, s: exorcise(g, s, NIFRID.abbrev, join='\n'),
    lambda g, s: exorcise(g, s, definition),
    lambda g, s: exorcise(g, s, editorNote),
    lambda g, s: exorcise(g, s, rdfs.comment),
]


class Main(clif.Dispatcher):

    def default(self):
        g = OntGraph().parse(auth.get_path('ontology-local-repo') / 'ttl/stimulation.ttl')
        preds = sorted(set(g.qname(p) for p in g.predicates()))

        header = [
            ['id', 'rdf:type', 'rdfs:domain', 'rdfs:range',
             'rdfs:label', 'NIFRID:synonym', 'NIFRID:abbrev',
             'definition:', 'editorNote:', 'rdfs:comment']]

        _rows = []
        for type_ in (owl.ObjectProperty, owl.Class,):
            for s in sorted(g[:rdf.type:type_], key=natsort):
                if isinstance(s, rdflib.URIRef):
                    row = [g.qname(s), g.qname(type_)] + [fun(g, s) for fun in funs]
                    _rows.append(row)

        rows = header + _rows

        defs = Defs(readonly=not self.options.update)
        if self.options.update:
            defs.upsert(*rows)  # FIXME upsert broken on header reordering ?
            defs.commit()

        return rows


def main():
    options, *ad = clif.Options.setup(__doc__, version='estim-defs 0.0.0')
    main = Main(options)
    if main.options.debug:
        print(main.options)

    out = main()


if __name__ == '__main__':
    main()
