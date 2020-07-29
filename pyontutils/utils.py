#!/usr/bin/env python3.7
"""
    A collection of reused functions and classes.
    Depends only on python standard library.
"""

import os
import ast
import math
import asyncio
import inspect
import logging
from time import time, sleep
from uuid import uuid4
from pathlib import Path
from datetime import datetime, date, timezone
from functools import wraps
from collections import namedtuple
from collections.abc import MutableMapping
from concurrent.futures import ThreadPoolExecutor
from colorlog import ColoredFormatter
from .clifun import python_identifier
import nest_asyncio


def get_working_dir(script__file__):
    """ hardcoded sets the 'equivalent' working directory if not in git """
    start = Path(script__file__).resolve()
    _root = Path(start.drive + start.root)  # posix + win
    working_dir = start
    while not list(working_dir.glob('.git')):
        if working_dir == _root:
            return

        working_dir = working_dir.parent

    return working_dir


# time functions TODO object version? use case not well understood enough yet

def TZLOCAL():
    return datetime.now(timezone.utc).astimezone().tzinfo


def TODAY():
    """ This needs to be a function for long running programs. """
    return date.today().isoformat()


def UTCNOW(): return datetime.utcnow().isoformat()


def utcnowtz(): return datetime.now(tz=timezone.utc)


def isoformat(datetime_instance, timespec='auto'):
    return (datetime_instance
            .isoformat(timespec=timespec)
            .replace('.', ',')
            .replace('+00:00', 'Z'))

def isoformat_safe(datetime_instance, timespec='auto'):
    """ portable file system safe iso format (sigh) """
    # FIXME this is super inefficient implement from scratch
    #'%Y%m%dT%H%M%S{}%z'
    unsafe = isoformat(datetime_instance, timespec)
    return unsafe.replace('-', '').replace(':', '')


def timeformat_friendly(datetime_instance, timespec='auto'):
    """ a not quite iso format that is file system safe
        to reach isoformat remove all dashes"""
    unsafe = isoformat(datetime_instance, timespec)
    return unsafe.replace(':', '')


def NOWDANGER(*, implicit_tz=None, timespec='auto'):
    """ now without a timezone, if you use this you WILL encounter
        a problem at some point in the future because the actual
        timezone is implicit and if you ever have to move a server
        you will want to record the original timezone to preserve
        the sequntial nature of the sequence

        the implicit_tz field is not used by the function but
        is there to document the original expectation of the
        programmer in the event that it changes in the future """

    return isoformat(datetime.now(), timespec=timespec)


def NOWISO(timespec='auto'):
    return isoformat(datetime.now(tz=TZLOCAL()), timespec=timespec)


def UTCNOWISO(timespec='auto'):
    """ timespec is the smallest level of percision rendered """
    return isoformat(utcnowtz(), timespec=timespec)


def logToFile(logger, path):
    lfh = logging.FileHandler(path.as_posix())
    lfh.setFormatter(logger.handlers[0].formatter)
    logger.addHandler(logger)


def makeSimpleLogger(name, color=True):
    # TODO use extra ...

    # remove any logging set by an inadvertent call to basicConfig
    # FIXME probably not the friendliest thing to do ...
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    fmt = ('[%(asctime)s] - %(levelname)8s - '
           '%(name)14s - '
           '%(filename)16s:%(lineno)-4d - '
           '%(message)s')
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    cfmt = ('%(green)s[%(asctime)s]%(reset)s - '
            '%(log_color)s%(levelname)8s%(reset)s - '
            '%(name)14s - '
            '%(blue)s%(filename)16s:%(lineno)-4d%(reset)s - '
            '%(message)s')
    formatter = ColoredFormatter(cfmt,
                                 #"%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s",
                                 #datefmt=None,
                                 reset=True,
                                 log_colors={
                                     'DEBUG':    'cyan',
                                     'INFO':     'green',
                                     'WARNING':  'yellow',
                                     'ERROR':    'bold_purple',
                                     'CRITICAL': 'red,bg_white',
                                 },
                                 secondary_log_colors={},
                                 style='%')

    if not color:
        formatter = logging.Formatter(fmt)

    ch = logging.StreamHandler()  # FileHander goes to disk
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


