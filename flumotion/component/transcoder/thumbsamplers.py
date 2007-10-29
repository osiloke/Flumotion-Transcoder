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

from zope.interface import Interface, implements

from flumotion.transcoder import log
from flumotion.transcoder.substitution import Variables
from flumotion.component.transcoder import compconsts
from flumotion.component.transcoder.thumbsink import IThumbnailSampler


class IThumbnailer(Interface):
    
    def push(self, buffer, vars):
        pass


_fixedFramesIndex = set([1, 25, 50, 100, 200, 400, 800])

class BaseSampler(log.LoggerProxy):
    """
    The thumbnail template variables:
        %(frame)d  => frame number (starting at 1)
        %(key)d  => key number (starting at 1)
        %(index)d  => index of the thumbnail (starting at 1)
        %(timestamp)d => timestamp of the thumbnail
        %(time)s => composed time of the thumbnail, 
                    like %(hours)02d:%(minutes)02d:%(seconds)02d
        %(hours)d => hours from start
        %(minutes)d => minutes from start
        %(seconds)d => seconds from start
    """
    
    implements(IThumbnailSampler)
    
    def __init__(self, logger, thumbnailer, analysis, ensureOne, maxThumb):
        log.LoggerProxy.__init__(self, logger)
        assert IThumbnailer.providedBy(thumbnailer)
        self._thumbnailer = thumbnailer
        self._streamLength = analysis.getMediaLength()
        self._ensureOne = ensureOne
        self._maxThumb = maxThumb
        self._fixedFrame = None
        self._lastBuffer = None
        self._lastStreamTime = None
        self._lastFrameDuration = None
        self._frameIndex = 0
        self._keyIndex = 0
        self._thumbIndex = 0

    
    ## IThumbnailSampler Methods ##
    
    def prepare(self, startTime):
        self._doPrepare(startTime)
        
    def update(self, streamTime, buffer):
        if (self._maxThumb > 0)  and (self._thumbIndex >= self._maxThumb):
            return
        # Have a one buffer delay to ensure having always the frame duration
        if self._lastBuffer:
            frameDuration = streamTime - self._lastStreamTime - 1
            self.__updateThumbnail(self._lastStreamTime, frameDuration,
                                   self._lastBuffer)
            self._lastFrameDuration = frameDuration
        self._lastBuffer = buffer
        self._lastStreamTime = streamTime

    def finalize(self):
        if self._lastBuffer:
            frameDuration = self._lastFrameDuration or (gst.SECOND / 25)
            self.__updateThumbnail(self._lastStreamTime, frameDuration, self._lastBuffer)
        self.__ensureOne()
        self._doFinalize()


    ## Protected Virtual Methods ##
    
    def _doPrepare(self, startTime):
        pass
    
    def _onKeepThumbnail(self, thumbIndex, frameIndex, keyIndex,
                         frameDuration, streamTime, streamLength):
        return False
    
    def _doFinalize(self):
        pass


    ## Private Methods ##

    def __updateThumbnail(self, streamTime, frameDuration, buffer):
        self._frameIndex += 1
        if not buffer.flag_is_set(gst.BUFFER_FLAG_DELTA_UNIT):
            self._keyIndex += 1
        frameIndex = self._frameIndex 
        keyIndex = self._keyIndex
        thumbIndex = self._thumbIndex + 1
        streamLength = self._streamLength
        self.__keepFixedFrames(frameIndex, keyIndex, frameDuration,
                               streamTime, streamLength, buffer)
        if self._onKeepThumbnail(thumbIndex, frameIndex, keyIndex,
                                 frameDuration, streamTime, streamLength):
            vars = self.__buildVars(thumbIndex, frameIndex, keyIndex,
                                    frameDuration, streamTime, streamLength)
            self._thumbnailer.push(buffer, vars)
            self._thumbIndex = thumbIndex
   
    def __keepFixedFrames(self, frameIndex, keyIndex, frameDuration,
                          streamTime, streamLength, buffer):
        if self._ensureOne:
            # Keep some frames to ensure at least one frame
            if frameIndex in _fixedFramesIndex:
                self._fixedFrame = (frameIndex, keyIndex, frameDuration,
                                    streamTime, streamLength, buffer)
        
    
    def __ensureOne(self):
        if not self._ensureOne: return
        if self._thumbIndex > 0: return
        if not self._fixedFrame:
            self.warning("Couldn't ensure at least on thumbnail; "
                         "empty video stream ?")
            return
        fi, ki, fd, st, sl, buffer = self._fixedFrame
        self.debug("No thumbnail found, ensuring a thumbnail "
                   "by using the fixed frame %d", fi)
        vars = self.__buildVars(1, fi, ki, fd, st, sl)
        self._thumbnailer.push(buffer, vars)
        self._thumbIndex = 1

    
    def __buildVars(self, thumbIndex, frameIndex, keyIndex,
                           frameDuration, streamTime, streamLength):
        if streamLength and (streamLength > 0):
            percent = int(round(streamTime * 100.0 / streamLength))
            percent = max(min(percent, 100), 0)
        else:
            percent = 0
        seconds = (streamTime + (gst.SECOND / 2)) / gst.SECOND
        minutes = seconds / 60
        hours = minutes / 60
        seconds = seconds % 60
        minutes = minutes % 60
        time = "%02d:%02d:%02d" % (hours, minutes, seconds)
        vars = Variables()
        vars.addVar("frame", frameIndex)
        vars.addVar("key", keyIndex)
        vars.addVar("timestamp", streamTime)
        vars.addVar("percent", percent)
        vars.addVar("seconds", seconds)
        vars.addVar("minutes", minutes)
        vars.addVar("hours", hours)
        vars.addVar("time", time)
        vars.addVar("index", thumbIndex)
        return vars
    

