# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import os

import gobject
import gst
from gst.extend.discoverer import Discoverer

from zope.interface import Interface
from twisted.internet import reactor
from twisted.python.failure import Failure

from flumotion.transcoder import log, defer, utils
from flumotion.transcoder.errors import TranscoderError
from flumotion.component.transcoder import compconsts
from flumotion.component.transcoder import analyst
from flumotion.component.transcoder.watcher import FilesWatcher

class ITranscoderProducer(Interface):
    
    def getLabel(self):
        pass
    
    def raiseError(self, msg, *args):
        """
        Raise an exception.
        Permit the producers to raise specific type of exceptions.
        """
    
    def getMonitoredFiles(self):
        """
        Retrieve the list of files that should be monitored
        during transcoding, these files should not stall.
        """

    def checkSourceMedia(self, sourcePath, analysis):
        """
        Let the producer check if the source file is correct for its purpose.
        If not, the producer will raise an exception
        """

    def updatePipeline(self, pipeline, analysis, tees, timeout=None):
        """
        Update the transcoding pipeline with this producer specific elements.
        The tees argument is a dict with references to tee elements for
        the different source's streams named 'videosink' and 'audiosink'.
        """
    
    def prepare(self, timeout=None):
        """
        Prepare the producer before playing the pipeline.
        Can return a Deferred.
        """

    def finalize(self, timeout=None):
        """
        Finalize the producer transcoding.
        Can return a Deferred.
        """
    
    def abort(self, timeout=None):
        """
        Abort the producer transcoding task.
        Can return a Deferred.
        """

    def onTranscodingFailed(self, failure):
        """
        Called when the transcoding process failed.
        """
    
    def onTranscodingDone(self):
        """
        Called when the transcoding process succeed.
        """


