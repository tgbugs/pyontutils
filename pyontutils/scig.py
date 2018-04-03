#!/usr/bin/env python3.6
"""Look look up ontology terms on the command line.

Usage:
    scig v [--local --verbose --key=KEY] <id>...
    scig i [--local --verbose --key=KEY] <id>...
    scig t [--local --verbose --limit=LIMIT --key=KEY] <term>...
    scig s [--local --verbose --limit=LIMIT --key=KEY] <term>...
    scig g [--local --verbose --rt=RELTYPE --key=KEY] <id>...
    scig e [--local --verbose --key=KEY] <p> <s> <o>
    scig c [--local --verbose --key=KEY]
    scig cy <query>

Options:
    -l --local          hit the local scigraph server
    -v --verbose        print the full uri
    -t --limit=LIMIT    limit number of results [default: 10]
    -k --key=KEY        api key

"""
from docopt import docopt
from pyontutils.scigraph import *
from pyontutils.core import PREFIXES


class scigPrint:

    _shorten_ = {
        'PR':'http://purl.obolibrary.org/obo/PR_',
        'RO':'http://purl.obolibrary.org/obo/RO_',
        'dc':'http://purl.org/dc/elements/1.1/',
        'BFO':'http://purl.obolibrary.org/obo/BFO_',
        'owl':'http://www.w3.org/2002/07/owl#',
        'rdfs':'http://www.w3.org/2000/01/rdf-schema#',
        'skos':'http://www.w3.org/2004/02/skos/core#',
        'NIFGA':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-GrossAnatomy.owl#',
        'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
        'oboInOwl':'http://www.geneontology.org/formats/oboInOwl#',
        'NIFSTD':'http://uri.neuinfo.org/nif/nifstd/',
        'NLX':'http://uri.neuinfo.org/nif/nifstd/nlx_',
        'SAO':'http://uri.neuinfo.org/nif/nifstd/sao',
        'BIRNLEX':'http://uri.neuinfo.org/nif/nifstd/birnlex_',
        'NIFRID':'http://uri.neuinfo.org/nif/nifstd/readable/',
        'NIFSUB':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Subcellular.owl#',
        'ro':'http://www.obofoundry.org/ro/ro.owl#',
        'UBERON':'http://purl.obolibrary.org/obo/UBERON_',
        'BIRNANN':'http://ontology.neuinfo.org/NIF/Backend/BIRNLex_annotation_properties.owl#',
        'NCBITaxon':'http://purl.obolibrary.org/obo/NCBITaxon_',
        'BRAINInfo':'http://braininfo.rprc.washington.edu/centraldirectory.aspx?ID=',
        'PMID':'http://www.ncbi.nlm.nih.gov/pubmed/',
    }
    _shorten_.update(PREFIXES)

    shorten = {v:k for k, v in _shorten_.items()}

    @staticmethod
    def wrap(string, start, ind, wrap_=80):
        if len(string) + start <= wrap_:
            return string
        else:
            out = ''
            ends = [_ for _ in range(wrap_ - start, len(string), wrap_ - ind - 4)] + [None]
            starts = [0] + [e for e in ends]
            blocks = [string[s:e] if e else string[s:] for s, e in zip(starts, ends)]
            return ('\n' + ' ' * (ind + 4)).join(blocks)

    @staticmethod
    def sv(asdf, start, ind):
        if type(asdf) is not bool and asdf.startswith('http'):
            for iri, short in scigPrint.shorten.items():
                if iri in asdf:
                    return scigPrint.wrap(asdf.replace(iri, short + ':'), start, ind)
            print('YOU HAVE FAILED!?', asdf)
            return scigPrint.wrap(repr(asdf), start, ind)
        else:
            return scigPrint.wrap(repr(asdf), start, ind)

    @staticmethod
    def pprint_node(node):
        nodes = node['nodes']
        if not nodes:
            return  # no node... probably put a None into SciGraph
        else:
            node = nodes[0]  # no edges here...
        print('---------------------------------------------------')
        print(node['id'], '  ', node['lbl'])
        print()
        scigPrint.pprint_meta(node['meta'])
        print('---------------------------------------------------')

    @staticmethod
    def pprint_meta(meta):
        for k, v in sorted(meta.items()):
            if k in ('curie', 'iri'):
                continue
            for iri, short in scigPrint.shorten.items():
                if iri in k:
                    k = k.replace(iri, short + ':')
                    break
            if v is not None:
                base = ' ' * 4 + '%s:' % k
                if hasattr(v, '__iter__'):
                    if len(v) > 1:
                        print(base, '[')
                        _ = [print(' ' * 8 + scigPrint.sv(_, 8, 8)) for _ in v]
                        print(' ' * 4 + ']')
                    elif len(v) == 1:
                        asdf = v[0]
                        print(base, scigPrint.sv(asdf, len(base) + 1, 4))
                    else:
                        pass
                else:
                    print(base, scigPrint.sv(v, len(base) + 1, 4))

    @staticmethod
    def pprint_edge(edge):
        def fix(value):
            for iri, short in scigPrint.shorten.items():
                if iri in value:
                    return value.replace(iri, short + ':')
            return value

        e = {k:fix(v) for k, v in edge.items()}
        print('({pred} {sub} {obj}) ; {meta}'.format(**e))

    @staticmethod
    def pprint_neighbors(result):
        print('\tnodes')
        for node in sorted(result['nodes'], key = lambda n: n['id']):
            scigPrint.pprint_node({'nodes':[node]})
        print('\tedges')
        for edge in sorted(result['edges'], key = lambda e: e['pred']):
            scigPrint.pprint_edge(edge)