class FrameSampler(BaseSampler):
    
    def __init__(self, logger, thumbnailer, analysis,
                 ensureOne, maxThumb, frames):
        BaseSampler.__init__(self, logger, thumbnailer, analysis,
                             ensureOne,  maxThumb)
        self._period = frames
        self.log("Sample thumbnails each %s frames %s", str(frames),
                 (self._maxThumb and ("to a maximum of %s thumbnails"
                                      % str(self._maxThumb)))
                 or "without limitation")
    
    
    ## Overriden Protected Methods ##
    
    def _onKeepThumbnail(self, thumbIndex, frameIndex, keyIndex,
                         frameDuration, streamTime, streamLength):
        return not (frameIndex % self._period)


class KeyFrameSampler(BaseSampler):
    
    def __init__(self, logger, thumbnailer, analysis,
                 ensureOne, maxThumb, keyFrames):
        BaseSampler.__init__(self, logger, thumbnailer, analysis, 
                             ensureOne, maxThumb)
        self._period = keyFrames
        self.log("Sample thumbnails each %s keyframes %s", str(keyFrames), 
                 (self._maxThumb and ("to a maximum of %s thumbnails"
                                      % str(self._maxThumb)))
                 or "without limitation")
    
    
    ## Overriden Protected Methods ##
    
    def _onKeepThumbnail(self, thumbIndex, frameIndex, keyIndex,
                         frameDuration, streamTime, streamLength):
        return not (keyIndex % self._period)


class TimeSampler(BaseSampler):
    """
    Sample thumbnails periodicaly every specified nanoseconds.
    """
    
    def __init__(self, logger, thumbnailer, analysis,
                 ensureOne, maxThumb, seconds):
        BaseSampler.__init__(self, logger, thumbnailer, analysis,
                             ensureOne, maxThumb)
        self._period = seconds * gst.SECOND
        self.log("Sample thumbnails each %d seconds %s", int(seconds),
                 (self._maxThumb and ("to a maximum of %s thumbnails"
                                      % str(self._maxThumb)))
                 or "without limitation")

        
    ## Overriden Protected Methods ##
    
    def _onKeepThumbnail(self, thumbIndex, frameIndex, keyIndex,
                         frameDuration, streamTime, streamLength):
        # Check if the nanosecond before the frame and the last
        # nanosecond of the frame are in different sections
        start = max(0, streamTime - 1) / self._period
        end = (streamTime + frameDuration) / self._period
        return start != end


class PercentSampler(BaseSampler):

    def __init__(self, logger, thumbnailer, analysis,
                 ensureOne, maxThumb, percents):
        BaseSampler.__init__(self, logger, thumbnailer, analysis,
                             ensureOne, maxThumb)
        if self._streamLength and (self._streamLength > 0): 
            self._period = self._streamLength * percents / 100
            self.log("Setup to creates thumbnails each %s percent of total "
                     "length %s seconds %s", str(percents), 
                     str(self._streamLength / gst.SECOND),
                     (self._maxThumb and ("to a maximum of %s thumbnails"
                                    % str(self._maxThumb)))
                     or "without limitation")
        else:
            self.warning("Cannot generate percent-based thumbnails with a "
                         "source media without known duration, "
                         "falling back to second-based thumbnailing.")
            __pychecker__ = "no-intdivide"
            newMax = max((100 / (int(percents) or 10)) - 1, 1)
            if self._maxThumb:
                newMax = min(self._maxThumb, newMax)
            else:
                newMax = newMax
            fallbackSeconds = compconsts.FALLING_BACK_THUMBS_PERIOD_VALUE
            self._period = fallbackSeconds * gst.SECOND
            self._maxThumb = newMax 
            self.log("Sample thumbnails each %d seconds %s",
                     int(self._period / gst.SECOND),
                     (self._maxThumb and ("to a maximum of %s thumbnails"
                                          % str(self._maxThumb)))
                     or "without limitation")


    ## Overriden Protected Methods ##
    
    def _onKeepThumbnail(self, thumbIndex, frameIndex, keyIndex,
                         frameDuration, streamTime, streamLength):
        # Check if the nanosecond before the frame and the last
        # nanosecond of the frame are in different sections
        start = max(0, streamTime - 1) / self._period
        end = (streamTime + frameDuration) / self._period
        return start != end    
