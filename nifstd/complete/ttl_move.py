#!/usr/bin/env python3
"""
    Generate a script to move files and update import iris.
"""

import os
from IPython import embed

#source locations TODO we should support arbitrary bases here and enforce subfolder namespace purity
GIT_BASE = '~/git/NIF-Ontology/'
GIT_FOLDER = os.path.expanduser(GIT_BASE + '.git/') 
with open(GIT_FOLDER + 'HEAD', 'rt') as f:
    ref = f.read().strip().split(': ')[-1]
with open(GIT_FOLDER + ref, 'rt') as f:
    head_commit = f.read().strip()

ttl_path = os.path.expanduser(GIT_BASE + 'ttl/')
iri_path = 'http://ontology.neuinfo.org/NIF/ttl/'

utility_path = 'utility'
bridge_path = 'bridge'
unused_path = 'unused'

CORE = ttl_path  + 'core.txt'
BRIDGE = ttl_path + 'bridge.txt'
VIEWS = ttl_path + 'views.txt'

USED = None
UNUSED = None

with open(CORE, 'rt') as f:
    core = [l.strip() for l in f.readlines()]
with open(BRIDGE, 'rt') as f:
    bridge = [l.strip() for l in f.readlines()]
with open(VIEWS, 'rt') as f:
    views = [l.strip() for l in f.readlines()]

used = core + bridge

all_ = [fn for fn in os.listdir(ttl_path) if fn.endswith('.ttl')]

unused = [a for a in all_ if a not in used and a not in views]

move_to_unused = unused
move_to_utility = views

move_dict = {
    utility_path:move_to_utility,
    unused_path:move_to_unused,
}

#embed()

MOVE = 'git mv {src_path} {target_path}'
IMPORT_RENAME = "sed -i 's/{src_iri}/{target_iri}/' {filename}"

commands = ["#/usr/bin/env sh",
            "cd " + GIT_BASE,
            "echo IF YOU SCREW SOMETHING UP YOU CAN REVERT BY RUNNING THE FOLLOWING COMMAND:",
            "echo git reset --hard {commit}".format(commit=head_commit),
            "echo WARNING: if you do this you may loose uncommited changes.",
           ]
for folder in (utility_path, bridge_path, unused_path):
    if not os.path.exists(ttl_path + folder):
        commands.append("mkdir " + ttl_path + folder)

renames, adds, moves = [], [], []
for target_path_folder, src_filenames in sorted(move_dict.items()):
    for filename in src_filenames:
        src_path = ttl_path + filename
        target_path = ttl_path + target_path_folder + '/' + filename
        src_iri = iri_path + filename
        src_iri = src_iri.replace('/','\/')
        target_iri = iri_path + target_path_folder + '/' + filename
        target_iri = target_iri.replace('/','\/')
        rename = IMPORT_RENAME.format(src_iri=src_iri, target_iri=target_iri, filename=ttl_path + '*.ttl')
        move = MOVE.format(src_path=src_path, target_path=target_path)
        renames.append(rename)
        adds.append(src_path)
        moves.append(move)

commands.extend(renames)
commands.append('git diff')
commands.append('git add ' + ' '.join(adds))  # XXX FIXME
commands.append('git commit -m "updated the uri locations ahead of moving unused and utility ttl files"')
commands.extend(moves)
commands.append('git commit -m "this commit completes the moves of ttl files to unused and utility folders"')
commands.extend(commands[2:5])

output = '\n'.join(commands)
with open('generated_move_rename.sh', 'wt') as f:
    f.write(output)
