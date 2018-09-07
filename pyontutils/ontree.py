#!/usr/bin/env python3.6
"""Render a tree from a predicate root pair.
Normally run as a web service.

Usage:
    ontree server [options]
    ontree [options] <predicate-curie> <root-curie>
    ontree --test

Options:
    -a --api=API            SciGraph api endpoint
    -k --key=APIKEY         apikey for SciGraph instance
    -f --input-file=FILE    don't use SciGraph, load an individual file instead
    -o --outgoing           if not specified defaults to incoming
    -b --both               if specified goes in both directions
    -t --test               run tests
    -v --verbose            print extra information

"""

import os
import re
import subprocess
from ast import literal_eval
from pathlib import Path
from datetime import datetime
from urllib.error import HTTPError
import rdflib
from flask import Flask, url_for, redirect, request, render_template, render_template_string, make_response, abort
from docopt import docopt, parse_defaults
from pyontutils import scigraph
from pyontutils.core import makeGraph, qname, OntId
from pyontutils.utils import getSourceLine
from pyontutils.ontload import import_tree
from pyontutils.htmlfun import htmldoc, titletag, atag
from pyontutils.hierarchies import Query, creatTree, dematerialize
from IPython import embed

sgg = scigraph.Graph(cache=False, verbose=True)
sgv = scigraph.Vocabulary(cache=False, verbose=True)
sgc = scigraph.Cypher(cache=False, verbose=True)

a = 'rdfs:subClassOf'
_hpp = 'RO_OLD:has_proper_part'  # and apparently this fails too
hpp = 'http://www.obofoundry.org/ro/ro.owl#has_proper_part'
hpp = 'NIFRID:has_proper_part'
po = 'BFO:0000050'  # how?! WHY does this fail!? the curie is there!
_po = 'http://purl.obolibrary.org/obo/BFO_0000050'
hr = 'RO:0000087'
_hr = 'http://purl.obolibrary.org/obo/RO_0000087'

inc = 'INCOMING'
out = 'OUTGOING'
both = 'BOTH'


def fix_quotes(string, s1=':["', s2='"],'):
    out = []
    def subsplit(sstr, s=s2):
        #print(s)
        if s == '",' and sstr.endswith('"}'):  # special case for end of record
            s = '"}'
        if s:
            string, *rest = sstr.rsplit(s, 1)
        else:
            string = sstr
            rest = '',

        if rest:
            #print('>>>>', string)
            #print('>>>>', rest)
            r, = rest
            if s == '"],':
                fixed_string = fix_quotes(string, '","', '') + s + r
            else:
                fixed_string = string.replace('"', r'\"') + s + r

            return fixed_string

    for sub1 in string.split(s1):
        ss = subsplit(sub1)
        if ss is None:
            if s1 == ':["':
                out.append(fix_quotes(sub1, ':"', '",'))
            else:
                out.append(sub1)
        else:
            out.append(ss)

    return s1.join(out)


def fix_cypher(record):
    rep = re.sub(r'({|, )(\S+)(: "|: \[)', r'\1"\2"\3',
                 fix_quotes(record.strip()).
                 split(']', 1)[1] .
                 replace(':"', ': "') .
                 replace(':[', ': [') .
                 replace('",', '", ') .
                 replace('"],', '"], ') .
                 replace('\n', '\\n') .
                 replace('xml:lang="en"', r'xml:lang=\"en\"')
                )
    try:
        value = {qname(k):v for k, v in literal_eval(rep).items()}
    except (ValueError, SyntaxError) as e:
        print(repr(record))
        print(repr(rep))
        raise e

    return value


def cypher_query(sgc, query, limit):
    out = sgc.execute(query, limit)
    rows = []
    if out:
        for raw in out.split('|')[3:-1]:
            record = raw.strip()
            if record:
                d = fix_cypher(record)
                rows.append(d)

    return rows


