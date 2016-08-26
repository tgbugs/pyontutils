#!/usr/bin/env python3.5

# this should be run at NIF-Ontology 9cce1401ea542be39408e2e46d85a9bae442faec

import os
from collections import defaultdict
import rdflib
from rdflib import URIRef, RDFS, RDF, OWL
from IPython import embed
from scigraph_client import Vocabulary, Graph
from utils import async_getter, TermColors as tc

sgg = Graph(cache=True)
sgv = Vocabulary(cache=True)

DBX = 'http://www.geneontology.org/formats/oboInOwl#hasDbXref'

nifga_path = os.path.expanduser('~/git/NIF-Ontology/ttl/NIF-GrossAnatomy.ttl')
uberon_path = os.path.expanduser('~/git/NIF-Ontology/ttl/external/uberon.owl')
#bridge_path = os.path.expanduser('~/git/NIF-Ontology/ttl/uberon-bridge-to-nifstd.ttl')

uberon_obsolete = {'UBERON:0022988',  # obsolete regional part of thalamaus
                  }
manual = {'NIFGA:nlx_144456':'UBERON:0034918',  # prefer over UBERON:0002565, see note on UBERON:0034918
         }

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
                print('NO FORWARD EQUIV', tc.red(curie), label)  # TODO
                replaced_by[curie] = None
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

    embed()

if __name__ == '__main__':
    main()
