#!/usr/bin/env python3.6
#!/usr/bin/env pypy3
"""Format ontology files using a uniform ttl serializer from rdflib

Usage:
    ttlfmt [options]
    ttlfmt [options] <file>...
    ttlfmt [options] <file>...

Options:
    -h --help       print this
    -v --verbose    do something fun!
    -a --vanilla    use the regular rdflib turtle serializer
    -y --subclass   use the subClassOf turtle serializer
    -c --compact    use the compact turtle serializer
    -u --uncompact  use the uncompact turtle serializer
    -r --racket     use the racket turtle serializer
    -j --jsonld     use the rdflib-jsonld serializer
    -f --format=FM  specify the input format (used for pipes)
    -t --outfmt=F   specify the output format [default: nifttl]
    -s --slow       do not use a process pool
    -n --nowrite    parse the file and reserialize it but do not write changes
    -o --output=FI  serialize all input files to output file
    -p --profile    enable profiling on parsing and serialization
    -d --debug      embed after parsing and before serialization

"""
import os
import sys
from io import StringIO, TextIOWrapper
from json.decoder import JSONDecodeError
from concurrent.futures import ProcessPoolExecutor
from docopt import docopt
import rdflib
from rdflib.plugins.parsers.notation3 import BadSyntax
from pyontutils.utils import readFromStdIn

profile_me = lambda f:f

def getVersion():
    ttlser = rdflib.plugin.get('nifttl', rdflib.serializer.Serializer)
    ttlser_version = ttlser._CustomTurtleSerializer__version  # FIXME
    version = f"ttlfmt v0.0.1\nttlser {ttlser_version}"
    return version

if __name__ == '__main__':
    args = docopt(__doc__, version=getVersion())
    if args['--debug']:
        from IPython import embed
    if args['--profile']:
        from desc.prof import profile_me


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
        elif filetype == 'json':
            infmt_guess = 'json-ld'
        else:
            infmt_guess = None
        if outpath is None:
            outpath = filepath_or_stream
        print(filepath_or_stream)
    return dict(source=filepath_or_stream,
                format_guess=infmt_guess,
                outpath=outpath)

formats = ('ttl', 'json-ld', None, 'xml', 'n3', 'nt', 'nquads', 'trix',
           'trig', 'hturtle', 'rdfa', 'mdata', 'rdfa1.0', 'html')
@profile_me
def parse(source, format_guess, outpath, graph=None):
    graph = rdflib.Graph() if graph is None else graph
    errors = []
    if args['--format']:
        format_guess = args['--format']
    for format in (format_guess, *(f for f in formats if f != format_guess)):
        # TODO we don't need to reset just saved parsed streams to the point where they fail?
        if type(source) == TextIOWrapper:  # stdin can't reset
            src = source.read()
            source = StringIO(src)
        try:
            graph.parse(source=source, format=format)
            a = next(iter(graph))
            return graph, outpath
        except (StopIteration, BadSyntax, JSONDecodeError) as e:
            print('PARSING FAILED', format, source)
            if args['--format']:  # or format_guess != None:
                raise e
            errors.append(e)
            if type(source) == StringIO:
                source.seek(0)
    raise BadSyntax(str(errors)) from errors[0]

@profile_me
def serialize(graph, outpath):
    if args['--debug']:
        if type(outpath) == type(sys.stdout):
            pipe_debug(graph=graph, outpath=outpath)
        else:
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

def convert(file, outpath=None, stream=False):
    if stream or type(file) == str:
        file_or_stream = file
        serialize(*parse(**prepare(file_or_stream, outpath, stream)))
    else:
        file_list = file
        graph = rdflib.Graph()
        [parse(**prepare(file, outpath), graph=graph) for file in file_list]
        serialize(graph, outpath)

def pipe_debug(*args, source=None, graph=None, outpath=None, **kwargs):
    fn = sys.stdout.fileno()
    tty = os.ttyname(fn)
    with open(tty) as sys.stdin:
        from IPython import embed
        embed()

def main():
    global args  # vastly preferable to classing everything since this way we can see
    global outfmt  # in 2 lines what is actually shared instead of stuffed into self
    if __name__ != '__main__':
        args = docopt(__doc__, version=getVersion())

    if args['--subclass']:
        outfmt = 'scottl'
    elif args['--vanilla']:
        outfmt = 'turtle'
    elif args['--compact']:
        outfmt = 'cmpttl'
    elif args['--uncompact']:
        outfmt = 'uncmpttl'
    elif args['--jsonld']:
        outfmt = 'json-ld'
    elif args['--racket']:
        outfmt = 'rktttl'
    else:
        outfmt = args['--outfmt']

    outpath = args['--output']
    files = args['<file>']
    if not files:
        stdin = readFromStdIn(sys.stdin)
        if stdin is not None:
            convert(stdin, outpath, stream=True)
        else:
            print(__doc__)
    else:
        from joblib import Parallel, delayed
        if outpath or args['--slow'] or len(files) == 1:
            if len(files) == 1:
                files,  = files
            convert(files, outpath=outpath)
        else:
            Parallel(n_jobs=9)(delayed(convert)(f) for f in files)

if __name__ == '__main__':
    main()