log = makeSimpleLogger('pyontutils')


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
    function_names = [f.function for f in stack]
    if len(stack) > 2 and 'exec_module' in function_names:
        for i, frame in enumerate(stack):
            fl = frame[0].f_locals
            if '__builtins__' in fl:
                #print('globals found at', i)
                return fl
    elif in_notebook or in_ipython or in_test:
        index = 1  # this seems to work for now
    elif function_names.count('main') >= 2:
        # FIXME this is a hack that only works
        # if the main of another module is called
        # it doesn't actually fix the case where
        # a context manager is used inside a class
        f = stack[1][0]
        if '__globals__' in f.f_globals:
            return f.f_globals['__globals__']

        index = -1
    else:
        index = -1

    return stack[index][0].f_locals


def subclasses(start):
    if issubclass(start, type):
        scs = start.__subclasses__(start)
    else:
        scs = start.__subclasses__()

    for sc in scs:
        if sc is not None:
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


def cacheout(function):
    # only runs the first time
    # expects a class
    name = '_cache_' + function.__name__
    cacheout_done_name = '_cacheout_' + function.__name__
    first = [True]
    @wraps(function)
    def inner(self, *args, **kwargs):
        out = function(self, *args, **kwargs)
        if not hasattr(self, cacheout_done_name):
            setattr(self, name, out)

        return out

    return inner


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
    """ set the title of the terminal window

        This is in a try block because colorama (used by colorlog)
        wraps redirected stdout to strip certain control codes which
        can cause an
        AttributeError: 'NoneType' object has no attribute 'set_title'
        because colorama changes os.sys.stdout.write in a way that
        removes the call to set_title """

    try:
        text = 'Running ' + os.path.basename(script__file__)
        os.sys.stdout.write('\x1b]2;{}\x07\n'.format(text))
    except AttributeError as e:
        log.exception(e)


def refile(script__file__, path):
    return str(Path(script__file__).parent / path)


def relative_path(script__file__):
    # FIXME will break outside of subfolders of working_dir neuron_models folder ...
    working_dir = get_working_dir(script__file__)
    rpath = (Path(script__file__).
             resolve().
             relative_to(working_dir.
                         resolve()).
             as_posix())
    return rpath


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

try:
    nest_asyncio.apply()
except Exception as e:
    log.exception(e)
    
def Async(rate=None, debug=False, collector=None):  # ah conclib

    # FIXME can't break this with C-c
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
            if not funclist:
                return tuple()  # make sure the result is always iterable

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


def listIn(container, maybe_contained, *, strict=True):
    """ strictly sublists no equality here """
    lc = len(container)
    lmc = len(maybe_contained)
    if lc > lmc or not strict and lc == lmc:
        z = maybe_contained[0]
        if z in container:
            substart = container.index(z)
            subcontained = maybe_contained[1:]
            if not subcontained:
                return substart

            ssp1 = substart + 1 
            subcontainer = container[ssp1:]
            maybe = listIn(subcontainer, subcontained, strict=False)
            if maybe is None or maybe > 0:
                maybe = listIn(subcontainer, maybe_contained, strict=False)
                if maybe is not None:
                    return ssp1 + maybe
            else:
                return substart


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


class LolPython(list):
    """ because who needs to setattr lists right? """

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._list[key] = value

    def _asdict(self):
        return {h:v for h, v in zip(self._header, self)}

    def _raw(self):
        return self._list


def _sigh(header, row, orig_row=None):
    if orig_row is None:
        orig_row = row

    out = LolPython(row)
    out._list = orig_row
    out._header = header
    out._fields = header
    for name, value in zip(header, out):
        setattr(out, name, value)

    return out


