# vi:si:et:sw=4:sts=4:ts=4

# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007,2008,2009 Fluendo, S.L.
# Copyright (C) 2010,2011 Flumotion Services, S.A.
# All rights reserved.
#
# This file may be distributed and/or modified under the terms of
# the GNU Lesser General Public License version 2.1 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.LGPL" in the source distribution for more information.
#
# Headers in this file shall remain intact.

from zope.interface import Interface, implements
from twisted.internet import reactor
from twisted.python.failure import Failure

from flumotion.common.planet import moods

from flumotion.inhouse import log, defer, utils, errors as iherrors

from flumotion.transcoder.admin import adminconsts, taskmanager, monbalancer


class Monitoring(taskmanager.TaskManager):

    logCategory = adminconsts.MONITORING_LOG_CATEGORY

    def __init__(self, workerPxySet, monitorPxySet):
        taskmanager.TaskManager.__init__(self)
        self._workerPxySet = workerPxySet
        self._monitorPxySet = monitorPxySet
        self._balancer = monbalancer.MonitorBalancer()
        # Registering Events
        self._register("task-added")
        self._register("task-removed")


    ## Public Method ##

    def initialize(self):
        self.log("Initializing Monitoring Manager")
        self._workerPxySet.connectListener("worker-added", self,
                                           self.__onWorkerAddedToSet)
        self._workerPxySet.connectListener("worker-removed", self,
                                           self.__onWorkerRemovedFromSet)
        self._monitorPxySet.connectListener("monitor-added", self,
                                            self.__onMonitorAddedToSet)
        self._monitorPxySet.connectListener("monitor-removed", self,
                                            self.__onMonitorRemovedFromSet)
        self._workerPxySet.refreshListener(self)
        self._monitorPxySet.refreshListener(self)
        return taskmanager.TaskManager.initialize(self)


    ## Overrided Virtual Methods ##

    def _doStart(self):
        self.log("Ready to start monitoring, waiting monitors to become idle")
        d = self._monitorPxySet.waitIdle(adminconsts.WAIT_IDLE_TIMEOUT)
        d.addBoth(self.__cbStartResumeMonitoring)
        return d

    def _doResume(self):
        self.log("Ready to resume monitoring, waiting monitors to become idle")
        d = self._monitorPxySet.waitIdle(adminconsts.WAIT_IDLE_TIMEOUT)
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

    def __onWorkerAddedToSet(self, workerPxySet, workerPxy):
        self.log("Worker '%s' added to monitoring", workerPxy.label)
        self._balancer.addWorker(workerPxy)
        self._balancer.balance()

    def __onWorkerRemovedFromSet(self, workerPxySet, workerPxy):
        self.log("Worker '%s' removed from monitoring", workerPxy.label)
        self._balancer.removeWorker(workerPxy)
        self._balancer.balance()


    ## MonitorSet Event Listeners ##

    def __onMonitorAddedToSet(self, monitorPxySet, monitorPxy):
        self.log("Monitor '%s' added to monitoring", monitorPxy.label)
        d = self.addComponent(monitorPxy)
        d.addErrback(self.__ebAddComponentFailed, monitorPxy.getName())

    def __onMonitorRemovedFromSet(self, monitorPxySet, monitorPxy):
        self.log("Monitor '%s' removed from monitoring", monitorPxy.label)
        d = self.removeComponent(monitorPxy)
        d.addErrback(self.__ebRemoveComponentFailed, monitorPxy.getName())


    ## Overriden Methods ##

    def refreshListener(self, listener):
        for t in self._tasks.itervalues():
            self.emitTo("task-added", listener, t)


    ## Private Methods ##

    def __cbStartResumeMonitoring(self, result):
        if (isinstance(result, Failure)
            and not result.check(iherrors.TimeoutError)):
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
        # Call self._balancer.addTask(task, workerPxy)
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
