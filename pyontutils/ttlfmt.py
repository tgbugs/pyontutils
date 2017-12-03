#!/usr/bin/env python3.6
"""Format ontology files using a uniform ttl serializer from rdflib

Usage:
    ttlfmt [options]
    ttlfmt [options] <file>...

Options:
    -h --help       print this
    -v --verbose    do something fun!
    -a --vanilla    use the regular rdflib turtle serializer
    -c --compact    use the compact turtle serializer
    -u --uncompact  use the uncompact turtle serializer
    -s --slow       do not use a process pool
    -n --nowrite    parse the file and reserialize it but do not write changes
    -o --output=F   serialize all input files to output file
    -p --profile    enable profiling on parsing and serialization
    -d --debug      embed after parsing and before serialization

"""
import os
import sys
from docopt import docopt
import rdflib
from rdflib.plugins.parsers.notation3 import BadSyntax
from concurrent.futures import ProcessPoolExecutor
from pyontutils.utils import readFromStdIn

profile_me = lambda f:f
if __name__ == '__main__':
    args = docopt(__doc__, version="ttlfmt 0")
    if args['--debug']:
        from IPython import embed
    if args['--profile']:
        from desc.prof import profile_me

rdflib.plugin.register('nifttl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'CustomTurtleSerializer')
rdflib.plugin.register('cmpttl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'CompactTurtleSerializer')
rdflib.plugin.register('uncmpttl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'UncompactTurtleSerializer')

def prepare(filepath_or_stream, outpath=None, stream=False):
    if stream:
        infmt_guess = 'turtle'
        if outpath is None:
            outpath = sys.stdout
    else:
        filepath_or_stream = os.path.expanduser(filepath_or_stream)
        _, ext = os.path.splitext(filepath_or_stream)
        filetype = ext.strip('.')
        if filetype == 'ttl':
            infmt_guess = 'ttl'
        else:
            infmt_guess = None
        if outpath is None:
            outpath = filepath_or_stream
        print(filepath_or_stream)
    return dict(source=filepath_or_stream,
                format_guess=infmt_guess,
                outpath=outpath)

formats = ('ttl', None, 'xml', 'n3', 'nt', 'nquads', 'trix',
           'trig', 'hturtle', 'rdfa', 'mdata', 'rdfa1.0', 'html')
@profile_me
def parse(source, format_guess, outpath, graph=rdflib.Graph()):
    filepath = source
    errors = []
    for format in (format_guess, *(f for f in formats if f != format_guess)):
        try:
            graph.parse(source=source, format=format)
            return graph, outpath
        except BadSyntax as e:
            print('PARSING FAILED', source)
            errors.append(e)
    raise BadSyntax(str(errors)) from errors[0]

@profile_me
def serialize(graph, outpath):
    if args['--debug']:
        from IPython import embed
        embed()
    out = graph.serialize(format=outfmt)
    if args['--nowrite']:
        print('PARSING Success', outpath)
    elif not isinstance(outpath, str):  # FIXME not a good test that it is stdout
        outpath.buffer.write(out)
    else:
        with open(outpath, 'wb') as f:
            f.write(out)

def convert(files, outpath=None, stream=False):
    if outpath and len(files) > 1:
        graph = rdflib.Graph()
        [parse(**prepare(file, outpath), graph=graph) for file in files]
        serialize(graph, outpath)
    else:
        file_or_stream = files
        serialize(*parse(**prepare(file_or_stream, outpath, stream)))

def main():
    global args  # vastly preferable to classing everything since this way we can see
    global outfmt  # in 2 lines what is actually shared instead of stuffed into self
    if __name__ != '__main__':
        args = docopt(__doc__, version="ttlfmt 0")

    if args['--vanilla']:
        outfmt = 'turtle'
    elif args['--compact']:
        outfmt = 'cmpttl'
    elif args['--uncompact']:
        outfmt = 'uncmpttl'
    else:
        outfmt = 'nifttl'

    outpath = args['--output']
    files = args['<file>']
    if not files:
        stdin = readFromStdIn(sys.stdin)
        if stdin is not None:
            convert(stdin, outpath, stream=True)
            #fn = sys.stdout.fileno()
            #tty = os.ttyname(fn)
            #with open(tty) as sys.stdin:
                #from IPython import embed
                #embed()
        else:
            print(__doc__)
    else:
        from joblib import Parallel, delayed
        if outpath or args['--slow'] or len(files) == 1:
            [convert(f, outpath=outpath) for f in files]
        else:
            Parallel(n_jobs=9)(delayed(convert)(f) for f in files)

if __name__ == '__main__':
    main()
