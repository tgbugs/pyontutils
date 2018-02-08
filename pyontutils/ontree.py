#!/usr/bin/env python3.6
""" Render a tree from a predicate root pair.

Usage:
    ontree [options] <predicate-curie> <root-curie>
    ontree server [options]

Options:
    -k --key=APIKEY         apikey for SciGraph instance [default: None]
    -f --input-file=FILE    don't use SciGraph, load an individual file instead
    -o --outgoing           if not specified defaults to incoming
    -b --both               if specified goes in both directions

"""

import os
import subprocess
from datetime import datetime
from inspect import getsourcelines
from urllib.error import HTTPError
import rdflib
from docopt import docopt, parse_defaults
from flask import Flask, url_for, redirect, request, render_template, render_template_string, make_response, abort 
from pyontutils.hierarchies import Query, creatTree, dematerialize
from pyontutils.scigraph_client import Graph, Vocabulary
from pyontutils.core import makeGraph
from IPython import embed

sgg = Graph(cache=False, verbose=True)
sgv = Vocabulary(cache=False, verbose=True)

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

def graphFromGithub(link):
    # mmmm no validation
    # also caching probably
    print(link)
    return makeGraph('', graph=rdflib.Graph().parse(f'{link}?raw=true', format='turtle'))

def render(pred, root, direction=None, depth=10, local_filepath=None, branch='master', restriction=False, wgb='FIXME', local=False):
    kwargs = {'local':local}
    prov = [
            f'<title>Transitive closure of {root} under {pred}</title>'
            f'<meta name="date" content="{datetime.utcnow().isoformat()}">',
            f'<link rel="http://www.w3.org/ns/prov#wasGeneratedBy" href="{wgb}">']
    if local_filepath is not None:
        github_link = f'https://github.com/SciCrunch/NIF-Ontology/raw/{branch}/{local_filepath}'
        prov.append(f'<link rel="http://www.w3.org/ns/prov#wasDerivedFrom" href="{github_link}">')
        g = graphFromGithub(github_link)
        if pred == 'subClassOf':
            pred = 'rdfs:subClassOf'  # FIXME qname properly?
        try:
            kwargs['json'] = g.make_scigraph_json(pred, direct=not restriction)
        except KeyError as e:
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
        if root.startswith('http'):
            rec = sgv.findById(root)
            if 'curie' in rec:
                root = rec['curie']
        tree, extras = creatTree(*Query(root, pred, direction, depth), **kwargs)
        dematerialize(list(tree.keys())[0], tree)
        return extras.html
    except (KeyError, TypeError) as e:
        print(e)
        if sgg.getNode(root):
            message = 'Unknown predicate or no results.'  # FIXME distinguish these cases...
        else:
            message = 'Unknown root.'

        return abort(422, message)

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

