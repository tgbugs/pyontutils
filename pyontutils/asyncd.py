import math
import asyncio
from time import time, sleep
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import nest_asyncio
from .utils_fast import chunk_list, log


def async_getter(function, listOfArgs):
    async def future_loop(future_):
        loop = asyncio.get_event_loop()
        futures = []
        for args in listOfArgs:
            future = loop.run_in_executor(None, function, *args)
            futures.append(future)
        log.debug('Futures compiled')
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
            log.info(f'Time estimate: {time_est}    rate: {rate}Hz    '
                     f'func: {funclist[0]}    args: {len(funclist)}    '
                     f'chunks: {lc}    size: {size}')
            generator = (lambda _c=chunk, _i=i: list(limited_gen(
                _c, smooth_offset=(_i % lc)/lc, time_est=time_est,
                debug=debug, thread=_i))
                         for i, chunk in enumerate(sorted(chunks, key=len, reverse=True)))

        async def future_loop(future_):
            loop = asyncio.get_event_loop()
            futures = []
            for wrapped_func_or_limgen in generator:
                future = loop.run_in_executor(executor, wrapped_func_or_limgen)
                futures.append(future)
            log.debug('Futures compiled')
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
