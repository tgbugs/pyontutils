#!/usr/bin/env python3
"""Render a tree from a predicate root pair.
Normally run as a web service.

Usage:
    ontree server [options]
    ontree [options] <predicate-curie> <root-curie>
    ontree --test

Options:
    -a --api=API            Full url to SciGraph api endpoint
       --data-api=DAPI      Full url to SciGraph data api endpoint
    -k --key=APIKEY         apikey for SciGraph instance
    -p --port=PORT          port on which to run the server [default: 8000]
    -f --input-file=FILE    don't use SciGraph, load an individual file instead
    -o --outgoing           if not specified defaults to incoming
    -b --both               if specified goes in both directions
    -t --test               run tests
    -v --verbose            print extra information

"""

import os
import asyncio
import subprocess
from pprint import pformat
from pathlib import Path
from datetime import datetime
from urllib.error import HTTPError
from urllib.parse import parse_qs
import htmlfn as hfn
from flask import (Flask,
                   url_for,
                   redirect,
                   request,
                   abort,
                   current_app,
                   send_from_directory)
from requests.exceptions import HTTPError as rHTTPError
from pyontutils import scigraph
from pyontutils.core import OntId, OntTerm, OntGraph
from pyontutils.scig import ImportChain, makeProv
from pyontutils.utils import getSourceLine, get_working_dir, makeSimpleLogger
from pyontutils.utils import Async, deferred, UTCNOWISO
from pyontutils.config import auth
from pyontutils.hierarchies import (Query,
                                    creatTree,
                                    dematerialize,
                                    flatten as flatten_tree)
from pyontutils.namespaces import rdfs, OntCuries
from pyontutils.scigraph_codegen import moduleDirect
from nifstd_tools.sheets_sparc import (hyperlink_tree,
                                       tag_row,
                                       open_custom_sparc_view_yml,
                                       YML_DELIMITER)
from nifstd_tools.simplify import simplify, apinat_deblob, cleanBad
from nifstd_tools import __version__

log = makeSimpleLogger('ontree')

# FIXME these will go to network which is :/
sgg = scigraph.Graph(cache=False, verbose=True)
sgv = scigraph.Vocabulary(cache=False, verbose=True)
sgc = scigraph.Cypher(cache=False, verbose=True)
sgd = scigraph.Dynamic(cache=False, verbose=True)

# This was for ttl creation extension for sparc view
# ixr.setup(instrumented=OntTerm)

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

uot =  (
    "UBERON:0000056",
    "UBERON:0000057",
    "UBERON:0000074",
    "UBERON:0001224",
    "UBERON:0001226",
    "UBERON:0001227",
    "UBERON:0001255",
    "UBERON:0001287",
    "UBERON:0001290",
    "UBERON:0001291",
    "UBERON:0001292",
    "UBERON:0004193",
    "UBERON:0004203",
    "UBERON:0004204",
    "UBERON:0004205",
    "UBERON:0004639",
    "UBERON:0004640",
    "UBERON:0005096",
    "UBERON:0005097",
    "UBERON:0005750",
    "UBERON:0005751",
    "UBERON:0009973",
    "UBERON:0012240",
    "UBERON:0012242",
)


def time():
    ''' Get current time in a year-month-day:meta format '''
    return str(datetime.utcnow().isoformat()).replace('.', ',')


def node_list(nodes):
    log.debug(pformat(nodes))
    # FIXME why the heck are these coming in as lbl now?!?!
    s = sorted([(n['lbl'], hfn.atag(n['id'], n['lbl'], new_tab=True))
                for n in nodes])
    return '<br>\n'.join([at for _, at in s])


def graphFromGithub(link, verbose=False):
    # mmmm no validation
    # also caching probably
    if verbose:
        log.info(link)

    g = OntGraph().parse(f'{link}?raw=true', format='turtle')
    OntCuries.populate(g)
    return g


collapse_apinat = [  # FIXME config?
    ['apinatomy:conveys', 'apinatomy:source'],
    ['apinatomy:conveys', 'apinatomy:target'],
    ['apinatomy:conveys', 'apinatomy:source',
     # FIXME if the final external is missing the rendering
     # halts at layerIn and doesn't show the subtree
     'apinatomy:internalIn', 'apinatomy:layerIn', 'apinatomy:external'],
    ['apinatomy:conveys', 'apinatomy:target',
     'apinatomy:internalIn', 'apinatomy:layerIn', 'apinatomy:external'],
    ['apinatomy:fasciculatesIn', 'apinatomy:external'],
    ['apinatomy:fasciculatesIn', 'apinatomy:layerIn', 'apinatomy:external'],
    ['apinatomy:fasciculatesIn', 'apinatomy:supertype', 'apinatomy:external'],
    ['apinatomy:fasciculatesIn', 'apinatomy:cloneOf', 'apinatomy:supertype', 'apinatomy:external'],
]