def main():
    args = docopt(__doc__, version='scig 0')
    #print(args)
    server = None
    api_key = args['--key']
    verbose = False
    if args['--local']:
        server = 'http://localhost:9000/scigraph'
    if args['--verbose']:
        verbose = True


    if args['i'] or args['v']:
        v = Vocabulary(server, verbose) if server else Vocabulary(verbose=verbose, key=api_key)
        for id_ in args['<id>']:
            out = v.findById(id_)
            if out:
                print(id_,)
                for key, value in sorted(out.items()):
                    print('\t%s:' % key, value)
    elif args['s'] or args['t']:
        v = Vocabulary(server, verbose, key=api_key) if server else Vocabulary(verbose=verbose, key=api_key)
        for term in args['<term>']:
            print(term)
            limit = args['--limit']
            out = v.searchByTerm(term, limit=limit) if args['s'] else v.findByTerm(term, limit=limit)
            if out:
                for resp in sorted(out, key=lambda t: t['labels'][0] if t['labels'] else 'zzzzzzzzz'):
                    try:
                        curie = resp.pop('curie')
                    except KeyError:
                        curie = resp.pop('iri')  # GRRRRRRRRRRRRRR
                    print('\t%s' % curie)
                    for key, value in sorted(resp.items()):
                        print('\t\t%s:' % key, value)
                print()
    elif args['g']:
        g = Graph(server, verbose, key=api_key) if server else Graph(verbose=verbose, key=api_key)
        for id_ in args['<id>']:
            out = g.getNeighbors(id_, relationshipType=args['--rt'])
            if out:
                print(id_,)
                scigPrint.pprint_neighbors(out)
    elif args['e']:
        v = Vocabulary(server, verbose, key=api_key) if server else Vocabulary(verbose=verbose, key=api_key)
        p, s, o = args['<p>'], args['<s>'], args['<o>']
        if ':' in p:
            p = v.findById(p)['labels'][0]
        if ':' in s:
            s = v.findById(s)['labels'][0]
        if ':' in o:
            o = v.findById(o)['labels'][0]
        print('(%s %s %s)' % tuple([_.replace(' ', '-') for _ in (p, s, o)]))
    elif args['c']:
        c = Cypher(server, verbose, key=api_key) if server else Cypher(verbose=verbose, key=api_key)
        curies = c.getCuries()
        align = max([len(c) for c in curies]) + 2
        fmt = '{: <%s}' % align
        for curie, iri in sorted(curies.items()):
            print(fmt.format(repr(curie)), repr(iri))
    elif args['cy']:
        c = Cypher(server, verbose, key=api_key) if server else Cypher(verbose=verbose, key=api_key)
        out = c.execute(args['<query>'], 10)
        if out:
            out = '\n'.join([_.strip() for _ in out.split('|')[3:-1]])
            print(out)
        else:
            print('Error?')

if __name__ == '__main__':
    main()
