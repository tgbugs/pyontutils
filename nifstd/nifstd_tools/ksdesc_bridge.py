#!/usr/bin/env python3.7
from pyontutils.config import auth
""" Synchronize KnowledgeSpace definitions to the ontology
"""

import os
from glob import glob
from pathlib import Path
from rdflib import Literal
from pyontutils.core import Ont, Source, build
from pyontutils.namespaces import makePrefixes
from pyontutils.closed_namespaces import skos

gitf = auth.get_path('git-local-base')

top_level = glob((gitf / 'ksdesc').as_posix() + '/*')

class ksDefsSource(Source):
    source = 'https://github.com/OpenKnowledgeSpace/ksdesc.git'
    source_original = True

class ksDefs(Ont):
    """ Definitions sourced from knowledge space descriptions. """
    filename = 'ksdesc-defs'
    name = 'Knolwedge Space Defs'
    shortname = 'ksdefs'
    sources = ksDefsSource,
    prefixes = makePrefixes('SCR', 'MBA', 'UBERON', 'PR',
                            #'NIFMOL', 'NIFCELL', 'NIFGA', 'NIFNEURMOR',
                            'NLXMOL', 'SAO', 'NLXCELL', 'NIFEXT', 'BIRNLEX')
    def _triples(self):
        skipped_prefixes = set()
        for putative_dir in top_level:
            if os.path.isdir(putative_dir):
                for putative_md in glob(putative_dir + '/*.md'):
                    prefix = os.path.split(putative_dir)[-1]
                    if prefix in self.prefixes:
                        ident = prefix + ':' + os.path.splitext(os.path.split(putative_md)[-1])[0]
                        id_ = self._graph.expand(ident)
                        with open(putative_md, 'rt') as f:
                            def_ = f.read()

                        for test in ('Description', 'Definition' ):
                            if test in def_:
                                def_ = def_.split(test, 1)[-1].strip().strip('=').strip()
                                break

                        yield id_, skos.definition, Literal(def_)
                    else:
                        skipped_prefixes.add(prefix)
        print(sorted(skipped_prefixes))

def main():
    build(ksDefs, n_jobs=1)

if __name__ == '__main__':
    main()
