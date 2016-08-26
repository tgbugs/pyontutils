#!/usr/bin/env python3.5

# this should be run at NIF-Ontology 9cce1401ea542be39408e2e46d85a9bae442faec

# TODO need to retrieve the FMA hierarchy...

import os
from collections import defaultdict
import rdflib
from rdflib import URIRef, RDFS, RDF, OWL
from IPython import embed
from scigraph_client import Vocabulary, Graph
from utils import makeGraph, async_getter, TermColors as tc

sgg = Graph(cache=True)
sgv = Vocabulary(cache=True)

DBX = 'http://www.geneontology.org/formats/oboInOwl#hasDbXref'

nifga_path = os.path.expanduser('~/git/NIF-Ontology/ttl/NIF-GrossAnatomy.ttl')
uberon_path = os.path.expanduser('~/git/NIF-Ontology/ttl/external/uberon.owl')
#bridge_path = os.path.expanduser('~/git/NIF-Ontology/ttl/uberon-bridge-to-nifstd.ttl')  # scigraph's got us

uberon_obsolete = {'UBERON:0022988',  # obsolete regional part of thalamaus
                  }
manual = {'NIFGA:nlx_144456':'UBERON:0034918',  # prefer over UBERON:0002565, see note on UBERON:0034918
         }

AAAAAAAAAAAAAAAAAAAAAA = {'NIFGA:birnlex_1557':'NIFGA:Class_4'} 
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

def do_deprecation(replaced_by, g):
    PREFIXES = {
        'UBERON':'http://purl.obolibrary.org/obo/UBERON_',
        'NIFGA':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-GrossAnatomy.owl#',
        'oboInOwl':'http://www.geneontology.org/formats/oboInOwl#',
    }
    bridge = makeGraph('uberon-bridge', PREFIXES)
    graph = makeGraph('NIF-GrossAnatomy', PREFIXES)
    graph.g = g
    udone = set('NOREP')

    def inner(nifga, uberon):

        # add replaced by -> uberon
        graph.add_node(nifga, 'oboInOwl:replacedBy', uberon)
        # add deprecated true (ok to do twice...)
        graph.add_node(nifga, OWL.deprecated, True)

        # review nifga relations, specifically has_proper_part, proper_part_of
        # put those relations on the uberon term in the 
        # if there is no uberon term raise an error so we can look into it

        resp = sgg.getNeighbors(nifga)
        edges = resp['edges']
        for edge in edges:  # FIXME TODO
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
            elif pred == 'http://www.obofoundry.org/ro/ro.owl#proper_part_of':
                hier = True

            if sub == nifga:
                try:
                    obj = replaced_by[obj]
                except KeyError:
                    embed()
                if type(obj) == tuple: continue  # TODO
                if hier:
                    bridge.add_hierarchy(obj, pred, uberon)
                else:
                    bridge.add_node(uberon, pred, obj)
            elif obj == nifga:
                try:
                    sub = replaced_by[sub]
                except KeyError:
                    embed()
                if type(sub) == tuple: continue  # TODO
                if hier:
                    bridge.add_hierarchy(uberon, pred, sub)
                else:
                    bridge.add_node(sub, pred, uberon)

        if uberon not in udone and edges:
            bridge.add_class(uberon)

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

    #print([(c['curie'], c['labels'][0]) for c in matches if c['deprecated']])
    equivs = async_getter(equiv, [(c['curie'], c['labels'][0]) for c in matches if not c['deprecated']])

    #review_reps(exact)  # these all look good
    #review_reps(replaced_by)  # as do these

    regional_no_replace = {k:v for k,v in replaced_by.items() if not v and sgv.findById(k)['labels'][0].startswith('Regional')}
    for k in regional_no_replace:
        replaced_by[k] = 'NOREP'
   
    graph, bridge = do_deprecation(replaced_by, g)
    bridge.write(delay=True)
    graph.write()

    embed()

if __name__ == '__main__':
    main()
