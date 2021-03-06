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

from flumotion.inhouse import log, defer, utils, events

from flumotion.transcoder.admin import adminconsts, transtask, notifysubs
from flumotion.transcoder.admin.enums import ActivityTypeEnum
from flumotion.transcoder.admin.enums import ActivityStateEnum
from flumotion.transcoder.admin.enums import NotificationTriggerEnum
from flumotion.transcoder.admin.context import profile

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
        self._order = [] # [puid]
        self._queue = {} # {puid: (ProfileContext, params)}
        self._activities = {} # {transtask.TranscodingTask: ActivityContext}
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
        self._transcoding.connectListener("task-added", self,
                                          self.__onTranscodingTaskAdded)
        self._transcoding.connectListener("task-removed", self,
                                          self.__onTranscodingTaskRemoved)
        self._transcoding.connectListener("slot-available", self,
                                          self.__onSlotsAvailable)
        self._transcoding.refreshListener(self)
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

    def addProfile(self, profCtx, params=None):
        assert isinstance(profCtx, profile.ProfileContext)
        if self.isProfileQueued(profCtx):
            self.log("Added an already queued profile '%s'", profCtx.inputPath)
        elif self._transcoding.getTask(profCtx.uid):
            self.log("Profile '%s' already scheduled", profCtx.inputPath)
        else:
            self.debug("Queued profile '%s'", profCtx.inputPath)
            self.__queueProfile(profCtx, params)
            self.__startupTasks()
            self.emit("profile-queued", profCtx)

    def removeProfile(self, profCtx):
        assert isinstance(profCtx, profile.ProfileContext)
        if self.isProfileQueued(profCtx):
            self.debug("Unqueue profile '%s'", profCtx.inputPath)
            self.__unqueuProfile(profCtx)
        trantask = self._transcoding.getTask(profCtx.uid, None)
        if trantask and not trantask.isAcknowledging():
            self.debug("Cancel transcoding of profile '%s'", profCtx.inputPath)
            self._transcoding.removeTask(profCtx.uid)

    def isProfileQueued(self, profCtx):
        assert isinstance(profCtx, profile.ProfileContext)
        return profCtx.uid in self._queue

    def isProfileActive(self, profCtx):
        assert isinstance(profCtx, profile.ProfileContext)
        trantask = self._transcoding.getTask(profCtx.uid, None)
        return trantask != None

    def waitIdle(self, timeout=None):
        return defer.succeed(self)


    ## ITranscoding Event Listers ##

    def __onTranscodingTaskAdded(self, takset, task):
        self.debug("Transcoding task '%s' added", task.label)
        task.connectListener("failed", self,
                             self.__onTranscodingFailed)
        task.connectListener("done", self,
                             self.__onTranscodingDone)
        task.connectListener("terminated", self,
                             self.__onTranscodingTerminated)
        task.refreshListener(self)

    def __onTranscodingTaskRemoved(self, tasker, task):
        self.debug("Transcoding task '%s' removed", task.label)
        task.disconnectListener("failed", self)
        task.disconnectListener("done", self)
        task.disconnectListener("terminated", self)

    def __onSlotsAvailable(self, tasker, count):
        self.log("Transcoding manager have %d slot(s) available", count)
        self.__startupTasks()


    ## transtask.TranscodingTask Event Listeners ##

    def __onTranscodingFailed(self, task, transPxy):
        activCtx = self._activities[task]
        activStore = activCtx.store
        activStore.state = ActivityStateEnum.failed
        activStore.store()
        if transPxy is not None:
            d = transPxy.retrieveReport()
            d.addErrback(self.__ebReportRetrievalFailed, False)
            d.addCallback(self.__transcodingFailed, task, transPxy)
        else:
            self.__transcodingFailed(None, task, transPxy)

    def __onTranscodingDone(self, task, transPxy):
        activCtx = self._activities[task]
        activStore = activCtx.store
        activStore.state = ActivityStateEnum.done
        activStore.store()
        if transPxy is not None:
            d = transPxy.retrieveReport()
            d.addErrback(self.__ebReportRetrievalFailed, True)
            d.addCallback(self.__transcodingDone, task, transPxy)
        else:
            self.__transcodingDone(None, task, transPxy)

    def __onTranscodingTerminated(self, task, succeed):
        self.info("Transcoding task '%s' %s", task.label,
                  (succeed and "succeed") or "failed")
        self._activities.pop(task)
        #FIXME: The task may have been already removed in response
        #       to the vile being removed from incoming.
        #       Canceling a task already acknowledged should be prevented.
        #       See #2921
        profCtx = task.getProfileContext()
        self._transcoding.removeTask(profCtx.uid)

    def __ebReportRetrievalFailed(self, failure, transcod_successful):
        if transcod_successful:
            msg = "successful"
        else:
            msg = "failed"
        log.notifyFailure(self, failure, "Failure during retrieving a %s transcoding report" % msg)
        # Not being able to retrieve the report doesn't mean that the
        # transcoding itself failed. Continue with the callback chain.
        return None

    ## EventSource Overriden Methods ##

    def refreshListener(self, listener):
        for (profCtx, params) in self._queue.itervalues():
            self.emitTo("profile-queued", listener, profCtx)
        for task in self._transcoding.iterTasks():
            self.emitTo("transcoding-started", listener, task)


    ## Private Methods ##

    def __transcodingDone(self, report, task, transPxy):
        self.emit("transcoding-done", task, report)
        docs = transPxy and transPxy.getDocuments()
        trigger = NotificationTriggerEnum.done
        profCtx = task.getProfileContext()
        self.__notify(task.label, trigger, profCtx, report, docs)

    def __transcodingFailed(self, report, task, transPxy):
        self.emit("transcoding-failed", task, report)
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
        trigger = NotificationTriggerEnum.failed
        profCtx = task.getProfileContext()
        self.__notify(task.label, trigger, profCtx, report,
                      docs, altErrorMessage=altErrorMessage)

    def __notify(self, label, trigger, profCtx, report,
                 docs, altErrorMessage=None):
        sourceVars = notifysubs.SourceNotificationVariables(profCtx, trigger, report)
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
                             activCtx.label)
                activCtx.store.delete()
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
        profCtx, params = self.__popNextProfile()
        if not profCtx:
            self._startDelay = None
            return
        self.__startTranscodingTask(profCtx, params=params)
        self._startDelay = utils.callNext(self.__asyncStartTask)

    def __startTranscodingTask(self, profCtx, activCtx=None, params=None):
        task = transtask.TranscodingTask(self._transcoding, profCtx, params)
        self.info("Starting transcoding task '%s'",  task.label)
        self._transcoding.addTask(profCtx.uid, task)
        self.emit("transcoding-started", task)
        if not activCtx:
            stateCtx = self._storeCtx.getStateContext()
            activCtx = stateCtx.newTranscodingContext(profCtx.activityLabel,
                                                      ActivityStateEnum.started,
                                                      profCtx)
            activCtx.store.store()
        self._activities[task] = activCtx

    def __getProfilePriority(self, profCtx):
        custCtx = profCtx.getCustomerContext()
        custPri = custCtx.customerPriority
        profPri = profCtx.transcodingPriority
        return custPri * 1000 + profPri

    def __getKeyPriority(self, key):
        return self.__getProfilePriority(self._queue[key][0])

    def __queueProfile(self, profCtx, params=None):
        puid = profCtx.uid
        assert not (puid in self._queue)
        self._queue[puid] =  (profCtx, params)
        self._order.append(puid)
        self._order.sort(key=self.__getKeyPriority)

    def __unqueuProfile(self, profCtx):
        puid = profCtx.uid
        assert puid in self._queue
        del self._queue[puid]
        self._order.remove(puid)

    def __popNextProfile(self):
        if not self._order:
            return (None, None)
        puid = self._order.pop()
        profCtx, params = self._queue.pop(puid)
        return (profCtx, params)

    def __clearQueue(self):
        self._queue.clear()
        del self._order[:]
