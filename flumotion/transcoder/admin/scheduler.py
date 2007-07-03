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
from flumotion.transcoder.admin.monitoring import MonitoringListener
from flumotion.transcoder.admin.transcoding import TranscodingListener
from flumotion.transcoder.admin.transtask import TranscodingTask
from flumotion.transcoder.admin.transtask import TranscodingTaskListener
from flumotion.transcoder.admin.montask import MonitoringTask
from flumotion.transcoder.admin.montask import MonitoringTaskListener

from flumotion.transcoder.admin.montask import IMonitoringTaskListener
from flumotion.transcoder.admin.monitoring import IMonitoringListener
from flumotion.transcoder.admin.transcoding import ITranscodingListener
from flumotion.transcoder.admin.transtask import ITranscodingTaskListener

#TODO: Implement a faire scheduler and prevent the possibility
#      of the profile priority making the overhaul customer priority
#      higher than other customer priorities.



class ISchedulerListener(Interface):
    pass

    
class SchedulerListener(object):
    
    implements(ISchedulerListener)


class Scheduler(log.Loggable, 
                EventSource, 
                MonitoringListener, 
                MonitoringTaskListener, 
                TranscodingListener, 
                TranscodingTaskListener):
    
    logCategory = adminconsts.SCHEDULER_LOG_CATEGORY
    
    def __init__(self, store, monitoring, transcoding):
        EventSource.__init__(self, ISchedulerListener)
        MonitoringTaskListener.__init__(self)
        self._store = store
        self._monitoring = monitoring
        self._transcoding = transcoding
        self._order = [] # [identifier]
        self._queue = {} # {identifier: ProfileContext}
        self._started = False
        self._paused = False
        
        
    ## Public Methods ##
        
    def initialize(self):
        #self._store.addListener(self)
        self._monitoring.addListener(self)
        self._transcoding.addListener(self)
        self._transcoding.syncListener(self)
        self._monitoring.syncListener(self)
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
        
    
    ## IMonitoringLister Overriden Methods ##
    
    def onMonitoringTaskAdded(self, takser, task):
        self.debug("Monitoring task '%s' added", task.getLabel())
        task.addListener(self)
        task.syncListener(self)
    
    def onMonitoringTaskRemoved(self, tasker, task):
        self.debug("Monitoring task '%s' removed", task.getLabel())
        task.removeListener(self)


    ## IMonitoringTaskLister Overriden Methods ##
    
    def onMonitoredFileAdded(self, task, profileContext):
        inputPath = profileContext.getInputPath()
        identifier = profileContext.getIdentifier()
        if self.__isProfileQueued(profileContext):
            self.debug("Already queued file '%s' added by "
                       "monitoring task '%s'", inputPath, task.getLabel())
        elif self._transcoding.getTask(identifier):
            self.debug("Already transcoding file '%s' added by "
                       "monitoring task '%s'", inputPath, task.getLabel())
        else:
            self.debug("Queued file '%s' added by monitoring task '%s'", 
                       inputPath, task.getLabel())
            self.__queueProfile(profileContext)
            self.__startupTasksIfPossible()
    
    def onMonitoredFileRemoved(self, montask, profileContext):
        inputPath = profileContext.getInputPath()
        identifier = profileContext.getIdentifier()
        if self.__isProfileQueued(profileContext):
            self.debug("Unqueue file '%s' removed by "
                       "monitoring task '%s'", inputPath, montask.getLabel())
            self.__unqueuProfile(profileContext)
        trantask = self._transcoding.getTask(identifier, None)
        if trantask and not trantask.isAcknowledging():
            self.debug("Cancel transcoding of file '%s' removed by "
                       "monitoring task '%s'", inputPath, 
                       montask.getLabel())
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
    
    def onTranscoderSelected(self, task, transcoder):
        pass
    
    def onTranscoderReleased(self, task, transcoder):
        pass
    
    def onTranscodingFailed(self, task, transcoder):
        pass
    
    def onTranscodingDone(self, task, transcoder):
        pass

    def onTranscodingTerminated(self, task, succeed):
        self.log("Transcoding task '%s' %s", task.getLabel(), 
                 (succeed and "succeed") or "failed")
        ctx = task.getProfileContext()
        self._transcoding.removeTask(ctx.getIdentifier())
        
        
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
