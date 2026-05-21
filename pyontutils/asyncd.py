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


def Async(rate=None, debug=False, collector=None, override_workers=None, n_jobs=None):  # ah conclib
    """ rate=0 or rate=False uses ThreadPoolExecutor defaults """

    if rate is None:
        # it turns out that rate=None being infinite causes massive issues
        # because it results in calling loop.run_in_executor for every single
        # element of a list, which it turns out has staggeringly large overhead
        # therefore we set the rate to True here and then calculate the rate to
        # be 100x the batch size so that best case possible time will always be
        # 10ms, this prevents the overhead
        rate = True

    if n_jobs and override_workers is None:
        override_workers = n_jobs

    # FIXME can't break this with C-c
    if rate:
        workers = math.ceil(rate) if rate < 40 else 40
        # 40 comes from the TPE default 5 * cpu cores, this has not been tuned
        executor = ThreadPoolExecutor(max_workers=workers)
    elif override_workers is not None:
        executor = ThreadPoolExecutor(max_workers=override_workers)
        workers = override_workers
    else:
        executor = ThreadPoolExecutor()
        workers = executor._max_workers

    if debug:
        log.debug((rate, workers))

    def inner(generator):
        #Async(rate=rate/2, debug)(funclist[])
        #funclist = list(generator)
        # the real effective throughput I am seeing per os thread is ~350Hz
        # I can push it to about 400Hz setting it to run at 3000Hz with 3000
        # entries but this is trivial to double using multiple processes
        # pushing the set rate higher does seem to max out around 400Hz if
        # the min time_per_job < our trouble threshold which is ping dependent
        #Parallel(generator)
        nonlocal rate
        nonlocal workers
        nonlocal executor
        if rate:
            funclist = list(generator)
            if not funclist:
                return tuple()  # make sure the result is always iterable
            elif isinstance(rate, bool):
                #rate = 10 # 10 * len(funclist)
                _lfu = len(funclist)
                # it seems that having less than 10k workers avoids some
                # nasty mega cpu blowup
                workers = 10_000 if _lfu > 10_000 else _lfu
                if override_workers is not None and override_workers < workers:
                    workers = override_workers

                rate = _lfu
                jobs_per_worker = _lfu / workers
                executor = ThreadPoolExecutor(max_workers=workers)

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
