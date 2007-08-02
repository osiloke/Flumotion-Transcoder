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

from twisted.internet import reactor
from twisted.python.failure import Failure

from flumotion.transcoder import log, defer
from flumotion.transcoder.errors import TranscoderError
from flumotion.component.transcoder import compconsts
from flumotion.component.transcoder.watcher import FilesWatcher
from flumotion.component.transcoder import targets

PLAY_ERROR_TIMEOUT = 8
PROGRESS_TIMEOUT = 1

class MultiTranscoder(log.LoggerProxy):
    """
    Takes a logger, an input file and a report and a timeout.
    transcoding and thumbnailing targets can be added.
    
    @type logger: L{flumotion.transcoder.log.Loggable}
    """    
    def __init__(self, logger, sourcePath, timeout=30,
                 progressCallback=None,
                 discoveredCallback=None, 
                 pipelineCallback=None):
        log.LoggerProxy.__init__(self, logger)
        self._sourcePath = sourcePath
        self._timeout = timeout
        self._discoveredCallback = discoveredCallback
        self._pipelineCallback = pipelineCallback
        self._progressCallback = progressCallback
        self._progressTimeout = None
        self._targets = []
        self._started = False
        self._pipeline = None
        self._watcher = None
        self._bus = None
        self._deferred = None
        self._waitingError = None
        self._progressSetup = False
        self._duration = None

    ## Public Methods ##

    def getSourcePath(self):
        return self._sourcePath
        
    def addTarget(self, target):
        self.__checkIfStarted("cannot add target")
        self._targets.append(target)
        return target

    def start(self):
        """
        Start transcoding and return a defer.Defferred 
        that will return the target list on success.
        """
        self.__checkIfStarted()
        self._started = True
        
        if not os.path.exists(self._sourcePath):
            error = TranscoderError("Source file '%s' does not exists"
                                    % self._sourcePath)
            return defer.fail(error)

        self._deferred = defer.Deferred()

        # discover the source media
        discoverer = Discoverer(self._sourcePath, 
                                max_interleave=compconsts.MAX_INTERLEAVE)
        discoverer.connect('discovered', self._discovered_callback)
        discoverer.discover()
        
        return self._deferred

    def abort(self):
        self.debug('Aborting Transcoding')
        self.__shutdownPipeline()
        return defer.succeed(self)

    
    ## Protected GObject Callback Methods ##

    def _discovered_callback(self, discoverer, ismedia):
        try:
            if self._discoveredCallback:
                self._discoveredCallback(discoverer, ismedia)
            
            if not ismedia:
                self.__failed("Source file is not a media file ('%s')",
                             self._sourcePath)
                return
            
            for t in self._targets:
                t._sourceDiscovered(discoverer)
            
            self.debug("Source media file is good for all targets")
            if discoverer.is_audio:
                self.log("Source media has audio stream")
            if discoverer.is_video:
                self.log("Source media has video stream")
            
            try:
                for target in self._targets:
                    target._setup(self)
            except Exception, e:
                self.debug("Target setup failed: %s", 
                           log.getExceptionMessage(e))
                self.__failed("Could not setup targets for file '%s': %s",
                             self._sourcePath, str(e))
                return
            
            try:
                self._pipeline = self.__makePipeline("transcoder-%s"
                                                    % self._sourcePath,
                                                    discoverer)
            except Exception, e:
                self.debug("Pipeline setup failed: %s", 
                           log.getExceptionMessage(e))
                self.__failed("Could not setup pipeline for file '%s': %s",
                             self._sourcePath, str(e))
                return

            self._bus = self._pipeline.get_bus()
            self._bus.add_signal_watch()
            self._bus.connect("message", self._bus_message_callback)
            
            ret = self._pipeline.set_state(gst.STATE_PLAYING)
            if ret == gst.STATE_CHANGE_FAILURE:
                self._waitingError = reactor.callLater(PLAY_ERROR_TIMEOUT,
                                                       self.__errorNotReceived)
                return
        
            # start a FilesWatcher on the expected output files
            expectedOutputs = list()
            for t in self._targets:
                t._pushMonitoredOutputs(expectedOutputs)
            self._watcher = FilesWatcher(self, expectedOutputs, 
                                         timeout=self._timeout)
            self._watcher.connect('file-completed', self._watcher_callback)
            self._watcher.connect('file-not-present', self._watcher_callback)
            self._watcher.start()
        except TranscoderError, e:
            self.__failed(e)
        except:
            self.__failed()

    def _bus_message_callback(self, bus, message):
        try:
            if message.type == gst.MESSAGE_STATE_CHANGED:
                if (message.src == self._pipeline):
                    old, new, pending = message.parse_state_changed()
                    if new == gst.STATE_PLAYING:
                        self.__startProgress()
                        if self._pipelineCallback:
                            self._pipelineCallback(self._pipeline, 
                                                   list(self._targets))
            elif message.type == gst.MESSAGE_ERROR:
                if self._waitingError:
                    self._waitingError.cancel()
                    self._waitingError = None
                gstgerror, debug = message.parse_error()
                msg = ("GStreamer error while processing '%s': %s" 
                       % (self._sourcePath, gstgerror.message))
                self.debug(msg)
                self.debug("Additional debug info: %s", debug)
                self.__failed(msg)
            elif message.type == gst.MESSAGE_EOS:
                self.__done()
            else:
                self.log('Unhandled GStreamer message %r', message)
        except TranscoderError, e:
            self.__failed(e)
        except:
            self.__failed()

    def _watcher_callback(self, watcher, file):
        """
        Called when a file has not been created after self._timeout seconds
        or gone unchanged in size for the past self._timeout seconds.
        """
        try:
            #Only process the first message, prevent multiple call to _fail
            #if more than one target timeout at the same time
            watcher.stop()
            if self._watcher == None:
                return
            self._watcher = None
            #try to find the target that failed
            for t in self._targets:
                if t._hasTargetFile(file):
                    t._raiseError("Timed out trying to transcode '%s' to '%s'",
                                  self._sourcePath, file)
            self.__failed("Timed out trying to transcode unknown file '%s'", 
                         file)
        except TranscoderError, e:
            self.__failed(e)
        except:
            self.__failed()

    def _decoder_pad_added(self, dbin, pad, tees):
        self.log("Decoder pad %r added, caps %s", pad, str(pad.get_caps()))
        try:
            if str(pad.get_caps()).startswith('audio/x-raw'):
                if not ('audiosink' in tees):
                    self.warning("Found an audio pad not previously "
                                 "discovered. Try a bigger max-interleave.")
                    gobject.idle_add(self._fail, 
                                     "Found an audio pad for '%s' "
                                     "not previously discovered. "
                                     "Try a bigger max-interleave."
                                     , self.inputfile)
                    return
                peer = tees['audiosink'].get_pad('sink')
                if peer.is_linked():
                    self.warning("Input file contains more than one "
                                 "audio stream. Using the first one.")
                else:
                    pad.link(peer)
            elif str(pad.get_caps()).startswith('video/x-raw'):
                if not ('videosink' in tees):
                    self.warning("Found a video pad not previously "
                                 "discovered. Try a bigger max-interleave.")
                    gobject.idle_add(self._fail, 
                                     "Found a video pad for '%s' "
                                     "not previously discovered. "
                                     "Try a bigger max-interleave."
                                     , self.inputfile)
                    return
                peer = tees['videosink'].get_pad('sink')
                if peer.is_linked():
                    self.warning("Input file contains more than one "
                                 "video stream. Using the first one.")
                else:
                    pad.link(peer)
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
        self.__failed("Could not play pipeline for file '%s'", self._sourcePath)
        
    def __postErrorMessage(self, msg, debug=None):
        error = gst.GError(gst.STREAM_ERROR, 
                           gst.STREAM_ERROR_FAILED, msg)
        message = gst.message_new_error(self._pipeline, error, debug)
        self._pipeline.post_message(message)

    def __failed(self, error=None, *args):
        self.__shutdownPipeline()
        if error == None:
            self._deferred.errback(Failure())
            return
        if not isinstance(error, Exception):
            error = TranscoderError(error % args)
        self._deferred.errback(error)

    def __done(self):
        if  self._progressCallback:
            self._progressCallback(100.0)
        self.__shutdownPipeline()
        self._deferred.callback(list(self._targets))

    def __shutdownPipeline(self):
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
            
    def __makePipeline(self, name, discoverer):
        pipeline = gst.Pipeline(name)
        src = gst.element_factory_make("filesrc")
        src.props.location = self._sourcePath
        dbin = gst.element_factory_make("decodebin")
        pipeline.add(src, dbin)
        src.link(dbin)

        tees = {}
        if discoverer.is_audio:
            tees["audiosink"] = gst.element_factory_make('tee')
        if discoverer.is_video:
            tees["videosink"] = gst.element_factory_make('tee')

        for tee in tees.values():
            pipeline.add(tee)

        for target in self._targets:
            target._updatePipeline(pipeline, discoverer, tees)

        dbin.connect('pad-added', self._decoder_pad_added, tees)
        
        return pipeline

    def __startProgress(self):
        if not self._duration:
            try:
                self.log('Querying the pipeline duration')
                pipe = self._pipeline
                duration, format = pipe.query_duration(gst.FORMAT_TIME)
            except gst.QueryError, e:
                self.warning("Failed to retrieve pipline duration: %s",
                             log.getExceptionMessage(e))
                self._duration = None
                self.__updateProgress()
                return
            if format != gst.FORMAT_TIME:
                self.__postErrorMessage("Bad pipline duration format",
                                       log.getExceptionMessage(e))
                self.warning("Bad pipline duration format: %s",
                             log.getExceptionMessage(e))
                self._duration = None
            else:
                self._duration = duration
            self.__updateProgress()

    def __updateProgress(self):
        # Check if progression annot be done
        if not (self._duration and (self._duration > 0)):
            if  self._progressCallback:
                self._progressCallback(None)
            return
        try:
            self._progressTimeout = None
            positions = []
            for sink in self._pipeline.sinks():
                try:
                    position, format = sink.query_position(gst.FORMAT_TIME)
                except gst.QueryError, e:
                    self.__postErrorMessage("Failed to retrieve pipline position", 
                                           log.getExceptionMessage(e))
                    return
                if format != gst.FORMAT_TIME:
                    self.__postErrorMessage("Bad pipline position format",
                                           log.getExceptionMessage(e))
                    return
                if position >= 0:
                    positions.append(position)
            position = position and min(positions) or 0
            # force position <= duration
            position = min(position, self._duration)
            if  self._progressCallback:
                self._progressCallback(position * 100.0 / self._duration)
            self._progressTimeout = reactor.callLater(PROGRESS_TIMEOUT,
                                                      self.__updateProgress)
        except TranscoderError, e:
            self.__failed(e)
        except:
            self.__failed()

    def __cleanupProgress(self):
        if self._progressTimeout:
            self._progressTimeout.cancel()
            self._progressTimeout = None
