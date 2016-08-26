#!/usr/bin/env python3.5

# this should be run at NIF-Ontology f4e332f3089e7d0c4bb6759a1f66ff0038d0b295

# TODO need to retrieve the FMA hierarchy...

import os
from collections import defaultdict, namedtuple
import rdflib
from rdflib import URIRef, RDFS, RDF, OWL
import requests
from IPython import embed
from scigraph_client import Vocabulary, Graph
from utils import scigPrint, makeGraph, async_getter, TermColors as tc
from hierarchies import creatTree

sgg = Graph(cache=True)
sgv = Vocabulary(cache=True)

Query = namedtuple('Query', ['root','relationshipType','direction','depth'])

DBX = 'http://www.geneontology.org/formats/oboInOwl#hasDbXref'

nifga_path = os.path.expanduser('~/git/NIF-Ontology/ttl/NIF-GrossAnatomy.ttl')
uberon_path = os.path.expanduser('~/git/NIF-Ontology/ttl/external/uberon.owl')
uberon_bridge_path = 'http://berkeleybop.org/ontologies/uberon/bridge/uberon-bridge-to-nifstd.owl'
#bridge_path = os.path.expanduser('~/git/NIF-Ontology/ttl/uberon-bridge-to-nifstd.ttl')  # scigraph's got us

uberon_obsolete = {'UBERON:0022988',  # obsolete regional part of thalamaus
                   'UBERON:0014606',  # replaced by UBERON:0002434
                  }
# TODO need to unpapck all the oboInOwl:hasAlternativeId entries for the purposes of resolution... (madness)
manual = {'NIFGA:nlx_144456':'UBERON:0034918',  # prefer over UBERON:0002565, see note on UBERON:0034918
          'NIFGA:birnlex_1248':'UBERON:0002434',  # fix for what is surely and outdated bridge
          'NIFGA:nlx_anat_20081242':'UBERON:0004073',  # as of late latest version of uberon 'UBERON:0004073' replaces 'UBERON:0019281'
         }

cross_over_issues = 'NIFSUB:nlx_subcell_100205'
wat = 'NIFGA:nlx_144456'


def invert(dict_):
    output = defaultdict(list)
    for k,v in dict_.items():
        output[v].append(k)

    return dict(output)

def review_reps(dict_):
    for k,v in invert(dict_).items():
        if k is None:
            continue
        if len(v) > 1:
            kn = sgv.findById(k)
            print(k, kn['labels'][0])
            for s in kn['synonyms']:
                print(' ' * 4, s)
            for v_ in v:
                n = sgv.findById(v_)
                print(' ' * 8, v_, n['labels'][0])
                for s in n['synonyms']:
                    print(' ' * 12, s)

def review_norep(list_):
    for curie in list_:
        n = sgg.getNode(curie)
        scigPrint.pprint_node(n)

def do_deprecation(replaced_by, g):
    PREFIXES = {
        'UBERON':'http://purl.obolibrary.org/obo/UBERON_',
        'NIFGA':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-GrossAnatomy.owl#',
        'oboInOwl':'http://www.geneontology.org/formats/oboInOwl#',
        'RO':'http://www.obofoundry.org/ro/ro.owl#',
    }
    bridge = makeGraph('uberon-bridge', PREFIXES)
    graph = makeGraph('NIF-GrossAnatomy', PREFIXES)
    graph.g = g
    udone = set('NOREP')
    uedges = defaultdict(lambda:defaultdict(set))

    def inner(nifga, uberon):

        # check neuronames id TODO

        # add replaced by -> uberon
        graph.add_node(nifga, 'oboInOwl:replacedBy', uberon)
        # add deprecated true (ok to do twice...)
        graph.add_node(nifga, OWL.deprecated, True)

        # review nifga relations, specifically has_proper_part, proper_part_of
        # put those relations on the uberon term in the 
        # if there is no uberon term raise an error so we can look into it

        #if uberon not in uedges:
            #uedges[uberon] = defaultdict(set)
        resp = sgg.getNeighbors(nifga)
        edges = resp['edges']
        include = False
        for edge in edges:  # FIXME TODO hierarchy extraction and porting
            #print(edge)
            sub = edge['sub']
            obj = edge['obj']
            pred = edge['pred']
            hier = False
            if pred == 'subClassOf':
                pred = RDFS.subClassOf
                continue
            elif pred == 'equivalentClass':
                pred = OWL.equivalentClass
                continue
            elif pred == 'isDefinedBy':
                pred = RDFS.isDefinedBy
                continue
            elif pred == 'http://www.obofoundry.org/ro/ro.owl#has_proper_part':
                hier = True
                include = True
            elif pred == 'http://www.obofoundry.org/ro/ro.owl#proper_part_of':
                hier = True
                include = True

            if sub == nifga:
                try:
                    obj = replaced_by[obj]
                except KeyError:
                    print('not in replaced_by', obj)
                if type(obj) == tuple: continue  # TODO
                if hier:
                    if uberon not in uedges[obj][pred]:
                        uedges[obj][pred].add(uberon)
                        bridge.add_hierarchy(obj, pred, uberon)
                else:
                    #bridge.add_node(uberon, pred, obj)
                    pass
            elif obj == nifga:
                try:
                    sub = replaced_by[sub]
                except KeyError:
                    print('not in replaced_by', sub)
                if type(sub) == tuple: continue  # TODO
                if hier:
                    if sub not in uedges[uberon][pred]:
                        uedges[uberon][pred].add(sub)
                        bridge.add_hierarchy(uberon, pred, sub)
                else:
                    #bridge.add_node(sub, pred, uberon)
                    pass

        if uberon not in udone and include:
            try:
                label = sgv.findById(uberon)['labels'][0]
            except IndexError:
                WAT = sgv.findById(uberon)
                embed()
            bridge.add_class(uberon, label=label)
            udone.add(uberon)

    for nifga, uberon in replaced_by.items():
        if type(uberon) == tuple:
            print(uberon)
            for ub in uberon:
                print(ub)
                inner(nifga, ub)
        elif uberon == 'NOREP':
            graph.add_node(nifga, OWL.deprecated, True)  # TODO check for missing edges?
        elif uberon is None:
            continue  # BUT TODAY IS NOT THAT DAY!
        else:
            inner(nifga, uberon)

    return graph, bridge

