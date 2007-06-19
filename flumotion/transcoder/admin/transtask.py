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

from flumotion.common.planet import moods

from flumotion.transcoder import log
from flumotion.transcoder import utils
from flumotion.transcoder.log import LoggerProxy
from flumotion.transcoder.enums import TranscoderStatusEnum
from flumotion.transcoder.enums import JobStateEnum
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
    def onTranscoderSelected(self, task, transcoder):
        pass
    
    def onTranscoderReleased(self, task, transcoder):
        pass
    
    def onTranscodingFailed(self, task, transcoder):
        pass
    
    def onTranscodingDone(self, task, transcoder):
        pass
    
    def onTranscodingTerminated(self, task, succeed):
        pass

    
class TranscodingTaskListener(object):
    
    implements(ITranscodingTaskListener)

    def onTranscoderSelected(self, task, transcoder):
        pass
    
    def onTranscoderReleased(self, task, transcoder):
        pass
    
    def onTranscodingFailed(self, task, transcoder):
        pass
    
    def onTranscodingDone(self, task, transcoder):
        pass

    def onTranscodingTerminated(self, task, succeed):
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
        self._terminated = False
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
        return (not self._terminated) and self._started and (not self._paused)

    def getActiveComponent(self):
        return self._transcoder

    def waitActiveWorker(self, timeout=None):
        if self._transcoder:
            return defer.succeed(self._transcoder.getWorker())
        d = self.__waitPotentialTranscoder(timeout)
        d.addCallback(lambda t: t and t.getWorker())
        return d

    def addComponent(self, transcoder):
        assert isinstance(transcoder, TranscoderProxy)
        assert not (transcoder in self._transcoders)
        self.log("Transcoder '%s' added to task '%s'", 
                 transcoder.getName(), self.getLabel())
        self._transcoders[transcoder] = None
        transcoder.addListener(self)
        transcoder.syncListener(self)
        
    def removeComponent(self, transcoder):
        assert isinstance(transcoder, TranscoderProxy)
        assert transcoder in self._transcoders
        self.log("Transcoder '%s' removed from task '%s'", 
                 transcoder.getName(), self.getLabel())
        del self._transcoders[transcoder]
        transcoder.removeListener(self)
        if transcoder == self._transcoder:
            self.__relieveTranscoder()
    
    def start(self, paused=False):
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
            m.removeListener(self)
        self._terminated = True
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
        self._terminated = True

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
    
    def onComponentMoodChanged(self, transcoder, mood):
        if not self.isActive(): return
        self.log("Transcoding task '%s' transcoder '%s' goes %s", 
                 self.getLabel(), transcoder.getName(), mood.name)
        if transcoder.getName() == self._pendingName:
            return
        if transcoder == self._transcoder:
            if mood == moods.happy:
                return
            if (mood == moods.sad) and (transcoder.isRunning()):
                return
            self.warning("Task '%s' selected transcoder '%s' gone %s",
                         self.getLabel(), transcoder.getName(), mood.name)
            self.__relieveTranscoder()
            self.__delayedStartTranscoder()
            return
        if mood == moods.sleeping:
            self.__deleteTranscoder(transcoder)
            return
        # If no transcoder is selected, don't stop any happy monitor
        if (not self._transcoder) and (mood == moods.happy):
            return
        self.__stopTranscoder(transcoder)


    ## ITranscoderListener Overrided Methods ##

    def onTranscoderJobStateChanged(self, transcoder, jobState):
        if not self.isActive() or (transcoder != self._transcoder): return
        self.log("Transcoding task '%s' transcoder '%s' "
                 "job state change to %s", self.getLabel(), 
                 transcoder.getName(), jobState.name)
        if jobState == JobStateEnum.waiting_ack:
            if not transcoder.isAcknowledged():
                d = transcoder.acknowledge()
                d.addErrback(self.__ebAcknowledgeFailed, transcoder)
            return
        if jobState == JobStateEnum.terminated:
            # I know the UI State is retrieved
            status = transcoder.getStatus()
            if status == TranscoderStatusEnum.done:
                self.info("Transcoding task '%s' done", self.getLabel())
                self._fireEvent(transcoder, "TranscodingDone")
                self.__taskTerminated(True)
            elif status == TranscoderStatusEnum.failed:
                self.info("Transcoding task '%s' failed", self.getLabel())
                self._fireEvent(transcoder, "TranscodingFailed")
                self.__taskTerminated(False)
            else:
                self.waring("Unexpected transcoder status/state combination.")
                self.__relieveTranscoder()
                self.__delayedStartTranscoder()
                return
    

    ## Overrided 
        

    ## Private Methods ##
    
    def __startup(self):
        for m in self._transcoders:
            self.onComponentMoodChanged(m, m.getMood())
        self.__startTranscoder()            
    
    def __taskTerminated(self, succeed):
        self._terminated = True        
        self.__relieveTranscoder()
        # Stop all transcoders
        for t in self._transcoders:
            self.__stopTranscoder(t)
        self._fireEvent(succeed, "TranscodingTerminated")
    
    def __relieveTranscoder(self):
        if self._transcoder:
            self.log("Transcoder '%s' releved by transcoding task '%s'",
                     self._transcoder.getName(), self.getLabel())
            self._fireEvent(self._transcoder, "TranscoderReleased")
            self._transcoder = None
            
    def __electTranscoder(self, transcoder):
        assert transcoder != None
        if self._transcoder:
            self.__relieveTranscoder()
        self._transcoder = transcoder
        self.log("Transcoder '%s' elected by transcoding task '%s'",
                 self._transcoder.getName(), self.getLabel())
        self._fireEvent(self._transcoder, "TranscoderSelected")
        # Retrieve and synchronize UI state
        d = transcoder.retrieveUIState(adminconsts.TRANSCODER_UI_TIMEOUT)
        d.addCallbacks(self.__cbGotUIState,
                       self.__ebUIStateFailed,
                       errbackArgs=(transcoder,))
        # Stop all transcoders other than the selected one
        for t in self._transcoders:
            if t != self._transcoder:
                self.__stopTranscoder(t)

    def  __cbGotUIState(self, transcoder):
        if transcoder != self._transcoder: return
        transcoder.syncListener(self)
            
    def __ebUIStateFailed(self, failure, transcoder):
        if transcoder != self._transcoder: return
        self.warning("Failed to retrieve task '%s' "
                     "transcoder '%s' UI state: %s",
                     self.getLabel(), transcoder.getName(), 
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        self.__relieveTranscoder()
        self.__delayedStartTranscoder()

    def __waitPotentialTranscoder(self, timeout=None):
        
        def cbGotStatus(status, transcoder):
            return (transcoder, status, transcoder.getMood())
        
        def ebGetStatusError(failure, transcoder):
            self.warning("Failed to retrieve transcoder '%s' status: %s",
                         transcoder.getName(), log.getFailureMessage(failure))
            self.debug("%s", log.getFailureTraceback(failure))
            # Resolve the error
            return None
        
        defs = []        
        for transcoder in self._transcoders:
            d = transcoder.waitStatus(adminconsts.TRANSCODER_UI_TIMEOUT)
            args = (transcoder,)
            d.addCallbacks(cbGotStatus, ebGetStatusError,
                           callbackArgs=args, errbackArgs=args)
            defs.append(d)
        dl = defer.DeferredList(defs, fireOnOneCallback=False,
                                fireOnOneErrback=True,
                                consumeErrors=True)
        dl.addCallback(self.__cbSelectPotentialTranscoder)
        return dl
        
    def __cbSelectPotentialTranscoder(self, results): 
        selected = None
        for succeed, result in results:
            if not succeed:
                continue
            transcoder, status, mood = result
            # If a transcoder is happy, it's a valid option
            if mood == moods.happy:
                selected = transcoder
            elif mood == moods.sad:
                # If it's sad but its status is failed,
                # it's a failed transcoding
                if status == TranscoderStatusEnum.failed:
                    # But only select it if there is no other
                    if not selected:
                        selected = transcoder
        return selected
    
    def __delayedStartTranscoder(self):
        if self._delayed:
            return
        self.log("Scheduling transcoder start for task '%s'",
                 self.getLabel())
        self._delayed = reactor.callLater(adminconsts.TRANSCODER_START_DELAY,
                                          self.__startTranscoder)

    def __startTranscoder(self):
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
            self.warning("Couldn't start transcoder for task '%s', "
                         "no worker found", self.getLabel())
            return
        # Set the pendingName right now to prevent other
        # transoder to be started
        self._pendingName = utils.genUniqueIdentifier()
        self.log("Task '%s' Looking for a potential transcoder",
                 self.getLabel())
        # Check there is a valid transcoder already running
        to = adminconsts.TRANSCODER_POTENTIAL_WORKER_TIMEOUT
        d = self.__waitPotentialTranscoder(to)
        d.addCallbacks(self.__cbGotPotentialTranscoder, 
                       self.__ebPotentialTranscoderFailure)
        
    def __ebPotentialTranscoderFailure(self, failure):
        self.warning("Failure looking for a potential transcoder for task '%s': %s", 
                     self.getLabel(), log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        self.__loadTranscoder()
        
        
    def __cbGotPotentialTranscoder(self, transcoder):
        if transcoder:
            self.log("Task '%s' Found a the potential transcoder '%s'",
                 self.getLabel(), transcoder.getName())
            self._pendingName = None
            self.__electTranscoder(transcoder)
            return
        self.__loadTranscoder()
        
    def __loadTranscoder(self):
        transcoderName = self._pendingName
        workerName = self._worker.getName()
        self.debug("Starting task '%s' transcoder '%s' on  worker '%s'",
                   self.getLabel(), transcoderName, workerName)
        d = TranscoderProxy.loadTo(self._worker, transcoderName, 
                                   self._label, self._properties,
                                   adminconsts.TRANSCODER_LOAD_TIMEOUT)
        args = (transcoderName, workerName)
        d.addCallbacks(self.__cbTranscoderStartSucceed,
                       self.__ebTranscoderStartFailed,
                       callbackArgs=args, errbackArgs=args)

    def __stopTranscoder(self, transcoder):
        self.debug("Stopping task '%s' transcoder '%s'", 
                   self.getLabel(), transcoder.getName())
        # Don't stop sad transcoders
        if transcoder.getMood() != moods.sad:
            d = transcoder.forceStop()
            d.addErrback(self.__ebTranscoderStopFailed, transcoder.getName())

    def __deleteTranscoder(self, transcoder):
        self.debug("Deleting task '%s' transcoder '%s'", 
                   self.getLabel(), transcoder.getName())
        d = transcoder.forceDelete()
        d.addErrback(self.__ebTranscoderDeleteFailed, transcoder.getName())
    
    def __cbTranscoderStartSucceed(self, result, transcoderName, workerName):
        self.debug("Succeed to start task '%s' transcoder '%s' on worker '%s'",
                   self.getLabel(), transcoderName, workerName)
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
        self.warning("Failed to start task '%s' transcoder '%s' "
                     "on worker '%s': %s", self.getLabel(), transcoderName, 
                     workerName, log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        self._pendingName = None
        self.__delayedStartTranscoder()
        
    def __cbTranscoderGoesHappy(self, mood, transcoder, workerName):
        self.debug("Task '%s' transcoder '%s' on worker '%s' goes happy", 
                   self.getLabel(), transcoder.getName(), workerName)
        self._pendingName = None
        if self._worker and (workerName == self._worker.getName()):
            self.__electTranscoder(transcoder)
        else:
            # If the wanted worker changed, just start a new transcoder
            self.__startTranscoder()
                
    def __ebTranscoderNotHappy(self, failure, transcoder, workerName):
        self.warning("Task '%s' transcoder '%s' on worker '%s' "
                     "fail to become happy: %s",
                     self.getLabel(), transcoder.getName(), workerName,
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
        self.warning("Failed to stop task '%s' transcoder '%s': %s", 
                     self.getLabel(), name, log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        
    def __ebTranscoderDeleteFailed(self, failure, transcoder):
        self.warning("Failed to delete task '%s' transcoder '%s': %s", 
                     self.getLabel(), transcoder.getName(),
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))

    def __ebAcknowledgeFailed(self, failure, transcoder):
        if self._transcoder != transcoder: return
        self.warning("Failed to acknowledge task '%s' transcoder '%s': %s", 
                     self.getLabel(), transcoder.getLabel(), 
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
        self.__relieveTranscoder()
        self.__delayedStartTranscoder()
    