def server(api_key=None):
    f = os.path.realpath(__file__)
    __file__name = os.path.basename(f)
    __file__path = os.path.dirname(f)
    try:
        commit = subprocess.check_output(['git', '-C', f'{__file__path}', 'rev-parse', 'HEAD']).decode().rstrip()
    except subprocess.CalledProcessError:
        commit = 'master' # 'NO-REPO-AT-MOST-TODO-GET-LATEST-HASH'
    wasGeneratedBy = ('https://github.com/tgbugs/pyontutils/blob/'
                      f'{commit}/pyontutils/{__file__name}'
                      '#L{line}')
    line = getsourcelines(render)[-1]
    wgb = wasGeneratedBy.format(line=line)

    app = Flask('ontology tree service')
    basename = 'trees'

    def link(href, value=None):
        if value is None:
            value = href
        return f'<a href="{href}">{value}</a>'

    @app.route(f'/{basename}', methods=['GET'])
    @app.route(f'/{basename}/', methods=['GET'])
    def route_():
        d = url_for('route_docs')
        e = url_for('route_examples')
        return ('<html><body>'
                f'{link(d, "Docs")}'
                '<br>'
                f'{link(e, "Examples")}'
                '</body><html>')

    @app.route(f'/{basename}/docs', methods=['GET'])
    def route_docs():
        return redirect('https://github.com/SciCrunch/NIF-Ontology/blob/master/docs')  # TODO

    @app.route(f'/{basename}/examples', methods=['GET'])
    def route_examples():
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
            ('Neurotransmitters', hr, 'CHEBI:25512'),
            ('Neurotransmitters', a, 'NLXMOL:100306'),
            ('IRIs ok for roots', a, 'http://uri.neuinfo.org/nif/nifstd/nlx_mol_100306'),
            ('Provenance', 'isDefinedBy',
             'http://ontology.neuinfo.org/NIF/ttl/generated/chebislim.ttl', '?depth=1'),
        )
        file_examples = (
            ('Resources', a, 'NLXRES:20090101', 'ttl/resources.ttl'),
            ('Parcellation branch', a, 'PAXRAT:0',
             'ttl/generated/parcellation/paxinos-rat-labels.ttl', '?branch=parcellation'),
            ('Restriction example', hpp, 'UBERON:0000955',
             'ttl/bridge/uberon-bridge.ttl', '?direction=OUTGOING&restriction=true'),
        )
        url = os.path.dirname(request.base_url)
        links = '\n'.join((f'<tr><td>{name}</td>\n<td><a href="{url}/query/{pred}/{root}{args[0] if args else ""}">'
                           f'../query/{pred}/{root}{args[0] if args else ""}</a></td></tr>')
                          for name, pred, root, *args in examples)
        flinks = '\n'.join((f'<tr><td>{name}</td>\n<td><a href="{url}/query/{pred}/{root}/{file}{args[0] if args else ""}">'
                            f'../query/{pred}/{root}/{file}{args[0] if args else ""}</a></td></tr>')
                           for name, pred, root, file, *args in file_examples)
        return ('<html>'
                '<body>'
                '<table><tr><th align="left">Root class</th><th align="left">'
                '../query/{predicate-curie}/{root-curie}?direction=INCOMING&depth=10&branch=master&local=false</th></tr>'
                f'{links}</table>'
                '<table><tr><th align="left">Root class</th><th align="left">'
                '../query/{predicate-curie}/{root-curie}/{ontology-filepath}?direction=INCOMING&depth=10&branch=master&restriction=false</th></tr>'
                f'{flinks}</table>'
                '</body>'
                '</html>')

    @app.route(f'/{basename}/query/<pred>/<root>', methods=['GET'])
    def route_query(pred, root):
        kwargs = getArgs(request)
        kwargs['wgb'] = wgb
        maybe_abort = sanitize(pred, kwargs)
        if maybe_abort is not None:
            return maybe_abort
        print(kwargs)
        return render(pred, root, **kwargs)

    @app.route(f'/{basename}/query/<pred>/http:/<path:iri>', methods=['GET'])
    @app.route(f'/{basename}/query/<pred>/https:/<path:iri>', methods=['GET'])  # just in case
    def route_iriquery(pred, iri):  # TODO maybe in the future
        root = 'http://' + iri  # for now we have to normalize down can check request in future
        print('ROOOOT', root)
        kwargs = getArgs(request)
        kwargs['wgb'] = wgb
        maybe_abort = sanitize(pred, kwargs)
        if maybe_abort is not None:
            return maybe_abort
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
        print(kwargs)
        try:
            return render(pred, root, **kwargs)
        except HTTPError:
            return abort(404, 'Unknown ontology file.')  # TODO 'Unknown git branch.'

    if api_key:
        sgg.api_key = api_key
    app.debug = False
    app.run(host='localhost', port=8000, threaded=True)  # nginxwoo
    # FIXME pypy3 has some serious issues yielding when threaded=True, gil issues?
    os.sys.exit()

def main():
    from docopt import docopt
    args = docopt(__doc__, version='ontree 0.0.0')
    defaults = {o.name:o.value if o.argcount else None for o in parse_defaults(__doc__)}

    if args['server']:
        k = args['--key']
        k = k if k != defaults['--key'] else None
        server(k)
    else:
        direction = both if args['--both'] else out if args['--incoming'] else inc
        # TODO default direction table to match to expected query behavior based on rdf direction
        pred = args['<predicate-curie>']
        root = args['<root-curie>']
        render(pred, root, direction)

if __name__ == '__main__':
    main()