class byCol:
    # FIXME this class +is+ was unpickleable, lol python
    def __init__(self, rows, header=None, to_index=tuple()):
        # what I think is a pickleable version
        if header is None:  # FIXME non None header might have bad names?
            _oh = [str(c) for c in rows[0]]
            header = [python_identifier(c) for i, c in enumerate(_oh)]
            #changes = {new:old for old, new in zip(rows[0], header) if old != new}
            orig_header = _sigh(header, _oh)  # normalize all to string for safety
            rows = rows[1:]
        else:
            orig_header = _sigh(header, header)

        # normalize row lenght  # FIXME account for rows longer than header
        rows = [_sigh(header, row + [None] * (len(header) - len(row)), row) for row in rows]
        #setattr(self, name, LOL_PYTHON(header, row))

        # so apparently using namedtuple dynamically breaks pickle LOL PYTHON LOL
        self.orig_header = orig_header
        self.header = _sigh(header, header)
        self.rows = rows
        self.__indexes = {}
        for col_name in to_index:
            hindex = self.header.index(col_name)
            ind = {r[hindex]:r for r in self.rows}
            ind[col_name] = self.header  # the header
            self.__indexes[col_name] = ind

        for i, name in enumerate(header):
            # so much for being dynamic!
            setattr(self, name, [row[i] for row in self.rows])

    def ___new__(cls, rows, header=None, to_index=tuple()):
        """ to_index should be a list of normalized column
            names that should be indexed for use in retrieving rows"""

        if header is None:  # FIXME non None header might have bad names?
            orig_header = [str(c) for c in rows[0]]  # normalize all to string for safety
            header = [python_identifier(c) for i, c in enumerate(orig_header)]
            #changes = {new:old for old, new in zip(rows[0], header) if old != new}
            rows = rows[1:]
        else:
            orig_header = header

        newcls = cls.bindHeader(header)
        self = super().__new__(newcls)

        # normalize row lenght  # FIXME account for rows longer than header
        rows = [row + [None] * (len(header) - len(row)) for row in rows]

        nt = namedtuple('row', header)
        self.orig_header = nt(*orig_header)
        self.header = nt(*header)
        self.rows = [nt(*r) for r in rows]
        self.__indexes = {}
        for col_name in to_index:
            ind = {getattr(r, col_name):r for r in self.rows}
            ind[col_name] = self.header  # the header
            self.__indexes[col_name] = ind

        for name in header:
            @property
            def col_gen(self, n=name):
                for row in self.rows:
                    yield getattr(row, n)

            setattr(newcls, name, col_gen)

        return self

    @classmethod
    def bindHeader(cls, header):
        new_name = cls.__name__ + '_' + '_'.join(header)
        classTypeInstance = type(new_name,
                                 (cls,),
                                 dict(__new__=object.__new__))
        return classTypeInstance

    @property
    def cols(self):
        for col in self.header:
            yield [col, *getattr(self, col)]

    def searchIndex(self, index, value, raw=False):
        row = self.__indexes[index][value]
        return row._raw() if raw else row

    def __getitem__(self, key):
        return list(getattr(self, key))

    def __iter__(self):
        yield self.orig_header
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


## ast printing

def findAssignToName(name, body, reverse=False, col_offset=0):
    eb = enumerate(body)
    gen = reversed(list(eb)) if reverse else eb
    return [(i, n) for i, n in gen
            if n.col_offset <= col_offset and
            isinstance(n, ast.Assign) and
            isinstance(n.targets[0], ast.Name) and
            n.targets[0].id == name]


def findImportName(name, body, reverse=False, col_offset=0):
    eb = enumerate(body)
    gen = reversed(list(eb)) if reverse else eb
    for i, node in gen:
        if node.col_offset <= col_offset:
            if not (isinstance(node, ast.Import) or
                    isinstance(node, ast.ImportFrom)):
                continue

            if name in [n.asname if n.asname
                        else n.name for n in node.names]:
                return [(i, node)]


def findName(name, body, reverse=False):
    out = findAssignToName(name, body, reverse=reverse)
    if not out:
        out = findImportName(name, body, reverse=reverse)

    return out


