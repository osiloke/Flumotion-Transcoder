# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder.enums import TargetTypeEnum


class BaseConfig(object):
    
    def __init__(self, data):
        self._data = data        


class AudioConfig(BaseConfig):
    """
    muxer (str)
    audioEncoder (str)
    audioRate (str) 
    audioChannels (str)
    """
    def __init__(self, data):
        super(AudioConfig, self).__init__(data)
    
    def getMuxer(self):
        return self._data.muxer
    
    def getAudioEncoder(self):
        return self._data.audioEncoder
    
    def getAudioRate(self):
        return self._data.audioRate
    
    def getAudioChannels(self):
        return self._data.audioChannels


class VideoConfig(BaseConfig):
    """
    muxer (str)
    videoEncoder (str)
    videoWidth (int)
    videoHeight (int)
    videoMaxWidth (int)
    videoMaxHeight (int)
    videoPAR (int[2])
    videoFramerate (int[2])
    """
    def __init__(self, data):
        super(VideoConfig, self).__init__(data)

    def getMuxer(self):
        return self._data.muxer
    
    def getVideoEncoder(self):
        return self._data.videoEncoder
    
    def getVideoWidth(self):
        return self._data.videoWidth
    
    def getVideoHeight(self):
        return self._data.videoHeight
    
    def getVideoMaxWidth(self):
        return self._data.videoMaxWidth
    
    def getVideoMaxHeight(self):
        return self._data.videoMaxHeight
    
    def getVideoPAR(self):
        return self._data.videoPAR
    
    def getVideoFramerate(self):
        return self._data.videoFramerate
    
    def getScaleMethod(self):
        return self._data.scaleMethod


class AudioVideoConfig(AudioConfig, VideoConfig):
    
    def __init__(self, data):
        super(AudioVideoConfig, self).__init__(data)


class ThumbnailsConfig(BaseConfig):
    """
    periodValue (int)
    periodUnit (str) in ['seconds', 'frames', 'keyframes', 'percent']
    maxCount (int)
    format (str) in ['png', 'jpg']
    """    
    def __init__(self, data):
        super(ThumbnailsConfig, self).__init__(data)

    def getThumbsWidth(self):
        return self._data.thumbsWidth
    
    def getThumbsHeight(self):
        return self._data.thumbsHeight
    
    def getPeriodValue(self):
        return self._data.periodValue
    
    def getPeriodUnit(self):
        return self._data.periodUnit
    
    def getMaxCount(self):
        return self._data.maxCount
    
    def getFormat(self):
        return self._data.format


_classLookup = {TargetTypeEnum.audio: AudioConfig,
                TargetTypeEnum.video: VideoConfig,
                TargetTypeEnum.audiovideo: AudioVideoConfig,
                TargetTypeEnum.thumbnails: ThumbnailsConfig}

def TargetConfig(data):
    assert data.type in _classLookup
    return _classLookup[data.type](data)
