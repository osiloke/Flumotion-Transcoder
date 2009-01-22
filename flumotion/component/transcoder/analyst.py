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

from flumotion.inhouse import defer, utils

from flumotion.component.transcoder import compconsts
from flumotion.transcoder.errors import TranscoderError


class MediaAnalysisError(TranscoderError):
    def __init__(self, msg, filePath, *args, **kwargs):
        TranscoderError.__init__(self, msg, *args, **kwargs)
        self.filePath = filePath


class MediaAnalysisTimeoutError(MediaAnalysisError):
    def __init__(self, *args, **kwargs):
        TranscoderError.__init__(self, *args, **kwargs)


class MediaAnalysisUnknownTypeError(MediaAnalysisError):
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

    def getAudioCapsAsString(self):
        if self.audioCaps:
            return self.audioCaps.to_string()
        return None

    def getAudioDuration(self):
        return self.audioLength and float(self.audioLength / gst.SECOND)

    def getVideoCapsAsString(self):
        if self.videoCaps:
            return self.videoCaps.to_string()
        return None

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
            return float(length) / gst.SECOND
        return length

    def printInfo(self):
        if not self.mimeType:
            print "Unknown media type"
            return
        print "Mime Type :\t", self.mimeType
        if not self.hasVideo and not self.hasAudio:
            return
        print "Length :\t", self.__time2Str(self.getMediaLength())
        print "\tAudio:", self.__time2Str(self.audioLength), "\tVideo:", self.__time2Str(self.videoLength)
        if self.hasVideo and self.videoRate:
            print "Video :"
            print "\t%d x %d @ %d/%d fps" % (self.videoWidth,
                                            self.videoHeight,
                                            self.videoRate.num, self.videoRate.denom)
            if self.videoTags.has_key("video-codec"):
                print "\tCodec :", self.videoTags.pop("video-codec")
        if self.hasAudio:
            print "Audio :"
            if self.audioFloat:
                print "\t%d channels(s) : %dHz @ %dbits (float)" % (self.audioChannels,
                                                                    self.audioRate,
                                                                    self.audioWidth)
            else:
                print "\t%d channels(s) : %dHz @ %dbits (int)" % (self.audioChannels,
                                                                  self.audioRate,
                                                                  self.audioDepth)
            if self.audioTags.has_key("audio-codec"):
                print "\tCodec :", self.audioTags.pop("audio-codec")
        for stream in self.otherStreams:
            if not stream == self.mimeType:
                print "Other unsuported Multimedia stream :", stream
        if self.audioTags or self.videoTags or self.otherTags:
            print "Additional information :"
            for tag in self.audioTags.keys():
                print "%20s :\t" % tag, self.audioTags[tag]
            for tag in self.videoTags.keys():
                print "%20s :\t" % tag, self.videoTags[tag]
            for tag in self.otherTags.keys():
                print "%20s :\t" % tag, self.otherTags[tag]


    ## Private Methods ##

    def __time2Str(self, value):
        ms = value / gst.MSECOND
        sec = ms / 1000
        ms = ms % 1000
        min = sec / 60
        sec = sec % 60
        return "%2dm %2ds %3d" % (min, sec, ms)


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


class NewMediaAnalyst(MediaAnalyst):

    def analyse(self, filePath, timeout=None):
        from disco2 import Analyzer, AnalysisTimeoutError
        from disco2 import PatchedDiscovererAdapter as DiscovererAdapter
        deferred = defer.Deferred()
        fileURI = 'file://%s' % filePath
        an = Analyzer(fileURI, timeout=timeout)
        self._pending[an] = (filePath, deferred, None)

        def an_cb(minfo, analyzer):
            filePath, deferred, to = self._pending.pop(analyzer)
            if minfo.audio or minfo.video:
                deferred.callback(MediaAnalysis(filePath,
                                                DiscovererAdapter(minfo)))
            else:
                msg = "Analyzed file is not a known media type"
                error = MediaAnalysisUnknownTypeError(msg, filePath)
                deferred.errback(error)

        def an_eb(failure, analyzer):
            filePath, deferred, to = self._pending.pop(analyzer)
            if failure.check(AnalysisTimeoutError):
                msg = "Media analyse timeout"
                error = MediaAnalysisTimeoutError(msg, filePath)
            else:
                msg = "Analyzed file is not a known media type"
                error = MediaAnalysisUnknownTypeError(msg, filePath)
            deferred.errback(error)

        d = an.analyze()
        d.addCallbacks(an_cb, an_eb, callbackArgs=(an,), errbackArgs=(an,))
        return deferred


MediaAnalyst = NewMediaAnalyst