def sparc_dynamic(data_sgd, data_sgc, path, wgb, process=lambda coll, blob: blob):
    args = dict(request.args)
    if 'direction' in args:
        direction = args.pop('direction')
    else:
        direction = 'OUTGOING'  # should always be outgoing here since we can't specify?

    if 'format' in args:
        format_ = args.pop('format')
    else:
        format_ = None

    if 'apinat' in path:  # FIXME bad hardcoded hack
        _old_get = data_sgd._get
        try:
            data_sgd._get = data_sgd._normal_get
            j = data_sgd.dispatch(path, **args)
        except ValueError as e:
            log.exception(e)
            abort(404)
        except rHTTPError as e:
            log.exception(e)
            abort(e.response.status_code)  # DO NOT PASS ALONG THE MESSAGE
        finally:
            data_sgd._get = _old_get
    else:
        try:
            j = data_sgd.dispatch(path, **args)
        except rHTTPError as e:
            log.exception(e)
            abort(e.response.status_code)  # DO NOT PASS ALONG THE MESSAGE
        except ValueError as e:
            log.exception(e)
            abort(404)

    j = process(collapse_apinat, j)

    if j is None or 'edges' not in j:
        log.error(pformat(j))
        return abort(400)

    elif not j['edges']:
        return node_list(j['nodes'])  # FIXME ... really should error?

    if path.endswith('housing-lyphs'):  # FIXME hack
        root = 'NLX:154731'
        #direction = 'INCOMING'
    else:
        root = None

    prov = [
        hfn.titletag(f'Dynamic query result for {path}'),
        f'<meta name="date" content="{UTCNOWISO()}">',
        f'<link rel="http://www.w3.org/ns/prov#wasGeneratedBy" href="{wgb}">',
        '<meta name="representation" content="SciGraph">',
        ('<link rel="http://www.w3.org/ns/prov#wasDerivedFrom" '
         f'href="{data_sgd._last_url}">')]

    kwargs = {'json': cleanBad(j),
                'html_head': prov,
                'prefixes': data_sgc.getCuries(),  # FIXME efficiency
    }
    tree, extras = creatTree(*Query(root, None, direction, None), **kwargs)
    #print(extras.hierarhcy)
    #print(tree)
    if format_ is not None:
        if format_ == 'table':
            #breakpoint()
            def nowrap(class_, tag=''):
                return (f'{tag}.{class_}'
                        '{ white-space: nowrap; }')

            ots = [OntTerm(n)
                   for n in flatten_tree(extras.hierarchy)
                   if 'CYCLE' not in n]
            #rows = [[ot.label, ot.asId().atag(), ot.definition] for ot in ots]
            rows = [[ot.label, hfn.atag(ot.iri, ot.curie), ot.definition]
                    for ot in ots]

            return hfn.htmldoc(hfn.render_table(rows, 'label', 'curie', 'definition'),
                               styles=(hfn.table_style, nowrap('col-label', 'td')))

    return hfn.htmldoc(extras.html,
                       other=prov,
                       styles=hfn.tree_styles)


