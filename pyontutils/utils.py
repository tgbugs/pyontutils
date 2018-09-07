#!/usr/bin/env python3.6
"""
    A collection of reused functions and classes.
"""

import os
import math
import asyncio
import hashlib
import inspect
from time import time, sleep
from pathlib import Path
from datetime import datetime, date
from functools import wraps
from collections import namedtuple, MutableMapping
from concurrent.futures import ThreadPoolExecutor
import psutil
import rdflib

working_dir = Path(__file__).absolute().resolve().parent.parent

def TODAY():
    """ This needs to be a function for long running programs. """
    date.today().isoformat()


def UTCNOW(): return datetime.utcnow().isoformat()


rdflib.plugin.register('nifttl', rdflib.serializer.Serializer,
                       'pyontutils.ttlser', 'CustomTurtleSerializer')
rdflib.plugin.register('cmpttl', rdflib.serializer.Serializer,
                       'pyontutils.ttlser', 'CompactTurtleSerializer')
rdflib.plugin.register('uncmpttl', rdflib.serializer.Serializer,
                       'pyontutils.ttlser', 'UncompactTurtleSerializer')
rdflib.plugin.register('scottl', rdflib.serializer.Serializer,
                       'pyontutils.ttlser', 'SubClassOfTurtleSerializer')
rdflib.plugin.register('rktttl', rdflib.serializer.Serializer,
                       'pyontutils.ttlser', 'RacketTurtleSerializer')

rdflib.plugin.register('librdfxml', rdflib.parser.Parser,
                       'pyontutils.librdf', 'libRdfxmlParser')
rdflib.plugin.register('libttl', rdflib.parser.Parser,
                       'pyontutils.librdf', 'libTurtleParser')

def check_value(v):
    if isinstance(v, rdflib.Literal) or isinstance(v, rdflib.URIRef):
        return v
    elif isinstance(v, str) and v.startswith('http'):
        return rdflib.URIRef(v)
    else:
        return rdflib.Literal(v)

def test_notebook():  # also tests ipython
    try:
        config = get_ipython().config
        return 'IPKernelApp' in config
    except NameError as e:
        return False


def test_ipython():
    try:
        config = get_ipython().config
        return 'TerminalInteractiveShell' in config
    except NameError as e:
        return False


def test_test():
    import __main__
    import sys
    return (hasattr(__main__, '__unittest')
            and __main__.__unittest
            or 'nose' in sys.modules)


in_notebook = test_notebook()
in_ipython = test_ipython()
in_test = test_test()


def stack_magic(stack):
    # note: calling globals() here fails because we want globals of the caller
    # note: in ipython with thing: print(name) will not work if on the same line
    # REMEMBER KIDS ALWAYS CALL inspect.stack(0) if you don't want
    # to acess the file system for every frame! (still slow, but better)
    if len(stack) > 2 and 'exec_module' in [f.function for f in stack]:
        for i, frame in enumerate(stack):
            fl = frame[0].f_locals
            if '__builtins__' in fl:
                #print('globals found at', i)
                return fl
    elif in_notebook or in_ipython or in_test:
        index = 1  # this seems to work for now
    else:
        index = -1

    return stack[index][0].f_locals


def subclasses(start):
    for sc in start.__subclasses__():
        yield sc
        yield from subclasses(sc)


def getSourceLine(cls):
    tc = TermColors
    try:
        return inspect.getsourcelines(cls)[-1]
    except OSError:  # we are probably in a debugger
        print(tc.red('WARNING:'),
              tc.yellow(f'No source found for {cls} are you in a debugger?'))
        return 'NO-SOURCE-FOUND'



def currentVMSKb():
    p = psutil.Process(os.getpid())
    return p.memory_info().vms


def memoryCheck(vms_max_kb):
    """ Lookup vms_max using getCurrentVMSKb """
    safety_factor = 1.2
    vms_max = vms_max_kb
    vms_gigs = vms_max / 1024 ** 2
    buffer = safety_factor * vms_max
    buffer_gigs = buffer / 1024 ** 2
    vm = psutil.virtual_memory()
    free_gigs = vm.available / 1024 ** 2
    if vm.available < buffer:
        raise MemoryError('Running this requires quite a bit of memory ~ '
                          f'{vms_gigs:.2f}, you have {free_gigs:.2f} of the '
                          f'{buffer_gigs:.2f} needed')