def asStr(astNode, prior=tuple(), dereference=False):
    """ having to explicitly pass prior to all recursive calls:
        racket: am I a joke to you? sigh continuation markes talk
        is just timely enough to realize how useful dynamic extent is
        and just how much we miss it in cases like this >_< """

    if isinstance(astNode, ast.Str):
        return repr(astNode.s)
    elif isinstance(astNode, ast.FormattedValue):
        return asStr(astNode.value, prior, dereference=True)
    elif isinstance(astNode, ast.JoinedStr):
        around = '"""'
        return (around +
                ''.join([ast.literal_eval(asStr(v, prior))
                         if isinstance(v, ast.Str) else asStr(v, prior)
                         for v in astNode.values]) +
                around)
    elif isinstance(astNode, ast.Name):
        if prior:
            # have to reverse to find the latest setting of the value
            # not the first since python allows rebinding
            maybe_name = findName(astNode.id, prior, reverse=True)
            if maybe_name:
                index, node = maybe_name[0]
                s = asStr(node, prior[:index],
                          dereference=astNode.id if dereference else False)
                return s
            else:
                raise NotImplementedError(f'found no assignment to {astNode.id}')

        return astNode.id
    elif isinstance(astNode, ast.Assign):
        value = asStr(astNode.value, prior, dereference=dereference)
        if dereference:
            return value
        else:
            return ', '.join([asStr(n, dereference=dereference)
                              for n in astNode.targets]) + ' = ' + value
    elif isinstance(astNode, ast.BinOp):
        return (asStr(astNode.left, prior, dereference) +
                ' ' + asStr(astNode.op, prior, dereference) + ' ' +
                asStr(astNode.right, prior, dereference))
    elif isinstance(astNode, ast.Add):
        return '+'
    elif isinstance(astNode, ast.Div):
        return '/'
    elif isinstance(astNode, ast.Call):
        return (asStr(astNode.func, prior, dereference) +
                '(' +
                ', '.join(asStr(a, prior, dereference) for a in astNode.args) +
                ')')
    elif isinstance(astNode, ast.Attribute):
        return asStr(astNode.value, prior, dereference) + '.' + astNode.attr
    elif isinstance(astNode, ast.Dict):
        return ('{' +
                ', '.join([(asStr(key, prior, dereference) +
                            ': ' + asStr(value, prior, dereference))
                           for key, value in zip(astNode.keys, astNode.values)]) +
                '}')
    elif isinstance(astNode, ast.Lambda):
        return ('lambda ' +
                ', '.join([asStr(a, prior, dereference) for a in astNode.args.args]) +
                ': ' +
                asStr(astNode.body, prior, dereference))
    elif isinstance(astNode, ast.Expr):
        return asStr(astNode.value, prior, dereference)
    elif isinstance(astNode, ast.Module):
        return '\n'.join([asStr(b, prior, dereference) for b in astNode.body])
    elif isinstance(astNode, ast.arg):
        return astNode.arg
    elif isinstance(astNode, ast.Import):
        return ('import ' + ', '.join([asStr(n) for n in astNode.names]))
    elif isinstance(astNode, ast.ImportFrom):
        _names = [asStr(n, dereference=dereference) for n in astNode.names]
        names = [n for n in _names if n]  # filter the dereferenced case
        if dereference:
            name = names[0]  # a, b = imported_name1, imported_name2 not an issue, resolved independently
            return astNode.module + '.' + name
        else:
            return ('from ' + astNode.module + ' ' +
                    'import ' + ', '.join(names))
    elif isinstance(astNode, ast.alias):
        if dereference:
            if (astNode.asname == dereference or
                not astNode.asname and astNode.name == dereference):
                # this deals with the threat of
                # from asdf import name as dereference, dereference as name
                return astNode.name
        else:
            return astNode.name + ((' as ' + astNode.asname)
                                   if astNode.asname else
                                   '')
    else:
        raise NotImplementedError(f'{astNode}')
