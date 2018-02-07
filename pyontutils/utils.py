#!/usr/bin/env python3.6
"""
    A collection of reused functions and classes.
"""

import os
import re
import math
import asyncio
import inspect
import subprocess
from datetime import date
from time import time, sleep
from pathlib import Path
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import psutil
import rdflib

TODAY = date.isoformat(date.today())

rdflib.plugin.register('nifttl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'CustomTurtleSerializer')
rdflib.plugin.register('cmpttl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'CompactTurtleSerializer')
rdflib.plugin.register('uncmpttl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'UncompactTurtleSerializer')

def subclasses(start):
    for sc in start.__subclasses__():
        yield sc
        yield from subclasses(sc)

def getCommit():
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().rstrip()
    return commit

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
        raise MemoryError('Running this requires quite a bit of memory ~ {vms_gigs:.2f}, you have {free_gigs:.2f} of the {buffer_gigs:.2f} needed'.format(vms_gigs=vms_gigs, free_gigs=free_gigs, buffer_gigs=buffer_gigs))

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
    os.sys.stdout.write('\x1b]2;{}\x07'.format(text))

def refile(script__file__, path):
    return str(Path(script__file__).parent / path)

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

def Async(rate=None):  # ah conclib
    if rate:
        #def scurve(x, a=32, b=1, d=2, c=8, i=20, e=1.5):
            #return a / (b + e ** (i - x)) + c
        #workers = scurve(rate)
        workers = rate if rate <= 40 else 40
        executor = ThreadPoolExecutor(max_workers=workers)
    else:
        executor = ThreadPoolExecutor()
        workers = executor._max_workers
    print(rate, workers)
    def inner(generator):
        if rate:
            funclist = list(generator)
            size = (len(funclist) // rate) if rate >= 1 else 1  # FIXME low rates should not have to worry about haning...
            print(f'Time estimate at {rate}Hz for apply {funclist[0]} to {len(funclist)} args: {size}s')
            chunks = chunk_list(funclist, size)
            generator = (lambda:list(limited_gen(chunk, smooth_offset=(i % workers)/workers))  # this was the slowdown culpret
                         for i, chunk in enumerate(sorted(chunks, key=len, reverse=True)))
        async def future_loop(future_):
            loop = asyncio.get_event_loop()
            futures = []
            for wrapped_function_or_limgen in generator:
                future = loop.run_in_executor(executor, wrapped_function_or_limgen)
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

def limited_gen(chunk, smooth_offset=0, debug=True):
    additional = 0
    additional_sleep = 0
    if smooth_offset:
        print('started running with offset', smooth_offset)
        sleep(smooth_offset)
    for element in chunk:
        if additional:
            additional -= 1
            additional_sleep = sleep_time
        start = time()
        yield element()
        stop = time()
        delta = stop - start
        if delta > 1:
            sleep_time = delta % 1
            additional += int(delta // 1)
            if debug:
                print(f'{start:<8f} {stop:<8f} {delta:<10f} {sleep_time:<10f} {additional_sleep:<10f} {additional} {delta - 1}')
            continue
        else:
            sleep_time = 1 - delta
        if debug:
            print(f'{start:<8f} {stop:<8f} {delta:<10f} {sleep_time:<10f} {additional_sleep:<10f} {additional}')
        sleep(sleep_time + additional_sleep)
        additional_sleep = 0

def mysql_conn_helper(host, db, user, port=3306):
    kwargs = {
        'host':host,
        'db':db,
        'user':user,
        'port':port,
        'password':None,  # no you may NOT pass it in
    }
    with open(os.path.expanduser('~/.mypass'), 'rt') as f:
        entries = [l.strip().split(':', 4) for l in f.readlines()]
    for e_host, e_port, e_db, e_user, e_pass in entries:
        e_port = int(e_port)
        if host == e_host:
            print('yes:', host)
            if  port == e_port:
                print('yes:', port)
                if db == e_db or e_db == '*':  # FIXME bad * expansion
                    print('yes:', db)
                    if user == e_user:
                        print('yes:', user)
                        kwargs['password'] = e_pass  # last entry wins
    e_pass = None
    if kwargs['password'] is None:
        raise ConnectionError('No password as found for {user}@{host}:{port}/{db}'.format(**kwargs))

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
            header = [c.split('(')[0].strip().replace(' ','_').replace('+','') for c in rows[0]]
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

class _TermColors:
    ENDCOLOR = '\033[0m'
    colors = dict(
    BOLD = '\033[1m',
    FAINT = '\033[2m',  # doesn't work on urxvt
    IT = '\033[3m',
    UL = '\033[4m',
    BLINKS = '\033[5m',
    BLINKF = '\033[6m',  # same as S?
    REV = '\033[7m',
    HIDE = '\033[8m',  # doesn't work on urxvt
    XOUT = '\033[9m',  # doesn't work on urxvt
    FONT1 = '\033[10m',  # doesn't work on urxvt use '\033]50;%s\007' % "fontspec"
    FONT2 = '\033[11m',  # doesn't work on urxvt
    FRAKTUR = '\033[20m',  # doesn't work on urxvt
    OFF_BOLD = '\033[21m',
    NORMAL = '\033[22m',
    OFF_IT = '\033[23m',
    OFF_UL = '\033[24m',
    OFF_BLINK = '\033[25m',
    POSITIVE = '\033[27m',
    OFF_HIDE = '\033[28m',
    RED = '\033[91m',
    GREEN = '\033[92m',
    YELLOW = '\033[93m',
    BLUE = '\033[94m',
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

