#!/usr/bin/env python3
import subprocess
from pathlib import Path
from collections import defaultdict
import rdflib
from ttlser import natsort
from pyontutils.core import qname, makeGraph
from pyontutils.utils import TermColors as tc
from pyontutils.namespaces import  NIFRID, ilxtr
from pyontutils.combinators import restriction, annotation
from pyontutils.closed_namespaces import owl, rdf, rdfs, skos

current_file = Path(__file__).absolute()
gitf = current_file.parent.parent.parent

def labelkey(line):
    label, *rest = line.split('|', 1)
    return natsort(label)

def edkey(line):
    ed, label, *rest = line.split('|', 2)
    return natsort(ed + ' ' + label)

def main():
    for filename in ('mbaslim', 'hbaslim', 'paxinos-rat-labels', 'waxholm-rat-labels'):
        filepath = gitf / 'NIF-Ontology/ttl/generated/parcellation' / (filename + '.ttl')
        dir_ = filepath.parent.as_posix()
        print(dir_)
        file_commit = subprocess.check_output(['git', 'log', '-n', '1',
                                               '--pretty=format:%H', '--',
                                               filepath.name],
                                              cwd=dir_,
                                              stderr=subprocess.DEVNULL).decode().rstrip()
        graph = rdflib.Graph().parse(filepath.as_posix(), format='ttl')
        g = makeGraph('', graph=graph)

        annos = defaultdict(set)
        anno_trips = defaultdict(set)
        for triple, predicate_objects in annotation.parse(graph=graph):
            for a_p, a_o in predicate_objects:
                annos[a_p, a_o].add(triple)
                anno_trips[triple].add((a_p, a_o))

        anno_trips = {k:v for k, v in anno_trips.items()}

        for lifted_triple in restriction.parse(graph=graph):
            graph.add(lifted_triple)

        out_header = 'label|abbrev|curie|superPart curie\n'
        out = []
        editions_header = 'edition|label|abbrev|curie\n'
        editions = []
        for s in graph.subjects(rdf.type, owl.Class):
            rdfsLabel = next(graph.objects(s, rdfs.label))
            try:
                prefLabel = next(graph.objects(s, skos.prefLabel))
            except StopIteration:
                print(tc.red('WARNING:'), f'skipping {s} {rdfsLabel} since it has no prefLabel')
                continue
            syns = sorted(graph.objects(s, NIFRID.synonym))  # TODO are there cases where we need to recaptulate what we are doing for for abbrevs?
            abbrevs = sorted(graph.objects(s, NIFRID.abbrev))  # FIXME paxinos has more than one
            try:
                if annos:
                    if len(abbrevs) > 1:
                        print(tc.blue('INFO:'), g.qname(s), repr(prefLabel.value), 'has multiple abbrevs', [a.value for a in abbrevs])
                    # prefer latest
                    current_edition = ''
                    for a in abbrevs:
                        for a_p, edition in anno_trips[s, NIFRID.abbrev, a]:
                            if a_p == ilxtr.literalUsedBy:
                                if current_edition < edition:
                                    current_edition = edition
                                    abbrev = a
                else:
                    abbrev = abbrevs[0]
            except IndexError:
                abbrev = ''
            try:
                superPart = next(graph.objects(s, ilxtr.labelPartOf))
            except StopIteration:
                superPart = ''

            out.append(f'{prefLabel}|{abbrev}|{g.qname(s)}|{g.qname(superPart)}')

            if annos:
                #asdf = {'ed':{'label':,'abbrev':,'curie':}}
                asdf = defaultdict(dict)
                triple = s, skos.prefLabel, prefLabel
                eds = anno_trips[triple]
                for a_p, a_o in eds:
                    asdf[a_o]['curie'] = g.qname(s)
                    asdf[a_o]['label'] = prefLabel
                for syn in graph.objects(s, NIFRID.synonym):
                    triple = s, NIFRID.synonym, syn
                    eds = anno_trips[triple]
                    for a_p, a_o in eds:
                        asdf[a_o]['curie'] = g.qname(s)
                        if 'label' in asdf[a_o]:
                            print(tc.red('WARNING:'), f'{a_o} already has a label "{asdf[a_o]["label"]}" for "{syn}"')
                        asdf[a_o]['label'] = syn
                for abbrev in graph.objects(s, NIFRID.abbrev):
                    triple = s, NIFRID.abbrev, abbrev
                    eds = anno_trips[triple]
                    #print('aaaaaaaaaaa', g.qname(s), )
                    for a_p, a_o in eds:
                        asdf[a_o]['curie'] = g.qname(s)
                        if 'abbrev' in asdf[a_o]:
                            print(tc.red('WARNING:'), f'{a_o} already has a abbrev "{asdf[a_o]["abbrev"]}" for "{abbrev}"')
                        asdf[a_o]['abbrev'] = abbrev

                #print(asdf)
                for ed, kwargs in sorted(asdf.items()):
                    if 'abbrev' not in kwargs:
                        print('Skipping', ed, 'for\n', kwargs)
                        continue
                    editions.append('{ed}|{label}|{abbrev}|{curie}'.format(ed=g.qname(ed), **kwargs))

        with open('/tmp/' + filename + f'-{file_commit[:8]}.psv', 'wt') as f:
            f.write(out_header + '\n'.join(sorted(out, key=labelkey)))
        if editions:
            with open('/tmp/' + filename + f'-editions-{file_commit[:8]}.psv', 'wt') as f:
                f.write(editions_header + '\n'.join(sorted(editions, key=edkey)))

if __name__ == '__main__':
    main()
