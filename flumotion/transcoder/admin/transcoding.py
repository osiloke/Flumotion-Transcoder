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
from flumotion.transcoder.admin.transbalancer import TranscoderBalancer


class Transcoding(TaskManager):
    
    logCategory = adminconsts.TRANSCODING_LOG_CATEGORY
    
    def __init__(self, workerset, transcoderset):
        TaskManager.__init__(self)
        self._workers = workerset
        self._transcoders = transcoderset
        self._balancer = TranscoderBalancer(self)
        # Registering Events
        self._register("task-added")
        self._register("task-removed")
        self._register("slot-available")

    ## Public Method ##
    
    def getAvailableSlots(self):
        return self._balancer.getAvailableSlots()

    def initialize(self):
        self.log("Initializing Transcoding Manager")
        self._workers.connect("worker-added",
                              self, self.onWorkerAddedToSet)
        self._workers.connect("worker-removed",
                              self, self.onWorkerRemovedFromSet)
        self._workers.update(self)
        self._transcoders.connect("transcoder-added",
                                  self, self.onTranscoderAddedToSet)
        self._transcoders.connect("transcoder-removed",
                                  self, self.onTranscoderRemovedFromSet)
        self._transcoders.update(self)
        return TaskManager.initialize(self)


    ## Overrided Virtual Methods ##

    def _doStart(self):
        self.log("Ready to start transcoding, waiting transcoders to become idle")
        d = self._transcoders.waitIdle(adminconsts.WAIT_IDLE_TIMEOUT)
        d.addBoth(self.__cbStartResumeTranscoding)
        return d
    
    def _doResume(self):
        self.log("Ready to resume transcoding, waiting transcoder to become idle")
        d = self._transcoders.waitIdle(adminconsts.WAIT_IDLE_TIMEOUT)
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
    
    def onWorkerAddedToSet(self, workerset, worker):
        self.log("Worker '%s' added to transcoding", worker.getLabel())
        self._balancer.addWorker(worker)
        self._balancer.balance()
    
    def onWorkerRemovedFromSet(self, workerset, worker):
        self.log("Worker '%s' removed from transcoding", worker.getLabel())
        self._balancer.removeWorker(worker)
        self._balancer.balance()


    ## TranscoderSet Event Listeners ##
    
    def onTranscoderAddedToSet(self, transcoderset, transcoder):
        self.log("Transcoder '%s' added to transcoding", transcoder.getLabel())
        d = self.addComponent(transcoder)
        d.addErrback(self.__ebAddComponentFailed, transcoder.getName())
    
    def onTranscoderRemovedFromSet(self, transcoderset, transcoder):
        self.log("Transcoder '%s' removed from transcoding", transcoder.getLabel())
        d = self.removeComponent(transcoder)
        d.addErrback(self.__ebRemoveComponentFailed, transcoder.getName())


    ## TranscodingBalancer Callback ##
    
    def onSlotsAvailable(self, balancer, count):
        self.emit("slot-available", count)


    ## Overriden Methods ##
    
    def update(self, listener):
        for t in self.iterTasks():
            self.emitTo("task-added", listener, t)
        available = self._balancer.getAvailableSlots()
        if available > 0:
            self.emitTo("slot-available", listener, available)


    ## Private Methods ##
    
    def __cbStartResumeTranscoding(self, result):
        if (isinstance(result, Failure) 
            and not result.check(TimeoutError)):
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
        # Call self._balancer.addTask(task, worker)
        d.addCallback(defer.shiftResult, self._balancer.addTask, 1, task)
        return d

    def __ebStartupResumingFailure(self, failure):
        log.notifyFailure(self, failure, 
                          "Failure during transcoding startup/resuming")

    def __ebAddComponentFailed(self, failure, name):
        log.notifyFailure(self, failure,
                          "Failed to add transcoder '%s' "
                          "to transcoding manager", name)
    
    def __ebRemoveComponentFailed(self, failure, name):
        log.notifyFailure(self, failure,
                          "Failed to remove transcoder '%s' "
                          "from transcoding manager", name)