class ImportChain:
    def __init__(self, sgg=sgg, sgc=sgc, wasGeneratedBy='FIXME#L{line}'):
        self.sgg = sgg
        self.sgc = sgc
        self.wasGeneratedBy = wasGeneratedBy

    def get_scigraph_onts(self):
        self.results = cypher_query(self.sgc, 'MATCH (n:Ontology) RETURN n', 1000)
        return self.results

    def get_itrips(self):
        results = self.get_scigraph_onts()
        iris = sorted(set(r['iri'] for r in results))
        nodes = [(i, self.sgg.getNeighbors(i, relationshipType='isDefinedBy',
                                           direction='OUTGOING'))
                 for i in iris]
        imports = [(i, *[(e['obj'], 'owl:imports', e['sub'])
                         for e in n['edges']])
                   for i, n in nodes if n]                               
        self.itrips = sorted(set(tuple(rdflib.URIRef(OntId(e).iri) for e in t)
                                 for i, *ts in imports if ts for t in ts))
        return self.itrips

    def make_import_chain(self, ontology='nif.ttl'):
        itrips = self.get_itrips()
        ontologies = ontology,  # hack around bad code in ontload
        import_graph = rdflib.Graph()
        [import_graph.add(t) for t in itrips]

        line = getSourceLine(self.__class__)
        wgb = self.wasGeneratedBy.format(line=line)
        prov = makeProv('owl:imports', 'NIFTTL:nif.ttl', wgb)
        self.tree, self.extra = next(import_tree(import_graph, ontologies, html_head=prov))
        return self.tree, self.extra

    def write_import_chain(self, location='/tmp/'):
        tree, extra  = self.make_import_chain()
        self.name = Path(next(iter(tree.keys()))).name
        self.path = Path(location, f'{self.name}-import-closure.html')
        with open(self.path.as_posix(), 'wt') as f:
            f.write(extra.html.replace('NIFTTL:', ''))  # much more readable


def graphFromGithub(link, verbose=False):
    # mmmm no validation
    # also caching probably
    if verbose:
        print(link)
    return makeGraph('', graph=rdflib.Graph().parse(f'{link}?raw=true', format='turtle'))

def makeProv(pred, root, wgb):
    return [titletag(f'Transitive closure of {root} under {pred}'),
            f'<meta name="date" content="{datetime.utcnow().isoformat()}">',
            f'<link rel="http://www.w3.org/ns/prov#wasGeneratedBy" href="{wgb}">']

def render(pred, root, direction=None, depth=10, local_filepath=None, branch='master', restriction=False, wgb='FIXME', local=False, verbose=False):
    kwargs = {'local':local, 'verbose':verbose}
    prov = makeProv(pred, root, wgb)
    if local_filepath is not None:
        github_link = f'https://github.com/SciCrunch/NIF-Ontology/raw/{branch}/{local_filepath}'
        prov.append(f'<link rel="http://www.w3.org/ns/prov#wasDerivedFrom" href="{github_link}">')
        g = graphFromGithub(github_link, verbose)
        if pred == 'subClassOf':
            pred = 'rdfs:subClassOf'  # FIXME qname properly?
        try:
            kwargs['json'] = g.make_scigraph_json(pred, direct=not restriction)
            kwargs['prefixes'] = {k:str(v) for k, v in g.namespaces.items()}
        except KeyError as e:
            if verbose:
                print(e)
            return abort(422, 'Unknown predicate.')
    else:
        kwargs['graph'] = sgg
        versionIRI = [e['obj'] for e in sgg.getNeighbors('http://ontology.neuinfo.org/NIF/ttl/nif.ttl')['edges'] if e['pred'] == 'versionIRI'][0]
        #print(versionIRI)
        prov.append(f'<link rel="http://www.w3.org/ns/prov#wasDerivedFrom" href="{versionIRI}">')  # FIXME wrong and wont resolve
        prov.append('<meta name="representation" content="SciGraph">')  # FIXME :/
    kwargs['html_head'] = prov
    try:
        if root.startswith('http'):  # FIXME this codepath is completely busted?
            if 'prefixes' in kwargs:
                rec = None
                for k, v in kwargs.items():
                    if root.startswith(v):
                        rec = k + 'r:' + root.strip(v)  # FIXME what?!
                        break
                if rec is None:
                    raise KeyError('no prefix found for {root}')
            else:
                rec = sgv.findById(root)
            if 'curie' in rec:
                root = rec['curie']
        tree, extras = creatTree(*Query(root, pred, direction, depth), **kwargs)
        dematerialize(list(tree.keys())[0], tree)
        return extras.html
    except (KeyError, TypeError) as e:
        if verbose:
            print(e)
        if sgg.getNode(root):
            message = 'Unknown predicate or no results.'  # FIXME distinguish these cases...
        elif 'json' in kwargs:
            message = 'Unknown root.'
            r = g.expand(root) 
            for s in g.g.subjects():
                if r == s: 
                    message = "No results. You are querying a ttl file directly, did you remember to set ?restriction=true?"
                    break
        else:
            message = 'Unknown root.'

        return abort(422, message)

class fakeRequest:
    args = {}

def getArgs(request):
    want = {'direction':inc,  # INCOMING OUTGOING BOTH
            'depth':10,
            'branch':'master',
            'restriction':False,  # True False
            'local':False,  # True False  # canonoical vs scigraph ? interlex?
           }

    def convert(k):
        if k in request.args:
            v = request.args[k]
        else:
            return want[k]

        if isinstance(want[k], bool):
            if v.lower() == 'true':
                return True
            elif v.lower() == 'false':
                return False
            else:
                raise TypeError(f'Expected a bool, got "{v}" instead.')
        elif isinstance(want[k], int):
            try:
                return int(v)
            except (TypeError, ValueError) as e:
                raise TypeError(f'Expected an int, got "{v}" instead.') from e
        else:
            return v


    return {k:convert(k)
            for k, v in want.items()}