class injective_dict(MutableMapping):

    class NotInjectiveError(Exception):
        pass

    class KeyAlreadyBoundError(NotInjectiveError):
        pass

    class ValueAlreadyBoundError(NotInjectiveError):
        pass

    def __init__(self, __mm=None, **kwargs):
        self._dict = {}
        self._inj = {}
        if __mm and isinstance(__mm, MutableMapping):
            for k, v in __mm.items():
                self.__setitem__(k, v)

        if kwargs:
            for k, v in kwargs.items():
                self.__setitem__(k, v)

    def inverted(self):
        new_ij = self.__class__()
        new_ij._dict = self._inj
        new_ij._inj = self._dict
        return new_ij

    def __contains__(self, key):
        return key in self._dict

    def __delitem__(self, key):
        value = self._dict[key]
        del self._inj[value]
        del self._dict[key]
        del value

    def __getitem__(self, key):
        return self._dict[key]

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self._dict)

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self._dict)

    def __setitem__(self, key, value):
        if key in self._dict and self._dict[key] != value:
            raise self.KeyAlreadyBoundError(f'{key!r} cannot be bound to {value!r}, '
                                            f'{key!r} is already bound to {self._dict[key]!r}')
        if value in self._inj and self._inj[value] != key:
            raise self.ValueAlreadyBoundError(f'{key!r} cannot be bound to {value!r}, '
                                              f'{value!r} is already bound to {self._inj[value]!r}')

        self._dict[key] = value
        self._inj[value] = key


class OrderInvariantHash:
    def __init__(self, cypher=hashlib.sha256, encoding='utf-8'):
        self.cypher = cypher
        self.encoding = encoding

    def convertToBytes(self, e):
        if isinstance(e, rdflib.BNode):
            raise TypeError('BNode detected, please convert bnodes to '
                            'ints in a deterministic manner first.')
        elif isinstance(e, rdflib.URIRef):
            return e.encode(self.encoding)
        elif isinstance(e, rdflib.Literal):
            return self.makeByteTuple((str(e), e.datatype, e.language))
        elif isinstance(e, int):
            return str(e).encode(self.encoding)
        elif isinstance(e, bytes):
            return e
        elif isinstance(e, str):
            return e.encode(self.encoding)
        else:
            raise TypeError(f'Unhandled type on {e!r} {type(e)}')

    def makeByteTuple(self, t):
        return b'(' + b' '.join(self.convertToBytes(e)
                                for e in t
                                if e is not None) + b')'

    def __call__(self, iterable):
        # convert all strings bytes
        # keep existing bytes as bytes
        # join as follows b'(http://s http://p http://o)'
        # join as follows b'(http://s http://p http://o)'
        # bnodes local indexes are treated as strings and converted
        # literals are treated as tuples of strings
        # if lang is not present then the tuple is only 2 elements

        # this is probably not the fastest way to do this but it works
        #bytes_ = [makeByteTuple(t) for t in sorted(tuples)]
        #embed()
        m = self.cypher()
        # when everything is replaced by an integer or a bytestring
        # it is safe to sort last because identity is ensured
        [m.update(b) for b in sorted(self.makeByteTuple(t) for t in iterable)]
        return m.digest()


def noneMembers(container, *args):
    for a in args:
        if a in container:
            return False
    return True


def anyMembers(container, *args):
    return not noneMembers(container, *args)


def allMembers(container, *args):
    return all(a in container for a in args)


def coln(n, iterable):
    """ Return an iterator on the nth column. """
    for rec in iterable:
        yield rec[n]


def setPS1(script__file__):
    text = 'Running ' + os.path.basename(script__file__)
    os.sys.stdout.write('\x1b]2;{}\x07\n'.format(text))


def refile(script__file__, path):
    return str(Path(script__file__).parent / path)


def relative_path(script__file__):
    # FIXME will break outside of subfolders of working_dir neuron_models folder ...
    rpath = (Path(script__file__).
             resolve().
             absolute().
             relative_to(working_dir.
                         absolute().
                         resolve()).
             as_posix())
    return rpath


def readFromStdIn(stdin=None):
    from select import select
    if stdin is None:
        from sys import stdin
    if select([stdin], [], [], 0.0)[0]:
        return stdin


def async_getter(function, listOfArgs):
    async def future_loop(future_):
        loop = asyncio.get_event_loop()
        futures = []
        for args in listOfArgs:
            future = loop.run_in_executor(None, function, *args)
            futures.append(future)
        print('Futures compiled')
        responses = []
        for f in futures:
            responses.append(await f)
        future_.set_result(responses)
    future = asyncio.Future()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(future_loop(future))
    return future.result()


def deferred(function):
    def wrapper(*args, **kwargs):
        @wraps(function)
        def inner(args=args, kwargs=kwargs):
            return function(*args, **kwargs)
        return inner
    return wrapper


