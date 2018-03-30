#!/usr/bin/env python3
""" Script for deploying files from github to the nifstd ftp. Must be run from the root of the ontology directory so we can glob files. NOTE: you can shoot yourself in the foot with this.
Usage:
    deploy [--branch=BRANCH] <path>...
    deploy [--commit=COMMIT] <path>...
    deploy <path>...
Options:
    -b --branch=BRANCH      Deploy from this branch [default: master].
    -c --commit=COMMIT      Deploy from this commit.
"""
# bug: <path>... by itself must come LAST under usage for parsing to work
import subprocess
from os import getcwd
from os.path import sep
from glob import glob
from datetime import datetime
from docopt import docopt
from IPython import embed
from requests import head

SERVER = 'nif-apps1.crbs.ucsd.edu'
FTP_BASE_PATH='/var/www/html/ontology.neuinfo.org/NIF/'
GITHUB_BASE_URL='https://raw.githubusercontent.com/SciCrunch/NIF-Ontology/'

def main():
    if getcwd().split(sep)[-1] != 'NIF-Ontology':
        print('This script must be invoked from the ontology git directory! Usually ~/git/NIF-Ontology')
        return

    args = docopt(__doc__, version='deploy 0')
    print(args)
    if args['--commit'] is not None:
        COMMIT = args['--commit']
    else:
        BRANCH_COMMIT = args['--branch']
        # get the exact commit in case someone pushes in the middle
        COMMIT = subprocess.check_output(['git', 'ls-remote', 'origin', BRANCH_COMMIT]).decode().split('\t')[0]

    FILEPATHS = args['<path>']

    filepaths = []
    for filepath in FILEPATHS:
        filepaths.extend(glob(filepath))

    template = 'sudo curl -o {FTP_BASE_PATH}{filepath} {GITHUB_BASE_URL}{COMMIT}/{filepath}'

    if not filepaths:
        print('No files found! Exiting...')
        return
    elif not head(GITHUB_BASE_URL + COMMIT + '/ttl/nif.ttl').ok:
        print('Commit or branch "%s" not found!' % COMMIT)
        return

    commands = []
    for filepath in filepaths:
        kwargs = {
            'FTP_BASE_PATH':FTP_BASE_PATH,
            'GITHUB_BASE_URL':GITHUB_BASE_URL,
            'COMMIT':COMMIT,
            'filepath':filepath,
        }
        string = template.format(**kwargs)
        commands.append(string)

    TIMESTAMP = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')  # ISO8601 boys
    string = 'sudo echo \'{} {} {}\' >> {FTP_BASE_PATH}updates.log'.format(TIMESTAMP,
                    COMMIT, str(filepaths), FTP_BASE_PATH=FTP_BASE_PATH)
    commands.append(string)

    COMMAND = ' && '.join(commands)

    run_it = 'ssh {server} "{command}"'.format(server=SERVER, command=COMMAND)

    print(run_it)


if __name__ == '__main__':
    main()
