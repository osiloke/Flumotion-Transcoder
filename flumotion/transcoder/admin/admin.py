# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import implements
from twisted.internet import reactor, defer

from flumotion.common.enum import EnumClass

from flumotion.transcoder import log
from flumotion.transcoder import utils
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.enums import MonitorFileStateEnum
from flumotion.transcoder.enums import TaskStateEnum
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.context.admincontext import AdminContext
from flumotion.transcoder.admin.context.transcontext import TranscodingContext
from flumotion.transcoder.admin.proxies.managerset import ManagerSet, ManagerSetListener
from flumotion.transcoder.admin.proxies.workerset import WorkerSet
from flumotion.transcoder.admin.proxies.transcoderset import TranscoderSet
from flumotion.transcoder.admin.proxies.monitorset import MonitorSet
from flumotion.transcoder.admin.datastore.adminstore import AdminStore, AdminStoreListener
from flumotion.transcoder.admin.datastore.customerstore import CustomerStore, CustomerStoreListener
from flumotion.transcoder.admin.datastore.profilestore import ProfileStore, ProfileStoreListener
from flumotion.transcoder.admin.datastore.targetstore import TargetStore, TargetStoreListener
from flumotion.transcoder.admin.monitoring import Monitoring, MonitoringListener
from flumotion.transcoder.admin.montask import MonitoringTask, MonitoringTaskListener
from flumotion.transcoder.admin.transcoding import Transcoding
from flumotion.transcoder.admin.scheduler import Scheduler, SchedulerListener


