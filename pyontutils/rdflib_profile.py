#!/usr/bin/env python

from __future__ import print_function
import os
import sys
import string
import rdflib
import cProfile
import pstats
import subprocess
from ast import literal_eval
from pathlib import Path
from pyontutils.ttlser import CustomTurtleSerializer
from pyontutils.config import devconfig
from IPython import embed

class CustomTurtleSerializer_prof(CustomTurtleSerializer):
    filters = 'namespace.py', 'compute_qname'
    def serialize(self, stream, base=None, encoding=None,
                  spacious=None, **args):
        pr = cProfile.Profile()
        pr.enable()
        out = CustomTurtleSerializer.serialize(self, stream, base, encoding, spacious, **args)
        pr.disable()
        self.do_stats(pr)
        return out

    def do_stats(self, pr):
        ps = pstats.Stats(pr)
        _ = [print(v[:4], ',') for k, v in ps.stats.items()
             if self.filters[0] in k[0] and self.filters[1] == k[2]]

rdflib.plugin.register('nifttl', rdflib.serializer.Serializer, 'pyontutils.rdflib_profile', 'CustomTurtleSerializer_prof')

def do_serialize(graph, reps, filename):
    sys.stdout.write('["' + filename + '",' + str(CustomTurtleSerializer_prof.filters) + ' , [')
    for i in range(reps):
        out = graph.serialize(format='nifttl')
    sys.stdout.write(']],')
    return out

def run(reps=2):
    filenames = "NIF-Ontology/ttl/NIF-Chemical.ttl", "NIF-Ontology/ttl/NIF-Molecule.ttl", "/tmp/uberon.ttl"
    sys.stdout.write('[')
    for filename in filenames:
        if not filename.startswith('/'):
            path = Path(devconfig.git_local_base, filename)
            filename = path.as_posix()

        if os.path.exists(filename):
            graph = rdflib.Graph()
            graph.parse(filename, format='turtle')
            out = do_serialize(graph, reps, os.path.basename(filename))
    out = constructed(reps)
    sys.stdout.write(']')

def constructed(reps=2):
    graph = rdflib.Graph()
    graph.namespace_manager.bind('owl', 'http://www.w3.org/2002/07/owl#Class')
    atz = string.ascii_lowercase[:26]
    base = 'http://thing.org/'
    bases = []
    for l in atz:
        base += '%s_' % l
        bases.append(base)
        graph.namespace_manager.bind(l, base)

    for base in bases:
        for i in range(0,999):
            graph.add((rdflib.URIRef(base + str(i)), rdflib.RDF.type, rdflib.OWL.Class))

    out = do_serialize(graph, reps, 'prefix_test')
    return out

def main():
    # To use this file all you need to do is have the versions of rdflib you
    # want to test set up in the requisite venvs and have all the filenames
    # listed in run extant on your filesystem
    REPS = 10
    if 'TESTING' in os.environ:
        run(REPS)
    else:
        venvs = '~/files/venvs/35_rdflib_upstream', '~/files/venvs/35_rdflib_tgbugs_master',
        data = {}
        for venv in venvs:
            env = os.environ.copy()
            venv = os.path.expanduser(venv)
            env['VIRTUAL_ENV'] = venv
            env['PATH'] = venv + '/bin:' + env['PATH']
            env['TESTING'] = ''
            p = subprocess.Popen(['./rdflib_profile.py'], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
            out, err = p.communicate()
            print(out.decode())
            asdf = literal_eval(out.decode())
            data[os.path.basename(venv)] = asdf  # nclass, ncalls, tottime, cumtime

        avg_cumtime = [{k:sum([_[3] for _ in v[i][2]])/REPS for k,v in data.items()} for i in range(3)]

        asdf = []
        for i in range(4):
            z = {}
            for k, v in data.items():
                nv = 0
                for q in v[i][2]:
                    nv += q[3]
                nv = nv/REPS
                z[k] = nv
            asdf.append(z)
        embed()

if __name__ == '__main__':
    main()
