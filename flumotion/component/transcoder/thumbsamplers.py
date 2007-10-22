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

from flumotion.transcoder.substitution import Variables
from flumotion.component.transcoder.thumbsink import IThumbnailSampler


class IThumbnailer(Interface):
    
    def push(self, buffer, vars):
        pass


class BaseSampler(object):
    """
    The thumbnail template variables:
        %(frame)d  => frame number (starting at 1)
        %(keyframe)d  => keyframe number (starting at 1)
        %(index)d  => index of the thumbnail (starting at 1)
        %(timestamp)d => timestamp of the thumbnail
        %(time)s => composed time of the thumbnail, 
                    like %(hours)02d:%(minutes)02d:%(seconds)02d
        %(hours)d => hours from start
        %(minutes)d => minutes from start
        %(seconds)d => seconds from start
    """
    
    implements(IThumbnailSampler)
    
    def __init__(self, thumbnailer, max, length):
        assert IThumbnailer.providedBy(thumbnailer)
        self._thumbnailer = thumbnailer
        self._thumbMax = max
        self._length = length
        self._frameCount = 0
        self._keyFrameCount = 0
        self._thumbIndex = 0
        self._frameTime = 0
        self._frameDuration = 0

    
    ## IThumbnailSampler Methods ##
    
    def prepare(self, startTime):
        self._doPrepare(startTime)
        
    def update(self, streamTime, buffer):
        if self._thumbIndex >= self._thumbMax: return
        self._frameCount += 1
        self._frameTime = streamTime
        if not buffer.flag_is_set(gst.BUFFER_FLAG_DELTA_UNIT):
            self._keyFrameCount += 1
        self._frameDuration = None
        if buffer.duration != gst.CLOCK_TIME_NONE:
            self._frameDuration = buffer.duration
        if self._onKeepThumbnail():
            self._thumbIndex += 1
            vars = self.__getThumbnailVars()
            self.__push(buffer, vars)

    def finalize(self):
        self._doFinalize()


    ## Protected Virtual Methods ##
    
    def _doPrepare(self, startTime):
        pass
    
    def _onKeepThumbnail(self):
        return False
    
    def _doFinalize(self):
        pass


    ## Private Methods ##
    
    def __getThumbnailVars(self):
        if self._length:
            percent = int(round(self._frameTime * 100.0 / self._length))
            percent = max(min(percent, 100), 0)
        else:
            percent = 0
        seconds = (self._frameTime + (gst.SECOND / 2)) / gst.SECOND
        minutes = seconds / 60
        hours = minutes / 60
        seconds = seconds % 60
        minutes = minutes % 60
        time = "%02d:%02d:%02d" % (hours, minutes, seconds)
        vars = Variables()
        vars.addVar("frame", self._frameCount)
        vars.addVar("keyframe", self._keyFrameCount)
        vars.addVar("timestamp", self._frameTime)
        vars.addVar("percent", percent)
        vars.addVar("seconds", seconds)
        vars.addVar("minutes", minutes)
        vars.addVar("hours", hours)
        vars.addVar("time", time)
        vars.addVar("index", self._thumbIndex)
        return vars
    
    def __push(self, data, vars):
        self._thumbnailer.push(data, vars)
    

class FrameSampler(BaseSampler):
    
    def __init__(self, thumbnailer, max, length, period):
        BaseSampler.__init__(self, thumbnailer, max, length)
        self._period = period
    
    
    ## Overriden Protected Methods ##
    
    def _onKeepThumbnail(self):
        return not (self._frameCount % self._period)


class KeyFrameSampler(BaseSampler):
    
    def __init__(self, thumbnailer, max, length, period):
        BaseSampler.__init__(self, thumbnailer, max, length)
        self._period = period
    
    
    ## Overriden Protected Methods ##
    
    def _onKeepThumbnail(self):
        return not (self._keyFrameCount % self._period)


class TimeSampler(BaseSampler):
    """
    Sample thumbnails periodicaly every specified nanoseconds.
    """
    
    def __init__(self, thumbnailer, max, length, period):
        BaseSampler.__init__(self, thumbnailer, max, length)
        self._period = period # in nanoseconds
        self._lastTime = None
        
    ## Overriden Protected Methods ##
    
    def _onKeepThumbnail(self):
        if self._frameDuration != None:
            # Do the correct calculation
            # The delta is to prevent keeping a fram when
            # (streameTime + frameDuration) % period == 0
            # because the next frame is more relevant
            delta = self._frameDuration / 10
            t = max(0, self._frameTime - delta)
            start = t / self._period
            end = (t + self._frameDuration) / self._period
            self._lastTime = self._frameTime
            return start != end
        elif self._lastTime != None:
            # Do an aproximation using the last frame stream time
            # It will keep the frame just after the correct one
            start = self._lastTime / self._period
            end = self._frameTime / self._period
            self._lastTime = self._frameTime
            return start != end
        return False


class PercentSampler(TimeSampler):

    def __init__(self, thumbnailer, max, length, period):
        assert length and (length > 0)
        TimeSampler.__init__(self, thumbnailer, max, length, length * period / 100)