class TranscoderAdmin(log.Loggable,
                      ManagerSetListener,
                      MonitoringListener,
                      MonitoringTaskListener,
                      SchedulerListener,
                      AdminStoreListener,
                      CustomerStoreListener,
                      ProfileStoreListener):
    
    logCategory = adminconsts.ADMIN_LOG_CATEGORY
    
    def __init__(self, config):
        self._adminCtx = AdminContext(config)
        self._datasource = self._adminCtx.getDataSource()
        self._store = AdminStore(self._datasource)
        self._transCtx = TranscodingContext(self._adminCtx, self._store)
        self._managers = ManagerSet(self._adminCtx)
        self._workers = WorkerSet(self._managers)
        self._transcoders = TranscoderSet(self._managers)
        self._monitors = MonitorSet(self._managers)
        self._monitoring = Monitoring(self._workers, self._monitors)
        self._transcoding = Transcoding(self._workers, self._transcoders)
        self._scheduler = Scheduler(self._transCtx, self._store, 
                                    self._transcoding)
        self._state = TaskStateEnum.stopped
        reactor.addSystemEventTrigger("before", "shutdown", self.__abort)

    
    ## Public Methods ##
    
    def initialize(self):
        self.info("Initializing Transcoder Administration")
        d = defer.Deferred()
        d.addCallback(lambda r: self._datasource.initialize())
        d.addCallback(lambda r: self._store.initialize())
        d.addCallback(lambda r: self._managers.initialize())
        d.addCallback(lambda r: self._workers.initialize())
        d.addCallback(lambda r: self._monitors.initialize())
        d.addCallback(lambda r: self._transcoders.initialize())
        d.addCallback(lambda r: self._scheduler.initialize())
        d.addCallback(lambda r: self._monitoring.initialize())
        d.addCallback(lambda r: self._transcoding.initialize())
        d.addCallbacks(self.__cbAdminInitialized, 
                       self.__ebAdminInitializationFailed)
        # Register listeners
        self._store.addListener(self)
        self._managers.addListener(self)
        self._scheduler.addListener(self)
        self._monitoring.addListener(self)
        self._store.syncListener(self)
        self._managers.syncListener(self)
        self._scheduler.syncListener(self)
        self._monitoring.syncListener(self)
        # fire the initialization
        d.callback(defer._nothing)
        return d


    ## IManagerSetListener Overriden Methods ##
    
    def onDetached(self, managerset):
        if self._state == TaskStateEnum.started:
            self.debug("Transcoder admin has been detached, "
                       "pausing transcoding")
            self.__pause()
        
        
    def onAttached(self, managerset):
        if self._state == TaskStateEnum.paused:
            self.debug("Transcoder admin attached, "
                       "resuming transcoding")
            self.__resume()


    ## IAdminStoreListener Overriden Methods ##
    
    def onCustomerAdded(self, admin, customer):
        self.debug("Customer '%s' Added", customer.getLabel())
        customer.addListener(self)
        customer.syncListener(self)
        custCtx = self._transCtx.getCustomerContext(customer)
        task = MonitoringTask(self._monitoring, custCtx)
        self._monitoring.addTask(custCtx.getIdentifier(), task)
        
    def onCustomerRemoved(self, admin, customer):
        self.debug("Customer '%s' Removed", customer.getLabel())
        customer.removeListener(self)
        custCtx = self._transCtx.getCustomerContext(customer)
        self._monitoring.removeTask(custCtx.getIdentifier())
        
        
    ## ICustomerStoreListener Overriden Methods ##
    
    def onProfileAdded(self, customer, profile):
        self.debug("Profile '%s' Added", profile.getLabel())
        profile.addListener(self)
        profile.syncListener(self)
        
    def onProfileRemoved(self, customer, profile):
        self.debug("Profile '%s' Removed", profile.getLabel())
        profile.removeListener(self)
        
    
    ## IProfileStoreListener Overriden Methods ##
    
    def onTargetAdded(self, profile, target):
        self.debug("Target '%s' Added", target.getLabel())
        
    def onTargetRemoved(self, profile, target):
        self.debug("Target '%s' Removed", target.getLabel())


    ## IMonitoringLister Overriden Methods ##
    
    def onMonitoringTaskAdded(self, takser, task):
        self.debug("Monitoring task '%s' added", task.getLabel())
        task.addListener(self)
        task.syncListener(self)
    
    def onMonitoringTaskRemoved(self, tasker, task):
        self.debug("Monitoring task '%s' removed", task.getLabel())
        task.removeListener(self)


    ## IMonitoringTaskLister Overriden Methods ##
    
    def onMonitoredFileAdded(self, montask, profileContext, state):
        self.log("Monitoring task '%s' added profile '%s'",
                 montask.getLabel(), profileContext.getInputPath())
        self.__fileStateChanged(montask, profileContext, state)
        
    def onMonitoredFileStateChanged(self, montask, profileContext, state):
        self.log("Monitoring task '%s' profile '%s' state "
                 "changed to %s", montask.getLabel(), 
                 profileContext.getInputPath(), state.name)
        self.__fileStateChanged(montask, profileContext, state)
    
    def onMonitoredFileRemoved(self, montask, profileContext, state):
        self.log("Monitoring task '%s' removed profile '%s'",
                 montask.getLabel(), profileContext.getInputPath())
        self._scheduler.removeProfile(profileContext)

    
    ## ISchedulerListener Overriden Methods ##
    
    def onProfileQueued(self, scheduler, profileContext):
        self.__setInputFileState(profileContext,
                                 MonitorFileStateEnum.queued)
        
    def onTranscodingStarted(self, scheduler, task):
        self.__setInputFileState(task.getProfileContext(),
                                 MonitorFileStateEnum.transcoding)
    
    def onTranscodingFail(self, sheduler, task):
        self.__setInputFileState(task.getProfileContext(),
                                 MonitorFileStateEnum.failed)
        if not task.isAcknowledged():
            # If a transcoding fail without acknowledgment,
            # it propably segfault or has been killed.
            # So we have to move the input file to the
            # "fail" directory ourself.
            ctx = task.getProfileContext()
            self.debug("Transcoding task for '%s' segfaulted "
                       "or has been kill", ctx.getInputPath())
            self.__moveFailedInputFiles(ctx)
    
    def onTranscodingDone(self, sheduler, task):
        self.__setInputFileState(task.getProfileContext(),
                                 MonitorFileStateEnum.done)

    
    ## Private Methods ##
    
    def __fileStateChanged(self, montask, profCtx, state):
        
        def changeState(newState):
            inputBase = profCtx.getInputBase()
            relPath = profCtx.getInputRelPath()        
            montask.setFileState(inputBase, relPath, newState)

        # Schedule new file if not alreday scheduled
        # and synchronize the file states
        queued = self._scheduler.isProfileQueued(profCtx)
        active = self._scheduler.isProfileActive(profCtx)
        if state == MonitorFileStateEnum.pending:
            if queued:
                changeState(MonitorFileStateEnum.queued)
                return
            if active:
                changeState(MonitorFileStateEnum.transcoding)
                return
            self._scheduler.addProfile(profCtx)
            return
        if state == MonitorFileStateEnum.queued:
            if active:
                changeState(MonitorFileStateEnum.transcoding)
                return
            if queued:
                return
            self._scheduler.addProfile(profCtx)
            return
        if state == MonitorFileStateEnum.transcoding:
            if queued:
                changeState(MonitorFileStateEnum.queued)
                return
            if active:
                return
            self._scheduler.addProfile(profCtx)
            return
    
    def __moveFailedInputFiles(self, profCtx):
        custCtx = profCtx.customer
        inputBase = profCtx.getInputBase()
        failedBase = profCtx.getFailedBase()
        relPath = profCtx.getInputRelPath()
        task = self._monitoring.getTask(custCtx.getIdentifier())
        if not task:
            self.warning("No monitoring task found for customer '%s'; "
                         "cannot move files from '%s' to '%s'",
                         custCtx.store.getLabel(), inputBase, failedBase)
            return
        task.moveFiles(inputBase, failedBase, [relPath])
    
    def __setInputFileState(self, profCtx, state):
        custCtx = profCtx.customer
        inputBase = profCtx.getInputBase()
        task = self._monitoring.getTask(custCtx.getIdentifier())
        if not task:
            self.warning("No monitoring task found for customer '%s'; "
                         "cannot set file '%s' state to %s",
                         custCtx.store.getLabel(), inputBase, state.name)
            return
        relPath = profCtx.getInputRelPath()        
        task.setFileState(inputBase, relPath, state)
    
    def __startup(self):
        if not (self._state == TaskStateEnum.stopped):
            raise TranscoderError("Cannot start transcoder admin when %s"
                                   % self._state.name)
        self.info("Starting Transcoder Administration")
        self._state = TaskStateEnum.starting
        d = defer.Deferred()
        d.addCallback(utils.bridgeResult, self.debug,
                      "Starting monitoring manager")
        d.addCallback(utils.dropResult, self._monitoring.start,
                      adminconsts.MONITORING_START_TIMEOUT)
        # Wait monitor components to be activated before continuing
        d.addCallback(utils.bridgeResult, self.debug,
                      "Waiting for monitoring to become active")
        d.addCallback(utils.dropResult, self._monitoring.waitActive,
                      adminconsts.MONITORING_ACTIVATION_TIMEOUT)
        d.addCallback(utils.bridgeResult, self.debug,
                      "Starting transcoding manager")
        d.addCallback(utils.dropResult, self._transcoding.start,
                      adminconsts.TRANSCODING_START_TIMEOUT)
        d.addCallback(utils.bridgeResult, self.debug,
                      "Starting scheduler manager")
        d.addCallback(utils.dropResult, self._scheduler.start,
                      adminconsts.SCHEDULER_START_TIMEOUT)
        d.addCallbacks(self.__cbSartupSucceed, self.__ebSartupFailed)
        d.callback(defer._nothing)
        
    def __resume(self):
        if not (self._state == TaskStateEnum.paused):
            raise TranscoderError("Cannot resume transcoder admin when %s"
                                  % self._state.name)
        self.info("Resuming Transcoder Administration")
        self._state = TaskStateEnum.resuming
        d = defer.Deferred()
        # Wait a moment to let the workers the oportunity 
        # to log back to the manager.
        d.addCallback(utils.bridgeResult, self.debug,
                      "Waiting for workers to log back")
        d.addCallback(utils.delayedSuccess, adminconsts.RESUME_DELAY)
        d.addCallback(utils.bridgeResult, self.debug,
                      "Resuming monitoring manager")
        d.addCallback(utils.dropResult, self._monitoring.resume,
                      adminconsts.MONITORING_RESUME_TIMEOUT)
        # Wait monitor components to be activated before continuing
        d.addCallback(utils.bridgeResult, self.debug,
                      "Waiting for monitoring to become active")
        d.addCallback(utils.dropResult, self._monitoring.waitActive,
                      adminconsts.MONITORING_ACTIVATION_TIMEOUT)
        d.addCallback(utils.bridgeResult, self.debug,
                      "Resuming transcoding manager")
        d.addCallback(utils.dropResult, self._transcoding.resume,
                      adminconsts.TRANSCODING_RESUME_TIMEOUT)
        d.addCallback(utils.bridgeResult, self.debug,
                      "Resuming scheduler")
        d.addCallback(utils.dropResult, self._scheduler.resume,
                      adminconsts.SCHEDULER_RESUME_TIMEOUT)
        d.addCallbacks(self.__cbResumingSucceed, self.__ebResumingFailed)
        d.callback(defer._nothing)
        
    def __pause(self):
        if not (self._state == TaskStateEnum.started):
            raise TranscoderError("Cannot pause transcoder admin when %s"
                                   % self._state.name)
        self.info("Pausing Transcoder Administration")
        d = defer.Deferred()
        d.addCallback(utils.bridgeResult, self.debug,
                      "Pausing scheduler")
        d.addCallback(utils.dropResult, self._scheduler.pause,
                      adminconsts.SCHEDULER_PAUSE_TIMEOUT)
        d.addCallback(utils.bridgeResult, self.debug,
                      "Pausing transcoding manager")
        d.addCallback(utils.dropResult, self._transcoding.pause,
                      adminconsts.TRANSCODING_PAUSE_TIMEOUT)
        d.addCallback(utils.bridgeResult, self.debug,
                      "Pausing monitoring manager")
        d.addCallback(utils.dropResult, self._monitoring.pause,
                      adminconsts.MONITORING_PAUSE_TIMEOUT)
        d.addCallbacks(self.__cbPausingSucceed, self.__ebPausingFailed)
        d.callback(defer._nothing)
        
    def __abort(self):
        if self._state == TaskStateEnum.terminated:
            return
        self._state = TaskStateEnum.terminated
        
    def __cbAdminInitialized(self, result):
        self.info("Waiting Transcoder Administration to become Idle")
        self.debug("Waiting store to become idle")
        # First wait for the store to become idle
        d = self._store.waitIdle(adminconsts.WAIT_IDLE_TIMEOUT)
        # And then for the managers/workers/components        
        d.addBoth(utils.bridgeResult, self.debug,
                  "Waiting managers to become idle")
        d.addBoth(utils.dropResult, self._managers.waitIdle, 
                  adminconsts.WAIT_IDLE_TIMEOUT)
        d.addBoth(utils.bridgeResult, self.debug,
                  "Waiting monitoring manager to become idle")
        d.addBoth(utils.dropResult, self._monitoring.waitIdle,
                  adminconsts.WAIT_IDLE_TIMEOUT)
        d.addBoth(utils.bridgeResult, self.debug,
                  "Waiting transcoding manager to become idle")
        d.addBoth(utils.dropResult, self._transcoding.waitIdle,
                  adminconsts.WAIT_IDLE_TIMEOUT)
        d.addBoth(utils.bridgeResult, self.debug,
                  "Waiting scheduler to become idle")
        d.addBoth(utils.dropResult, self._scheduler.waitIdle,
                  adminconsts.WAIT_IDLE_TIMEOUT)
        d.addBoth(utils.dropResult, self.__startup)
        return self
    
    def __ebAdminInitializationFailed(self, failure):
        reactor.stop()
        self.error("Transcoder Administration Initialization Failed: %s",
                   log.getFailureMessage(failure))

    def __cbSartupSucceed(self, result):
        self.info("Transcoder Administration Successfully Started")
        self._state = TaskStateEnum.started

    def __ebSartupFailed(self, failure):
        self.warning("Failed to startup administration: %s",
                     log.getFailureMessage(failure))
        self.debug("Startup failure traceback:\n%s", 
                   log.getFailureTraceback(failure))
        self._state = TaskStateEnum.stopped

    def __cbResumingSucceed(self, result):
        self.info("Transcoder Administration Successfully Resumed")
        self._state = TaskStateEnum.started

    def __ebResumingFailed(self, failure):
        self.warning("Failed to resume administration: %s",
                     log.getFailureMessage(failure))
        self.debug("Resuming failure traceback:\n%s", 
                   log.getFailureTraceback(failure))
        self._state = TaskStateEnum.paused
        
    def __cbPausingSucceed(self, result):
        self.info("Transcoder Administration Successfully Paused")
        self._state = TaskStateEnum.paused

    def __ebPausingFailed(self, failure):
        self.warning("Failed to pause administration: %s",
                     log.getFailureMessage(failure))
        self.debug("Pausing failure traceback:\n%s", 
                   log.getFailureTraceback(failure))
        self._state = TaskStateEnum.started