def sanitize(pred, kwargs):
    if pred == 'isDefinedBy' and kwargs['depth'] > 1:
        return abort(400, 'isDefinedBy not allowed for queries with depth > 1.')

examples = (
    ('Brain parts', hpp, 'UBERON:0000955', '?direction=OUTGOING'),  # FIXME direction=lol doesn't cause issues...
    ('Brain parts alt', po, 'UBERON:0000955'),
    ('Anatomical entities', a, 'UBERON:0001062'),
    ('Cell parts', a, 'GO:0044464'),
    ('Cells', a, 'SAO:1813327414'),
    ('Proteins', a, 'SAO:26622963'),
    ('GPCRs', a, 'NIFEXT:5012'),
    ('Mulitmeric ion channels', a, 'NIFEXT:2502'),
    ('Monomeric ion channels', a, 'NIFEXT:2500'),
    ('Diseases', a, 'DOID:4'),
    ('Vertebrata', a, 'NCBITaxon:7742', '?depth=40'),
    ('Metazoa', a, 'NCBITaxon:33208', '?depth=40'),
    ('Rodentia', a, 'NCBITaxon:9989'),
    ('Insecta', a, 'NCBITaxon:50557', '?depth=40'),
    ('Neurotransmitters', hr, 'CHEBI:25512'),
    ('Neurotransmitters', a, 'NLXMOL:100306'),
    ('IRIs ok for roots', a, 'http://uri.neuinfo.org/nif/nifstd/nlx_mol_100306'),
    ('Provenance', 'isDefinedBy',
     'http://ontology.neuinfo.org/NIF/ttl/generated/chebislim.ttl', '?depth=1'),
)

extra_examples = (
    ('Old NIFGA part of', hpp, 'BIRNLEX:796'),
    ('Cereberal cortex parts', po, 'UBERON:0002749'),
)

file_examples = (
    ('Resources', a, 'NLXRES:20090101', 'ttl/resources.ttl'),
    ('Staging branch', a, 'PAXRAT:',
     'ttl/generated/parcellation/paxinos-rat-labels.ttl', '?branch=staging'),
    ('Restriction example', hpp, 'UBERON:0000955',
     'ttl/bridge/uberon-bridge.ttl', '?direction=OUTGOING&restriction=true'),
)

