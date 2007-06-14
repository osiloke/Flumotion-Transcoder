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

from flumotion.common.log import Loggable
from flumotion.common.planet import moods

from flumotion.transcoder import log
from flumotion.transcoder import utils
from flumotion.transcoder.log import LoggerProxy
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.eventsource import EventSource
from flumotion.transcoder.admin.admintask import IAdminTask
from flumotion.transcoder.admin.transprops import TranscoderProperties
from flumotion.transcoder.admin.proxies.transcoderproxy import TranscoderProxy
from flumotion.transcoder.admin.proxies.transcoderproxy import TranscoderListener

#TODO: Schedule the component startup to prevent to starts 
#      lots of component at the same time.
#      Because when starting lots of components, the transcoders
#      happy timeout may be triggered. For now, just using a large timeout.

class ITranscodingTaskListener(Interface):
    def onTranscoderStart(self, task, transcoder):
        pass
    
    def onTranscoderLost(self, task, transcoder):
        pass
    
    def onTranscodingFailed(self, task, transcoder):
        pass
    
    def onTranscodingSucceed(self, task, transcoder):
        pass

    
class TranscodingTaskListener(object):
    
    implements(ITranscodingTaskListener)

    def onTranscoderStart(self, task, transcoder):
        pass
    
    def onTranscoderLost(self, task, transcoder):
        pass
    
    def onTranscodingFailed(self, task, transcoder):
        pass
    
    def onTranscodingSucceed(self, task, transcoder):
        pass