def render(pred, root, direction=None, depth=10, local_filepath=None,
           branch='master', restriction=False, wgb='FIXME', local=False,
           verbose=False, flatten=False,):

    kwargs = {'local':local, 'verbose':verbose}
    prov = makeProv(pred, root, wgb)
    if local_filepath is not None:
        github_link = ('https://github.com/SciCrunch/NIF-Ontology/raw/'
                       f'{branch}/{local_filepath}')
        prov.append('<link rel="http://www.w3.org/ns/prov#wasDerivedFrom" '
                    f'href="{github_link}">')
        graph = graphFromGithub(github_link, verbose)
        qname = graph.namespace_manager._qhrm  # FIXME
        labels_index = {qname(s):str(o) for s, o in graph[:rdfs.label:]}
        if pred == 'subClassOf':
            pred = 'rdfs:subClassOf'  # FIXME qname properly?
        elif pred == 'subPropertyOf':
            pred = 'rdfs:subPropertyOf'
        try:
            kwargs['json'] = graph.asOboGraph(pred, restriction=restriction)
            kwargs['prefixes'] = {k:str(v) for k, v in graph.namespace_manager}
        except KeyError as e:
            if verbose:
                log.error(str(e))
            return abort(422, 'Unknown predicate.')
    else:
        kwargs['graph'] = sgg
        # FIXME this does not work for a generic scigraph load ...
        # and it should not be calculated every time anyway!
        # oh look, here we are needed a class again
        if False:
            versionIRI = [
                e['obj']
                for e in sgg.getNeighbors('http://ontology.neuinfo.org/'
                                          'NIF/ttl/nif.ttl')['edges']
                if e['pred'] == 'versionIRI'][0]
            #print(versionIRI)
            prov.append('<link rel="http://www.w3.org/ns/prov#wasDerivedFrom" '
                        f'href="{versionIRI}">')  # FIXME wrong and wont resolve
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
                root_curie = rec['curie']
                # FIXME https://github.com/SciGraph/SciGraph/issues/268
                if not root_curie.endswith(':') and '/' not in root_curie:
                    root = root_curie
                else:
                    kwargs['curie'] = root_curie
        elif 'prefixes' not in kwargs and root.endswith(':'):
            kwargs['curie'] = root
            root = sgc._curies[root.rstrip(':')]  # also 268

        tree, extras = creatTree(*Query(root, pred, direction, depth), **kwargs)
        dematerialize(list(tree.keys())[0], tree)
        if flatten:
            if local_filepath is not None:
                def safe_find(n):
                    return {'labels':[labels_index[n]],
                            'deprecated': False  # FIXME inacurate
                           }

            else:
                def safe_find(n):  # FIXME scigraph bug
                    if n.endswith(':'):
                        n = sgc._curies[n.rstrip(':')]
                    elif '/' in n:
                        prefix, suffix = n.split(':')
                        iriprefix = sgc._curies[prefix]
                        n = iriprefix + suffix

                    return sgv.findById(n)

            out = set(n for n in flatten_tree(extras.hierarchy))

            try:
                lrecs = Async()(deferred(safe_find)(n) for n in out)
            except RuntimeError:
                asyncio.set_event_loop(current_app.config['loop'])
                lrecs = Async()(deferred(safe_find)(n) for n in out)

            rows = sorted(((r['labels'][0] if r['labels'] else '')
                           + ',' + n for r, n in zip(lrecs, out)
                           # FIXME still stuff wrong, but better for non cache case
                           if not r['deprecated']), key=lambda lid: lid.lower())
            return '\n'.join(rows), 200, {'Content-Type':'text/plain;charset=utf-8'}

        else:
            return hfn.htmldoc(extras.html,
                               other=prov,
                               styles=hfn.tree_styles)

    except (KeyError, TypeError) as e:
        if verbose:
            log.error(f'{type(e)} {e}')
        if sgg.getNode(root):
            # FIXME distinguish these cases...
            message = 'Unknown predicate or no results.'
        elif 'json' in kwargs:
            message = 'Unknown root.'
            r = graph.namespace_manager.expand(root)
            for s in graph.subjects():
                if r == s:
                    message = ('No results. '
                               'You are querying a ttl file directly, '
                               'did you remember to set ?restriction=true?')
                    break
        else:
            message = 'Unknown root.'

        return abort(422, message)


def getArgs(request):
    want = {'direction':inc,  # INCOMING OUTGOING BOTH
            'depth':10,
            'branch':'master',
            'restriction':False,  # True False
            'local':False,  # True False  # canonoical vs scigraph ? interlex?
            'flatten':False,
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
    ('Brain parts alt flat', po, 'UBERON:0000955', '?flatten=true'),
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
    ('No tech?', a, 'ilxtr:technique'),
    ('Cell septum', a, 'GO:0044457'),
    ('Old NIFGA part of', hpp, 'BIRNLEX:796'),
    ('Cereberal cortex parts', po, 'UBERON:0002749'),
    ('Broken iri of borken curie', a, 'http://uri.interlex.org/paxinos/uris/rat/labels/'),
    ('Broken curie', a, 'PAXRAT:'),
)

file_examples = (
    ('Resources', a, 'NLXRES:20090101', 'ttl/resources.ttl'),
    ('Staging branch', a, 'PAXRAT:',
     'ttl/generated/parcellation/paxinos-rat-labels.ttl', '?branch=staging'),
    ('Restriction example', hpp, 'UBERON:0000955',
     'ttl/bridge/uberon-bridge.ttl', '?direction=OUTGOING&restriction=true'),
)

dynamic_examples = (
    ('Shortest path', 'shortestSimple',
     '?start_id=UBERON:0000955&end_id=UBERON:0001062&relationship=subClassOf'),
    ('Shortest path table', 'shortestSimple',
     '?start_id=UBERON:0000955&end_id=UBERON:0001062&relationship=subClassOf&format=table'),
    ('Stomach parts', 'prod/sparc/organParts/FMA:7148', None),
    ('Parc graph', 'prod/sparc/parcellationGraph', '?direction=INCOMING'),
    ('Parc arts', 'prod/sparc/parcellationArtifacts/NCBITaxon:10116', '?direction=INCOMING'),
    ('Parc roots', 'prod/sparc/parcellationRoots/NCBITaxon:10116', '?direction=INCOMING'),
    ('Parc region roots', 'prod/sparc/parcellationRoots/NCBITaxon:10116/UBERON:0000955', '?direction=INCOMING'),
)

demo_examples = (
    #('All connectivity', '/trees/sparc/demos/isan2019/flatmap-queries'),  # broken due to scigraph segfault for json return
    ('Neuron connectivity', '/trees/sparc/demos/isan2019/neuron-connectivity'),
)

