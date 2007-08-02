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
from flumotion.transcoder.admin.datastore.basestore import MetaStore

class BaseConfig(object):
    
    __metaclass__ = MetaStore
    
    __getters__ = {"basic": 
                       {"getType":       ("type", None),
                        "getIdentifier": ("identifier", None)}}
    
    def __init__(self, data):
        self._data = data        
        
    def getType(self):
        return self._data.type


class IdentityConfig(BaseConfig):
    
    def __init__(self, data):
        BaseConfig.__init__(self, data)
        

class AudioConfig(BaseConfig):
    """
    muxer (str)
    audioEncoder (str)
    audioRate (str) 
    audioChannels (str)
    """
    
    # MetaStore metaclass will create getters for these properties
    __getters__ = {"basic": 
                      {"getMuxer":         ("muxer", None),
                       "getAudioEncoder":  ("audioEncoder", None),
                       "getAudioRate":     ("audioRate", None),
                       "getAudioChannels": ("audioChannels", None)}}
    
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

    # MetaStore metaclass will create getters for these properties
    __getters__ = {"basic":
                      {"getMuxer":             ("muxer", None),
                       "getVideoEncoder":      ("videoEncoder", None),
                       "getVideoWidth":        ("videoWidth", None),
                       "getVideoHeight":       ("videoHeight", None),
                       "getVideoMaxWidth":     ("videoMaxWidth", None),
                       "getVideoMaxHeight":    ("videoMaxHeight", None),
                       "getVideoPAR":          ("videoPAR", None),
                       "getVideoFramerate":    ("videoFramerate", None),
                       "getVideoScaleMethod":  ("videoScaleMethod", None)}}
    
    def __init__(self, data):
        super(VideoConfig, self).__init__(data)


class AudioVideoConfig(AudioConfig, VideoConfig):
    
    # MetaStore metaclass will create getters for these properties
    __properties__ = {"Tolerance": ("tolerance", None)}
    
    def __init__(self, data):
        super(AudioVideoConfig, self).__init__(data)

    def getTolerance(self):
        return self._data.tolerance        


class ThumbnailsConfig(BaseConfig):
    """
    periodValue (int)
    periodUnit (str) in ['seconds', 'frames', 'keyframes', 'percent']
    maxCount (int)
    format (str) in ['png', 'jpg']
    """    
    
    # MetaStore metaclass will create getters for these properties
    __getters__ = {"basic":
                      {"getThumbsWidth":  ("thumbsWidth", None),
                       "getThumbsHeight": ("thumbsHeight", None),
                       "getPeriodValue":  ("periodValue", None),
                       "getPeriodUnit":   ("periodUnit", None),
                       "getMaxCount":     ("maxCount", None),
                       "getFormat":       ("format", None)}}
    
    def __init__(self, data):
        super(ThumbnailsConfig, self).__init__(data)


_configLookup = {TargetTypeEnum.audio: AudioConfig,
                 TargetTypeEnum.video: VideoConfig,
                 TargetTypeEnum.audiovideo: AudioVideoConfig,
                 TargetTypeEnum.thumbnails: ThumbnailsConfig,
                 TargetTypeEnum.identity: IdentityConfig}

def TargetConfigFactory(data):
    assert data.type in _configLookup
    return _configLookup[data.type](data)
