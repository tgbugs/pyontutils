""" Compares Interlex turtle (reference) to NIF/External merged turtle file (target).
    Output is a json file with a structure:

        dict[ interlex_id ] : {
            shared_iris : {
                'ilx_only'     : (predicate, object),
                'nif_only'     : (predicate, object),
                'both_contain' : (predicate, object),
                'expo'         : (predicate, object),   #experimental comparisons
            }
        }

Usage:  nif-ilx-comparator.py [-h | --help]
        nif-ilx-comparator.py [-v | --version]
        nif-ilx-comparator.py [-r REFERENCE_GRAPH] [-t TARGET_GRAPH] [-o OUTPUT]

Options:
    -h, --help                  Display this help message
    -v, --version               Current version of file

    -r, --ref=<path>            Graph used as base case or foundation of comparison [default: ../Interlex.ttl]
    -t, --target=<path>         Graph used as the target of comparison [default: ../NIF-ALL.pickle]
    -o, --output=<path>         Resulting Json formatted comparison [default: ../nif-ilx-comparator/dump/nif-ilx-comparison.json]
"""
from docopt import docopt
from graph_edge_cases import edge_cases, expo, full
import json
import pickle
import pandas as pd
import numpy as np
from pyontutils.utils import *
from pyontutils.core import *
from pyontutils.closed_namespaces import *
import rdflib
from collections import defaultdict
import sys
from subprocess import call, check_output
import re
import pathlib

VERSION = '0.3'
args = pd.Series({k.replace('--', ''):v for k,v in docopt(__doc__, version=VERSION).items()})

g_ilx = makeGraph('', graph=rdflib.Graph().parse(args.ref, format='turtle'))
g_qnames_purpose_only = makeGraph('', graph=rdflib.Graph().parse(args.ref, format='turtle'))
g_nif = makeGraph('', graph=pickle.load(open(args.target, 'rb')))

qilx = g_ilx.qname
qnif = g_nif.qname
qall = g_qnames_purpose_only.qname

edge_cases = {**{qnif(v):k+':' for k,v in full.items()}, **edge_cases, **expo}

''' Custom encoder to allow json to convert any sets in nested data to become lists '''
class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)

def update_namespaces():
    ns_to_del = []
    for namespace in g_nif.namespaces:
        if 'default' in namespace.split(':')[0]:
            ns_to_del.append(namespace)
    for ns in ns_to_del:
        g_nif.del_namespace(ns)

    """ Create new namespaces; old are messed up """
    for s, ns in g_nif.namespaces.items():
        g_nif.del_namespace(s)
        g_nif.add_namespace(s, rdflib.Namespace(str(ns)))

    """ Reset blasted cache """
    for _ in range(10):
        g_nif.g.namespace_manager.reset()

    """ Fill ilx qname to fix the existing ids """
    for s, ns in g_nif.namespaces.items():
        if not g_qnames_purpose_only.namespaces.get(s):
            g_qnames_purpose_only.add_namespace(s, rdflib.Namespace(str(ns)))

def get_iri_to_family_iris():

    iri_lumps = []
    for subj in g_ilx.g.subjects(rdflib.RDF.type, rdflib.OWL.Class):
        lump = []
        for pred, obj in g_ilx.g.predicate_objects(subject=subj):
            if str(pred).rsplit('/')[-1].lower() == 'existingids':
                lump.append(str(obj))
        iri_lumps.append(lump)

    iri_to_family_iris = defaultdict(list)
    for lump in iri_lumps:
        for i, iri in enumerate(lump):
            iri_to_family_iris[iri].extend([e for j, e in enumerate(lump) if j != i])

    return iri_to_family_iris

def add_experiental(comparator_data):

    def cv(string, test):
        if test == 'label':
            return ' '.join(string.strip().split())
        return ' '.join(string.lower().strip().split())

    hits = set()
    new_comparator_data = comparator_data.copy()
    count_per_id = 0
    count_per_element = 0
    tests = [r'definition', r'synonym', r'label']

    for ilx_identifer, shared_iris in comparator_data.items():
        for i, shared_iri in enumerate(shared_iris):
            for iri, inb in shared_iri.items():
                expo = {'same':{}, 'different':{'label':set(), 'definition':set(), 'synonym':set()}}
                for ilx_pred, ilx_obj in inb['ilx_only']:
                    #print(inb['nif_only'])
                    for nif_pred, nif_obj in inb['nif_only']:

                        ''' diff logic here '''
                        for test in tests: #for each test case given; keeps noise out
                            #expo['different'].update({test:[]})
                            if re.search(test, cv(ilx_pred, test)) and re.search(test, cv(nif_pred, test)): #and nif_pred != 'skos:definition':
                                if cv(ilx_obj, test) == cv(nif_obj, test):
                                    count_per_element += 1
                                    """
                                    same:{
                                        obj:[pred1, pred2]
                                    }
                                    """
                                    if not expo['same'].get(nif_obj):
                                        expo['same'].update({
                                            nif_obj:[ilx_pred, nif_pred],
                                        })
                                    else:
                                        expo['same'][nif_obj].append(nif_pred)
                                    #print(test, ilx_pred, nif_pred)
                                else:
                                    """
                                    different:{
                                        'label': [
                                            [pred, obj]
                                        ]
                                        etc...
                                    }
                                    """
                                    expo['different'][test].add((nif_pred, nif_obj))
                                    expo['different'][test].add((ilx_pred, ilx_obj))


                if expo: count_per_id += 1
                new_comparator_data[ilx_identifer][i][iri]['experimental'] = expo #[(),(),()]

    print('Total expo hits: ', count_per_id)
    print('Number of Ids with hits: ', count_per_element)
    print('Experimental Complete')
    return new_comparator_data