def server(api_key=None, verbose=False, data_endpoint=None):
    if data_endpoint:
        _dataBP = data_endpoint
        scigraphd = moduleDirect(_dataBP, 'scigraphd')
    else:
        from pyontutils import scigraph as scigraphd

    data_sgd = scigraphd.Dynamic(cache=True, verbose=True, do_error=True)
    data_sgc = scigraphd.Cypher(cache=True, verbose=True)

    if data_endpoint:
        data_sgd._basePath = _dataBP
        data_sgc._basePath = _dataBP

    f = Path(__file__).resolve()
    working_dir = get_working_dir(__file__)
    resources = auth.get_path('resources')
    if working_dir:
        git_dir = working_dir / '.git'
    else:
        git_dir = Path('/dev/null')

    try:
        if working_dir is not None:
            ref = subprocess.check_output(['git',
                                           '--git-dir', git_dir.as_posix(),
                                           '--work-tree', working_dir.as_posix(),
                                           'rev-parse', 'HEAD'],
                                          stderr=subprocess.DEVNULL).decode().rstrip()
        else:
            ver = __version__
            if '+' in ver:
                ref = ver.split('+', 1)[-1]
            else:
                ref = ver

    except subprocess.CalledProcessError:
        ref = 'master' # 'NO-REPO-AT-MOST-TODO-GET-LATEST-HASH'

    wasGeneratedBy = ('https://github.com/tgbugs/pyontutils/blob/'
                      f'{ref}/pyontutils/{f.name}'
                      '#L{line}')
    line = getSourceLine(render)
    wgb = wasGeneratedBy.format(line=line)

    importchain = ImportChain(sgg=sgg, sgc=sgc, wasGeneratedBy=wasGeneratedBy)
    importchain.make_html()  # run this once, restart services on a new release

    loop = asyncio.get_event_loop()
    app = Flask('ontology tree service')
    app.config['loop'] = loop

    # gsheets = GoogleSheets()
    sparc_view = open_custom_sparc_view_yml()
    # sparc_view_raw = open_custom_sparc_view_yml(False)

    log.info('starting index load')

    uot_terms = [OntTerm(t) for t in uot]
    uot_lookup = {t.label:t for t in uot_terms}
    uot_ordered = sorted(t.label for t in uot_terms)

    basename = 'trees'

    @app.route(f'/{basename}', methods=['GET'])
    @app.route(f'/{basename}/', methods=['GET'])
    def route_():
        d = url_for('route_docs')
        e = url_for('route_examples')
        i = url_for('route_import_chain')
        return hfn.htmldoc(hfn.atag(d, 'Docs'),
                       '<br>',
                       hfn.atag(e, 'Examples'),
                       '<br>',
                       hfn.atag(i, 'Import chain'),
                       title='NIF ontology hierarchies')

    @app.route(f'/{basename}/docs', methods=['GET'])
    def route_docs():
        return redirect('https://github.com/SciCrunch/NIF-Ontology/blob/master/docs')  # TODO

    @app.route(f'/{basename}/examples', methods=['GET'])
    def route_examples():
        links = hfn.render_table(
            [[name,
              hfn.atag(url_for("route_query", pred=pred, root=root) + (args[0] if args else ''),
                   f'../query/{pred}/{root}{args[0] if args else ""}')]
             for name, pred, root, *args in examples],
            'Root class',
            '../query/{predicate-curie}/{root-curie}?direction=INCOMING&depth=10&branch=master&local=false',
            halign='left')

        flinks = hfn.render_table(
            [[name,
              hfn.atag(url_for("route_filequery", pred=pred, root=root, file=file) + (args[0] if args else ''),
                       f'../query/{pred}/{root}/{file}{args[0] if args else ""}')]
             for name, pred, root, file, *args in file_examples],
            'Root class',
            '../query/{predicate-curie}/{root-curie}/{ontology-filepath}?direction=INCOMING&depth=10&branch=master&restriction=false',
            halign='left')

        dlinks = hfn.render_table(
            [[name,
              hfn.atag(url_for("route_dynamic", path=path) + (querystring if querystring else ''),
                       f'../query/dynamic/{path}{querystring if querystring else ""}')]
             for name, path, querystring in dynamic_examples],
            'Root class',
            '../query/dynamic/{path}?direction=OUTGOING&dynamic=query&args=here',
            halign='left')

        return hfn.htmldoc(links, flinks, dlinks, title='Example hierarchy queries')

    @app.route(f'/{basename}/sparc/demos/isan2019/neuron-connectivity', methods=['GET'])
    def route_sparc_demos_isan2019_neuron_connectivity():
        def connected(start):
            log.debug(start)
            blob = data_sgd.neurons_connectivity(start)#, limit=9999)
            edges = blob['edges']
            neurons = {}
            types = {}
            rows = []
            start_type = None
            sc = OntId(start).curie
            for e in edges:
                s, p, o = e['sub'], e['pred'], e['obj']
                if p == 'operand':
                    continue

                if s.startswith('_:'):
                    if s not in neurons:
                        neurons[s] = []
                        types[s] = {}
                otp = OntTerm(p)
                oto = OntTerm(o)
                neurons[s].append((otp, oto))
                if o == sc:
                    start_type = otp

                if oto not in types[s]:
                    types[s][oto] = []

                types[s][oto].append(otp)

            for v in neurons.values():
                v.sort()

            return OntTerm(start), start_type, neurons, types

        hrm = [connected(t) for t in set(test_terms)]
        header =['Start', 'Start Type', 'Neuron', 'Relation', 'Target']
        rows = []
        for start, start_type, neurons, types in sorted(hrm):
            start = start.atag()
            start_type = start_type.atag() if start_type is not None else ''
            for i, v in enumerate(neurons.values(), 1):
                neuron = i
                for p, o in v:
                    relation = p.atag()
                    target = o.atag()
                    row = start, start_type, neuron, relation, target
                    rows.append(row)

                rows.append(['|'] + [' '] * 4)

        h = hfn.htmldoc(hfn.render_table(rows, *header), title='neuron connectivity')
        return h

    @app.route(f'/{basename}/sparc/demos/isan2019/flatmap-queries', methods=['GET'])
    def route_sparc_demos_isan2019_flatmap_queries():
        # lift up to load from an external source at some point
        # from pyontutils.core import OntResPath
        # orp = OntResPath('annotations.ttl')
        # [i for i in sorted(set(OntId(e) for t in orp.graph for e in t)) if i.prefix in ('UBERON', 'FMA', 'ILX')]
        query = """
      MATCH (blank)-
      [entrytype:ilxtr:hasSomaLocatedIn|ilxtr:hasAxonLocatedIn|ilxtr:hasDendriteLocatedIn|ilxtr:hasPresynapticTerminalsIn]
      ->(location:Class{{iri: "{iri}"}})
      WITH entrytype, location, blank
      MATCH (phenotype)<-[predicate]-(blank)<-[:equivalentClass]-(neuron)
      WHERE NOT (phenotype.iri =~ ".*_:.*")
      RETURN location, entrytype.iri, neuron.iri, predicate.iri, phenotype
        """

        def fetch(iri, limit=10):
            q = query.format(iri=iri)
            log.debug(q)
            blob = data_sgc.execute(q, limit, 'application/json')
            # oh boy
            # if there are less results than the limit scigraph segfaults
            # and returns nothing
            return blob

        hrm = [fetch(oid) for oid in test_terms]

        return hfn.htmldoc(hfn.render_table([[1, 2]],'oh', 'no'),
                           title='Simulated flatmap query results',
        )

    @app.route(f'/{basename}/sparc/demos/apinat', methods=['GET'])
    @app.route(f'/{basename}/sparc/demos/apinat/', methods=['GET'])
    def route_sparc_demos_apinat():
        return 'apinat'

    @app.route(f'/{basename}/sparc/connectivity/query', methods=['GET'])
    def route_sparc_connectivity_query():
        kwargs = request.args
        log.debug(kwargs)
        script = """
        var ele = document.getElementById('model-selector')
        ele.onselect
        """

        return hfn.htmldoc(hfn.render_form(
            [[('Model',), {}],
             [None, None],
             [
                 #('Kidney', 'Defensive breathing',),  # TODO autopopulate
                 ('Urinary Omega Tree',),
              {'id':'model-selector', 'name': 'model'}]],  # FIXME auto via js?

            # FIXME must switch start and stop per model (argh)
            # or hide/show depending on which model is selected
            [[('start',), {}],
             [None, None],
             [
                 #('one', 'two', 'three'),  # TODO auto populate
                 uot_ordered,
              {'name': 'start'}]],  # FIXME auto via js?

            [[('end',), {}],
             [None, None],
             [
                 #('one', 'two', 'three'),  # TODO auto populate
                 uot_ordered,
              {'name': 'end'}]],  # FIXME auto via js?

            [[tuple(), {}],
             [tuple(), {'type': 'submit', 'value': 'Query'}],
             [None, None]]  # FIXME auto via js?
            , action='view', method='POST'
        ),
            scripts=(script,),
            title='Connectivity query')

    @app.route(f'/{basename}/sparc/connectivity/view', methods=['POST'])
    def route_sparc_connectivity_view():
        kwargs = request.args
        log.debug(kwargs)
        # FIXME error handling for bad data
        model = request.form['model']
        start = request.form['start']
        end = request.form['end']
        sid = uot_lookup[start].curie
        eid = uot_lookup[end].curie
        #start = 'UBERON:0005157'
        #end = 'UBERON:0001255'
        return redirect(f'/{basename}/sparc/dynamic/shortestSimple?start_id={sid}'
                        f'&end_id={eid}&direction=INCOMING&format=table')  # TODO
        #return hfn.htmldoc(title='Connectivity view')

    @app.route(f'/{basename}/sparc/simple/dynamic/<path:path>', methods=['GET'])
    def route_sparc_simple_dynamic(path):
        if '/neru-' in path:
            process = lambda x, blob: apinat_deblob(blob, remove_converge=True)[0]
        else:
            process = simplify

        return sparc_dynamic(data_sgd, data_sgc, path, wgb, process)

    @app.route(f'/{basename}/sparc/dynamic/<path:path>', methods=['GET'])
    def route_sparc_dynamic(path):
        return sparc_dynamic(data_sgd, data_sgc, path, wgb)

    @app.route(f'/{basename}/dynamic/<path:path>', methods=['GET'])
    def route_dynamic(path):
        args = dict(request.args)
        if 'direction' in args:
            direction = args.pop('direction')
        else:
            direction = 'OUTGOING'  # should always be outgoing here since we can't specify?

        if 'format' in args:
            format_ = args.pop('format')
        else:
            format_ = None

        try:
            j = sgd.dispatch(path, **args)
        except rHTTPError as e:
            log.exception(e)
            abort(e.response.status_code)  # DO NOT PASS ALONG THE MESSAGE
        except ValueError as e:
            log.exception(e)
            abort(404)

        if j is None or 'edges' not in j or not j['edges']:
            log.error(pformat(j))
            log.debug(sgd._last_url)
            return abort(400)

        prov = [hfn.titletag(f'Dynamic query result for {path}'),
                f'<meta name="date" content="{UTCNOWISO()}">',
                f'<link rel="http://www.w3.org/ns/prov#wasGeneratedBy" href="{wgb}">',
                '<meta name="representation" content="SciGraph">',
                f'<link rel="http://www.w3.org/ns/prov#wasDerivedFrom" href="{sgd._last_url}">']

        kwargs = {'json': cleanBad(j),
                  'html_head': prov}
        tree, extras = creatTree(*Query(None, None, direction, None), **kwargs)
        #print(extras.hierarhcy)
        #print(tree)
        if format_ is not None:
            if format_ == 'table':
                #breakpoint()
                def nowrap(class_, tag=''):
                    return (f'{tag}.{class_}'
                            '{ white-space: nowrap; }')

                ots = [OntTerm(n) for n in flatten_tree(extras.hierarchy) if 'CYCLE' not in n]
                #rows = [[ot.label, ot.asId().atag(), ot.definition] for ot in ots]
                rows = [[ot.label, hfn.atag(ot.iri, ot.curie), ot.definition] for ot in ots]

                return hfn.htmldoc(hfn.render_table(rows, 'label', 'curie', 'definition'),
                                   styles=(hfn.table_style, nowrap('col-label', 'td')))

        return hfn.htmldoc(extras.html,
                           other=prov,
                           styles=hfn.tree_styles)

    @app.route(f'/{basename}/imports/chain', methods=['GET'])
    def route_import_chain():
        return importchain.html

    @app.route(f'/{basename}/query/<pred>/<root>', methods=['GET'])
    def route_query(pred, root):
        kwargs = getArgs(request)
        kwargs['wgb'] = wgb
        maybe_abort = sanitize(pred, kwargs)
        if maybe_abort is not None:
            return maybe_abort
        if verbose:
            kwargs['verbose'] = verbose
            log.debug(str(kwargs))
        return render(pred, root, **kwargs)

    @app.route(f'/{basename}/query/<pred>/http:/<path:iri>', methods=['GET'])  # one / due to nginx
    @app.route(f'/{basename}/query/<pred>/https:/<path:iri>', methods=['GET'])  # just in case
    def route_iriquery(pred, iri):  # TODO maybe in the future
        root = 'http://' + iri  # for now we have to normalize down can check request in future
        if verbose:
            log.debug(f'ROOOOT {root}')
        kwargs = getArgs(request)
        kwargs['wgb'] = wgb
        maybe_abort = sanitize(pred, kwargs)
        if maybe_abort is not None:
            return maybe_abort
        if verbose:
            kwargs['verbose'] = verbose
            log.debug(str(kwargs))
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
            kwargs['verbose'] = verbose
            log.debug(str(kwargs))
        try:
            return render(pred, root, **kwargs)
        except HTTPError:
            return abort(404, 'Unknown ontology file.')  # TODO 'Unknown git branch.'

    @app.route(f'/{basename}/sparc/view/<tier1>', methods=['GET'])
    @app.route(f'/{basename}/sparc/view/<tier1>/', methods=['GET'])
    @app.route(f'/{basename}/sparc/view/<tier1>/<tier2>', methods=['GET'])
    @app.route(f'/{basename}/sparc/view/<tier1>/<tier2>/', methods=['GET'])
    def route_sparc_view_query(tier1, tier2=None):
        journey = sparc_view
        if tier1 not in journey:
            return abort(404)

        journey = journey[tier1]
        if tier2 is not None:
            if tier2 not in journey:
                return abort(404)
            journey = journey[tier2]

        hyp_rows = hyperlink_tree(journey)

        return hfn.htmldoc(
            hfn.render_table(hyp_rows),
            title = 'Terms for ' + (tier2 if tier2 is not None else tier1),
            metas = ({'name':'date', 'content':time()},),
        )

    @app.route(f'/{basename}/sparc/view', methods=['GET'])
    @app.route(f'/{basename}/sparc/view/', methods=['GET'])
    def route_sparc_view():
        hyp_rows = []
        spaces = hfn.nbsp * 8
        for tier1, tier2_on in sorted(sparc_view.items()):
            url = url_for('route_sparc_view_query', tier1=tier1)
            tier1_row = tier1.split(YML_DELIMITER)
            tier1_row += tier2_on['CURIES']
            tagged_tier1_row = tag_row(tier1_row, url)
            hyp_rows.append(tagged_tier1_row)
            if not tier2_on:
                continue
            # BUG: Will break what we want if more is added to spinal cord
            if len(tier2_on.keys()) > 15:
                continue
            if tier1_row[0] == 'Nerve roots of spinal cord segments':
                continue
            for tier2, tier3_on in tier2_on.items():
                if tier2 == 'CURIES':
                    continue
                url = url_for('route_sparc_view_query', tier1=tier1, tier2=tier2)
                tier2_row = tier2.split(YML_DELIMITER)
                tier2_row += tier3_on['CURIES']
                tagged_tier2_row = tag_row(row=tier2_row, url=url, tier_level=1)
                if len(list(sparc_view[tier1_row[0]][tier2_row[0]].keys())) == 1:
                    tagged_tier2_row[0] = spaces+tier2_row[0]
                hyp_rows.append(tagged_tier2_row)
        return hfn.htmldoc(
            hfn.render_table(hyp_rows),
            title= 'Main Page Sparc',
            styles= ["p {margin: 0px; padding: 0px;}"],
            metas= ({'name':'date', 'content':time()},),
        )

    @app.route(f'/{basename}/sparc/index', methods=['GET'])
    @app.route(f'/{basename}/sparc/index/', methods=['GET'])
    def route_sparc_index():
        hyp_rows = hyperlink_tree(sparc_view)
        return hfn.htmldoc(
            hfn.render_table(hyp_rows),
            title = 'SPARC Anatomical terms index',
            metas = ({'name':'date', 'content':time()},),
        )

    @app.route(f'/{basename}/sparc', methods=['GET'])
    @app.route(f'/{basename}/sparc/', methods=['GET'])
    def route_sparc():
        # FIXME TODO route to compiled
        p = Path('/var/www/ontology/trees/sparc/sawg.html')
        if p.exists():
            return send_from_directory(p.parent.as_posix(), p.name)

        log.critical(f'{resources}/sawg.org has not been published')
        return send_from_directory(resources.as_posix(), 'sawg.org')
        #return hfn.htmldoc(
            #atag(url_for('route_sparc_view'), 'Terms by region or atlas'), '<br>',
            #atag(url_for('route_sparc_index'), 'Index'),
            #title='SPARC Anatomical terms', styles=["p {margin: 0px; padding: 0px;}"],
            #metas = ({'name':'date', 'content':time()},),
        #)

    return app

