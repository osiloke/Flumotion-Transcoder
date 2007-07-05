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

from flumotion.transcoder import log

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
    
    def onTranscodingStarted(self, scheduler, profileContext):
        pass
    
    def onTranscodingFail(self, sheduler, profileContext):
        pass
    
    def onTranscodingDone(self, sheduler, profileContext):
        pass


class Scheduler(log.Loggable, 
                EventSource, 
                TranscodingListener, 
                TranscodingTaskListener):
    
    logCategory = adminconsts.SCHEDULER_LOG_CATEGORY
    
    def __init__(self, store, transcoding):
        EventSource.__init__(self, ISchedulerListener)
        self._store = store
        self._transcoding = transcoding
        self._order = [] # [identifier]
        self._queue = {} # {identifier: ProfileContext}
        self._started = False
        self._paused = False
        
        
    ## Public Methods ##
        
    def initialize(self):
        #self._store.addListener(self)
        self._transcoding.addListener(self)
        self._transcoding.syncListener(self)
        return defer.succeed(self)
    
    def waitIdle(self, timeout=None):
        return defer.succeed(self)
    
    def start(self, timeout=None):
        if not self._started:
            self._started = True
            self._paused = False
            self.__startup()
        return defer.succeed(self)
    
    def pause(self):
        if not self._paused:
            self._paused = True
    
    def resume(self):
        if self._started and self._paused:
            self._paused = False
            self.__startup()
        return defer.succeed(self)
        
    def addProfile(self, profileContext):
        inputPath = profileContext.getInputPath()
        identifier = profileContext.getIdentifier()
        if self.__isProfileQueued(profileContext):
            self.debug("Added an already queued profile '%s'", inputPath)
        elif self._transcoding.getTask(identifier):
            self.debug("Added an already transcoding profile '%s'", inputPath)
        else:
            self.debug("Queued profile '%s'", inputPath)
            self.__queueProfile(profileContext)
            self.__startupTasksIfPossible()
            self._fireEvent(profileContext, "ProfileQueued")
    
    def removeProfile(self, profileContext):
        inputPath = profileContext.getInputPath()
        identifier = profileContext.getIdentifier()
        if self.__isProfileQueued(profileContext):
            self.debug("Unqueue profile '%s'", inputPath)
            self.__unqueuProfile(profileContext)
        trantask = self._transcoding.getTask(identifier, None)
        if trantask and not trantask.isAcknowledging():
            self.debug("Cancel transcoding of profile '%s'", inputPath)
            self._transcoding.removeTask(trantask)
    
    
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
        self.__startupTasks(count)


    ## ITranscodingTaskLister Overriden Methods ##
    
    def onTranscodingFailed(self, task, transcoder):
        self._fireEvent(task, "TranscodingFail")
    
    def onTranscodingDone(self, task, transcoder):
        self._fireEvent(task, "TranscodingDone")

    def onTranscodingTerminated(self, task, succeed):
        self.log("Transcoding task '%s' %s", task.getLabel(), 
                 (succeed and "succeed") or "failed")
        ctx = task.getProfileContext()
        self._transcoding.removeTask(ctx.getIdentifier())
        
        
    ## EventSource Overriden Methods ##
    
    def _doSyncListener(self, listener):
        for ctx in self._queue.itervalues():
            self._fireEventTo(ctx, listener, "ProfileQueued")
        for task in self._transcoding.iterTasks():
            ctx = task.getProfileContext()
            self._fireEnvetTo(ctx, listener, "TranscodingStarted")

        
    ## Private Methods ##
    
    def __startup(self):
        available = self._transcoding.getAvailableSlots()
        self.debug("Starting/Resuming transcoding scheduler (%d slots)", available)
        self.__startupTasks(available)
    
    def __startupTasksIfPossible(self):
        available = self._transcoding.getAvailableSlots()
        if available > 0:
            self.__startupTasks(available)
    
    def __startupTasks(self, count):
        while count > 0:
            profCtx = self.__popNextProfile()
            if not profCtx: return
            self.log("Creating transcoding task for file '%s'", 
                     profCtx.getInputPath())
            identifier = profCtx.getIdentifier()
            task = TranscodingTask(self._transcoding, profCtx)
            self._transcoding.addTask(identifier, task)
            self._fireEvent(task, "TranscodingStarted")
            count -= 1

    def __isProfileQueued(self, profCtx):
        return profCtx.getIdentifier() in self._queue
            
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
