#!/usr/bin/env python3
import os
import csv
import json
import rdflib
from rdflib.extras import infixowl
from IPython import embed
from pyontutils.slimgen import add_hierarchy
from pyontutils.scr_sync import makeGraph
from pyontutils.scigraph_client import Vocabulary
v = Vocabulary()

def memoize(filepath, ser='json'):
    """ The wrapped function should take no arguments
        and return the object to be serialized
    """
    if ser == 'json':
        serialize = json.dump
        deserialize = json.load
        mode = 't'
    else:
        raise TypeError('Bad serialization format.')

    def inner(function):
        def superinner(reup=False, **kwargs):
            if os.path.exists(filepath) and not reup:
                print('deserializing from', filepath)
                with open(filepath, 'r' + mode) as f:
                    return deserialize(f)
            else:
                output = function(**kwargs)
                with open(filepath, 'w' + mode) as f:
                    serialize(output, f)
                return output

        return superinner

    return inner
# load existing ontology

PREFIXES = {
    'ilx':'http://uri.interlex.org/base/',
    'skos':'http://www.w3.org/2004/02/skos/core#',
    'HBP_CELL':'http://www.hbp.FIXME.org/hbp_cell_ontology/',
    'NIFCELL':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Cell.owl#',
    'NIFMOL':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Molecule.owl#',
    'NIFNEURNT':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Neuron-NT-Bridge.owl#',
    'NIFNEURON':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF_Neuron_MolecularConstituent_Bridge.owl#',
    'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
    'NIFSTD':'http://uri.neuinfo.org/nif/nifstd/'
}

def expand(curie):
    prefix, suffix = curie.split(':')
    return rdflib.URIRef(PREFIXES[prefix] + suffix)


def ilx_get_start():
    with open(os.path.expanduser('~/git/NIF-Ontology/interlex_reserved.txt'), 'rt') as f:
        for line in f.readlines()[::-1]:  # go backward to find the first non empty
            new_ilx_id, label = line.strip().split(':')
            if label:
                break
            else:
                ilx_id = new_ilx_id

    print(ilx_id)
    ilx_start = int(ilx_id.split('_')[1])
    return ilx_start


def ilx_add_ids(ilx_labels):
    with open(os.path.expanduser('~/git/NIF-Ontology/interlex_reserved.txt'), 'rt') as f:
        new_lines = []
        for line in f.readlines():
            ilx_id, label = line.strip().split(':')
            if ilx_id in ilx_labels:
                if label:
                    raise KeyError('That ILX identifier is already in use! %s %s' % (ilx_id, label))
                else:
                    new_lines.append(ilx_id + ':' + label)
            else:
                new_lines.append(line)

    new_text = '\n'.join(new_lines)
    with open(os.path.expanduser('interlex_reserved.txt.new'), 'wt') as f:
        f.write(new_text)
    

def ilx_conv(graph, prefix, ilx_start):
    """ convert a set of temporary identifiers to ilx and modify the graph in place """
    to_sub = set()
    for subject in graph.subjects(rdflib.RDF.type, rdflib.OWL.Class):
        if PREFIXES[prefix] in subject:
            to_sub.add(subject)

    ilx_base = 'ilx_{:0>7}'
    ILX_base = 'ILX:{:0>7}'  # ah rdflib/owlapi, you infuriate me

    ilx_labels = {}
    replace = {}
    for sub in sorted(to_sub):
        ilx_format = ilx_base.format(ilx_start)
        ILX_format = ILX_base.format(ilx_start)
        ilx_start += 1
        prefix, url, suffix = graph.namespace_manager.compute_qname(sub)
        curie = prefix + ':' + suffix
        replace[curie] = ILX_format
        label = [_ for _ in graph.objects(sub, rdflib.RDFS.label)][0]
        ilx_labels[ilx_format] = label
        new_sub = expand('ilx:' + ilx_format)
        for p, o in graph.predicate_objects(sub):
            graph.remove((sub, p, o))
            graph.add((new_sub, p, o))

        for s, p in graph.subject_predicates(sub):
            graph.remove((s, p, sub))
            graph.add((s, p, new_sub))


    return ilx_labels, replace


