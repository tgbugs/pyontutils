#!/usr/bin/env python3
import os
import csv
import json
from pathlib import Path
from datetime import date
import rdflib
from rdflib.extras import infixowl
from pyontutils.core import makeGraph
from pyontutils.scigraph import Vocabulary
from pyontutils.namespaces import makePrefixes
from IPython import embed

current_file = Path(__file__).absolute()
gitf = current_file.parent.parent.parent

v = Vocabulary()

PREFIXES = makePrefixes('ilx', 'owl', 'skos', 'NIFSTD', 'NIFRID', 'SAO', 'NIFEXT', 'NLXCELL')
PREFIXES.update({
    'HBP_CELL':'http://www.hbp.FIXME.org/hbp_cell_ontology/',
})


def expand(curie):
    prefix, suffix = curie.split(':')
    return rdflib.URIRef(PREFIXES[prefix] + suffix)


def ilx_get_start():
    with open((gitf /
               'NIF-Ontology/interlex_reserved.txt').as_posix(), 'rt') as f:
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
    with open((gitf /
               'NIF-Ontology/interlex_reserved.txt').as_posix(), 'rt') as f:
        new_lines = []
        for line in f.readlines():
            ilx_id, label = line.strip().split(':')
            if ilx_id in ilx_labels:
                if label:
                    raise KeyError('That ILX identifier is already in use! %s %s' % (ilx_id, label))
                else:
                    new_lines.append(ilx_id + ':' + ilx_labels[ilx_id])
            else:
                new_lines.append(line.strip())

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


NEURON = 'SAO:1417703748'
def clean_hbp_cell():
    #old graph
    g = rdflib.Graph()
    if __name__ == '__main__':
        embed()
    g.parse((gitf /
             'methodsOntology/ttl/hbp_cell_ontology.ttl').as_posix(), format='turtle')
    g.remove((None, rdflib.OWL.imports, None))
    g.remove((None, rdflib.RDF.type, rdflib.OWL.Ontology))

    #new graph
    NAME = 'NIF-Neuron-HBP-cell-import'
    mg = makeGraph(NAME, prefixes=PREFIXES)
    ontid = 'http://ontology.neuinfo.org/NIF/ttl/generated/' + NAME + '.ttl'
    mg.add_trip(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
    mg.add_trip(ontid, rdflib.RDFS.label, 'NIF Neuron HBP cell import')
    mg.add_trip(ontid, rdflib.RDFS.comment, 'this file was automatically using pyontutils/hbp_cells.py')
    mg.add_trip(ontid, rdflib.OWL.versionInfo, date.isoformat(date.today()))
    newgraph = mg.g

    skip = {
        '0000000':'SAO:1813327414',  # cell
        #'0000001':NEURON,  # neuron  (equiv)
        #'0000002':'SAO:313023570',  # glia  (equiv)
        #'0000021':'NLXNEURNT:090804',  # glut  (equiv, but phen)
        #'0000022':'NLXNEURNT:090803',  # gaba  (equiv, but phen)

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
        '0000021':('ilx:hasExpressionPhenotype', 'SAO:1744435799'),  # glut, all classes that might be here are equived out
        '0000022':('ilx:hasExperssionPhenotype', 'SAO:229636300'),  # gaba
    }
    lookup = {'NIFCELL', 'NIFNEURNT'}
    missing_supers = {
        'HBP_CELL:0000136',
        'HBP_CELL:0000137',
        'HBP_CELL:0000140',
    }

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
                    #mg.add_trip(triple[2], rdflib.RDFS.label, lab)
                    #mg.add_trip(triple[0], PREFIXES['NIFRID'] + 'synonym', lab)  # so we can see it
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
            edge =  mg.expand('NIFRID:abbrev')
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
            mg.add_trip(triple[0], edge, skip[obj_suffix])
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

    # add missing subClasses
    for nosub in missing_supers:
        mg.add_trip(nosub, rdflib.RDFS.subClassOf, NEURON)

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
    #ilx_conv_mem = memoize('hbp_cell_interlex.json')(ilx_conv)  # FIXME NOPE, also need to modify the graph :/
    ilx_labels, ilx_replace = ilx_conv(graph=newgraph, prefix='HBP_CELL', ilx_start=ilx_start)
    ilx_add_ids(ilx_labels)

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
    if __name__ == '__main__':
        with open('hbp_cell_conv.json', 'wt') as f:
            json.dump(rep_map, f)
        with open('hbp_cell_conv.csv', 'wt') as f:
            writer = csv.writer(f)
            for hbp_new in sorted(rep_map.items()):
                writer.writerow(hbp_new)

        mg.write()

if __name__ == '__main__':
    main()

