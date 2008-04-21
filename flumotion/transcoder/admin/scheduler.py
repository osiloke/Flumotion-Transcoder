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

from flumotion.inhouse import log, defer, utils, events

from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.enums import ActivityTypeEnum
from flumotion.transcoder.admin.enums import ActivityStateEnum
from flumotion.transcoder.admin.enums import NotificationTriggerEnum
from flumotion.transcoder.admin.transtask import TranscodingTask
from flumotion.transcoder.admin.notifysubs import SourceNotificationVariables
from flumotion.transcoder.admin.notifysubs import TargetNotificationVariables

#TODO: Implement a faire scheduler and prevent the possibility
#      of the profile priority making the overhaul customer priority
#      higher than other customer priorities.


class IScheduler(Interface):
    pass


class Scheduler(log.Loggable, events.EventSourceMixin):
    implements(IScheduler)
    
    logCategory = adminconsts.SCHEDULER_LOG_CATEGORY
    
    def __init__(self, schedulerContext, storeContext, 
                 notifier, transcoding, diagnostician):
        self._schedulerCtx = schedulerContext
        self._storeCtx = storeContext
        self._notifier = notifier
        self._transcoding = transcoding
        self._diagnostician = diagnostician
        self._order = [] # [identifier]
        self._queue = {} # {identifier: ProfileContext}
        self._activities = {} # {TranscodingTask: ActivityContext}
        self._started = False
        self._paused = False
        self._startDelay = None
        # Registering Events
        self._register("profile-queued")
        self._register("transcoding-started")
        self._register("transcoding-failed")
        self._register("transcoding-done")
        
        
    ## Public Methods ##
        
    def initialize(self):
        self.debug("Retrieve transcoding activities")
        self._transcoding.connectListener("task-added", self, self._onTranscodingTaskAdded)
        self._transcoding.connectListener("task-removed", self, self._onTranscodingTaskRemoved)
        self._transcoding.connectListener("slot-available", self, self._onSlotsAvailable)
        self._transcoding.update(self)
        states = [ActivityStateEnum.started]
        stateCtx = self._storeCtx.getStateContext()
        d = stateCtx.retrieveTranscodingContexts(states)
        d.addCallback(self.__cbRestoreTasks)
        d.addErrback(self.__ebInitializationFailed)
        return d
    
    def isStarted(self):
        return self._started and not self._paused
    
    def start(self, timeout=None):
        if not self._started:
            self._started = True
            self._paused = False
            self.__startup()
        return defer.succeed(self)
    
    def pause(self, timeout=None):
        if not self._paused:
            self._paused = True
            self.__clearQueue()
            self.__cancelTasksStartup()
        return defer.succeed(self)
    
    def resume(self, timeout=None):
        if self._started and self._paused:
            self._paused = False
            self.__startup()
        return defer.succeed(self)
        
    def addProfile(self, profCtx):
        inputPath = profCtx.getInputPath()
        identifier = profCtx.getIdentifier()
        if self.isProfileQueued(profCtx):
            self.log("Added an already queued profile '%s'", inputPath)
        elif self._transcoding.getTask(identifier):
            self.log("Added an already transcoding profile '%s'", inputPath)
        else:
            self.debug("Queued profile '%s'", inputPath)
            self.__queueProfile(profCtx)
            self.__startupTasks()
            self.emit("profile-queued", profCtx)
    
    def removeProfile(self, profCtx):
        inputPath = profCtx.getInputPath()
        identifier = profCtx.getIdentifier()
        if self.isProfileQueued(profCtx):
            self.debug("Unqueue profile '%s'", inputPath)
            self.__unqueuProfile(profCtx)
        trantask = self._transcoding.getTask(identifier, None)
        if trantask and not trantask.isAcknowledging():
            self.debug("Cancel transcoding of profile '%s'", inputPath)
            self._transcoding.removeTask(identifier)
    
    def isProfileQueued(self, profCtx):
        return profCtx.getIdentifier() in self._queue
    
    def isProfileActive(self, profCtx):
        identifier = profCtx.getIdentifier()
        trantask = self._transcoding.getTask(identifier, None)
        return trantask != None
    
    def waitIdle(self, timeout=None):
        return defer.succeed(self)
    
    
    ## ITranscoding Event Listers ##
    
    def _onTranscodingTaskAdded(self, takset, task):
        self.debug("Transcoding task '%s' added", task.getLabel())
        task.connectListener("failed", self, self._onTranscodingFailed)
        task.connectListener("done", self, self._onTranscodingDone)
        task.connectListener("terminated", self, self._onTranscodingTerminated)
        task.update(self)
    
    def _onTranscodingTaskRemoved(self, tasker, task):
        self.debug("Transcoding task '%s' removed", task.getLabel())
        task.disconnectListener("failed", self)
        task.disconnectListener("done", self)
        task.disconnectListener("terminated", self)

    def _onSlotsAvailable(self, tasker, count):
        self.log("Transcoding manager have %d slot(s) available", count)
        self.__startupTasks()


    ## TranscodingTask Event Listeners ##
    
    def _onTranscodingFailed(self, task, transPxy):
        activCtx = self._activities[task]
        activStore = activCtx.getStore()
        activStore.setState(ActivityStateEnum.failed)
        activStore.store()
        self.emit("transcoding-failed", task)
        if transPxy is not None:
            d = transPxy.retrieveReport()
            d.addCallback(self.__transcodingFailed, task, transPxy)
        else:
            self.__transcodingFailed(None, task, transPxy)
            
    def _onTranscodingDone(self, task, transPxy):
        activCtx = self._activities[task]
        activStore = activCtx.getStore()
        activStore.setState(ActivityStateEnum.done)
        activStore.store()
        self.emit("transcoding-done", task)
        if transPxy is not None:
            d = transPxy.retrieveReport()
            d.addCallback(self.__transcodingDone, task, transPxy)
        else:
            self.__transcodingDone(None, task, transPxy)

    def _onTranscodingTerminated(self, task, succeed):
        self.info("Transcoding task '%s' %s", task.getLabel(), 
                  (succeed and "succeed") or "failed")
        profCtx = task.getProfileContext()
        self._transcoding.removeTask(profCtx.getIdentifier())
        self._activities.pop(task)

        
    ## EventSource Overriden Methods ##
    
    def update(self, listener):
        for profCtx in self._queue.itervalues():
            self.emitTo("profile-queued", listener, profCtx)
        for task in self._transcoding.iterTasks():
            self.emitTo("transcoding-started", listener, task)

        
    ## Private Methods ##
    
    def __transcodingDone(self, report, task, transPxy):
        label = task.getLabel()
        docs = transPxy and transPxy.getDocuments()
        trigger = NotificationTriggerEnum.done
        profCtx = task.getProfileContext()
        self.__notify(label, trigger, profCtx, report, docs)
    
    def __transcodingFailed(self, report, task, transPxy):    
        d = self._diagnostician.diagnoseTranscodingFailure(task, transPxy)
        args = (report, task, transPxy)
        d.addCallbacks(self.__notifyTranscodingfailure,
                       self.__ebFailureDiagnosticFailed,
                       callbackArgs=args, errbackArgs=args)
    
    def __ebFailureDiagnosticFailed(self, failure, report, task, transPxy):
        log.notifyFailure(self, failure, "Failure during transcoding failure diagnostic")
        # But we continue like if nothing has append
        self.__notifyTranscodingfailure(None, report, task, transPxy)
    
    def __notifyTranscodingfailure(self, diagnostic, report, task, transPxy):
        docs = transPxy and transPxy.getDocuments()
        # It possible create an alternative error message for
        # when there is no report or no error message in the report
        altErrorMessage = None
        sigv = task.getProcessInterruptionCount()
        if (sigv > 0):
            altErrorMessage = ("Transcoding Job seems to have segfaulted "
                               "%d time(s)" % sigv)
        if diagnostic:
            if docs:
                docs.extend(diagnostic)
            else:
                docs = diagnostic
        label = task.getLabel()                
        trigger = NotificationTriggerEnum.failed
        profCtx = task.getProfileContext()
        self.__notify(label, trigger, profCtx, report,
                      docs, altErrorMessage=altErrorMessage)
    
    def __notify(self, label, trigger, profCtx, report,
                 docs, altErrorMessage=None):
        sourceVars = SourceNotificationVariables(profCtx, trigger, report)
        if altErrorMessage and (not sourceVars["errorMessage"]):
            sourceVars["errorMessage"] = altErrorMessage
        # Global notifications
        storeCtx = profCtx.getStoreContext()
        contexts = storeCtx.getNotificationContexts(trigger)
        for n in contexts:
            d = self._notifier.notify(label, trigger, n, sourceVars, docs)
            # Ignore Failures to prevent defer to notify them
            d.addErrback(defer.resolveFailure)
        # Customer notifications
        custCtx = profCtx.getCustomerContext()
        notifCtxs = custCtx.getNotificationContexts(trigger)
        for n in notifCtxs:
            d = self._notifier.notify(label, trigger, n, sourceVars, docs)
            # Ignore Failures to prevent defer to notify them
            d.addErrback(defer.resolveFailure)
        # Profile notifications
        notifCtxs = profCtx.getNotificationContexts(trigger)
        for n in notifCtxs:
            d = self._notifier.notify(label, trigger, n, sourceVars, docs)
            # Ignore Failures to prevent defer to notify them
            d.addErrback(defer.resolveFailure)
        # Targets notifications
        for targCtx in profCtx.iterTargetContexts():
            notifCtxs = targCtx.getNotificationContexts(trigger)
            if not notifCtxs:
                continue
            for n in notifCtxs:
                targVars = sourceVars.getTargetVariables(targCtx)
                d = self._notifier.notify(label, trigger, n, targVars, docs)
                # Ignore Failures to prevent defer to notify them
                d.addErrback(defer.resolveFailure)
    
    def __cbRestoreTasks(self, activCtxs):
        self.debug("Restoring transcoding tasks")
        for activCtx in activCtxs:
            profCtx = activCtx.getProfileContext()
            if (profCtx is None) or (not profCtx.isBound()):
                self.warning("Activity without valid profile information (%s)",
                             activCtx.getLabel())
                activStore = activCtx.getStore()
                activStore.delete()
                continue
            if self.isProfileQueued(profCtx):
                self.__unqueuProfile(profCtx)
            self.__startTranscodingTask(profCtx, activCtx)
    
    def __ebInitializationFailed(self, failure):
        return failure
    
    def __startup(self):
        available = self._transcoding.getAvailableSlots()
        self.debug("Starting/Resuming transcoding scheduler (%d slots)", available)
        self.__startupTasks()
    
    def __startupTasks(self):
        if self.isStarted() and not self._startDelay:
            self._startDelay = utils.callNext(self.__asyncStartTask)
    
    def __cancelTasksStartup(self):
        if self._startDelay:
            self._startDelay.cancel()
            self._startDelay = None
    
    def __asyncStartTask(self):
        available = self._transcoding.getAvailableSlots()
        if available <= 0:
            self._startDelay = None
            return
        profCtx = self.__popNextProfile()
        if not profCtx: 
            self._startDelay = None
            return
        self.__startTranscodingTask(profCtx)
        self._startDelay = utils.callNext(self.__asyncStartTask)
        
    def __startTranscodingTask(self, profCtx, activCtx=None):
        identifier = profCtx.getIdentifier()
        task = TranscodingTask(self._transcoding, profCtx)
        self.info("Starting transcoding task '%s'", 
                  task.getLabel())
        self._transcoding.addTask(identifier, task)
        self.emit("transcoding-started", task)
        if not activCtx:
            stateCtx = self._storeCtx.getStateContext()
            activCtx = stateCtx.newTranscodingContext(profCtx.getActivityLabel(),
                                                      ActivityStateEnum.started,
                                                      profCtx)
            activStore = activCtx.getStore()
            activStore.store()
        self._activities[task] = activCtx

    def __getProfilePriority(self, profCtx):
        custCtx = profCtx.getCustomerContext()
        custPri = custCtx.getCustomerPriority()
        profPri = profCtx.getTranscodingPriority()
        return custPri * 1000 + profPri

    def __getKeyPriority(self, key):
        return self.__getProfilePriority(self._queue[key])

    def __queueProfile(self, profCtx):
        profIdent = profCtx.getIdentifier()
        assert not (profIdent in self._queue)
        self._queue[profIdent] =  profCtx
        self._order.append(profIdent)
        self._order.sort(key=self.__getKeyPriority)
    
    def __unqueuProfile(self, profCtx):
        profIdent = profCtx.getIdentifier()
        assert profIdent in self._queue
        del self._queue[profIdent]
        self._order.remove(profIdent)

    def __popNextProfile(self):
        if not self._order:
            return None
        profIdent = self._order.pop()
        profCtx = self._queue.pop(profIdent)
        return profCtx
    
    def __clearQueue(self):
        self._queue.clear()
        del self._order[:]