class TranscodingTask(LoggerProxy, EventSource, TranscoderListener):
    
    implements(IAdminTask)
    
    def __init__(self, logger, profileCtx):
        LoggerProxy.__init__(self, logger)
        EventSource.__init__(self, ITranscodingTaskListener)
        self._profileCtx = profileCtx
        self._worker = None # WorkerProxy
        self._started = False
        self._paused = False
        self._pendingName = None
        self._active = True
        self._delayed = None # IDelayedCall
        self._transcoder = None # Active TranscoderProxy
        self._transcoders = {} # {TranscoderProxy: None}
        self._label = profileCtx.getTranscoderLabel()
        self._properties = TranscoderProperties.createFromContext(profileCtx)
        

    ## IAdminTask IMplementation ##
        
    def getLabel(self):
        return self._label
    
    def getProperties(self):
        return self._properties

    def isActive(self):
        return self._started and (not self._paused)

    def getActiveComponent(self):
        return self._transcoder

    def getActiveWorker(self):
        if self._transcoder:
            return self._transcoder.getWorker()
        for m in self._transcoders:
            if m.getMood() == moods.happy:
                return m.getWorker()
        return None

    def addComponent(self, transcoder):
        assert isinstance(transcoder, TranscoderProxy)
        assert not (transcoder in self._transcoders)
        self.log("Transcoder '%s' added to task %s", 
                 transcoder.getLabel(), self.getLabel())
        self._transcoders[transcoder] = None
        transcoder.addListener(self)
        transcoder.syncListener(self)
        
    def removeComponent(self, transcoder):
        assert isinstance(transcoder, TranscoderProxy)
        assert transcoder in self._transcoders
        self.log("Transcoder '%s' removed from task %s", 
                 transcoder.getLabel(), self.getLabel())
        del self._transcoders[transcoder]
        transcoder.removeListener(self)
        if transcoder == self._transcoder:
            self.__relieveTranscoder()
    
    def start(self, paused=False):
        print "%"*40
        if self._started: return
        self.log("Starting transcoding task '%s'", self.getLabel())
        self._started = True
        if paused:
            self.pause()
        else:
            self._paused = False
            self.__startup()
    
    def pause(self):
        if self._started and (not self._paused):
            self.log("Pausing transcoding task '%s'", self.getLabel())
            self._paused = True
    
    def resume(self):
        if self._started and self._paused:
            self.log("Resuming transcoding task '%s'", self.getLabel())
            self._paused = False
            self.__startup()
                    
    
    def stop(self):
        """
        Relieve the selected transcoder, and return
        all the transcoders for the caller to choose what
        to do with them.
        After this, no transcoder will/should be added or removed.
        """
        self.log("Stopping transcoding task '%s'", self.getLabel())
        self.__relieveTranscoder()
        for m in self._transcoders:
            m.removeListener()
        self._active = False
        return self._transcoders.keys()
    
    def abort(self):
        """
        After this, no transcoder will/should be added or removed.
        """
        self.log("Aborting transcoding task '%s'", self.getLabel())
        self.__relieveTranscoder()
        for m in self._transcoders:
            m.removeListener(self)
        self._transcoders.clear()
        self._active = False

    def suggestWorker(self, worker):
        self.log("Worker '%s' suggested to transcoding task '%s'", 
                 worker and worker.getLabel(), self.getLabel())
        # Change task's worker for None or if there is no active transcoder
        if ((worker != self._worker) 
            and (not self._worker or not self._transcoder)):
            self._worker = worker
            self.__startTranscoder()
        return self._worker


    ## IComponentListener Overrided Methods ##
    
    def onComponentMoodChanged(self, component, mood):
        if not self.isActive(): return
        self.log("Transcoding task '%s' transcoder '%s' goes %s", 
                 self.getLabel(), component.getLabel(), mood.name)
        if component.getName() == self._pendingName:
            return
        if component == self._transcoder:
            if mood == moods.happy:
                return
            self.warning("Selected transcoder for '%s' gone %s", 
                         self._label, mood.name)
            self.__relieveTranscoder()
            self.__delayedStartTranscoder()
            return
        if mood == moods.sleeping:
            d = component.forceDelete()
            d.addErrback(self.__ebTranscoderDeleteFailed, component)
            return
        # Don't stop/delete sad component
        if mood == moods.sad:
            return
        # If no transcoder is selected, don't stop any happy transcoder
        if (not self._transcoder) and (mood == moods.happy):
            return
        d = component.forceStop()
        d.addErrback(self.__ebTranscoderStopFailed, component)


    ## ITranscoderListener Overrided Methods ##
    

    ## Overrided 
        

    ## Private Methods ##
    
    def __startup(self):
        for m in self._transcoders:
            self.onComponentMoodChanged(m, m.getMood())
        self.__startTranscoder()            
    
    def __relieveTranscoder(self):
        if self._transcoder:
            self.log("Transcoder %s releved by transcoding task %s",
                     self._transcoder.getName(), self.getLabel())
            self._fireEvent(self._transcoder, "TranscoderLost")
            self._transcoder = None
            
    def __electTranscoder(self, transcoder):
        assert transcoder != None
        if self._transcoder:
            self.__relieveTranscoder()
        self._transcoder = transcoder
        self.log("Transcoder %s elected by transcoding task %s",
                 self._transcoder.getName(), self.getLabel())
        self._fireEvent(self._transcoder, "TranscoderStart")
        # Stop all transcoder other than the selected one
        for m in self._transcoders:
            if m != self._transcoder:
                self.__stopTranscoder(m)

    def __delayedStartTranscoder(self):
        if self._delayed:
            return
        self.log("Scheduling transcoder start for task '%s'",
                 self.getLabel())
        self._delayed = reactor.callLater(adminconsts.TRANSCODER_START_DELAY,
                                          self.__startTranscoder)

    def __startTranscoder(self):
        print "#"*40, "__startTranscoder", self.isActive()
        if not self.isActive(): return
        if self._delayed:
            if self._delayed.active():
                self._delayed.cancel()
            self._delayed = None
        if self._pendingName:
            self.log("Canceling transcoder startup for task '%s', "
                     "transcoder '%s' is pending", self.getLabel(),
                     self._pendingName)
            return
        if not self._worker:
            self.warning("Couldn't start transcoder for '%s', no worker found",
                         self._label)
            return
        # Check there is a valid transcoder already running
        for m in self._transcoders:
            # If it exists an happy transcoder on the 
            # wanted worker, just elect it
            if ((m.getWorker() == self._worker) 
                and (m.getMood() == moods.happy)):
                self.__electTranscoder(m)
                return
        print "#"*40, "__startTranscoder", "Ok"
        transcoderName = utils.genUniqueIdentifier()
        workerName = self._worker.getName()
        self.debug("Starting %s transcoder %s on %s",
                   self._label, transcoderName, workerName)
        self._pendingName = transcoderName
        d = TranscoderProxy.loadTo(self._worker, transcoderName, 
                                   self._label, self._properties,
                                   adminconsts.TRANSCODER_LOAD_TIMEOUT)
        args = (transcoderName, workerName)
        d.addCallbacks(self.__cbTranscoderStartSucceed,
                       self.__ebTranscoderStartFailed,
                       callbackArgs=args, errbackArgs=args)

    def __stopTranscoder(self, transcoder):
        self.debug("Stopping %s transcoder %s", self._label, transcoder.getName())
        # Don't stop sad transcoders
        if transcoder.getMood() != moods.sad:
            d = transcoder.forceStop()
            d.addErrback(self.__ebTranscoderStopFailed, transcoder.getName())

    def __deleteTranscoder(self, transcoder):
        self.debug("Deleting %s transcoder %s", self._label, transcoder.getName())
        d = transcoder.forceDelete()
        d.addErrback(self.__ebTranscoderDeleteFailed, transcoder.getName())
    
    def __cbTranscoderStartSucceed(self, result, transcoderName, workerName):
        self.debug("Succeed to load %s transcoder '%s' on worker '%s'", 
                   self._label, transcoderName, workerName)
        assert transcoderName == result.getName()
        assert transcoderName == self._pendingName
        # If the target worker changed, abort and start another transcoder
        if ((not self._worker) 
            or (self._worker and (workerName != self._worker.getName()))):
            self._pendingName = None
            self.__stopTranscoder(result)
            self.__delayedStartTranscoder()
            return
        # If not, wait for the transcoder to go happy
        d = result.waitHappy(adminconsts.TRANSCODER_HAPPY_TIMEOUT)
        args = (result, workerName)
        d.addCallbacks(self.__cbTranscoderGoesHappy, 
                       self.__ebTranscoderNotHappy,
                       callbackArgs=args, errbackArgs=args)
        
    def __ebTranscoderStartFailed(self, failure, transcoderName, workerName):
        self.warning("Failed to start %s transcoder '%s' on worker '%s': %s", 
                     self._label, transcoderName, workerName, 
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        self._pendingName = None
        self.__delayedStartTranscoder()
        
    def __cbTranscoderGoesHappy(self, mood, transcoder, workerName):
        self.debug("%s transcoder '%s' on worker '%s' goes Happy", 
                   self._label, transcoder.getName(), workerName)
        self._pendingName = None
        if workerName == self._worker:
            self.__electTranscoder(transcoder)
        else:
            # If the wanted worker changed, just start a new transcoder
            self.__startTranscoder()
                
    def __ebTranscoderNotHappy(self, failure, transcoder, workerName):
        self.warning("%s transcoder '%s' on worker '%s' fail to be happy: %s", 
                     self._label, transcoder.getName(), workerName,
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        self._pendingName = None
        mood = transcoder.getMood()
        # Because the transcoder was pending to start, its event were ignored
        # So resend the mood changing event
        self.onComponentMoodChanged(transcoder, mood)
        # And schedule starting a new one
        self.__delayedStartTranscoder()
        
    def __ebTranscoderStopFailed(self, failure, name):
        self.warning("Failed to stop %s transcoder %s: %s", 
                     self._label, name, log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        
    def __ebTranscoderDeleteFailed(self, failure, transcoder):
        self.warning("Failed to delete transcoder '%s': %s", 
                     transcoder.getLabel(), log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
