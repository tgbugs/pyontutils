#!/usr/bin/env python3.6
""" Run in NIF-Ontology/ttl/ """

import os
import json
import yaml
from glob import glob
import rdflib
from pyontutils.utils import makeGraph, makePrefixes, memoryCheck, noneMembers  # TODO make prefixes needs an all...
from pyontutils.hierarchies import creatTree
from collections import namedtuple
from IPython import embed


remote_base = 'http://ontology.neuinfo.org/NIF/ttl'
local_base = os.path.expanduser('~/git/NIF-Ontology/ttl')
cwd = os.getcwd()

if cwd == local_base:
    memoryCheck(2665488384)

with open(os.path.expanduser('~/git/NIF-Ontology/scigraph/nifstd_curie_map.yaml'), 'rt') as f:
    curies = yaml.load(f)
curie_prefixes = set(curies.values())

bigleaves = 'go.owl', 'uberon.owl', 'pr.owl', 'doid.owl', 'taxslim.owl', 'chebislim.ttl', 'ero.owl'

Query = namedtuple('Query', ['root','relationshipType','direction','depth'])

def local_imports(dobig=False):
    """ Read the import closure and use the local versions of the files. """
    done = []
    p = rdflib.OWL.imports
    oi = b'owl:imports'
    def inner(local_filepath):
        if noneMembers(local_filepath, *bigleaves) or dobig:
            ext = os.path.splitext(local_filepath)[-1]
            if ext == '.ttl':
                infmt = 'turtle'
            else:
                print(ext, local_filepath)
                infmt = None
            scratch = rdflib.Graph()
            with open(local_filepath, 'rb') as f:
                raw = f.read()
            if oi in raw:  # we only care if there are imports
                start, ont_rest = raw.split(oi, 1)
                ont, rest = ont_rest.split(b'###', 1)
                data = start + oi + ont
                scratch.parse(data=data, format=infmt)
                for s, o in sorted(scratch.subject_objects(p)):
                    nlfp = o.replace(remote_base, local_base)
                    if local_base in nlfp:
                        scratch.add((s, p, rdflib.URIRef('file://' + nlfp)))
                        scratch.remove((s, p, o))
                    if nlfp not in done:
                        done.append(nlfp)
                        if local_base in nlfp and 'external' not in nlfp:  # skip externals
                            inner(nlfp)
                ttl = scratch.serialize(format='nifttl')
                ndata, comment = ttl.split(b'###', 1)
                out = ndata + b'###' + rest
                with open(local_filepath, 'wb') as f:
                    f.write(out)

    start = os.path.join(local_base, 'nif.ttl')
    done.append(start)
    inner(start)
    return done

def loadall():
    if cwd != local_base:
        raise FileNotFoundError('Please run this in NIF-Ontology/ttl') 

    graph = rdflib.Graph()

    done = []
    for f in glob('*/*/*.ttl') + glob('*/*.ttl') + glob('*.ttl'):
        print(f)
        done.append(os.path.basename(f))
        graph.parse(f, format='turtle')

    def repeat(dobig=False):  # we don't really know when to stop, so just adjust
        for s, o in graph.subject_objects(rdflib.OWL.imports):
            if os.path.basename(o) not in done and o not in done:
            #if (o, rdflib.RDF.type, rdflib.OWL.Ontology) not in graph:
                print(o)
                done.append(o)
                ext = os.path.splitext(o)[1]
                fmt = 'turtle' if ext == '.ttl' else 'xml'
                if noneMembers(o, *bigleaves) or dobig:
                    graph.parse(o, format=fmt)

    for i in range(4):
        repeat(True)

    return graph