def main():
    #ub = rdflib.Graph()
    #ub.parse(uberon_path)  # LOL rdflib your parser is slow
    SANITY = rdflib.Graph()
    SANITY.parse(data=requests.get(uberon_bridge_path).text)
    embed()
    return
    g = rdflib.Graph()
    getQname = g.namespace_manager.qname
    g.parse(nifga_path, format='turtle')
    classes = sorted([getQname(_) for _ in g.subjects(RDF.type, OWL.Class) if type(_) is URIRef])
    curies = ['NIFGA:' + n for n in classes if ':' not in n]
    matches = async_getter(sgv.findById, [(c,) for c in curies])
    #tests = [n for n,t in zip(curies, matches) if not t]  # passed
    replaced_by = {}
    exact = {}
    internal_equivs = {}
    def equiv(curie, label):
        if curie in manual:
            replaced_by[curie] = manual[curie]
            return manual[curie]

        ec = sgg.getNeighbors(curie, relationshipType='equivalentClass')
        nodes = [n for n in ec['nodes'] if n['id'] != curie]
        if len(nodes) > 1:
            #print('wtf node', [n['id'] for n in nodes], curie)
            for node in nodes:
                id_ = node['id']
                label_ = node['lbl']

                if id_.startswith('UBERON'):
                    if curie in replaced_by:
                        one = replaced_by[curie]
                        replaced_by[curie] = one, id_
                        print('WE GOT DUPES', curie, label, one, id_)  # TODO
                    else:
                        replaced_by[curie] = id_
                else:
                    internal_equivs[curie] = id_
        elif not nodes:
            moar = [t for t in sgv.findByTerm(label) if t['curie'].startswith('UBERON')]
            if moar:
                #print(moar)
                #replaced_by[curie] = moar[0]['curie']
                if len(moar) > 1:
                    print('WARNING', curie, label, [(m['curie'], m['labels'][0]) for m in moar])

                for node in moar:
                    if node['curie'] in uberon_obsolete:  # node['deprecated']?
                        continue
                    ns = sgg.getNode(node['curie'])
                    assert len(ns['nodes']) == 1, "WTF IS GOING ON %s" % node['curie']
                    ns = ns['nodes'][0]
                    if DBX in ns['meta']:
                        print(' ' * 8, node['curie'], ns['meta'][DBX],
                              node['labels'][0], node['synonyms'])
                    else:
                        #print(' ' * 8, 'NO DBXREF', node['curie'],
                              #node['labels'][0], node['synonyms'])
                        pass  # these are all to obsolote uberon classes
                    replaced_by[curie] = ns['id']
            else:
                replaced_by[curie] = None
                if False:  # review
                    print('NO FORWARD EQUIV', tc.red(curie), label)  # TODO
                    for k,v in sorted(sgg.getNode(curie)['nodes'][0]['meta'].items()):
                        if type(v) == iter:
                            print(' ' * 4, k)
                            for _ in v:
                                print(' ' * 8, _)
                        else:
                            print(' ' * 4, k, v)
        else:
            node = nodes[0]
            replaced_by[curie] = node['id']
            exact[curie] = node['id']

        return nodes

    review_norep([m['curie'] for m in matches if m['deprecated']])
    embed()
    return
    equivs = async_getter(equiv, [(c['curie'], c['labels'][0]) for c in matches if not c['deprecated']])

    #review_reps(exact)  # these all look good
    #review_reps(replaced_by)  # as do these

    regional_no_replace = {k:v for k,v in replaced_by.items() if not v and sgv.findById(k)['labels'][0].startswith('Regional')}
    for k in regional_no_replace:
        replaced_by[k] = 'NOREP'
   
    graph, bridge = do_deprecation(replaced_by, g)
    with makeGraph('',{}):
        bridge.write(delay=True)
        graph.write(delay=True)

    PPO = 'RO:proper_part_of'
    HPP = 'RO:has_proper_part'
    hpp = HPP.replace('RO:', graph.namespaces['RO'])
    a, b = creatTree(*Query(tc.red('birnlex_796'), HPP, 'OUTGOING', 10),
                     json=graph.make_scigraph_json(HPP))
    c, d = creatTree(*Query('NIFGA:birnlex_796', hpp, 'OUTGOING', 10), graph=sgg)
    e, f = creatTree(*Query('UBERON:0000955', HPP, 'OUTGOING', 10),
                     json=bridge.make_scigraph_json(HPP))
    print(a)
    print(c)
    print(e)
    embed()

if __name__ == '__main__':
    main()
