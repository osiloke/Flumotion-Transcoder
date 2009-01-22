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

from flumotion.transcoder.admin import admintask


class ITranscoderBalancerListener(Interface):

    def onSlotsAvailable(self, balancer, count):
        pass


class TranscoderBalancerListener(object):

    implements(ITranscoderBalancerListener)

    def onSlotsAvailable(self, balancer, count):
        pass


class TranscoderBalancer(object):
    """
    Handle the distribution of transcoding tasks to a set of workerPxy.
    """

    def __init__(self, listener=None):
        self._listener = listener
        self._workerTasks = {} # {workerPxy: [task]}
        self._orphanes = []
        self._current = 0
        self._maximum = 0


    ## Public Methods ##

    def getAvailableSlots(self):
        return max(self._maximum - self._current, 0)

    def clearTasks(self):
        self._current = 0
        del self._orphanes[:]
        for tasks in self._workerTasks.itervalues():
            del tasks[:]

    def addWorker(self, workerPxy):
        assert not (workerPxy in self._workerTasks)
        self._workerTasks[workerPxy] = []
        self._maximum += workerPxy.getWorkerContext().getMaxTask()

    def removeWorker(self, workerPxy):
        assert workerPxy in self._workerTasks
        self._maximum -= workerPxy.getWorkerContext().getMaxTask()
        self._orphanes.extend(self._workerTasks[workerPxy])
        del self._workerTasks[workerPxy]

    def addTask(self, task, workerPxy=None):
        assert admintask.IAdminTask.providedBy(task)
        assert (workerPxy == None) or (workerPxy in self._workerTasks)
        self._current += 1
        if workerPxy:
            max = workerPxy.getWorkerContext().getMaxTask()
            curr = len(self._workerTasks[workerPxy])
            if max > curr:
                self._workerTasks[workerPxy].append(task)
                task.suggestWorker(workerPxy)
                return
        self._orphanes.append(task)

    def removeTask(self, task):
        assert admintask.IAdminTask.providedBy(task)
        if task in self._orphanes:
            self._orphanes.remove(task)
            self._current -= 1
            return
        for tasks in self._workerTasks.itervalues():
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
                           for w, t in self._workerTasks.items()
                           if len(t) < w.getWorkerContext().getMaxTask()])
            workerPxys = lookup.keys()
            workerPxys.sort(key=lookup.get)
            return workerPxys

        if self._workerTasks:
            # First remove the exceding tasks
            for workerPxy, tasks in self._workerTasks.iteritems():
                max = workerPxy.getWorkerContext().getMaxTask()
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
                workerPxys = getSortedWorkers()
                if not workerPxys: break
                for workerPxy in workerPxys:
                    if not self._orphanes: break
                    tasks = self._workerTasks[workerPxy]
                    task = self._orphanes.pop()
                    tasks.append(task)
                    task.suggestWorker(workerPxy)
                else:
                    continue
                break
        available = self.getAvailableSlots()
        if self._listener and (available > 0):
            self._listener.onSlotsAvailable(self, available)
