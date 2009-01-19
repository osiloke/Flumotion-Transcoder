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
from twisted.spread.pb import PBConnectionLost

from flumotion.common.planet import moods

from flumotion.inhouse import log, defer, utils

from flumotion.transcoder.enums import TranscoderStatusEnum
from flumotion.transcoder.enums import JobStateEnum
from flumotion.transcoder.admin import adminconsts, admintask
from flumotion.transcoder.admin.property import filetrans
from flumotion.transcoder.admin.proxy import transcoder

#TODO: Schedule the component startup to prevent starting
#      lots of component at the same time.
#      Because when starting lots of components, the transcoders
#      happy timeout may be triggered. For now, just using a large timeout.
#TODO: Cancel operations when going sad or lost, do not wait 
#      for the timeout to be triggered


class TranscodingTask(admintask.AdminTask):
    
    MAX_RETRIES = adminconsts.TRANSCODER_MAX_RETRIES
    
    def __init__(self, logger, profCtx):
        admintask.AdminTask.__init__(self, logger, profCtx.transcoderLabel,
                           filetrans.TranscoderProperties.createFromContext(profCtx))
        self._profCtx = profCtx
        self._acknowledging = False
        self._sadTimeout = None
        # Registering events
        self._register("component-selected")
        self._register("component-released")
        self._register("failed")
        self._register("done")
        self._register("terminated")
        self._attempts = 0
        
    ## Public Methods ##
    
    def getProfileContext(self):
        return self._profCtx

    def isAcknowledging(self):
        return self._acknowledging

    def isAcknowledged(self):
        transPxy= self.getActiveComponent()
        return (transPxy != None) and transPxy.isAcknowledged()

    # Number of times a transcoding task actually gets exectuted. Different
    # from getRetryCount which returns the number of time a task is aborted.
    def getAttemptCount(self):
        return self._attempts

    ## Component Event Listeners ##
    
    def __onComponentOrphaned(self, transPxy, workerPxy):
        if not self.isStarted(): return
        if not self._isElectedComponent(transPxy): return
        # The component segfaulted or has been killed
        self.log("Transcoding task '%s' selected transcoder '%s' "
                 "goes orphaned of worker '%s'", self.label,
                 transPxy.getName(), workerPxy.getName())
        # The transcoder has been killed or has segfaulted.
        # We abort only if the transcoder is already sad,
        # because if it was not sad yet, it would be stopped and deleted.
        # And we want it to be keeped for later investigations
        if transPxy.getMood() == moods.sad:
            self._processInterruptionDetected()
            self._abort()
            return
    
    def __onComponentMoodChanged(self, transPxy, mood):
        if not self.isStarted(): return
        self.log("Transcoding task '%s' transcoder '%s' goes %s", 
                 self.label, transPxy.getName(), mood.name)
        if self._isPendingComponent(transPxy):
            # Currently beeing started up
            return
        if self._isElectedComponent(transPxy):
            if (mood != moods.sad):
                utils.cancelTimeout(self._sadTimeout)
            if mood == moods.happy:
                if self._isHoldingLostComponent():
                    self._restoreLostComponent(transPxy)
                return
            if mood == moods.sad:
                if not transPxy.isRunning():
                    # The transcoder has been killed or segfaulted
                    self._processInterruptionDetected()
                    self._abort()
                    return
                # The transcoder can be a zombie or waiting for acknowledge.
                # Timeout to prevent the task to stall.
                timeout = adminconsts.TRANSCODER_SAD_TIMEOUT
                to = utils.createTimeout(timeout, self.__asyncSadTimeout, 
                                         transPxy)
                self._sadTimeout = to
                return
            self.warning("Transcoding task '%s' selected transcoder '%s' "
                         "gone %s", self.label, transPxy.getName(), mood.name)
            if mood == moods.lost:
                # If the transcoder goes lost, wait a fixed amount of time
                # to cope with small transient failures.
                self._holdLostComponent(transPxy)
                return
            self._abort()
        if mood == moods.waking:
            # Keep the waking components 
            return
        if mood == moods.sleeping:
            self._deleteComponent(transPxy)
            return
        # If no transcoder is selected, don't stop any happy monitor
        if (not self._hasElectedComponent()) and (mood == moods.happy):
            return
        self._stopComponent(transPxy)


    ## Transcoder Event Listeners ##

    def __onTranscoderStatusChanged(self, transPxy, status):
        if not self.isStarted(): return
        if not self._isElectedComponent(transPxy): return
        self.log("Transcoding task '%s' transcoder '%s' "
                 "status change to %s", self.label, 
                 transPxy.getName(), status.name)
        if status in [TranscoderStatusEnum.unexpected_error,
                      TranscoderStatusEnum.error]:
            self.__cbJobTerminated(status, transPxy)

    def __onTranscoderJobStateChanged(self, transPxy, jobState):
        if not self.isStarted(): return
        if not self._isElectedComponent(transPxy): return
        self.log("Transcoding task '%s' transcoder '%s' "
                 "job state change to %s", self.label, 
                 transPxy.getName(), jobState.name)
        if jobState == JobStateEnum.waiting_ack:
            if not (transPxy.isAcknowledged() or self._acknowledging):
                self._acknowledging = True
                self.log("Acknowledging transcoding task '%s' transcoder '%s'",
                         self.label, transPxy.getName())
                d = transPxy.acknowledge(adminconsts.TRANSCODER_ACK_TIMEOUT)
                d.addCallback(defer.bridgeResult, self.log,
                              "Transcoding task '%s' transcoder '%s' Acknowledged",
                              self.label, transPxy.getName())
                args = (transPxy,)
                d.addCallbacks(self.__cbJobTerminated,
                               self.__ebAcknowledgeFailed,
                               callbackArgs=args, errbackArgs=args)
            return
        if jobState == JobStateEnum.terminated:
            if not self._acknowledging:
                status = transPxy.getStatus()
                self.__cbJobTerminated(status, transPxy)
    

    ## Virtual Methods Implementation ##
    
    def _onComponentAdded(self, compPxy):
        compPxy.connectListener("orphaned", self,
                                self.__onComponentOrphaned)
        compPxy.connectListener("mood-changed", self,
                                self.__onComponentMoodChanged)
        compPxy.connectListener("status-changed", self,
                                self.__onTranscoderStatusChanged)
        compPxy.connectListener("job-state-changed", self,
                                self.__onTranscoderJobStateChanged)
        compPxy.refreshListener(self)

    def _onComponentRemoved(self, compPxy):
        compPxy.disconnectListener("orphaned", self)
        compPxy.disconnectListener("mood-changed", self)
        compPxy.disconnectListener("status-changed", self)
        compPxy.disconnectListener("job-state-changed", self)

    def _onComponentElected(self, compPxy):
        self.emit("component-selected", compPxy)
        compPxy.refreshListener(self)

    def _onComponentRelieved(self, compPxy):
        # If elected component is relieved we cannot be acknowledging anymore
        self._acknowledging = False
        utils.cancelTimeout(self._sadTimeout)
        self.emit("component-released", compPxy)

    def _onComponentStartupCanceled(self, compPxy):
        # Because the monitor was pending to start, 
        # this event was ignored
        # So resend the mood changing event
        mood = compPxy.getMood()
        self.__onComponentMoodChanged(compPxy, mood)

    def _onStarted(self):
        for compPxy in self.iterComponentProxies():
            self.__onComponentMoodChanged(compPxy, compPxy.getMood())
    
    def _doAcceptSuggestedWorker(self, workerPxy):
        currWorkerPxy = self.getWorkerProxy()
        transPxy = self.getActiveComponent()
        # Change task's worker for None or if there is no active transcoder
        return (workerPxy != currWorkerPxy) and (not currWorkerPxy or not transPxy)
    
    def _doTerminated(self, result):
        self.emit("terminated", result)
    
    def _doAborted(self):
        # We tried but there nothing to do...
        lastCompPxy = self.getActiveComponent()
        self.__transcodingFailed(lastCompPxy)
    
    def _doSelectPotentialComponent(self, compPxys):
        selected = None
        for transPxy in compPxys:
            # We know the component UI State has been retrieved
            status = transPxy.getStatus()
            acknowledged = transPxy.isAcknowledged()
            mood = transPxy.getMood()
            # If a transcoder is happy, it's a valid option
            if mood == moods.happy:
                selected = transPxy
            elif mood == moods.sad:
                # If it's sad but its status is failed,
                # it's a failed transcoding
                if status == TranscoderStatusEnum.failed:
                    # But only select it if there is no other already 
                    # selected, and it was not already acknowledged
                    if not (selected or acknowledged):
                        selected = transPxy
        return selected

    
    def _doLoadComponent(self, workerPxy, compName, compLabel,
                         compProperties, loadTimeout):
        self._attempts += 1
        return transcoder.TranscoderProxy.loadTo(workerPxy, compName, compLabel,
                                                 compProperties, loadTimeout)
        

    ## Private Methods ##
    
    def __transcodingFailed(self, transPxy=None):
        transPxy = transPxy or self.getActiveComponent()
        self.info("Transcoding task '%s' failed", self.label)
        self.emit("failed", transPxy)
        self._terminate(False)
    
    def __transcodingSucceed(self, transPxy=None):
        transPxy = transPxy or self.getActiveComponent()
        self.info("Transcoding task '%s' done", self.label)
        self.emit("done", transPxy)
        self._terminate(True)
    
    def __cbJobTerminated(self, status, transPxy):
        if status == TranscoderStatusEnum.done:
            self.__transcodingSucceed(transPxy)
        elif status == TranscoderStatusEnum.failed:
            self.__transcodingFailed(transPxy)
        elif status == TranscoderStatusEnum.unexpected_error:
            # If the transcoder component got an unexpected error
            # abort and eventualy retry
            self.warning("Transcoding task '%s' transcoder '%s' "
                         "got an unexpected error",
                         self.label, transPxy.getName())
            self._abort()
        elif status == TranscoderStatusEnum.error:
            # If the transcoder component got a known error (transcoder related)
            # it's assumed the error will raise again if we retry.
            # So we do not retry and treat as a failed transcoding.
            self.warning("Transcoding task '%s' transcoder '%s' "
                         "goes to error status", self.label, transPxy.getName())
            self.__transcodingFailed(transPxy)
        else:
            self.warning("Unexpected transcoder status/state combination.")
            self._abort()
    
    def __ebAcknowledgeFailed(self, failure, transPxy):
        if not self._isElectedComponent(transPxy): return
        if not failure.check("twisted.spread.pb.PBConnectionLost",
                             "flumotion.common.errors.SleepingComponentError"):
            log.notifyFailure(self, failure, 
                              "Failed to acknowledge task '%s' transcoder '%s'",
                              self.label, transPxy.getName())
        # If the acknowledge fail, the state is unpredictable,
        # so there is no sense to abort and retry.
        self.__transcodingFailed(transPxy)
        
    def __asyncSadTimeout(self, transPxy):
        if not self._isElectedComponent(transPxy): return
        if self._acknowledging: return
        if transPxy.getMood() == moods.sad:
            self.warning("Transcoding task '%s' transcoder '%s' stall in sad mood", 
                         self.label, transPxy.getName())
            self._abort()
