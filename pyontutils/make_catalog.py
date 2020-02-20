#!/usr/bin/env python3
from pyontutils.config import auth
__doc__ = f"""Generate ttl/catalog-*.xml

Usage:
    ont-catalog [options]
    ont-catalog [options] <file> ...

Options:
    -b --big                        when creating catalog also import big files
                                    reccomend running this option with pypy3
    -j --jobs=NJOBS                 number of parallel jobs to run [default: 9]
    -d --debug                      break at the end
    -l --ontology-local-repo=OLR    path to ontology [default: {auth.get_path('ontology-local-repo')}]

"""
import os
import tempfile
from glob import glob
from pathlib import Path
from git import Repo
from pyontutils.utils import anyMembers
from pyontutils.core import displayTriples
from pyontutils.ontload import local_imports
try:
    breakpoint
except NameError:
    from IPython import embed as breakpoint


def main():
    from docopt import docopt
    args = docopt(__doc__, version='ont-catalog 0.0.1')
    dobig = args['--big']
    remote_base = 'http://ontology.neuinfo.org/NIF/ttl/'
    olr = Path(args['--ontology-local-repo'])
    local_base = (olr / 'ttl').as_posix() + '/'

    #list of all nif ontologies
    #onts = [f for f in fs if f.endswith('.ttl') or f.endswith('.owl') and 'NEMO_' not in f]

    repo = Repo(olr)
    repo_path = Path(olr)
    tracked_files = [(repo_path / f).as_posix()
                     # FIXME missing scicrunch-registry.ttl
                     for f in repo.git.ls_files('--', 'ttl/').split('\n')
                     if f.endswith('.ttl') or f.endswith('.owl')]

    #_ = [print(f) for f in fs]

    extra_files = []  # TODO pass in via cli?
    mapping = [(remote_base + fragment, fragment)
               for file in tracked_files + extra_files
               for _, fragment in (file.split('/ttl/', 1),)
    ]

    # check for mismatched import and ontology iris
    itrips = local_imports(remote_base, local_base, tracked_files, readonly=True, dobig=dobig)  # XXX these files are big and slow, run at own peril
    sa = {os.path.basename(o):s for s, p, o in itrips if 'sameAs' in p}

    # FIXME should be able to do this by checking what is tracked by git...
    externals = ('CogPO.owl', 'NEMO_vv2.98.owl', 'cogat_v0.3.owl', 'doid.owl',
                 'ero.owl', 'pato.owl', 'pr.owl', 'ro_bfo1-1_bridge.owl', 'uberon.owl')

    for f in tracked_files + extra_files:
        if '/external/' in f and anyMembers(f, *externals):
            basename = os.path.basename(f)
            if basename in sa:
                target = sa[basename]
                if 'external' not in target:
                    mapping.append((target, 'external/' + basename))

    # make a protege catalog file to simplify life
    uriline = '    <uri id="User Entered Import Resolution" name="{ontid}" uri="{filename}"/>'

    xmllines = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
    '<catalog prefer="public" xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">',] + \
    [uriline.format(ontid=ont, filename=file) for ont,file in sorted(mapping)] + \
    ['</catalog>']
    xml = '\n'.join(xmllines)
    with open(f'{tempfile.tempdir}/nif-catalog-v001.xml','wt') as f:
        f.write(xml)

    if args['--debug']:
        breakpoint()

if __name__ == '__main__':
    main()