def normalize_prefixes(graph):
    mg = makeGraph('nifall', makePrefixes('owl', 'skos', 'oboInOwl'), graph=graph)
    mg.del_namespace('')

    old_namespaces = list(graph.namespaces())
    ng_ = makeGraph('', prefixes=makePrefixes('oboInOwl', 'skos'))
    [ng_.g.add(t) for t in mg.g]
    [ng_.add_namespace(n, p) for n, p in curies.items() if n != '']
    #[mg.add_namespace(n, p) for n, p in old_namespaces if n.startswith('ns') or n.startswith('default')]
    #[mg.del_namespace(n) for n in list(mg.namespaces)]
    #graph.namespace_manager.reset()
    #[mg.add_namespace(n, p) for n, p in wat.items() if n != '']
    return mg, ng_

def import_tree(graph, mg):

    mg.add_known_namespace('NIFTTL')
    j = mg.make_scigraph_json('owl:imports', direct=True)
    #asdf = sorted(set(_ for t in graph for _ in t if type(_) == rdflib.URIRef))  # this snags a bunch of other URIs
    #asdf = sorted(set(_ for _ in graph.subjects() if type(_) != rdflib.BNode))
    asdf = set(_ for t in graph.subject_predicates() for _ in t if type(_) == rdflib.URIRef)
    prefs = set(_.rsplit('#', 1)[0] + '#' if '#' in _
                       else (_.rsplit('_',1)[0] + '_' if '_' in _
                             else _.rsplit('/',1)[0] + '/') for _ in asdf)
    nots = set(_ for _ in prefs if _ not in curie_prefixes)
    sos = set(prefs) - set(nots)

    print(len(prefs))
    t, te = creatTree(*Query('NIFTTL:nif.ttl', 'owl:imports', 'OUTGOING', 30), json=j)
    print(t)
    return t, te

def for_burak(ng_):
    syn_predicates = (ng_.expand('OBOANN:synonym'),
                      ng_.expand('OBOANN:acronym'),
                      ng_.expand('OBOANN:abbrev'),
                      ng_.expand('oboInOwl:hasExactSynonym'),
                      ng_.expand('oboInOwl:hasNarrowSynonym'),
                      ng_.expand('oboInOwl:hasBroadSynonym'),
                      ng_.expand('oboInOwl:hasRelatedSynonym'),
                      ng_.expand('skos:prefLabel'),
                      rdflib.URIRef('http://purl.obolibrary.org/obo/go#systematic_synonym'),
                     )
    lab_predicates = rdflib.RDFS.label,
    def inner(ng):
        graph = ng.g
        for s in graph.subjects(rdflib.RDF.type, rdflib.OWL.Class):
            if not isinstance(s, rdflib.BNode):
                curie = ng.qname(s)
                labels = [o for p in lab_predicates for o in graph.objects(s, p)
                          if not isinstance(o, rdflib.BNode)]
                synonyms = [o for p in syn_predicates for o in graph.objects(s, p)
                            if not isinstance(o, rdflib.BNode)]
                parents = [ng.qname(o) for o in graph.objects(s, rdflib.RDFS.subClassOf)
                           if not isinstance(o, rdflib.BNode)]
                yield [curie, labels, synonyms, parents]

    records = {c:[l, s, p] for c, l, s, p in inner(ng_) if l or s}
    with open(os.path.expanduser('~/files/ontology-classes-with-labels-synonyms-parents.json'), 'wt') as f:
              json.dump(records, f, sort_keys=True, indent=2)

def make_graphload_yaml(tc):
    with open(local_base + '/../scigraph/graphload-template.yaml', 'rt') as f:
        base = yaml.load(f)
    embed()
    #with open(local_base + '/../scigraph/graphload.yaml', 'wt') as f:
        #yaml.dump(base, f)

def main():
    tc = local_imports()
    return
    graph = loadall()
    mg, ng_ = normalize_prefixes(graph)
    tree, extra = import_tree(graph, mg)
    with open('/tmp/nifstd-import-closure.html', 'wt') as f:
        f.write(extra.html)
    for_burak(ng_)
    embed()

if __name__ == '__main__':
    main()