def Async(rate=None, debug=False, collector=None):  # ah conclib
    if rate:
        workers = math.ceil(rate) if rate < 40 else 40
        # 40 comes from the TPE default 5 * cpu cores, this has not been tuned
        executor = ThreadPoolExecutor(max_workers=workers)
    else:
        executor = ThreadPoolExecutor()
        workers = executor._max_workers

    if debug:
        print(rate, workers)

    def inner(generator):
        #Async(rate=rate/2, debug)(funclist[])
        #funclist = list(generator)
        # the real effective throughput I am seeing per os thread is ~350Hz
        # I can push it to about 400Hz setting it to run at 3000Hz with 3000
        # entries but this is trivial to double using multiple processes
        # pushing the set rate higher does seem to max out around 400Hz if
        # the min time_per_job < our trouble threshold which is ping dependent
        #Parallel(generator)
        if rate:
            funclist = list(generator)
            # divide by workers not rate, time_per_job will compensate
            size = math.ceil(len(funclist) / workers) if rate >= 1 else 1
            time_est = len(funclist) / rate
            chunks = chunk_list(funclist, size)
            lc = len(chunks)
            print(f'Time estimate: {time_est}    rate: {rate}Hz    '
                  f'func: {funclist[0]}    args: {len(funclist)}    '
                  f'chunks: {lc}    size: {size}')
            generator = (lambda:list(limited_gen(chunk, smooth_offset=(i % lc)/lc, time_est=time_est, debug=debug, thread=i))  # this was the slowdown culpret
                         for i, chunk in enumerate(sorted(chunks, key=len, reverse=True)))

        async def future_loop(future_):
            loop = asyncio.get_event_loop()
            futures = []
            for wrapped_func_or_limgen in generator:
                future = loop.run_in_executor(executor, wrapped_func_or_limgen)
                futures.append(future)
            print('Futures compiled')
            responses = []
            for f in futures:
                if rate:
                    responses.extend(await f)
                else:
                    responses.append(await f)
            future_.set_result(responses)

        future = asyncio.Future()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future_loop(future))
        return future.result()
    return inner


def limited_gen(chunk, smooth_offset=0, time_est=None, debug=True, thread='_'):
    cumulative_delta = 0
    time_alloted = 0
    time_per_job = (time_est - smooth_offset) / len(chunk)
    if debug: print(f'{thread:0>2}    offset: {smooth_offset:<.4f}    '
                    f'jobs: {len(chunk)}    s/job: {time_per_job:<.4f}    '
                    f'total: {time_est:<.4f}s')
    if smooth_offset:
        sleep(smooth_offset)
    real_start = time()
    for element in chunk:
        real_stop = time_per_job + real_start
        real_start += time_per_job
        yield element()
        stop = time()
        if debug:
            print(f'{thread:<3} {stop:<8f} {real_stop:<10f}     '
                  f'{stop - real_stop:<10f}')
        if stop > real_stop:
            sleep(0)  # give the thread a chance to yield
            continue
        else:
            sleep_time = real_stop - stop
            #if debug: print(f'{thread:<3} {stop:<8f} {real_stop:<10f} {sleep_time:<10f}')
            sleep(sleep_time)


def mysql_conn_helper(host, db, user, port=3306):
    kwargs = {
        'host':host,
        'db':db,
        'user':user,
        'port':port,
        'password':None,  # no you may NOT pass it in
    }
    port = int(port)
    with open(os.path.expanduser('~/.mypass'), 'rt') as f:
        entries = [l.strip().split(':', 4) for l in f.readlines()]
    for e_host, e_port, e_db, e_user, e_pass in entries:
        e_port = int(e_port)
        if host == e_host:
            print('host:', host)
            if  port == e_port:
                print('port:', port)
                if db == e_db or e_db == '*':  # FIXME bad * expansion
                    print('database:', db)
                    if user == e_user:
                        print('user:', user)
                        kwargs['password'] = e_pass  # last entry wins
    e_pass = None
    if kwargs['password'] is None:
        raise ConnectionError(f'No record for {user}@{host}:{port}/{db}')

    return kwargs


def chunk_list(list_, size):
    """ Split a list list_ into sublists of length size.
        NOTE: len(chunks[-1]) <= size. """
    ll = len(list_)
    if ll <= size:
        return [list_]
    elif size == 0:
        return list_ # or None ??
    elif size == 1:
        return [[l] for l in list_]
    else:
        chunks = []
        for start, stop in zip(range(0, ll, size), range(size, ll, size)):
            chunks.append(list_[start:stop])
        chunks.append(list_[stop:])  # snag unaligned chunks from last stop
        return chunks


