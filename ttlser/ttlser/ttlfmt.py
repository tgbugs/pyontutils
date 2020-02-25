#!/usr/bin/env python3.7
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
    -d --debug      launch debugger after parsing and before serialization

"""
import os
import sys
from io import StringIO, TextIOWrapper
from json.decoder import JSONDecodeError
from concurrent.futures import ProcessPoolExecutor
from docopt import docopt, parse_defaults
import rdflib
from rdflib.plugins.parsers.notation3 import BadSyntax

defaults = {o.name:o.value if o.argcount else None for o in parse_defaults(__doc__)}
GRAPHCLASS = rdflib.Graph


def getVersion():
    ttlser = rdflib.plugin.get('nifttl', rdflib.serializer.Serializer)
    ttlser_version = ttlser._CustomTurtleSerializer__version  # FIXME
    version = "ttlfmt v0.0.2\nttlser {}".format(ttlser_version)
    return version


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


def parse(source, format_guess, outpath, graph=None, infmt=None, graph_class=GRAPHCLASS):
    graph = graph_class() if graph is None else graph
    errors = []
    if infmt:
        format_guess = infmt

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
            if infmt:  # or format_guess != None:
                raise e
            errors.append(e)
            if type(source) == StringIO:
                source.seek(0)
    raise BadSyntax(str(errors)) from errors[0]


def serialize(graph, outpath, outfmt=defaults['--outfmt'], debug=False, profile=False):
    if debug:
        if type(outpath) == type(sys.stdout):
            pipe_debug(graph=graph, outpath=outpath)
        else:
            breakpoint()

    elif profile and type(outpath) != type(sys.stdout):
        *_, _out = outpath.rsplit('/', 1)
        print('triple count for {_out}:'.format(_out=_out), len(graph))

    if outfmt == 'json-ld':
        kwargs = {'auto_compact': True}
    else:
        kwargs = {}
    out = graph.serialize(format=outfmt, **kwargs)
    if profile:
        print('PARSING Success', outpath)
    elif not isinstance(outpath, str):  # FIXME not a good test that it is stdout
        outpath.buffer.write(out)
    else:
        with open(outpath, 'wb') as f:
            f.write(out)


def convert(file_or_list_or_stream, outpath=None, stream=False,
            infmt=None, outfmt=defaults['--outfmt'],
            debug=False, profile=False, graph_class=GRAPHCLASS):
    if stream or type(file_or_list_or_stream) == str:
        file_or_stream = file_or_list_or_stream
        serialize(*parse(**prepare(file_or_stream, outpath, stream),
                         infmt=infmt),
                  outfmt=outfmt, debug=debug, profile=profile)
    else:
        # file list is used here because this allows is to merge files
        # without any additional code if we pass it more than one file
        # in normal use a tuple with a single element is passed in
        file_list = file_or_list_or_stream
        if outpath is not None:
            graph = graph_class()
            [parse(**prepare(file, outpath), graph=graph, infmt=infmt) for file in file_list]
            serialize(graph, outpath, outfmt=outfmt,
                      debug=debug, profile=profile)
        else:
            [convert(file, infmt=infmt, outfmt=outfmt,
                     debug=debug, profile=profile,
                     graph_class=graph_class) for file in file_list]


def pipe_debug(*args, source=None, graph=None, outpath=None, **kwargs):
    fn = sys.stdout.fileno()
    tty = os.ttyname(fn)
    with open(tty) as sys.stdin:
        breakpoint()


def main():
    #global args  # vastly preferable to classing everything since this way we can see
    #global outfmt  # in 2 lines what is actually shared instead of stuffed into self
    args = docopt(__doc__, version=getVersion())

    profile = args['--profile']
    if profile:
        try:
            from desc.prof import profile_me
            global parse
            global serialize
            parse = profile_me(parse)
            serialize = profile_me(serialize)
        except ImportError:
            pass

    infmt = args['--format']
    debug = args['--debug']

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
        from ttlser.utils import readFromStdIn
        stdin = readFromStdIn(sys.stdin)
        if stdin is not None:
            convert(stdin, outpath, stream=True,
                    infmt=infmt, outfmt=outfmt,
                    debug=debug, profile=profile)
        else:
            print(__doc__)
    else:
        lenfiles = len(files)
        if outpath or args['--slow'] or lenfiles == 1:
            if lenfiles == 1:
                files,  = files

            convert(files, outpath=outpath,
                    infmt=infmt, outfmt=outfmt,
                    debug=debug, profile=profile)
        else:
            from joblib import Parallel, delayed
            nj = 9
            if lenfiles < nj:
                nj = lenfiles

            Parallel(n_jobs=nj, verbose=10)(delayed(convert)
                                            (file,
                                             infmt=infmt, outfmt=outfmt,
                                             debug=debug, profile=profile)
                                            for file in files)


if __name__ == '__main__':
    main()
