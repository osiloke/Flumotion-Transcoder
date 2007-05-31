# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import math

from zope.interface import Interface


class ITask(Interface):

    def setTaskWorker(self, worker):
        pass
    

class TaskBalancer(object):
    """
    Handle the distribution of tasks to a set of worker.
    """
    
    def __init__(self):
        self._workers = {} # {worker: [task]}
        self._orphanes = []
        self._total = 0
        
    def clearTasks(self):
        self._total = 0
        del self._orphanes[:]
        for tasks in self._workers.itervalues():
            del tasks[:]
        
    def addWorker(self, worker):
        assert not (worker in self._workers)
        self._workers[worker] = []
        
    def removeWorker(self, worker):
        assert worker in self._workers
        self._orphanes.extend(self._workers[worker])
        del self._workers[worker]
    
    def addTask(self, task, worker=None):
        assert (worker == None) or (worker in self._workers)
        self._total += 1
        if not self._workers:
            self._orphanes.append(task)
            task.setTaskWorker(None)
            return
        if worker == None:
            workers = self._workers.keys()
            workers.sort(key=lambda w: len(self._workers[w]))
            worker = workers[0]
        self._workers[worker].append(task)
        
        task.setTaskWorker(worker)
    
    def removeTask(self, task):
        if task in self._orphanes:
            self._orphanes.remove(task)
            self._total -= 1
            return
        for tasks in self._workers.itervalues():
            if task in tasks:
                tasks.remove(task)
                self._total -= 1
                return

    def balanceTasks(self):
        if not self._workers:
            return
        max = int(math.ceil(float(self._total) / len(self._workers)))
        workers = self._workers.keys()
        workers.sort(key=lambda w: -len(self._workers[w]))
        for worker in workers:
            tasks = self._workers[worker]
            l = len(tasks)
            if l > max:
                self._orphanes.extend(tasks[max:])
                del tasks[max:]
            elif l < max:
                i = -(max - l)
                migrated = self._orphanes[i:]
                del self._orphanes[i:]
                tasks.extend(migrated)
                for j in migrated:
                    j.setTaskWorker(worker)
        if len(self._orphanes) > 0:
            assert len(self._workers) == 0
            for j in self._orphanes:
                j.setTaskWorker(None)

