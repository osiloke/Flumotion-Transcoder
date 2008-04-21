# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import Interface, implements

from flumotion.transcoder.admin.admintask import IAdminTask


class ITranscoderBalancerListener(Interface):

    def onSlotsAvailable(self, balancer, count):
        pass


class TranscoderBalancerListener(object):

    implements(ITranscoderBalancerListener)

    def onSlotsAvailable(self, balancer, count):
        pass


class TranscoderBalancer(object):
    """
    Handle the distribution of transcoding tasks to a set of worker.
    """
    
    def __init__(self, listener=None):
        self._listener = listener
        self._workers = {} # {worker: [task]}
        self._orphanes = []
        self._current = 0
        self._maximum = 0
        
    
    ## Public Methods ##
        
    def getAvailableSlots(self):
        return max(self._maximum - self._current, 0)
        
    def clearTasks(self):
        self._current = 0
        del self._orphanes[:]
        for tasks in self._workers.itervalues():
            del tasks[:]
        
    def addWorker(self, worker):
        assert not (worker in self._workers)
        self._workers[worker] = []
        self._maximum += worker.getWorkerContext().getMaxTask()
        
    def removeWorker(self, worker):
        assert worker in self._workers
        self._maximum -= worker.getWorkerContext().getMaxTask()
        self._orphanes.extend(self._workers[worker])
        del self._workers[worker]
    
    def addTask(self, task, worker=None):
        assert IAdminTask.providedBy(task)
        assert (worker == None) or (worker in self._workers)
        self._current += 1
        if worker:
            max = worker.getWorkerContext().getMaxTask()
            curr = len(self._workers[worker])
            if max > curr:
                self._workers[worker].append(task)
                task.suggestWorker(worker)
                return
        self._orphanes.append(task)
    
    def removeTask(self, task):
        assert IAdminTask.providedBy(task)
        if task in self._orphanes:
            self._orphanes.remove(task)
            self._current -= 1
            return
        for tasks in self._workers.itervalues():
            if task in tasks:
                tasks.remove(task)
                self._current -= 1
                return

    def balance(self):
        
        def getSortedWorkers():
            """
            Return all the workers with at least 1 free slot
            with the ones with the most free slots first.
            """
            lookup = dict([(w, float(len(t)) / w.getWorkerContext().getMaxTask()) 
                           for w, t in self._workers.items()
                           if len(t) < w.getWorkerContext().getMaxTask()])
            workers = lookup.keys()
            workers.sort(key=lookup.get)
            return workers
        
        if self._workers:
            # First remove the exceding tasks
            for worker, tasks in self._workers.iteritems():
                max = worker.getWorkerContext().getMaxTask()
                if len(tasks) > max:
                    diff = len(tasks) - max
                    oldTasks = tasks[diff:]
                    del tasks[diff:]
                    self._orphanes.extend(oldTasks)
                    for task in oldTasks:
                        task.suggestWorker(None)
            # Then distribute the orphanes until there is 
            # no more free slots or no more orphane tasks
            while True:
                workers = getSortedWorkers()
                if not workers: break
                for worker in workers:                    
                    if not self._orphanes: break
                    tasks = self._workers[worker]
                    task = self._orphanes.pop()
                    tasks.append(task)
                    task.suggestWorker(worker)
                else:
                    continue
                break
        available = self.getAvailableSlots()
        if self._listener and (available > 0):
            self._listener.onSlotsAvailable(self, available)