# for now hardcode
test_terms = [OntId('UBERON:0001759'),
              OntId('UBERON:0000388'),
              OntId('UBERON:0001629'),
              OntId('UBERON:0001723'),
              OntId('UBERON:0001737'),
              OntId('UBERON:0001930'),
              OntId('UBERON:0001989'),
              OntId('UBERON:0001990'),
              OntId('UBERON:0002024'),
              OntId('UBERON:0002440'),
              OntId('UBERON:0003126'),
              OntId('UBERON:0003708'),
              OntId('UBERON:0009050'),
              OntId('UBERON:0011326'),
              OntId('FMA:6240'),
              OntId('FMA:6243'),
              OntId('FMA:6474'),
              OntId('FMA:6579'),
              OntId('ILX:0738293'),
              # # #
              OntId('UBERON:0000388'),
              OntId('UBERON:0000988'),
              OntId('UBERON:0001103'),
              OntId('UBERON:0001508'),
              OntId('UBERON:0001629'),
              OntId('UBERON:0001649'),
              OntId('UBERON:0001650'),
              OntId('UBERON:0001723'),
              OntId('UBERON:0001737'),
              OntId('UBERON:0001759'),
              OntId('UBERON:0001884'),
              OntId('UBERON:0001891'),
              OntId('UBERON:0001896'),
              OntId('UBERON:0001930'),
              OntId('UBERON:0001990'),
              OntId('UBERON:0002024'),
              OntId('UBERON:0002126'),
              OntId('UBERON:0002440'),
              OntId('UBERON:0003126'),
              OntId('UBERON:0003708'),
              OntId('UBERON:0005807'),
              OntId('UBERON:0006457'),
              OntId('UBERON:0006469'),
              OntId('UBERON:0006470'),
              OntId('UBERON:0006488'),
              OntId('UBERON:0006489'),
              OntId('UBERON:0006490'),
              OntId('UBERON:0006491'),
              OntId('UBERON:0006492'),
              OntId('UBERON:0006493'),
              OntId('UBERON:0009009'),
              OntId('UBERON:0009918'),
              OntId('UBERON:0011326'),
              OntId('FMA:67532'),
              OntId('FMA:7643'),
              OntId('ILX:0485722'),
              OntId('ILX:0505839'),
              OntId('ILX:0725956'),
              OntId('ILX:0731873'),
              OntId('ILX:0736966'),
              OntId('ILX:0738279'),
              OntId('ILX:0738290'),
              OntId('ILX:0738291'),
              OntId('ILX:0738292'),
              OntId('ILX:0738293'),
              OntId('ILX:0738308'),
              OntId('ILX:0738309'),
              OntId('ILX:0738312'),
              OntId('ILX:0738313'),
              OntId('ILX:0738315'),
              OntId('ILX:0738319'),
              OntId('ILX:0738324'),
              OntId('ILX:0738325'),
              OntId('ILX:0738342'),
              OntId('ILX:0738371'),
              OntId('ILX:0738372'),
              OntId('ILX:0738373'),
              OntId('ILX:0738374')]