NEURON = 'NIFCELL:sao1417703748'
def clean_hbp_cell():
    mg = makeGraph('testing', prefixes=PREFIXES)
    newgraph = mg.g
    skip = {
        '0000000':'NIFCELL:sao1813327414',  # cell
        #'0000001':NEURON,  # neuron  (equiv)
        #'0000002':'NIFCELL:sao313023570',  # glia  (equiv)
        #'0000021':'NIFNEURNT:nlx_neuron_nt_090804',  # glut  (equiv, but phen)
        #'0000022':'NIFNEURNT:nlx_neuron_nt_090803',  # gaba  (equiv, but phen)

        '0000003':NEURON,
        '0000004':NEURON,
        '0000005':NEURON,
        '0000006':NEURON,
        '0000007':NEURON,
        '0000008':NEURON,
        '0000009':NEURON,
        '0000010':NEURON,
        '0000019':NEURON,
        '0000020':NEURON,
        '0000033':NEURON,
        '0000034':NEURON,
        '0000070':NEURON,
        '0000071':NEURON,
    }
    to_phenotype = {
        '0000021':('ilx:hasMolecularPhenotype', 'NIFMOL:sao1744435799'), # glut
        '0000022':('ilx:hasMolecularPhenotype', 'NIFMOL:sao229636300'), # gaba
    }
    lookup = {'NIFCELL', 'NIFNEURNT'}

    g = rdflib.Graph()
    g.parse(os.path.expanduser('~/git/methodsOntology/ttl/hbp_cell_ontology.ttl'), format='turtle')
    g.remove((None, rdflib.OWL.imports, None))
    g.remove((None, rdflib.RDF.type, rdflib.OWL.Ontology))

    replace = set()
    phen = set()
    equiv = {}
    for triple in sorted(g.triples((None, None, None))):
        id_suffix = newgraph.namespace_manager.compute_qname(triple[0].toPython())[2]
        try:
            obj_suffix = newgraph.namespace_manager.compute_qname(triple[2].toPython())[2]
        except:  # it wasn't a url
            pass
        # equiv insert for help
        if triple[1] == rdflib.OWL.equivalentClass and id_suffix not in skip and id_suffix not in to_phenotype:
            qnt = newgraph.namespace_manager.compute_qname(triple[2].toPython())
            #print(qnt)
            if qnt[0] in lookup:
                try:
                    lab = v.findById(qnt[0] + ':' + qnt[2])['labels'][0]
                    print('REMOTE', qnt[0] + ':' + qnt[2], lab)
                    #mg.add_node(triple[2], rdflib.RDFS.label, lab)
                    #mg.add_node(triple[0], PREFIXES['OBOANN'] + 'synonym', lab)  # so we can see it
                except TypeError:
                    if qnt[2].startswith('nlx'):
                        triple = (triple[0], triple[1], expand('NIFSTD:' + qnt[2]))
                    #print('bad identifier')

        #check for equiv
        if triple[0] not in equiv:
            eq = [o for o in g.objects(triple[0], rdflib.OWL.equivalentClass)]
            if eq and id_suffix not in skip and id_suffix not in to_phenotype:
                if len(eq) > 1:
                    print(eq)
                equiv[triple[0]] = eq[0]
                continue
        elif triple[0] in equiv:
            continue

        # edge replace
        if triple[1].toPython() == 'http://www.FIXME.org/nsupper#synonym':
            edge =  rdflib.URIRef('http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#abbrev')
        elif triple[1].toPython() == 'http://www.FIXME.org/nsupper#definition':
            edge = rdflib.namespace.SKOS.definition
        else:
            edge = triple[1]

        # skip or to phenotype or equiv
        if id_suffix in skip:  # have to make a manual edit to rdflib to include 'Nd' in allowed 1st chars
            replace.add(triple[0])
            #print('MEEP MEEP')
        elif id_suffix in to_phenotype:  # have to make a manual edit to rdflib to include 'Nd' in allowed 1st chars
            phen.add(triple[0])
        elif triple[1] == rdflib.RDFS.label:  # fix labels
            if not triple[2].startswith('Hippocampus'):
                new_label = rdflib.Literal('Neocortex ' + triple[2], lang='en')
                newgraph.add((triple[0], edge, new_label))
            else:
                newgraph.add((triple[0], edge, triple[2]))
        elif triple[2] in replace:
            mg.add_node(triple[0], edge, skip[obj_suffix])
        elif triple[2] in phen:
            edge_, rst_on = to_phenotype[obj_suffix]
            edge_ = expand(edge_)
            rst_on = expand(rst_on)

            this = triple[0]
            this = infixowl.Class(this, graph=newgraph)
            this.subClassOf = [expand(NEURON)] + [c for c in this.subClassOf]

            restriction = infixowl.Restriction(edge_, graph=newgraph, someValuesFrom=rst_on)
            this.subClassOf = [restriction] + [c for c in this.subClassOf]
        elif triple[2] in equiv:
            newgraph.add((triple[0], edge, equiv[triple[2]]))
        else:
            newgraph.add((triple[0], edge, triple[2]))

    # final cleanup for forward references (since we iterate through sorted)
    
    tt = rdflib.URIRef(expand('HBP_CELL:0000033'))
    tf = rdflib.URIRef(expand('HBP_CELL:0000034'))
    newgraph.remove((None, None, tt))
    newgraph.remove((None, None, tf))

    # cleanup for subClassOf
    for subject in sorted(newgraph.subjects(rdflib.RDFS.subClassOf, expand(NEURON))):
        sco = [a for a in newgraph.triples((subject, rdflib.RDFS.subClassOf, None))]
        #print('U WOT M8')
        if len(sco) > 1:
            #print('#############\n', sco)
            for s, p, o in sco:
                if 'hbp_cell_ontology' in o or 'NIF-Cell' in o and o != expand(NEURON): #or 'sao2128417084' in o:  # neocortex pyramidal cell
                    #print(sco)
                    newgraph.remove((subject, rdflib.RDFS.subClassOf, expand(NEURON)))
                    break

    # do ilx
    ilx_start = ilx_get_start()

    ilx_conv_mem = memoize('hbp_cell_interlex.json')(ilx_conv)

    ilx_labels, ilx_replace = ilx_conv_mem(graph=newgraph, prefix='HBP_CELL', ilx_start=ilx_start)
    ilx_add_ids(ilx_labels)
    with open('hbp_cell_ilx_ids.json', 'wt') as f:
        json.dump(ilx_replace, f)

    replace_map = ilx_replace
    for hbp, rep in skip.items():
        ori = 'HBP_CELL:'+hbp
        if ori in replace_map: raise KeyError('identifier already in!??! %s' % ori)
        replace_map[ori] = rep
    for hbp, (e, rep) in to_phenotype.items():
        ori = 'HBP_CELL:'+hbp
        if ori in replace_map: raise KeyError('identifier already in!??! %s' % ori)
        replace_map[ori] = edge, rep
    for hbp_iri, rep_iri in equiv.items():
        hbp = newgraph.compute_qname(hbp_iri)[2]
        rep = newgraph.qname(rep_iri)
        ori = 'HBP_CELL:'+hbp
        if ori in replace_map: raise KeyError('identifier already in!??! %s' % ori)
        replace_map[ori] = rep

    return mg, replace_map


def main():
    mg, rep_map = clean_hbp_cell()
    #print(sorted(rep_map.items()))
    with open('hbp_cell_conv.json', 'wt') as f:
        json.dump(rep_map, f)
    with open('hbp_cell_conv.csv', 'wt') as f:
        writer = csv.writer(f)
        for hbp_new in sorted(rep_map.items()):
            writer.writerow(hbp_new)
    mg.write()
    #embed()

if __name__ == '__main__':
    main()

