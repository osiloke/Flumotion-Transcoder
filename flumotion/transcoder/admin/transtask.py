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
from flumotion.transcoder.enums import TranscoderStatusEnum
from flumotion.transcoder.enums import JobStateEnum
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.admintask import AdminTask
from flumotion.transcoder.admin.transprops import TranscoderProperties
from flumotion.transcoder.admin.proxies.transcoderproxy import TranscoderProxy
from flumotion.transcoder.admin.proxies.transcoderproxy import TranscoderListener

#TODO: Schedule the component startup to prevent starting
#      lots of component at the same time.
#      Because when starting lots of components, the transcoders
#      happy timeout may be triggered. For now, just using a large timeout.
#TODO: Cancel operations when going sad or lost, do not wait 
#      for the timeout to be triggered

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


class TranscodingTask(AdminTask, TranscoderListener):
    
    MAX_RETRIES = adminconsts.TRANSCODER_MAX_RETRIES
    
    def __init__(self, logger, profileCtx):
        AdminTask.__init__(self, logger, profileCtx.getTranscoderLabel(),
                           TranscoderProperties.createFromContext(profileCtx),
                           ITranscodingTaskListener)
        self._profileCtx = profileCtx
        self._acknowledging = False
        self._sadTimeout = None
        
    ## Public Methods ##
    
    def getProfileContext(self):
        return self._profileCtx

    def isAcknowledging(self):
        return self._acknowledging

    def isAcknowledged(self):
        transcoder = self.getActiveComponent()
        return (transcoder != None) and transcoder.isAcknowledged()


    ## IComponentListener Overrided Methods ##
    
    def onComponentOrphaned(self, transcoder, worker):
        if not self.isStarted(): return
        if not self._isElectedComponent(transcoder): return
        # The component segfaulted or has been killed
        self.log("Transcoding task '%s' selected transcoder '%s' "
                 "goes orphaned of worker '%s'", self.getLabel(),
                 transcoder.getName(), worker.getName())
        # The transcoder has been killed or has segfaulted.
        # We abort only if the transcoder is already sad,
        # because if it was not sad yet, it would be stopped and deleted.
        # And we want it to be keeped for later investigations
        if transcoder.getMood() == moods.sad:
            self._abort()
            return
    
    def onComponentMoodChanged(self, transcoder, mood):
        if not self.isStarted(): return
        self.log("Transcoding task '%s' transcoder '%s' goes %s", 
                 self.getLabel(), transcoder.getName(), mood.name)
        if self._isPendingComponent(transcoder):
            # Currently beeing started up
            return
        if self._isElectedComponent(transcoder):
            if (mood != moods.lost):
                self._cancelComponentHold()
            if (mood != moods.sad):
                utils.cancelTimeout(self._sadTimeout)
            if mood == moods.happy:
                return
            if mood == moods.sad:
                if not transcoder.isRunning():
                    # The transcoder has been killed or segfaulted
                    self._abort()
                    return
                # The transcoder can be a zombie or waiting for acknowledge.
                # Timeout to prevent the task to stall.
                timeout = adminconsts.TRANSCODER_SAD_TIMEOUT
                to = utils.createTimeout(timeout, self.__asyncSadTimeout, 
                                         transcoder)
                self._sadTimeout = to
                return
            self.warning("Transcoding task '%s' selected transcoder '%s' "
                         "gone %s", self.getLabel(), 
                         transcoder.getName(), mood.name)
            if mood == moods.lost:
                # If the transcoder goes lost, wait a fixed amount of time
                # to cope with small transient failures.
                self._holdLostComponent(transcoder)
                return
            self._abort()
            return
        if mood == moods.sleeping:
            self._deleteComponent(transcoder)
            return
        # If no transcoder is selected, don't stop any happy monitor
        if (not self._hasElectedComponent()) and (mood == moods.happy):
            return
        self._stopComponent(transcoder)


    ## ITranscoderListener Overrided Methods ##

    def onTranscoderStatusChanged(self, transcoder, status):
        if not self.isStarted(): return
        if not self._isElectedComponent(transcoder): return
        self.log("Transcoding task '%s' transcoder '%s' "
                 "status change to %s", self.getLabel(), 
                 transcoder.getName(), status.name)
        if status in [TranscoderStatusEnum.unexpected_error,
                      TranscoderStatusEnum.error]:
            self.__cbJobTerminated(status, transcoder)

    def onTranscoderJobStateChanged(self, transcoder, jobState):
        if not self.isStarted(): return
        if not self._isElectedComponent(transcoder): return
        self.log("Transcoding task '%s' transcoder '%s' "
                 "job state change to %s", self.getLabel(), 
                 transcoder.getName(), jobState.name)
        if jobState == JobStateEnum.waiting_ack:
            if not transcoder.isAcknowledged():
                self._acknowledging = True
                d = transcoder.acknowledge(adminconsts.TRANSCODER_ACK_TIMEOUT)
                args = (transcoder,)
                d.addCallbacks(self.__cbJobTerminated,
                               self.__ebAcknowledgeFailed,
                               callbackArgs=args, errbackArgs=args)
            return
        if jobState == JobStateEnum.terminated:
            if not self._acknowledging:
                status = transcoder.getStatus()
                self.__cbJobTerminated(status, transcoder)
    

    ## Virtual Methods Implementation ##
    
    def _onComponentAdded(self, component):
        component.addListener(self)
        component.syncListener(self)

    def _onComponentRemoved(self, component):
        component.removeListener(self)

    def _onComponentElected(self, component):
        self._fireEvent(component, "TranscoderSelected")
        component.syncListener(self)

    def _onComponentRelieved(self, component):
        utils.cancelTimeout(self._sadTimeout)
        self._fireEvent(component, "TranscoderReleased")

    def _onComponentStartupCanceled(self, component):
        # Because the monitor was pending to start, 
        # this event was ignored
        # So resend the mood changing event
        mood = component.getMood()
        self.onComponentMoodChanged(component, mood)

    def _onStarted(self):
        for c in self.iterComponents():
            self.onComponentMoodChanged(c, c.getMood())
    
    def _doAcceptSuggestedWorker(self, worker):
        current = self.getWorker()
        transcoder = self.getActiveComponent()
        # Change task's worker for None or if there is no active transcoder
        return (worker != current) and (not current or not transcoder)
    
    def _doTerminated(self, result):
        self._fireEvent(result, "TranscodingTerminated")
    
    def _doAborted(self):
        # We tried but there nothing to do...
        self.__transcodingFailed()
    
    def _doSelectPotentialComponent(self, components):
        selected = None
        for transcoder in components:
            # We know the component UI State has been retrieved
            status = transcoder.getStatus()
            acknowledged = transcoder.isAcknowledged()
            mood = transcoder.getMood()
            # If a transcoder is happy, it's a valid option
            if mood == moods.happy:
                selected = transcoder
            elif mood == moods.sad:
                # If it's sad but its status is failed,
                # it's a failed transcoding
                if status == TranscoderStatusEnum.failed:
                    # But only select it if there is no other already 
                    # selected, and it was not already acknowledged
                    if not (selected or acknowledged):
                        selected = transcoder
        return selected

    
    def _doLoadComponent(self, worker, componentName, componentLabel,
                         componentProperties, loadTimeout):
        return TranscoderProxy.loadTo(worker, componentName, 
                                      componentLabel, componentProperties,
                                      loadTimeout)
        

    ## Private Methods ##
    
    def __transcodingFailed(self, transcoder=None):
        transcoder = transcoder or self.getActiveComponent()
        self.info("Transcoding task '%s' failed", self.getLabel())
        self._fireEvent(self.getActiveComponent(), "TranscodingFailed")
        self._terminate(False)
    
    def __transcodingSucceed(self, transcoder=None):
        transcoder = transcoder or self.getActiveComponent()
        self.info("Transcoding task '%s' done", self.getLabel())
        self._fireEvent(transcoder, "TranscodingDone")
        self._terminate(True)
    
    def __cbJobTerminated(self, status, transcoder):
        if status == TranscoderStatusEnum.done:
            self.__transcodingSucceed(transcoder)
        elif status == TranscoderStatusEnum.failed:
            self.__transcodingFailed(transcoder)
        elif status == TranscoderStatusEnum.unexpected_error:
            # If the transcoder component got an unexpected error
            # abort and eventualy retry
            self.warning("Transcoding task '%s' transcoder '%s' "
                         "got an unexpected error", 
                         self.getLabel(), transcoder.getName())
            self._abort()
        elif status == TranscoderStatusEnum.error:
            # If the transcoder component got a known error (transcoder related)
            # it's assumed the error will raise again if we retry.
            # So we do not retry and treat as a failed transcoding.
            self.warning("Transcoding task '%s' transcoder '%s' "
                         "goes to error status", self.getLabel(), 
                         transcoder.getName())
            self.__transcodingFailed(transcoder)
        elif status == TranscoderStatusEnum.aborted:
            self.info("Transcoding task '%s' aborted", self.getLabel())
            # Handled by the __cbCheckForAbortedTranscoder set in 
            # onComponentMoodChanged
            # Not done here because components could abort before
            # beeing able to send UI State events.
            # It's assumed that the components go sad after aborting.
        else:
            self.warning("Unexpected transcoder status/state combination.")
            self._abort()
    
    def __ebAcknowledgeFailed(self, failure, transcoder):
        if not self._isElectedComponent(transcoder): return
        self.warning("Failed to acknowledge task '%s' transcoder '%s': %s", 
                     self.getLabel(), transcoder.getName(), 
                     log.getFailureMessage(failure))
        self.debug("Acknowledge failure traceback:\n%s", 
                   log.getFailureTraceback(failure))
        # If the acknowledge fail, the state is unpredictable,
        # so there is no sense to abort and retry.
        self.__transcodingFailed(transcoder)
        
    def __asyncSadTimeout(self, transcoder):
        if not self._isElectedComponent(transcoder): return
        if self._acknowledging: return
        if transcoder.getMood() == moods.sad:
            self.warning("Transcoding task '%s' transcoder '%s' stall in sad mood", 
                         self.getLabel(), transcoder.getName())
            self._abort()