class dictParse:
    """ Base class for building dict parsers (that can also handle lists).
        Methods should be named after the keys in the dict and specify
        what to do with the contents.
    """
    def __init__(self, thing, order=[]):
        if type(thing) == dict:
            if order:
                for key in order:
                    func = getattr(self, key, None)
                    if func:
                        func(thing.pop(key))
            self._next_dict(thing)

        #elif type(thing) == list:
            #self._next_list(thing)
        else:
            print('NOPE')

    def _next_dict(self, dict_):
        for key, value in dict_.items():
            func = getattr(self, key, None)
            if func:
                func(value)

    def _next_list(self, list_):
        for value in list_:
            if type(value) == dict:
                self._next_dict(value)

    def _terminal(self, value):
        print(value)
        pass


class rowParse:
    """ Base class for parsing a list of fixed lenght lists whose
        structure is defined by a header (eg from a csv file).
        Methods should match the name of the 'column' header.
    """

    class SkipError(BaseException):
        pass

    def __init__(self, rows, header=None, order=[]):
        if header is None:
            header = [c.split('(')[0].strip().replace(' ', '_').replace('+', '')
                      for c in rows[0]]
            rows = rows[1:]
        eval_order = []
        self._index_order = []
        for column in order:
            index = header.index(column)
            self._index_order.append(index)
            eval_order.append(header.pop(index))
        eval_order.extend(header)  # if not order then just do header order

        self.lookup = {index:name for index, name in enumerate(eval_order)}

        for name, obj in inspect.getmembers(self):
            if inspect.ismethod(obj) and not name.startswith('_'):  # FIXME _ is hack
                _set = '_set_' + name
                setattr(self, _set, set())
                @wraps(obj)
                def getunique(value, set_=_set, func=obj):  # ah late binding hacks
                    getattr(self, set_).add(value)
                    return func(value)
                setattr(self, name, getunique)

        self._next_rows(rows)
        self._end()

    def _order_enumerate(self, row):
        i = 0
        for index in self._index_order:
            yield i, row.pop(index)
            i += 1
        for value in row:
            yield i, value
            i += 1

    def _next_rows(self, rows):
        for self._rowind, row in enumerate(rows):
            skip = False
            for i, value in self._order_enumerate(row):
                func = getattr(self, self.lookup[i], None)
                if func:
                    try:
                        func(value)
                    except self.SkipError:
                        skip = True  # ick
                        break
            if not skip:
                self._row_post()

    def _row_post(self):
        """ Run this code after all columns have been parsed """
        pass

    def _end(self):
        """ Run this code after all rows have been parsed """
        pass


class byCol:
    def __init__(self, rows, header=None):
        if header is None:
            header = [c.split('(')[0].strip().replace(' ', '_').replace('+', '')
                      for c in rows[0]]
            rows = rows[1:]

        for name, col in zip(header, zip(*rows)):
            setattr(self, name, list(col))

        nt = namedtuple('row', header)
        self.rows = [nt(*r) for r in rows]

    def __iter__(self):
        yield from self.rows


class _TermColors:
    ENDCOLOR = '\033[0m'
    colors = dict(
        BOLD      = '\033[1m',
        FAINT     = '\033[2m',  # doesn't work on urxvt
        IT        = '\033[3m',
        UL        = '\033[4m',
        BLINKS    = '\033[5m',
        BLINKF    = '\033[6m',  # same as S?
        REV       = '\033[7m',
        HIDE      = '\033[8m',  # doesn't work on urxvt
        XOUT      = '\033[9m',  # doesn't work on urxvt
        FONT1     = '\033[10m',  # doesn't work on urxvt use '\033]50;%s\007' % "fontspec"
        FONT2     = '\033[11m',  # doesn't work on urxvt
        FRAKTUR   = '\033[20m',  # doesn't work on urxvt
        OFF_BOLD  = '\033[21m',
        NORMAL    = '\033[22m',
        OFF_IT    = '\033[23m',
        OFF_UL    = '\033[24m',
        OFF_BLINK = '\033[25m',
        POSITIVE  = '\033[27m',
        OFF_HIDE  = '\033[28m',
        RED       = '\033[31m',
        GREEN     = '\033[32m',
        YELLOW    = '\033[33m',
        BLUE      = '\033[34m',
        PURPLE    = '\033[35m',
        CYANE     = '\033[36m',
        WHITE     = '\033[37m',
        LTRED     = '\033[91m',
        LTGREEN   = '\033[92m',
        LTYELLOW  = '\033[93m',
        LTBLUE    = '\033[94m',
    )

    def __init__(self):
        for color, esc in self.colors.items():  # esc blocks runtime changes
            def latebindingfix(string, e=esc):
                return self.endcolor(e + string)
            setattr(self, color.lower(), latebindingfix)

    def endcolor(self, string):
        if string.endswith(self.ENDCOLOR):
            return string
        else:
            return string + self.ENDCOLOR


TermColors = _TermColors()
