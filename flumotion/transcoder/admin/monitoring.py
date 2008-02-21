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
from twisted.internet import reactor
from twisted.python.failure import Failure

from flumotion.common.planet import moods

from flumotion.inhouse import log, defer, utils
from flumotion.inhouse.errors import TimeoutError

from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.taskmanager import TaskManager
from flumotion.transcoder.admin.monbalancer import MonitorBalancer


class Monitoring(TaskManager):
    
    logCategory = adminconsts.MONITORING_LOG_CATEGORY
    
    def __init__(self, workerset, monitorset):
        TaskManager.__init__(self)
        self._workers = workerset
        self._monitors = monitorset
        self._balancer = MonitorBalancer()
        # Registering Events
        self._register("task-added")
        self._register("task-removed")
        

    ## Public Method ##
    
    def initialize(self):
        self.log("Initializing Monitoring Manager")
   

        self._workers.connectListener("worker-added", self, self.onWorkerAddedToSet)
        self._workers.connectListener("worker-removed", self, self.onWorkerRemovedFromSet)
        self._monitors.connectListener("monitor-added", self, self.onMonitorAddedToSet)
        self._monitors.connectListener("monitor-removed", self, self.onMonitorRemovedFromSet)
        self._workers.update(self)
        self._monitors.update(self)
        return TaskManager.initialize(self)

    
    ## Overrided Virtual Methods ##

    def _doStart(self):
        self.log("Ready to start monitoring, waiting monitors to become idle")
        d = self._monitors.waitIdle(adminconsts.WAIT_IDLE_TIMEOUT)
        d.addBoth(self.__cbStartResumeMonitoring)
        return d
    
    def _doResume(self):
        self.log("Ready to resume monitoring, waiting monitors to become idle")
        d = self._monitors.waitIdle(adminconsts.WAIT_IDLE_TIMEOUT)
        d.addBoth(self.__cbStartResumeMonitoring)
        return d
    
    def _doPause(self):
        self.log("Pausing monitoring manager")
        for task in self.iterTasks():
            self._balancer.removeTask(task)
    
    def _doAbort(self):
        self.log("Aborting monitoring")
        self._balancer.clearTasks()

    def _onTaskAdded(self, task):
        if self.isStarted():
            self._balancer.addTask(task)
            self._balancer.balance()
        self.emit("task-added", task)
    
    def _onTaskRemoved(self, task):
        if self.isStarted():
            self._balancer.removeTask(task)
            self._balancer.balance()
        self.emit("task-removed", task)

            
    ## WorkerSet Event Listeners ##
    
    def onWorkerAddedToSet(self, workerset, worker):
        self.log("Worker '%s' added to monitoring", worker.getLabel())
        self._balancer.addWorker(worker)
        self._balancer.balance()
    
    def onWorkerRemovedFromSet(self, workerset, worker):
        self.log("Worker '%s' removed from monitoring", worker.getLabel())
        self._balancer.removeWorker(worker)
        self._balancer.balance()


    ## MonitorSet Event Listeners ##
    
    def onMonitorAddedToSet(self, monitorset, monitor):
        self.log("Monitor '%s' added to monitoring", monitor.getLabel())
        d = self.addComponent(monitor)
        d.addErrback(self.__ebAddComponentFailed, monitor.getName())
    
    def onMonitorRemovedFromSet(self, monitorset, monitor):
        self.log("Monitor '%s' removed from monitoring", monitor.getLabel())
        d = self.removeComponent(monitor)
        d.addErrback(self.__ebRemoveComponentFailed, monitor.getName())


    ## Overriden Methods ##
    
    def update(self, listener):
        for t in self._tasks.itervalues():
            self.emitTo("task-added", listener, t)


    ## Private Methods ##
    
    def __cbStartResumeMonitoring(self, result):
        if (isinstance(result, Failure) 
            and not result.check(TimeoutError)):
            log.notifyFailure(self, result,
                              "Failure waiting monitor set "
                              "to become idle")
        self.log("Free to continue monitoring startup/resuming")
        d = defer.Deferred()
        for task in self.iterTasks():
            d.addCallback(self.__cbAddBalancedTask, task)
        d.addCallback(defer.dropResult, self._balancer.balance)
        d.addErrback(self.__ebStartupResumingFailure)
        d.callback(None)
        return d
    
    def __cbAddBalancedTask(self, _, task):
        timeout = adminconsts.MONITORING_POTENTIAL_WORKER_TIMEOUT
        d = task.waitPotentialWorker(timeout)
        # Call self._balancer.addTask(task, worker)
        d.addCallback(defer.shiftResult, self._balancer.addTask, 1, task)
        return d
    
    def __ebStartupResumingFailure(self, failure):
        log.notifyFailure(self, failure, 
                          "Failure during monitoring startup/resuming")
        return failure

    def __ebAddComponentFailed(self, failure, name):
        log.notifyFailure(self, failure,
                          "Failed to add monitor '%s' "
                          "to monitoring manager", name)
    
    def __ebRemoveComponentFailed(self, failure, name):
        log.notifyFailure(self, failure,
                          "Failed to remove monitor '%s' "
                          "from monitoring manager", name)