class MediaTranscoder(log.LoggerProxy):
    """
    Transcode a source file to a list of producer.
    The producers should be child class of TranscodingProducers.
    """    
    def __init__(self, logger, analyzedCB=None,
                 preparedCB=None, playingCB=None, progressCB=None):
        log.LoggerProxy.__init__(self, logger)
        self._preparedCallback = preparedCB
        self._analyzedCallback = analyzedCB
        self._playingCallback = playingCB
        self._progressCallback = progressCB
        self._sourcePath = None
        self._sourceAnalysis = None
        self._analyst = None
        self._pipeline = None
        self._bus = None
        self._watcher = None
        self._started = False
        self._aborted = False
        self._deferred = None
        self._progressSetup = False
        self._progressTimeout = None
        self._producers = {} # ITranscodingProducers
        self._playErrorTimeout = None
        self._playStateTimeout = None
        self._duration = None
        self._monitoredFiles = {} # {filePath: TranscodingProducers}

    ## Public Methods ##

    def addProducer(self, producer):
        assert ITranscoderProducer.providedBy(producer)
        self.__checkIfStarted("cannot add producer")
        self._producers[producer] = None
        return producer

    def getProducers(self):
        return self._producers.keys()

    def start(self, sourcePath, sourceAnalysis=None, timeout=30):
        """
        Start transcoding and return a defer.Deferred
        that will be call when all producer terminate.
        """
        if self._aborted: return
        self.__checkIfStarted()
        self._started = True
        
        self.log("Starting media transcoder")
        
        if not os.path.exists(sourcePath):
            error = TranscoderError("Source file '%s' does not exists"
                                    % sourcePath)
            return defer.fail(error)

        self._sourcePath = sourcePath
        self._stallTimeout = timeout
        self._deferred = defer.Deferred()

        # Analyse the source media if needed
        if not sourceAnalysis:
            self._analyst = analyst.MediaAnalyst()
            analyseTimeout = compconsts.SOURCE_ANALYSE_TIMEOUT
            d = self._analyst.analyse(sourcePath, timeout=analyseTimeout)
        else:
            assert sourceAnalysis.filePath == sourcePath
            d = defer.succeed(sourceAnalysis)
        
        d.addCallbacks(self.__cbCheckSourceAnalysis,
                       self.__ebSourceAnalysisError)
        d.addErrback(self.__failed)
        
        return self._deferred

    def abort(self):
        if self._aborted: return
        self.debug("Aborting media transcoder")
        self._aborted = True
        d = defer.succeed(self)
        for producer in self._producers:
            d.addBoth(defer.dropResult, producer.abort,
                      compconsts.TRANSCODER_ABORT_TIMEOUT)
        d.addBoth(defer.dropResult, self.__shutdownPipeline)
        if self._analyst:
            d.addBoth(defer.dropResult, self._analyst.abort)
        return d

    
    ## Protected GObject Callback Methods ##

    def _bus_message_callback(self, bus, message):
        if self._aborted: return
        try:
            if message.type == gst.MESSAGE_STATE_CHANGED:
                if (message.src == self._pipeline):
                    new = message.parse_state_changed()[1]
                    if new == gst.STATE_PLAYING:
                        self.__onPipelinePlaying()
                return
            if message.type == gst.MESSAGE_EOS:
                self.__finalizeProducers()
                return
            if message.type == gst.MESSAGE_ERROR:
                gstgerror, debug = message.parse_error()
                self.__onPipelineError(gstgerror.message, debug)
                return
            self.log("Unhandled GStreamer message in transcoding "
                     "pipeline:  %s", message)
        except TranscoderError, e:
            self.__failed(e)
        except:
            self.__failed()

    def _watcher_callback(self, watcher, file):
        """
        Called when a file has not been created after self._stallTimeout seconds
        or gone unchanged in size for the past self._stallTimeout seconds.
        """
        if self._aborted: return
        try:
            # Only process the first message, prevent multiple call to __failed
            # if more than one producer timeout at the same time
            watcher.stop()
            if self._watcher == None:
                return
            self._watcher = None
            producer = self._monitoredFiles.get(file, None)
            if producer:
                producer.raiseError("Producers '%s' output file stalled during "
                                  "transcoding: '%s'", producer.getLabel(), file)
            else:
                self.__failed("Unknown producer output file stalled during "
                              "transcoding: '%s'" % file)
        except TranscoderError, e:
            self.__failed(e)
        except:
            self.__failed()

    def _decoder_pad_added(self, dbin, pad, tees):
        if self._aborted: return
        self.log("Decoder pad %r added, caps %s", pad, str(pad.get_caps()))
        try:
            if str(pad.get_caps()).startswith('audio/x-raw'):
                if not ('audiosink' in tees):
                    self.warning("Found an audio pad not previously "
                                 "discovered. Try a bigger max-interleave.")
                    gobject.idle_add(self.__failed,
                                     "Found an audio pad for '%s' "
                                     "not previously discovered. "
                                     "Try a bigger max-interleave."
                                     % self._sourcePath)
                    return
                peer = tees['audiosink'].get_pad('sink')
                if peer.is_linked():
                    self.warning("Input file contains more than one "
                                 "audio stream. Using the first one.")
                else:
                    pad.link(peer)
                    return
            elif str(pad.get_caps()).startswith('video/x-raw'):
                if not ('videosink' in tees):
                    self.warning("Found a video pad not previously "
                                 "discovered. Try a bigger max-interleave.")
                    gobject.idle_add(self.__failed, 
                                     "Found a video pad for '%s' "
                                     "not previously discovered. "
                                     "Try a bigger max-interleave."
                                     % self._sourcePath)
                    return
                peer = tees['videosink'].get_pad('sink')
                if peer.is_linked():
                    self.warning("Input file contains more than one "
                                 "video stream. Using the first one.")
                else:
                    pad.link(peer)
                    return
            else:
                self.debug('Unknown pad from decodebin: %r (caps %s)',
                           pad, pad.get_caps())
        except Exception, e:
            self.__postErrorMessage(str(e), log.getExceptionMessage(e))


    ## Private Methods ##

    def __checkIfStarted(self, msg=None):
        if self._started:
            error = "Transcoder already started"
            if msg:
                error = error + ", " + msg
            raise TranscoderError(error)
        
    def __errorNotReceived(self):
        self.__failed("Could not play pipeline for file '%s'" % self._sourcePath)
        
    def __postErrorMessage(self, msg, debug=None):
        error = gst.GError(gst.STREAM_ERROR, 
                           gst.STREAM_ERROR_FAILED, msg)
        message = gst.message_new_error(self._pipeline, error, debug)
        self._pipeline.post_message(message)

    def __failed(self, error=None, cause=None):
        if self._aborted: return
        self.log('Media Transcoding failed')
        if error == None:
            error = Failure()
        if not isinstance(error, (Exception, Failure)):
            error = TranscoderError(error, cause=cause)
        self.__shutdownPipeline()
        if self._analyst:
            return self._analyst.abort()
        for producer in self._producers:
            producer.onTranscodingFailed(error)
        self._deferred.errback(error)

    def __done(self):
        if self._aborted: return
        self.log('Media Transcoding done')
        self.__fireProgressCallback(100.0)
        self.__shutdownPipeline()
        if self._analyst:
            return self._analyst.abort()
        for producer in self._producers:
            producer.onTranscodingDone()
        self._deferred.callback(self)

    def __onPipelineError(self, message, debug):
        self.log('Media transcoder error: %s', message)
        utils.cancelTimeout(self._playErrorTimeout)
        msg = ("GStreamer error during transcoding: " + message)
        self.debug(msg)
        self.debug("Additional debug info: %s", debug)
        self.__failed(msg)

    def __playPipelineTimeout(self):
        self.log('Media transcoder pipeline stalled at prerolling')
        error = TranscoderError("Transcoder pipeline stalled at prerolling")
        self.__failed(error)

    def __onPipelinePlaying(self):
        utils.cancelTimeout(self._playStateTimeout)
        self.__startProgress()
        self.__firePlayingCallback()

    def __shutdownPipeline(self):
        self.log('Shutting down media transcoder pipeline')
        self.__cleanupProgress()
        if self._bus:
            self._bus.remove_signal_watch()
        self._bus = None
        if self._pipeline:
            self._pipeline.set_state(gst.STATE_NULL)
        self._pipeline = None
        if self._watcher:
            self._watcher.stop()
            self._watcher = None

    def __fireAnalyzedCallback(self, analysis):
        if self._analyzedCallback:
            self._analyzedCallback(self, analysis)

    def __fireProgressCallback(self, value):
        if  self._progressCallback:
            self._progressCallback(self, value)

    def __firePreparedCallback(self):
        if self._preparedCallback:
            self._preparedCallback(self, self._pipeline)

    def __firePlayingCallback(self):
        if self._playingCallback:
            self._playingCallback(self, self._pipeline)

    def __ebSourceAnalysisError(self, failure):
        if self._aborted: return
        self.log('Media transcoder source analysis failed: %s',
                 log.getFailureMessage(failure))
        self.__fireAnalyzedCallback(None)
        error = TranscoderError("Source file is not a known media",
                                cause=failure)
        self.__failed(error)
        # The error has been deal with, resolve the errback
        return None

    def __cbCheckSourceAnalysis(self, sourceAnalysis):
        if self._aborted: return
        self.log('Checking source analysis')
        self.__fireAnalyzedCallback(sourceAnalysis)
        
        if sourceAnalysis.hasAudio:
            self.debug("Source audio caps: '%s'" % sourceAnalysis.getAudioCapsAsString())
        if sourceAnalysis.hasVideo:
            self.debug("Source video caps: '%s'" % sourceAnalysis.getVideoCapsAsString())

        if not self._producers:
            # If there is no producer, the transcoding succeed for sure.
            self.__done()
            return
            
        for producer in self._producers:
            producer.checkSourceMedia(self._sourcePath, sourceAnalysis)
        
        self.debug("Source media file is good for all producers")
        self._sourceAnalysis = sourceAnalysis
        
        d = defer.succeed(None)
        for producer in self._producers:
            d.addCallback(defer.dropResult, producer.prepare,
                          compconsts.TRANSCODER_PREPARE_TIMEOUT)
        d.addCallbacks(self.__cbSetupPipeline,
                       self.__ebProducersSetupFailed)
        d.addErrback(self.__failed)

    def __ebProducersSetupFailed(self, failure):
        if self._aborted: return
        self.debug("Producers setup failed: %s", 
                   log.getFailureMessage(failure))
        self.__failed("Could not setup producers for file '%s': %s"
                     % (self._sourcePath, str(failure.value)), cause=failure)
        # The error has been deal with, resolve the errback
        return None

    def __cbSetupPipeline(self, _):
        if self._aborted: return
        self.log('Setting up transcoding pipeline')
        pipelineName = "transcoder-%s" % self._sourcePath
        pipeline = gst.Pipeline(pipelineName)
        src = gst.element_factory_make("filesrc")
        src.props.location = self._sourcePath
        dbin = gst.element_factory_make("decodebin")
        pipeline.add(src, dbin)
        src.link(dbin)
        
        tees = {}
        if self._sourceAnalysis.hasAudio:
            tees["audiosink"] = gst.element_factory_make('tee')
        if self._sourceAnalysis.hasVideo:
            tees["videosink"] = gst.element_factory_make('tee')

        for tee in tees.values():
            pipeline.add(tee)

        dbin.connect('pad-added', self._decoder_pad_added, tees)

        d = defer.succeed(pipeline)
        for producer in self._producers:
            d.addCallback(defer.keepResult,
                          producer.updatePipeline,
                          self._sourceAnalysis, tees,
                          compconsts.TRANSCODER_UPDATE_TIMEOUT)
        d.addCallbacks(self.__cbStartupPipeline,
                       self.__ebPipelineSetupFailed)
        d.addErrback(self.__failed)
        
    def __ebPipelineSetupFailed(self, failure):
        if self._aborted: return
        self.debug("Pipeline setup failed: %s", 
                   log.getFailureMessage(failure))
        self.__failed("Could not setup pipeline for file '%s': %s"
                      % (self._sourcePath, str(failure.value)), cause=failure)
        # The error has been deal with, resolve the errback
        return None
    
    def __cbStartupPipeline(self, pipeline):
        if self._aborted: return
        self.log('Starting up transcoding pipeline')
        self._pipeline = pipeline
        self._bus = self._pipeline.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect("message", self._bus_message_callback)
        
        self.__firePreparedCallback()
        
        ret = self._pipeline.set_state(gst.STATE_PLAYING)
        if ret == gst.STATE_CHANGE_FAILURE:
            timeout = compconsts.TRANSCODER_PLAY_ERROR_TIMEOUT
            to = utils.createTimeout(timeout, self.__errorNotReceived)
            self._playErrorTimeout = to
            return
        
        timeout = compconsts.TRANSCODER_PLAYING_TIMEOUT
        to = utils.createTimeout(timeout, self.__playPipelineTimeout)
        self._playStateTimeout = to
    
        # Start a FilesWatcher for producers' monitored files
        for producer in self._producers:
            files = producer.getMonitoredFiles()
            for path in files:
                assert not (path in self._monitoredFiles)
                self._monitoredFiles[path] = producer
        
        self._watcher = FilesWatcher(self, self._monitoredFiles.keys(), 
                                     timeout=self._stallTimeout)
        self._watcher.connect('file-completed', self._watcher_callback)
        self._watcher.connect('file-not-present', self._watcher_callback)
        self._watcher.start()

    def __finalizeProducers(self):
        if self._aborted: return
        self.log('Finalizing transcoding pipeline')
        d = defer.succeed(None)
        for producer in self._producers:
            d.addCallback(defer.dropResult,
                          producer.finalize,
                          compconsts.TRANSCODER_FINALIZE_TIMEOUT)
        d.addCallback(defer.dropResult, self.__done)
        d.addErrback(self.__failed)

    def __startProgress(self):
        if not self._duration:
            try:
                self.log('Querying the pipeline duration')
                pipe = self._pipeline
                duration, format = pipe.query_duration(gst.FORMAT_TIME)
            except gst.QueryError, e:
                self.warning("Failed to retrieve pipline duration, "
                             "disabling progression notification: %s",
                             log.getExceptionMessage(e))
                self._duration = None
                self.__updateProgress()
                return
            if format != gst.FORMAT_TIME:
                self.warning("Bad pipline duration format, "
                             "disabling progression notification")
                self._duration = None
            else:
                self._duration = duration
            self.__updateProgress()

    def __updateProgress(self):
        # Check if progression cannot be done
        if not (self._duration and (self._duration > 0)):
            self.__fireProgressCallback(None)
            return
        try:
            self._progressTimeout = None
            positions = []
            for sink in self._pipeline.sinks():
                try:
                    position, format = sink.query_position(gst.FORMAT_TIME)
                    if format != gst.FORMAT_TIME:
                        self.warning("Bad pipline position format, "
                                     "disabling progression notification")
                    elif position >= 0:
                        positions.append(position)
                except gst.QueryError, e:
                    self.warning("Failed to retrieve pipline position, "
                                 "disabling progression notification: %s", 
                                 log.getExceptionMessage(e))
            if not positions:
                # Disabling progression notification
                self._duration = None
                self.__fireProgressCallback(None)
                return
            position = position and min(positions) or 0
            # force position <= duration
            position = min(position, self._duration)
            self.__fireProgressCallback(position * 100.0 / self._duration)
            self._progressTimeout = reactor.callLater(compconsts.PROGRESS_PERIOD,
                                                      self.__updateProgress)
        except TranscoderError, e:
            self.__failed(e)
        except:
            self.__failed()

    def __cleanupProgress(self):
        if self._progressTimeout:
            self._progressTimeout.cancel()
            self._progressTimeout = None
