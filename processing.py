#import yappi
import os, sys, time
from copy import copy
from collections import OrderedDict
from datetime import date
import multiprocessing
from threading import Thread
from queue import Queue, Empty
import logging

from util import Util
from environment import Environment, Scandata
from core.featuredetection import FeatureDetection
from core.derive import PDF
from core.derive import Djvu
from core.crop import Crop
from core.ocr import OCR
from gui.common import CommonActions as ca


class ProcessHandling(object):
    """
    """
    thread_count_ignore = ('drain_queue',
                           'handle_thread_exceptions',
                           'distribute',
                           'run_pipeline')

    def __init__(self, max_threads=None):
        if max_threads:
            self.cores = max_threads
        else:
            try:
                self.cores = multiprocessing.cpu_count()
            except NotImplemented:
                self.cores = 1
        self.processes = 0
        self._active_threads = {}
        self._inactive_threads = self.new_queue()
        self.item_queue = self.new_queue()
        self._ExceptionQueue = Queue()
        self.handled_exceptions = []
        self.polling_threads = False
        self.OperationObjects = {}
        
    def _init_polls(self):        
        if not self.polling_threads:
            self._init_thread_poll()
        if Environment.interface == 'shell':
            self._init_progress_poll()

    def _init_thread_poll(self):
        self.polling_threads = True
        self._thread_poll = Thread(target=self._poll_threads,
                                   name='_poll_threads')
        self._thread_poll.start()

    def _init_progress_poll(self):
        pass

    def _poll_threads(self):
        while True:
            if not self.polling_threads:
                return
            time.sleep(1.0)
            self._clear_inactive()
            self._submit_waiting()
            if not self._are_active_processes():
                self.polling_threads = False
                return

    def _are_active_processes(self):
        if (self.processes == 0 and
            not [thread.func for pid, thread in self._active_threads.items()
                 if thread.func in ProcessHandling.thread_count_ignore]):
            return False
        else:
            return True

    def _already_processing(self, pid):
        if pid in self._active_threads:
            return True
        else:
            return False

    def wait_till_idle(self, pids):
        finished = set()
        while True:
            self.check_ExceptionQueue()
            active_pids = set()
            for pid, thread in self._active_threads.items():
                active_pids.add(pid)
            for id in pids:
                if id not in active_pids and id not in self.item_queue:
                    finished.add(id)
            if len(finished) == len(pids):
                break
            else:
                time.sleep(1)

    def _wait(self, func, pid, args):
        if not pid in self.item_queue:
            self.item_queue[pid] = (func, args)

    def _submit_waiting(self):
        queue = []
        for pid, item in self.item_queue.items():
            if self.add_process(item[0], pid, item[1]):
                queue.append(pid)
            else:
                break
        queue.reverse()
        for pid in queue:
            del self.item_queue[pid]

    def _clear_inactive(self):
        inactive = {}
        for pid, thread in self._active_threads.items():
            if not thread.is_alive():
                thread.end_time = Util.microseconds()
                exec_time = round((thread.end_time - thread.start_time)/60, 2)
                thread.logger.info('Thread ' + str(pid) + 
                                   ' finished in ' + str(exec_time) + 
                                   ' minutes')
                inactive[pid] = thread
        for pid, thread in inactive.items():
            identifier, cls = pid.split('.')[:2]
            if thread.func not in ProcessHandling.thread_count_ignore:
                self.OperationObjects[identifier][cls].thread_count -= 1
                self.processes -= 1
            self._inactive_threads[pid] = thread
            del self._active_threads[pid]

    def finish(self, identifier=None):
        destroy = []
        for pid, thread in self._active_threads.items():
            if not identifier:
                destroy.append(pid)
            else:
                if pid.startswith(identifier):
                    destroy.append(pid)
        for pid in destroy:
            self.destroy_thread(pid)
        #self.item_queue = self.new_queue()
        #self.polling_threads = False

    def destroy_thread(self, pid):
        if pid in self._active_threads:
            thread = self._active_threads[pid]
            thread.logger.info('Destroying Thread ' + str(pid))
            if thread.func not in ProcessHandling.thread_count_ignore:
                self.processes -= 1
            del self._active_threads[pid]

    def clear_exceptions(self, pid):
        remove = None
        for num, item in enumerate(self.handled_exceptions):
            if item == pid:
                remove = num
            if remove is not None:
                del self.handled_exceptions[remove]

    def check_ExceptionQueue(self):
        try:
            pid, traceback = self._ExceptionQueue.get_nowait()
        except Empty:
            pass
        else:
            self.handled_exceptions.append(pid)
            msg = 'Exception in ' + pid + ':\n' + traceback
            identifier = pid.split('_')[0]
            if Environment.interface == 'gui':
                self.finish(identifier)
                ca.dialog(message=msg)
            elif Environment.interface == 'shell':
                self.finish(identifier)
                raise Exception(msg)

    def join(self, args):
        self._ExceptionQueue.put(args)
        self._ExceptionQueue.join()

    def parse_args(self, args, kwargs):
        if not isinstance(args, list):
            args = list([args,]) if args is not None else []
        if kwargs is None:
            kwargs = {}
        return args, kwargs

    def parse_queue_data(self, data):
        d = []
        if 'func' not in data:
            raise LookupError('Failed to find \'func\' argument; nothing to do.')
        else:
            d.append(data['func'])
        for i in ('args', 'kwargs', 'callback'):
            if i in data:
                d.append(data[i])
            else:
                d.append(None)
        return d

    def new_queue(self):
        return OrderedDict()

    def drain_queue(self, queue, mode, qpid=None, qlogger=None):
        self._init_polls()
        if qlogger and qpid:
            qstart = Util.microseconds()
        pids = []
        for pid, data in queue.items():
            pids.append(pid)
            func, args, kwargs, callback = self.parse_queue_data(data)
            args, kwargs = self.parse_args(args, kwargs)
            identifier = pid.split('.')[0]
            logger = logging.getLogger(identifier)
            #print ('DRAIN\n', mode, pid, callback)
            if mode == 'sync':                
                if callback:
                    kwargs['callback'] = callback
                try:
                    start = Util.microseconds()
                    func(*args, **kwargs)
                    end = Util.microseconds()
                    exec_time = round((end-start)/60, 2)
                    logger.info('pid ' + pid + ' finished in ' + 
                                str(exec_time) + ' minutes')
                except Exception as e:
                    logger.error('pid ' + str(pid) + ' encountered an error; ' + 
                                 str(e) + '\nAborting.')
                    return False
            elif mode == 'async':
                self.add_process(func, pid, args, kwargs, callback)                
        if mode == 'async':
            self.wait_till_idle(pids)      
        if qlogger and qpid:
            qend = Util.microseconds()
            qexec_time = str(round((qend - qstart)/60, 2))
            qlogger.info('Drained queue ' + qpid + ' in ' + qexec_time + ' minutes')
                        
    def add_process(self, func, pid, args=None, kwargs=None, callback=None):
        self._init_polls()
        if self._already_processing(pid):
            return False
        self.clear_exceptions(pid)
        if self.processes >= self.cores:
            self._wait(func, pid, args)
            return False
        else:
            args, kwargs = self.parse_args(args, kwargs)
            #print ('ADD PROC\n', pid, callback)
            new_thread = Thread(target=func, name=pid, 
                                args=args, kwargs=kwargs)
            new_thread.func = func.__name__
            new_thread.daemon = True
            identifier = pid.split('.')[0]
            new_thread.logger = logging.getLogger(identifier)
            new_thread.start_time = Util.microseconds()
            new_thread.start()
            self._active_threads[pid] = new_thread
            if new_thread.func not in ProcessHandling.thread_count_ignore:
                self.processes += 1
            new_thread.logger.info('New Thread Started --> ' +
                                   'Pid: ' + str(pid))                                   
            return True

    def _create_operation_instance(self, identifier, cls, method, book):
        if cls not in globals():
            raise LookupError('Could not find module \'' + cls + '\'')
        else:
            if identifier not in self.OperationObjects:
                self.OperationObjects[identifier] = {}
            self.OperationObjects[identifier][cls] = globals()[cls](self, book)
            self.OperationObjects[identifier][cls].init_bookkeeping()
            function = getattr(self.OperationObjects[identifier][cls], method)
            return function

    def get_chunk(self, pagecount, chunk):
        remainder = pagecount % self.cores
        pagecount = pagecount - remainder
        chunksize = pagecount/self.cores
        start = chunksize * chunk
        end = start + chunksize
        if chunk == self.cores-1:
            end += remainder
        return int(start), int(end)
    
    def multi_threaded(f):
        def distribute(self, cls, mth, book, 
                       args=None, kwargs=None, callback=None):
            if not kwargs:
                kwargs = {}
            identifier = book.identifier
            function = self._create_operation_instance(identifier, cls, mth, book)
            queue = self.new_queue()
            available_cores = self.cores - self.processes
            self.OperationObjects[identifier][cls].thread_count = available_cores
            for chunk in range(0, available_cores):
                start, end = self.get_chunk(book.page_count, chunk)
                kwargs['start'], kwargs['end'] = start, end
                pid = '.'.join((book.identifier, cls, mth, str(start)))
                queue[pid] = {'func': function,
                              'args': args, 
                              'kwargs': copy(kwargs),
                              'callback': None}
            return f(self, queue, identifier, cls, callback)
        return distribute

    def add_default_op_cb(self, callback):
        if not callback:
            callback = []
        elif not isinstance(callback, list):
            callback = [callback, ]
        callback.append('set_finished')
        return callback

    @multi_threaded
    def run_pipeline_distributed(self, queue, identifier, cls, callback=None):
        callback = self.add_default_op_cb(callback)
        self.drain_queue(queue, 'async')
        if callback:
            self.execute_callback(identifier, cls, callback)
                        
    def run_pipeline(self, cls, mth, book, 
                     args=None, kwargs=None, callback=None):
        identifier = book.identifier
        function = self._create_operation_instance(identifier, cls, 
                                                   mth, book)
        queue = self.new_queue()
        pid = '.'.join((book.identifier, cls, mth))
        queue[pid] = {'func': function,
                      'args': args, 
                      'kwargs': kwargs,
                      'callback': None}
        self.drain_queue(queue, 'async')
        if callback:
            self.execute_callback(identifier, cls, callback)

    def execute_callback(self, identifier, _class, callback):
        if not isinstance(callback, list):
            callback = [callback, ]
        for cb in callback:
            if isinstance(cb, str):
                getattr(self.OperationObjects[identifier][_class], cb)()
            elif hasattr(cb, '__call__'):
                cb()

    def get_time_elapsed(self, start_time):
        current_time = time.time()
        elapsed_secs = int(current_time - start_time)
        elapsed_mins = int(elapsed_secs/60)
        elapsed_secs -= elapsed_mins * 60
        return elapsed_mins, elapsed_secs

    def get_time_remaining(self, total, completed, avg_exec_time, thread_count):
        fraction = float(completed) / (float(total))
        remaining_page_count = total - completed
        estimated_secs = int((int(avg_exec_time * remaining_page_count))/thread_count)
        estimated_mins = int(estimated_secs/60)
        estimated_secs -= estimated_mins * 60
        return estimated_mins, estimated_secs

    def get_operation_state(self, book, identifier, cls, total):
        state = {'finished': False}
        op_obj = self.OperationObjects[identifier][cls]
        thread_count = self.OperationObjects[identifier][cls].thread_count
        if op_obj.completed['__finished__'] or thread_count == 0:
            elapsed_mins, elapsed_secs = \
                self.get_time_elapsed(book.start_time)
            state['finished'] = True
            state['completed'] = total
            state['fraction'] = 1.0
            state['estimated_mins'] = 0.0
            state['estimated_secs'] = 0.0
            state['elapsed_mins'] = elapsed_mins
            state['elapsed_secs'] = elapsed_secs
        else:
            completed = 0
            op_num = len(op_obj.completed) - 1
            avg_exec_time = 0
            for op, leaf_t, in op_obj.completed.items():
                if op != '__finished__':
                    c = len(leaf_t)
                    completed += c
                    if c > 0:
                        avg_exec_time += op_obj.get_avg_exec_time(op)
            fraction = float(completed)/(float(total)*op_num)
            estimated_mins, estimated_secs = \
                self.get_time_remaining(total, completed,
                                        avg_exec_time,
                                        thread_count)
            elapsed_mins, elapsed_secs = \
                self.get_time_elapsed(book.start_time)            
            state['completed'] = completed
            state['fraction'] = fraction
            state['estimated_mins'] = estimated_mins
            state['estimated_secs'] = estimated_secs
            state['elapsed_mins'] = elapsed_mins
            state['elapsed_secs'] = elapsed_secs
        return state
