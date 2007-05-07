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


class AudioVideoConfig(AudioConfig, VideoConfig):
    
    def __init__(self, data):
        super(AudioVideoConfig, self).__init__(data)


class ThumbnailsConfig(BaseConfig):
    """
    intervalValue (int)
    intervalUnit (str) in ['seconds', 'frames', 'keyframes', 'percent']
    maxCount (int)
    format (str) in ['png', 'jpg']
    """    
    def __init__(self, data):
        super(ThumbnailsConfig, self).__init__(data)


_classLookup = {TargetTypeEnum.audio: AudioConfig,
                TargetTypeEnum.video: VideoConfig,
                TargetTypeEnum.audiovideo: AudioVideoConfig,
                TargetTypeEnum.thumbnails: ThumbnailsConfig}

def TargetConfig(data):
    assert data.type in _classLookup
    return _classLookup[data.type](data)
