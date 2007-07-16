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
from twisted.internet import reactor, defer

from flumotion.common.enum import EnumClass

from flumotion.transcoder import log
from flumotion.transcoder.enums import ActivityTypeEnum
from flumotion.transcoder.enums import ActivityStateEnum
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.eventsource import EventSource
from flumotion.transcoder.admin.transcoding import TranscodingListener
from flumotion.transcoder.admin.transtask import TranscodingTask
from flumotion.transcoder.admin.transtask import TranscodingTaskListener

#TODO: Implement a faire scheduler and prevent the possibility
#      of the profile priority making the overhaul customer priority
#      higher than other customer priorities.



class ISchedulerListener(Interface):
    
    def onProfileQueued(self, scheduler, profileContext):
        pass
    
    def onTranscodingStarted(self, scheduler, task):
        pass
    
    def onTranscodingFail(self, sheduler, task):
        pass
    
    def onTranscodingDone(self, sheduler, task):
        pass
        

class SchedulerListener(object):
    
    implements(ISchedulerListener)
    
    def onProfileQueued(self, scheduler, profileContext):
        pass
    
    def onTranscodingStarted(self, scheduler, task):
        pass
    
    def onTranscodingFail(self, sheduler, task):
        pass
    
    def onTranscodingDone(self, sheduler, task):
        pass


class Scheduler(log.Loggable, 
                EventSource, 
                TranscodingListener, 
                TranscodingTaskListener):
    
    logCategory = adminconsts.SCHEDULER_LOG_CATEGORY
    
    def __init__(self, transCtx, activityStore, transcoding):
        EventSource.__init__(self, ISchedulerListener)
        self._transCtx = transCtx
        self._store = activityStore
        self._transcoding = transcoding
        self._order = [] # [identifier]
        self._queue = {} # {identifier: ProfileContext}
        self._activities = {} # {TranscodingTask: Activity}
        self._started = False
        self._paused = False
        self._startDelay = None
        
        
    ## Public Methods ##
        
    def initialize(self):
        self.debug("Retrieve transcoding activities")
        states = [ActivityStateEnum.started]
        d = self._store.getTranscodings(states)
        d.addCallback(self.__cbRestoreTasks)
        d.addErrback(self.__ebInitializationFailed)
        self._transcoding.addListener(self)
        self._transcoding.syncListener(self)
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
        
    def addProfile(self, profileContext):
        inputPath = profileContext.getInputPath()
        identifier = profileContext.getIdentifier()
        if self.isProfileQueued(profileContext):
            self.log("Added an already queued profile '%s'", inputPath)
        elif self._transcoding.getTask(identifier):
            self.log("Added an already transcoding profile '%s'", inputPath)
        else:
            self.debug("Queued profile '%s'", inputPath)
            self.__queueProfile(profileContext)
            self.__startupTasks()
            self._fireEvent(profileContext, "ProfileQueued")
    
    def removeProfile(self, profileContext):
        inputPath = profileContext.getInputPath()
        identifier = profileContext.getIdentifier()
        if self.isProfileQueued(profileContext):
            self.debug("Unqueue profile '%s'", inputPath)
            self.__unqueuProfile(profileContext)
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
    
    
    ## ITranscodingLister Overriden Methods ##
    
    def onTranscodingTaskAdded(self, takser, task):
        self.debug("Transcoding task '%s' added", task.getLabel())
        task.addListener(self)
        task.syncListener(self)
    
    def onTranscodingTaskRemoved(self, tasker, task):
        self.debug("Transcoding task '%s' removed", task.getLabel())
        task.removeListener(self)

    def onSlotsAvailable(self, tasker, count):
        self.log("Transcoding manager have %d slot(s) available", count)
        self.__startupTasks()


    ## ITranscodingTaskLister Overriden Methods ##
    
    def onTranscodingFailed(self, task, transcoder):
        activity = self._activities[task]
        activity.setState(ActivityStateEnum.failed)
        activity.store()
        self._fireEvent(task, "TranscodingFail")
        
    
    def onTranscodingDone(self, task, transcoder):
        activity = self._activities[task]
        activity.setState(ActivityStateEnum.done)
        activity.store()
        self._fireEvent(task, "TranscodingDone")

    def onTranscodingTerminated(self, task, succeed):
        self.log("Transcoding task '%s' %s", task.getLabel(), 
                 (succeed and "succeed") or "failed")
        ctx = task.getProfileContext()
        self._transcoding.removeTask(ctx.getIdentifier())
        self._activities.pop(task)

        
    ## EventSource Overriden Methods ##
    
    def _doSyncListener(self, listener):
        for ctx in self._queue.itervalues():
            self._fireEventTo(ctx, listener, "ProfileQueued")
        for task in self._transcoding.iterTasks():
            self._fireEventTo(task, listener, "TranscodingStarted")

        
    ## Private Methods ##
    
    def __cbRestoreTasks(self, activities):
        self.debug("Restoring transcoding tasks")
        for activity in activities:
            prof = activity.getProfile()
            relPath = activity.getInputRelPath()
            if not (prof and relPath):
                self.warning("Activity without valid profile information (%s)",
                             activity.getLabel())
                activity.delete()
                continue
            profCtx = self._transCtx.getProfileContext(prof, relPath)
            if self.isProfileQueued(profCtx):
                self.__unqueuProfile(profCtx)
            self.__startTranscodingTask(profCtx, activity)
    
    def __ebInitializationFailed(self, failure):
        return failure
    
    def __startup(self):
        available = self._transcoding.getAvailableSlots()
        self.debug("Starting/Resuming transcoding scheduler (%d slots)", available)
        self.__startupTasks()
    
    def __startupTasks(self):
        if self.isStarted() and not self._startDelay:
            self._startDelay = reactor.callLater(0, self.__asyncStartTask)
    
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
        self._startDelay = reactor.callLater(0, self.__asyncStartTask)
        
    def __startTranscodingTask(self, profCtx, activity=None):
        self.log("Creating transcoding task for file '%s'", 
                 profCtx.getInputPath())
        identifier = profCtx.getIdentifier()
        task = TranscodingTask(self._transcoding, profCtx)
        self._transcoding.addTask(identifier, task)
        self._fireEvent(task, "TranscodingStarted")
        if not activity:
            activity = self._store.newTranscoding(profCtx.getActivityLabel(),
                                                  ActivityStateEnum.started,
                                                  profCtx.store,
                                                  profCtx.getInputRelPath())
            activity.store()
        self._activities[task] = activity

    def __getProfilePriority(self, profCtx):
        custPri = profCtx.customer.store.getCustomerPriority()
        profPri = profCtx.store.getTranscodingPriority()
        return custPri * 1000 + profPri

    def __getKeyPriority(self, key):
        return self.__getProfilePriority(self._queue[key])

    def __queueProfile(self, profCtx):
        identifier = profCtx.getIdentifier()
        assert not (identifier in self._queue)
        self._queue[identifier] =  profCtx
        self._order.append(identifier)
        self._order.sort(key=self.__getKeyPriority)
    
    def __unqueuProfile(self, profCtx):
        identifier = profCtx.getIdentifier()
        assert identifier in self._queue
        del self._queue[identifier]
        self._order.remove(identifier)

    def __popNextProfile(self):
        if not self._order:
            return None
        identifier = self._order.pop()
        profCtx = self._queue.pop(identifier)
        return profCtx
    
    def __clearQueue(self):
        self._queue.clear()
        del self._order[:]
