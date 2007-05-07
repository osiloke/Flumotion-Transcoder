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
from twisted.internet import reactor, defer
from twisted.python.failure import Failure
from flumotion.component.transcoder import gstutils
from flumotion.transcoder import log
from flumotion.transcoder.errors import TranscoderError
from flumotion.component.transcoder.watcher import FilesWatcher
from flumotion.component.transcoder import targets

PLAY_ERROR_TIMEOUT = 8
PROGRESS_TIMEOUT = 1

class MultiTranscoder(object):
    """
    Takes a logger, an input file and a report and a timeout.
    transcoding and thumbnailing targets can be added.
    
    @type logger: L{flumotion.common.log.Loggable}
    """    
    def __init__(self, logger, sourcePath, timeout=30,
                 progressCallback=None,
                 discoveredCallback=None, 
                 pipelineCallback=None):
        self._logger = logger
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
        
    def log(self, *args, **kwargs):
        self._logger.log(*args, **kwargs)
        
    def debug(self, *args, **kwargs):
        self._logger.debug(*args, **kwargs)

    def info(self, *args, **kwargs):
        self._logger.info(*args, **kwargs)

    def warning(self, *args, **kwargs):
        self._logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        self._logger.error(*args, **kwargs)

    def _checkIfStarted(self, msg=None):
        if self._started:
            error = "Transcoder already started"
            if msg:
                error = error + ", " + msg
            raise TranscoderError(error)

    def addTarget(self, target):
        self._checkIfStarted("cannot add target")
        self._targets.append(target)
        return target

    def start(self):
        """
        Start transcoding and return a defer.Defferred 
        that will return the target list on success.
        """
        self._checkIfStarted()
        self._started = True
        
        if not os.path.exists(self._sourcePath):
            error = TranscoderError("Source file '%s' does not exists"
                                    % self._sourcePath)
            return defer.fail(error)

        self._deferred = defer.Deferred()

        # discover the source media
        discoverer = Discoverer(self._sourcePath, 
                                max_interleave=gstutils.MAX_INTERLEAVE)
        discoverer.connect('discovered', self._discovered_callback)
        discoverer.discover()
        
        return self._deferred

    def abort(self):
        self.debug('Aborting Transcoding')
        self._shutdownPipeline()
        return defer.succeed(self)

    def _postErrorMessage(self, msg, debug=None):
        error = gst.GError(gst.STREAM_ERROR, 
                           gst.STREAM_ERROR_FAILED, msg)
        message = gst.message_new_error(self._pipeline, error, debug)
        self._pipeline.post_message(message)

    def _failed(self, error=None, *args):
        self._shutdownPipeline()
        if error == None:
            self._deferred.errback(Failure())
            return
        if not isinstance(error, Exception):
            error = TranscoderError(error % args)
        self._deferred.errback(error)

    def _done(self):
        if  self._progressCallback:
            self._progressCallback(100.0)
        self._shutdownPipeline()
        self._deferred.callback(list(self._targets))

    def _discovered_callback(self, discoverer, ismedia):
        try:
            if self._discoveredCallback:
                self._discoveredCallback(discoverer, ismedia)
            
            if not ismedia:
                self._failed("Source file is not a media file ('%s')",
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
                self._pipeline = self._makePipeline("transcoder-%s"
                                                    % self._sourcePath,
                                                    discoverer)
            except Exception, e:
                self.debug("Pipeline setup failed: %s", 
                           log.getExceptionMessage(e))
                self._failed("Could not setup pipeline for file '%s': %s",
                             self._sourcePath, str(e))
                return

            self._bus = self._pipeline.get_bus()
            self._bus.add_signal_watch()
            self._bus.connect("message", self._bus_message_callback)
            
            ret = self._pipeline.set_state(gst.STATE_PLAYING)
            if ret == gst.STATE_CHANGE_FAILURE:
                self._waitingError = reactor.callLater(PLAY_ERROR_TIMEOUT,
                                                       self._errorNotReceived)
                return
        
            # start a FilesWatcher on the expected output files
            expectedOutputs = list()
            for t in self._targets:
                t._pushExpectedOutputs(expectedOutputs)
            self._watcher = FilesWatcher(expectedOutputs, 
                                         timeout=self._timeout)
            self._watcher.connect('file-completed', self._watcher_callback)
            self._watcher.connect('file-not-present', self._watcher_callback)
            self._watcher.start()
        except TranscoderError, e:
            self._failed(e)
        except:
            self._failed()
            
    def _errorNotReceived(self):
        self._failed("Could not play pipeline for file '%s'", self._sourcePath)

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
            self._failed("Timed out trying to transcode unknown file '%s'", 
                         file)
        except TranscoderError, e:
            self._failed(e)
        except:
            self._failed()

    def _bus_message_callback(self, bus, message):
        try:
            if message.type == gst.MESSAGE_STATE_CHANGED:
                if (message.src == self._pipeline):
                    old, new, pending = message.parse_state_changed()
                    if new == gst.STATE_PLAYING:
                        self._startProgress()
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
                self._failed(msg)
            elif message.type == gst.MESSAGE_EOS:
                self._done()
            else:
                self.log('Unhandled GStreamer message %r' % message)
        except TranscoderError, e:
            self._failed(e)
        except:
            self._failed()

    def _shutdownPipeline(self):
        self._cleanupProgress()
        if self._bus:
            self._bus.remove_signal_watch()
        self._bus = None
        if self._pipeline:
            self._pipeline.set_state(gst.STATE_NULL)
        self._pipeline = None
        if self._watcher:
            self._watcher.stop()
            self._watcher = None
            
    def _makePipeline(self, name, discoverer):
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

    def _decoder_pad_added(self, dbin, pad, tees):
        self.log('Decoder pad %r added, caps %s' % (pad, str(pad.get_caps())))
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
            self._postErrorMessage(str(e), log.getExceptionMessage(e))

    def _startProgress(self):
        if not self._duration:
            try:
                pipe = self._pipeline
                duration, format = pipe.query_duration(gst.FORMAT_TIME)
            except gst.QueryError, e:
                self._postErrorMessage("Failed to retrieve pipline duration", 
                                       log.getExceptionMessage(e))
                return
            if format != gst.FORMAT_TIME:
                self._postErrorMessage("Bad pipline duration format",
                                       log.getExceptionMessage(e))
                return
            self._duration = duration
            self._updateProgress()

    def _updateProgress(self):
        try:
            self._progressTimeout = None
            positions = []
            for sink in self._pipeline.sinks():
                try:
                    position, format = sink.query_position(gst.FORMAT_TIME)
                except gst.QueryError, e:
                    self._postErrorMessage("Failed to retrieve pipline position", 
                                           log.getExceptionMessage(e))
                    return
                if format != gst.FORMAT_TIME:
                    self._postErrorMessage("Bad pipline position format",
                                           log.getExceptionMessage(e))
                    return
                if position >= 0:
                    positions.append(position)
            position = min(positions)
            if  self._progressCallback:
                self._progressCallback(position * 100.0 / self._duration)
            self._progressTimeout = reactor.callLater(PROGRESS_TIMEOUT,
                                                  self._updateProgress)
        except TranscoderError, e:
            self._failed(e)
        except:
            self._failed()
    
    def _cleanupProgress(self):
        if self._progressTimeout:
            self._progressTimeout.cancel()
            self._progressTimeout = None