def server(api_key=None, verbose=False):
    f = os.path.realpath(__file__)
    __file__name = os.path.basename(f)
    __file__path = os.path.dirname(f)
    try:
        commit = subprocess.check_output(['git', '-c', f'{__file__path}', 'rev-parse', 'HEAD']).decode().rstrip()
    except subprocess.CalledProcessError:
        commit = 'master' # 'NO-REPO-AT-MOST-TODO-GET-LATEST-HASH'
    wasGeneratedBy = ('https://github.com/tgbugs/pyontutils/blob/'
                      f'{commit}/pyontutils/{__file__name}'
                      '#L{line}')
    line = getSourceLine(render)
    wgb = wasGeneratedBy.format(line=line)

    importchain = ImportChain(wasGeneratedBy=wasGeneratedBy)
    importchain.make_import_chain()  # run this once, restart services on a new release

    app = Flask('ontology tree service')
    basename = 'trees'

    @app.route(f'/{basename}', methods=['GET'])
    @app.route(f'/{basename}/', methods=['GET'])
    def route_():
        d = url_for('route_docs')
        e = url_for('route_examples')
        i = url_for('route_import_chain')
        return htmldoc(atag(d, 'Docs'),
                       '<br>',
                       atag(e, 'Examples'),
                       '<br>',
                       atag(i, 'Import chain'),
                       title='NIF ontology hierarchies')

    @app.route(f'/{basename}/docs', methods=['GET'])
    def route_docs():
        return redirect('https://github.com/SciCrunch/NIF-Ontology/blob/master/docs')  # TODO

    @app.route(f'/{basename}/examples', methods=['GET'])
    def route_examples():
        links = '\n'.join((f'<tr><td>{name}</td>\n<td><a href="{url_for("route_query", pred=pred, root=root)}{args[0] if args else ""}">'
                           f'../query/{pred}/{root}{args[0] if args else ""}</a></td></tr>')
                          for name, pred, root, *args in examples)
        flinks = '\n'.join((f'<tr><td>{name}</td>\n<td><a href="{url_for("route_filequery", pred=pred, root=root, file=file)}{args[0] if args else ""}">'
                            f'../query/{pred}/{root}/{file}{args[0] if args else ""}</a></td></tr>')
                           for name, pred, root, file, *args in file_examples)
        return htmldoc(('<table><tr><th align="left">Root class</th><th align="left">'
                        '../query/{predicate-curie}/{root-curie}?direction=INCOMING&depth=10&branch=master&local=false</th></tr>'
                        f'{links}</table>'
                        '<table><tr><th align="left">Root class</th><th align="left">'
                        '../query/{predicate-curie}/{root-curie}/{ontology-filepath}?direction=INCOMING&depth=10&branch=master&restriction=false</th></tr>'
                        f'{flinks}</table>'),
                       title='Example hierarchy queries'
        )

    @app.route(f'/{basename}/imports/chain', methods=['GET'])
    def route_import_chain():
        return importchain.extra.html

    @app.route(f'/{basename}/query/<pred>/<root>', methods=['GET'])
    def route_query(pred, root):
        kwargs = getArgs(request)
        kwargs['wgb'] = wgb
        maybe_abort = sanitize(pred, kwargs)
        if maybe_abort is not None:
            return maybe_abort
        if verbose:
            print(kwargs)
            kwargs['verbose'] = verbose
        return render(pred, root, **kwargs)

    @app.route(f'/{basename}/query/<pred>/http:/<path:iri>', methods=['GET'])  # one / due to nginx
    @app.route(f'/{basename}/query/<pred>/https:/<path:iri>', methods=['GET'])  # just in case
    def route_iriquery(pred, iri):  # TODO maybe in the future
        root = 'http://' + iri  # for now we have to normalize down can check request in future
        if verbose:
            print('ROOOOT', root)
        kwargs = getArgs(request)
        kwargs['wgb'] = wgb
        maybe_abort = sanitize(pred, kwargs)
        if maybe_abort is not None:
            return maybe_abort
        if verbose:
            print(kwargs)
        return render(pred, root, **kwargs)

    @app.route(f'/{basename}/query/<pred>/<root>/<path:file>', methods=['GET'])
    def route_filequery(pred, root, file):
        kwargs = getArgs(request)
        kwargs['local_filepath'] = file
        kwargs['wgb'] = wgb
        maybe_abort = sanitize(pred, kwargs)
        if maybe_abort is not None:
            return maybe_abort
        if verbose:
            print(kwargs)
        try:
            return render(pred, root, **kwargs)
        except HTTPError:
            return abort(404, 'Unknown ontology file.')  # TODO 'Unknown git branch.'

    return app

def test():
    global request
    request = fakeRequest()
    request.args['depth'] = 1
    app = server()
    (route_, route_docs, route_filequery, route_examples, route_iriquery,
     route_query) = (app.view_functions[k]
                     for k in ('route_', 'route_docs', 'route_filequery',
                               'route_examples', 'route_iriquery', 'route_query'))

    for _, predicate, root, *_ in examples + extra_examples:
        if root == 'UBERON:0001062':
            continue  # too big

        print('ontree testing', predicate, root)
        if root.startswith('http'):
            root = root.split('://')[-1]  # FIXME nginx behavior...
            resp = route_iriquery(predicate, root)
        else:
            resp = route_query(predicate, root)

    for _, predicate, root, file, *args in file_examples:
        print('ontree testing', predicate, root, file)
        if args and 'restriction' in args[0]:
            request.args['restriction'] = 'true'

        resp = route_filequery(predicate, root, file)

        if args and 'restriction' in args[0]:
            request.args.pop('restriction')

def main():
    from docopt import docopt
    args = docopt(__doc__, version='ontree 0.0.0')
    defaults = {o.name:o.value if o.argcount else None for o in parse_defaults(__doc__)}
    verbose = args['--verbose']
    sgg._verbose = verbose
    sgv._verbose = verbose
    sgc._verbose = verbose

    if args['--test']:
        test()
    elif args['server']:
        api = args['--api']
        if api is not None:
            scigraph.scigraph_client.BASEPATH = api
            sgg._basePath = api
            sgv._basePath = api
        api_key = args['--key']
        if api_key:
            sgg.api_key = api_key
            sgv.api_key = api_key
            sgc.api_key = api_key
        app = server(verbose=verbose)
        app.debug = False
        app.run(host='localhost', port=8000, threaded=True)  # nginxwoo
        # FIXME pypy3 has some serious issues yielding when threaded=True, gil issues?
        os.sys.exit()
    else:
        direction = both if args['--both'] else out if args['--incoming'] else inc
        # TODO default direction table to match to expected query behavior based on rdf direction
        pred = args['<predicate-curie>']
        root = args['<root-curie>']
        render(pred, root, direction)

if __name__ == '__main__':
    main()