def compare_graphs():
    data = defaultdict(list)

    interlex_with_mods = defaultdict(set)
    nif_with_mods = defaultdict(set)

    iri_to_family_iris = get_iri_to_family_iris()

    #changed to list to have a ranking system within the data to make it more complicated with bloat data.
    rank_list = []
    def rank(pad, rank_list):
        if not rank_list: return pad
        score = []
        rank_list = rank_list[::-1]
        for item in pad:
            if item in rank_list:
                score.append((rank_list.index(item), item))
            else:
                score.append((-1, item))
        return [v[1] for v in sorted(score)[::-1]]

    for subj in g_ilx.g.subjects(rdflib.RDF.type, rdflib.OWL.Class):

        shared_iris = set()
        ilx_mod_conversion = {}
        nif_mod_conversion = {}

        for pred, obj in g_ilx.g.predicate_objects(subject=subj):


            '''Needs traversal convert superclass ilx to its respected exisiting ids'''
            if qilx(pred) == 'rdfs:subClassOf':
                superclasses_iris = iri_to_family_iris[str(obj)]
                for superclasses_iri in superclasses_iris:
                    tup = (qilx(pred), ' '.join(superclasses_iri.lower().strip().split()))
                    ilx_mod_conversion[tup] = (qilx(pred), superclasses_iri)
                    interlex_with_mods[qilx(subj)].add(tup)
            else:
                ''' Special condition for label bc we want to know Cap diff '''
                if qilx(pred) == 'rdfs:label':
                    tup = (qnif(pred), ' '.join(str(obj).strip().split()))
                else:
                    tup = (qnif(pred), ' '.join(str(obj).lower().strip().split()))
                #print(tup)
                ilx_mod_conversion[tup] = (qilx(pred), str(obj))
                interlex_with_mods[qilx(subj)].add(tup)

            '''Build nif when ilx exisiting id found in nif'''
            if qilx(pred) == 'ilxtr:existingIds':
                for p, o in g_nif.g.predicate_objects(subject=obj):
                    shared_iris.add(obj)
                    if edge_cases.get(qnif(p)) == 'rdfs:label':
                        tup = (qnif(p), ' '.join(str(o).strip().split()))
                    else:
                        tup = (qnif(p), ' '.join(str(o).lower().strip().split()))
                    if edge_cases.get(qnif(p)):
                        nif_with_mods[qnif(obj)].add((edge_cases[tup[0]], tup[1]))
                        nif_mod_conversion[(edge_cases[tup[0]], tup[1])] = (qnif(p), str(o))
                    else:
                        nif_with_mods[qnif(obj)].add(tup)
                        nif_mod_conversion[tup] = (qnif(p), str(o))

        '''Comparator btw current ilx term and each nif term sharing ilx existing id'''
        for shared_iri in rank(shared_iris, rank_list):
            nif = nif_with_mods[qnif(shared_iri)]
            ilx = interlex_with_mods[qilx(subj)]

            i = ilx - nif
            n = nif - ilx
            b = nif & ilx

            def formatter(current_set, mod_conversion):
                return sorted([(p,qall(o)) for p,o in [mod_conversion[po] for po in current_set]])

            data[qall(subj)].append({
                qall(shared_iri): {
                    'ilx_only'     : formatter(i, ilx_mod_conversion),
                    'nif_only'     : formatter(n, nif_mod_conversion),
                    'both_contain' : formatter(b, nif_mod_conversion),
                }
            })

    return data

def main():
    update_namespaces()

    comparison_data = compare_graphs()
    print('Graphs Compared')

    comparison_data = add_experiental(comparison_data)


    json.dump(comparison_data, open(args.output, 'w'), indent=4, cls=SetEncoder)
    print('Comparison Data Saved')

    shellcommand = 'ex -s +\'g/\[[\ \\n]\+"/j4\' -cwq ' + args.output
    if call(shellcommand, shell=True) == 1:
        print('Not prettyfied')
    else:
        print('COMPLETE')

if __name__ == '__main__':
    main()
