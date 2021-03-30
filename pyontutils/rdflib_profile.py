#!/usr/bin/env python3
"""run rdflib performance tests

Usage:
    rdflib_profile [options]

Options:
    -s --setup      run setup only
    -p --pipenv     setup pipenv
    -l --local      run tests in the parent process rather than forking
"""

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
from ttlser import CustomTurtleSerializer
from rdflib.plugins.serializers.turtle import TurtleSerializer
try:
    breakpoint
except NameError:
    from IPython import embed as breakpoint


class _prof:
    #filters = 'namespace.py', 'compute_qname'
    filters = 'turtle.py', 'serialize'

    def serialize(self, stream, base=None, encoding='utf-8',
                  spacious=None, **args):
        pr = cProfile.Profile()
        pr.enable()
        if 'Custom' in self.__class__.__name__:
            out = CustomTurtleSerializer.serialize(self, stream, base, encoding, spacious, **args)
        else:
            out = TurtleSerializer.serialize(self, stream, base, encoding, spacious, **args)
        pr.disable()
        ps = self.do_stats(pr)
        self.__class__.results.append(ps)  # TODO tag with additional information

    def do_stats(self, pr):
        ps = pstats.Stats(pr)
        #print({k:v for k, v in ps.stats.items()})
        _ = [print(v[:4], ',') for k, v in ps.stats.items()
             if self.filters[0] in k[0] and self.filters[1] == k[2]]
        return ps


class TurtleSerializer_prof(_prof, TurtleSerializer):
    results = []


class CustomTurtleSerializer_prof(_prof, CustomTurtleSerializer):
    results = []


# FIXME this breaks results reporting
rdflib.plugin.register('pttl', rdflib.serializer.Serializer, 'pyontutils.rdflib_profile', 'TurtleSerializer_prof')
rdflib.plugin.register('pnifttl', rdflib.serializer.Serializer, 'pyontutils.rdflib_profile', 'CustomTurtleSerializer_prof')


def do_serialize(graph, reps, filename, format):
    sys.stdout.write('["' + Path.cwd().name +
                     '", "' + filename +
                     '", ' + str(_prof.filters) + ',\n[')
    for i in range(reps):
        ser = graph.serialize(format=format, encoding='utf-8')
    sys.stdout.write(']],')
    return ser


def run(reps=2, filenames=tuple(), functions=tuple()):
    if 'rdflib-4' in Path.cwd().as_posix():  # FIXME
        format = 'pttl'
    else:
        format = 'pttl'
        #format = 'pnifttl'

    sys.stdout.write('[')
    for filename in filenames:
        if os.path.exists(filename):
            graph = rdflib.Graph()
            graph.parse(filename, format='turtle')
            do_serialize(graph, reps, os.path.basename(filename), format)

    for function in functions:
        function(reps, format=format)

    sys.stdout.write(']')

def constructed(reps=2, format='nifttl'):
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

    do_serialize(graph, reps, 'prefix_test', format)

def filenames_from_fetch(fetch, cwd):
    for f in fetch:
        yield (cwd / Path(f).name).as_posix()

def main():
    # TODO test parsing since the trie shifts a lot of the load there

    REPS = 1  # 10 is a good number

    # files to test
    fetch = ('http://ontology.neuinfo.org/NIF/ttl/NIF-Chemical.ttl',
             'http://ontology.neuinfo.org/NIF/ttl/NIF-Molecule.ttl',
             'https://raw.githubusercontent.com/tgbugs/pyontutils/master/test/nasty.ttl')

    # functions to test
    functions = constructed,

    if 'TESTING' in os.environ:
        filenames = [f.strip("'").rstrip("'") for f in os.environ['FILENAMES'].split("' '")]
        run(REPS, filenames=filenames, functions=functions)
    else:
        import shutil
        import requests
        from docopt import docopt

        args = docopt(__doc__)

        if args['--local']:
            filenames = list(filenames_from_fetch(fetch, Path.cwd().parent))  # FIXME
            run(REPS, filenames=filenames, functions=functions)
            # check *.results
            breakpoint()
            return

        filenames = list(filenames_from_fetch(fetch, Path.cwd()))
        for name, fe in zip(filenames, fetch):
            if not Path(name).exists():
                print(f'fetching test file {fe}')
                resp = requests.get(fe)
                with open(name, 'wb') as f:
                    f.write(resp.content)

        thisfile = Path(__file__).resolve().absolute()
        thisfolder = thisfile.parent
        files = thisfile, thisfolder / '__init__.py'

        venvs = 'rdflib-4.2.2', 'rdflib-5.0.0'

        data = {}
        pipenv = args['--pipenv']
        for venv in venvs:
            p = Path.cwd() / venv
            po = p / 'pyontutils'
            if pipenv:
                if p.exists():
                    shutil.rmtree(venv)
                po.mkdir(parents=True)

                pkg, version = venv.split('-', 1)

                os.system(f'cd {p.as_posix()} && unset PYTHONPATH && pipenv install {pkg}=={version}')

            for f in files:
                shutil.copy(f.as_posix(), (po / f.name).as_posix())

            if args['--setup']:
                continue

            env = os.environ.copy()
            venv = os.path.expanduser(venv)
            env['PATH'] = venv + '/bin:' + env['PATH']
            env['TESTING'] = ''
            env['PYTHONPATH'] = p.as_posix()
            env['FILENAMES'] = ' '.join(repr(f) for f in filenames)
            sp = subprocess.Popen(['pipenv', 'run', 'pyontutils/rdflib_profile.py'], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  env=env, cwd=p.as_posix())
            out, err = sp.communicate()
            print(out.decode())
            asdf = literal_eval(out.decode())
            data[os.path.basename(venv)] = asdf  # nclass, ncalls, tottime, cumtime

        if args['--setup']:
            return

        n_files_tested = len(fetch + functions)
        perf_result_index = 3
        avg_cumtime = [{k:sum([_[3] for _ in v[i][perf_result_index]]) / REPS
                        for k, v in data.items()}
                       for i in range(n_files_tested)]

        print(avg_cumtime)

        asdf = []  # alternate computation
        for i, name in enumerate(fetch + tuple(f.__name__ for f in functions)):
            z = {'name':name}
            for k, v in data.items():
                nv = 0
                for q in v[i][perf_result_index]:
                    nv += q[3]
                nv = nv/REPS
                z[k] = nv
            asdf.append(z)

        print(asdf)
        breakpoint()

if __name__ == '__main__':
    main()