class fakeRequest:
    args = {}


def test():
    global request
    request = fakeRequest()
    app = server()
    (route_, route_docs, route_filequery, route_examples, route_iriquery,
     route_query, route_dynamic, route_sparc_demos_isan2019_flatmap_queries,
     route_sparc_demos_isan2019_neuron_connectivity, route_sparc_dynamic,
    ) = (app.view_functions[k]
         for k in ('route_', 'route_docs', 'route_filequery',
                   'route_examples', 'route_iriquery', 'route_query',
                   'route_dynamic', 'route_sparc_demos_isan2019_flatmap_queries',
                   'route_sparc_demos_isan2019_neuron_connectivity',
                   'route_sparc_dynamic',
         ))

    #for name, path in demo_examples:
    #request = fakeRequest()
    #route_sparc_demos_isan2019_flatmap_queries()
    request = fakeRequest()
    route_sparc_demos_isan2019_neuron_connectivity()

    def test_dynamic():
        for _, path, querystring in dynamic_examples:
            if 'shortestSimple' in path:
                log.warning('skipping test of shortestSimple')
                continue
            log.info(f'ontree testing {path} {querystring}')
            global request
            request = fakeRequest()
            if querystring is not None:
                request.args = {k:v[0] if len(v) == 1 else v
                                for k,v in parse_qs(querystring.strip('?')).items()}
            else:
                request.args = {}

            resp = route_dynamic(path)

    def test_dynamic_negative():
        try:
            resp = route_dynamic('this/endpoint/does/not/exist')
            assert False, 'should have failed'
        except ValueError:
            pass

    def test_simple_dynamic():
        resp = route_sparc_dynamic('demos/apinat/housing-lyphs')

    def test_examples():
        for _, predicate, root, *_ in extra_examples + examples:
            if root == 'UBERON:0001062':
                continue  # too big
            if root == 'PAXRAT:':
                continue  # not an official curie yet

            log.info(f'ontree testing {predicate} {root}')
            if root.startswith('http'):
                root = root.split('://')[-1]  # FIXME nginx behavior...
                resp = route_iriquery(predicate, root)
            else:
                resp = route_query(predicate, root)

    def test_file_examples():
        for _, predicate, root, file, *args in file_examples:
            log.info(f'ontree testing {predicate} {root} {file}')
            if args and 'restriction' in args[0]:
                request.args['restriction'] = 'true'

            resp = route_filequery(predicate, root, file)

            if args and 'restriction' in args[0]:
                request.args.pop('restriction')

    test_simple_dynamic()
    return
    test_dynamic()
    test_dynamic_negative()
    request.args['depth'] = 1
    #test_examples()
    #test_file_examples()
    request.args.pop('depth')


