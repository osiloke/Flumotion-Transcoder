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

import gst
from gst.extend.discoverer import Discoverer

from flumotion.component.transcoder import compconsts
from flumotion.transcoder import defer, utils
from flumotion.transcoder.errors import TranscoderError


class MediaAnalysisError(TranscoderError):
    def __init__(self, msg, filePath, *args, **kwargs):
        TranscoderError.__init__(self, msg, *args, **kwargs)
        self.filePath = filePath


class MediaAnalysisTimeoutError(MediaAnalysisError):
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


class MediaAnalysisUnknownTypeError(TranscoderError):
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


class MediaAnalysis(object):

    def __init__(self, filePath, discoverer):
        self.filePath = filePath
        self.mimeType = discoverer.mimetype
        self.hasAudio = discoverer.is_audio
        self.audioCaps = discoverer.audiocaps
        self.audioFloat = discoverer.audiofloat
        self.audioRate = discoverer.audiorate
        self.audioDepth = discoverer.audiodepth
        self.audioWidth = discoverer.audiowidth
        self.audioChannels = discoverer.audiochannels
        self.audioLength = discoverer.audiolength
        self.hasVideo = discoverer.is_video
        self.videoCaps = discoverer.videocaps
        self.videoWidth = discoverer.videowidth
        self.videoHeight = discoverer.videoheight
        self.videoRate = discoverer.videorate
        self.videoLength = discoverer.videolength
        self.otherStreams = list(discoverer.otherstreams)
        self.audioTags = dict(discoverer.audiotags)
        self.videoTags = dict(discoverer.videotags)
        self.otherTags = dict(discoverer.othertags)
        self.otherStreams = list(discoverer.otherstreams)

    def getAudioCapsAsString(self):
        return self.audioCaps and self.audioCaps.to_string()
    
    def getAudioDuration(self):
        return self.audioLength and float(self.audioLength / gst.SECOND)
    
    def getVideoCapsAsString(self):
        return self.videoCaps and self.videoCaps.to_string()
    
    def getVideoDuration(self):
        return self.videoLength and float(self.videoLength / gst.SECOND)

    def getMediaLength(self):
        if self.videoLength and self.audioLength:
            return max(self.videoLength, self.audioLength)
        if self.videoLength:
            return self.videoLength
        if self.audioLength:
            return self.audioLength
        return -1

    def getMediaDuration(self):
        length = self.getMediaLength()
        if length and (length > 0):
            return float(length / gst.SECOND)
        return length


class MediaAnalyst(object):

    def __init__(self):
        self._pending = {}
        
    def hasPendingAnalysis(self):
        return len(self._pending) > 0
        
    def abort(self):
        return defer.succeed(self)
        
    def analyse(self, filePath, timeout=None):
        deferred = defer.Deferred()
        discoverer = Discoverer(filePath,
                                max_interleave=compconsts.MAX_INTERLEAVE)
        discoverer.connect('discovered', self._discoverer_callback)
        to = utils.createTimeout(timeout, self.__analyseTimeout, discoverer)
        self._pending[discoverer] = (filePath, deferred, to)
        discoverer.discover()
        return deferred


    ## Protected Methods ##
    
    def _discoverer_callback(self, discoverer, is_media):
        if not (discoverer in self._pending):
            # Analyse timed out before completion
            return
        filePath, deferred, to = self._pending.pop(discoverer)
        utils.cancelTimeout(to)
        if is_media:
            deferred.callback(MediaAnalysis(filePath, discoverer))
        else:
            msg = "Analyzed file is not a known media type"
            error = MediaAnalysisUnknownTypeError(msg, filePath)
            deferred.errback(error)


    ## Private Methods ##
    
    def __analyseTimeout(self, discoverer):
        filePath, deferred = self._pending.pop(discoverer)[:2]
        msg = "Media analyse timeout"
        error = MediaAnalysisTimeoutError(msg, filePath)
        deferred.errback(error)
