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

from flumotion.transcoder.admin import adminconsts, taskmanager, transbalancer


class Transcoding(taskmanager.TaskManager):

    logCategory = adminconsts.TRANSCODING_LOG_CATEGORY

    def __init__(self, workerPxySet, transPxySet):
        taskmanager.TaskManager.__init__(self)
        self._workerPxySet = workerPxySet
        self._transPxySet = transPxySet
        self._balancer = transbalancer.TranscoderBalancer(self)
        # Registering Events
        self._register("task-added")
        self._register("task-removed")
        self._register("slot-available")

    ## Public Method ##

    def getAvailableSlots(self):
        return self._balancer.getAvailableSlots()

    def initialize(self):
        self.log("Initializing Transcoding Manager")
        self._workerPxySet.connectListener("worker-added", self,
                                           self.__onWorkerAddedToSet)
        self._workerPxySet.connectListener("worker-removed", self,
                                           self.__onWorkerRemovedFromSet)
        self._transPxySet.connectListener("transcoder-added", self,
                                          self.__onTranscoderAddedToSet)
        self._transPxySet.connectListener("transcoder-removed", self,
                                          self.__onTranscoderRemovedFromSet)
        self._workerPxySet.refreshListener(self)
        self._transPxySet.refreshListener(self)
        return taskmanager.TaskManager.initialize(self)


    ## Overrided Virtual Methods ##

    def _doStart(self):
        self.log("Ready to start transcoding, waiting transcoders to become idle")
        d = self._transPxySet.waitIdle(adminconsts.WAIT_IDLE_TIMEOUT)
        d.addBoth(self.__cbStartResumeTranscoding)
        return d

    def _doResume(self):
        self.log("Ready to resume transcoding, waiting transcoder to become idle")
        d = self._transPxySet.waitIdle(adminconsts.WAIT_IDLE_TIMEOUT)
        d.addBoth(self.__cbStartResumeTranscoding)
        return d

    def _doPause(self):
        self.log("Pausing transcoding manager")
        for task in self.iterTasks():
            self._balancer.removeTask(task)

    def _doAbort(self):
        self.log("Aborting transcoding")
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
        self.log("Worker '%s' added to transcoding", workerPxy.label)
        self._balancer.addWorker(workerPxy)
        self._balancer.balance()

    def __onWorkerRemovedFromSet(self, workerPxySet, workerPxy):
        self.log("Worker '%s' removed from transcoding", workerPxy.label)
        self._balancer.removeWorker(workerPxy)
        self._balancer.balance()


    ## TranscoderSet Event Listeners ##

    def __onTranscoderAddedToSet(self, transPxySet, transPxy):
        self.log("Transcoder '%s' added to transcoding", transPxy.label)
        d = self.addComponent(transPxy)
        d.addErrback(self.__ebAddComponentFailed, transPxy.getName())

    def __onTranscoderRemovedFromSet(self, transPxySet, transPxy):
        self.log("Transcoder '%s' removed from transcoding", transPxy.label)
        d = self.removeComponent(transPxy)
        d.addErrback(self.__ebRemoveComponentFailed, transPxy.getName())


    ## TranscodingBalancer Callback ##

    def onSlotsAvailable(self, balancer, count):
        self.emit("slot-available", count)


    ## Overriden Methods ##

    def refreshListener(self, listener):
        for t in self.iterTasks():
            self.emitTo("task-added", listener, t)
        available = self._balancer.getAvailableSlots()
        if available > 0:
            self.emitTo("slot-available", listener, available)


    ## Private Methods ##

    def __cbStartResumeTranscoding(self, result):
        if (isinstance(result, Failure)
            and not result.check(iherrors.TimeoutError)):
            log.notifyFailure(self, result,
                              "Failure waiting transcoder set "
                              "to become idle")
        self.log("Free to continue transcoding startup/resuming")
        d = defer.Deferred()
        for task in self.iterTasks():
            d.addCallback(self.__cbAddBalancedTask, task)
        d.addCallback(defer.dropResult, self._balancer.balance)
        d.addErrback(self.__ebStartupResumingFailure)
        d.callback(None)
        return d

    def __cbAddBalancedTask(self, _, task):
        timeout = adminconsts.TRANSCODING_POTENTIAL_WORKER_TIMEOUT
        d = task.waitPotentialWorker(timeout)
        # Call self._balancer.addTask(task, workerPxy)
        d.addCallback(defer.shiftResult, self._balancer.addTask, 1, task)
        return d

    def __ebStartupResumingFailure(self, failure):
        log.notifyFailure(self, failure,
                          "Failure during transcoder startup/resuming")

    def __ebAddComponentFailed(self, failure, name):
        log.notifyFailure(self, failure,
                          "Failed to add transcoder '%s' "
                          "to transcoding manager", name)

    def __ebRemoveComponentFailed(self, failure, name):
        log.notifyFailure(self, failure,
                          "Failed to remove transcoder '%s' "
                          "from transcoding manager", name)