def main():
    from docopt import docopt, parse_defaults
    args = docopt(__doc__, version='ontree 0.0.0')
    defaults = {o.name:o.value if o.argcount else None for o in parse_defaults(__doc__)}
    verbose = args['--verbose']
    sgg._verbose = verbose
    sgv._verbose = verbose
    sgc._verbose = verbose
    sgd._verbose = verbose

    if verbose:
        log.setLevel('DEBUG')

    if args['--test']:
        test()
    elif args['server']:
        api = args['--api']
        if api is not None:
            scigraph.scigraph_client.BASEPATH = api
            sgg._basePath = api
            sgv._basePath = api
            sgc._basePath = api
            # reinit curies state
            sgc.__init__(cache=sgc._get == sgc._cache_get, verbose=sgc._verbose)
            sgd._basePath = api

        api_key = args['--key']
        if api_key:
            sgg.api_key = api_key
            sgv.api_key = api_key
            sgc.api_key = api_key
            sgd.api_key = api_key
            scs = OntTerm.query.services[0]
            scs.api_key = api_key
            scs.setup(instrumented=OntTerm)

        _data_endpoint = args['--data-api']
        data_endpoint = (
            _data_endpoint if _data_endpoint else
            scigraph.scigraph_client.BASEPATH)

        app = server(verbose=verbose, data_endpoint=data_endpoint)
        # app.debug = False
        # app.run(host='localhost', port=args['--port'], threaded=True)  # nginxwoo
        # app.debug = True
        app.run(host='0.0.0.0', port=args['--port'], threaded=True)  # nginxwoo
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
