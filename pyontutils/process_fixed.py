import signal
from multiprocessing import Process
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import _process_worker as _process_worker_base

def _process_worker(call_queue, result_queue):
    """ This worker is wrapped to block KeyboardInterrupt """
    signal.signal(signal.SIGINT, signal.SIG_IGN)  #block ctrl-c
    return _process_worker_base(call_queue, result_queue)

_process_worker.__doc__ = _process_worker_base.__doc__ + _process_worker.__doc__

def startup():  # super hack!
    """ dummy function populate the process pool """
    return "Starting."

class ProcessPoolExecutor_fixed(ProcessPoolExecutor):
    """ A ProcessPoolExecutor that doesn't succumb to KeyboardInterrups """
    def __init__(self, max_workers=None):
        super().__init__(max_workers=max_workers)
        self.submit(startup)

    def _adjust_process_count(self):
        for _ in range(len(self._processes), self._max_workers):
            p = Process(
                    target=_process_worker,
                    args=(self._call_queue,
                          self._result_queue))
            p.start()
            self._processes[p.pid] = p
