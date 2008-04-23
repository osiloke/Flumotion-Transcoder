# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import implements

from flumotion.transcoder.enums import TargetTypeEnum
from flumotion.transcoder.admin import interfaces
from flumotion.transcoder.admin.datastore import base


class IConfigStore(base.IBaseStore):
    
    def getCustomerStore(self):
        pass
    
    def getProfileStore(self):
        pass
    
    def getTargetStore(self):
        pass
    
    def getType(self):
        pass


class IIdentityConfigStore(IConfigStore):
    pass


class IAudioConfigStore(IConfigStore):
    
    def getMuxer(self):
        pass

    def getAudioEncoder(self):
        pass
    
    def getAudioRate(self):
        pass
    
    def getAudioChannels(self):
        pass



class IVideoConfigStore(IConfigStore):
    
    def getMuxer(self):
        pass
    
    def getVideoEncoder(self):
        pass
    
    def getVideoWidth(self):
        pass
    
    def getVideoHeight(self):
        pass
    
    def getVideoMaxWidth(self):
        pass
    
    def getVideoMaxHeight(self):
        pass
    
    def getVideoWidthMultiple(self):
        pass
    
    def getVideoHeightMultiple(self):
        pass
    
    def getVideoPAR(self):
        pass
    
    def getVideoFramerate(self):
        pass
    
    def getVideoScaleMethod(self):
        pass


class IAudioVideoConfigStore(IAudioConfigStore, IVideoConfigStore):
    
    def getTolerance(self):
        pass


class IThumbnailsConfigStore(IConfigStore):
    
    def getThumbsWidth(self):
        pass
    
    def getThumbsHeight(self):
        pass
    
    def getPeriodValue(self):
        pass
    
    def getPeriodUnit(self):
        pass
    
    def getMaxCount(self):
        pass
    
    def getEnsureOne(self):
        pass
    
    def getFormat(self):
        pass



class ConfigStore(base.DataStore):
    implements(IConfigStore)
    
    base.genGetter("getType",       "type")
    base.genGetter("getIdentifier", "identifier")

    def __init__(self, targStore, data):
        base.DataStore.__init__(self, targStore, data)
    
    def getAdminStore(self):
        return self.parent.getAdminStore()
    
    def getCustomerStore(self):
        return self.parent.getCustomerStore()
    
    def getProfileStore(self):
        return self.parent.getProfileStore()
    
    def getTargetStore(self):
        return self.parent
    
    def getLabel(self):
        return "%s config" % self.parent.getLabel()


class IdentityConfigStore(ConfigStore):
    implements(IIdentityConfigStore)
    
    def __init__(self, targStore, data):
        super(ConfigStore, self).__init__(targStore, data)
        

class AudioConfigStore(ConfigStore):
    """
    muxer (str)
    audioEncoder (str)
    audioRate (str) 
    audioChannels (str)
    """
    
    implements(IAudioConfigStore)
    
    base.genGetter("getMuxer",         "muxer")
    base.genGetter("getAudioEncoder",  "audioEncoder")
    base.genGetter("getAudioRate",     "audioRate")
    base.genGetter("getAudioChannels", "audioChannels")

    def __init__(self, targStore, data):
        super(AudioConfigStore, self).__init__(targStore, data)
    

class VideoConfigStore(ConfigStore):
    """
    muxer (str)
    videoEncoder (str)
    videoWidth (int)
    videoHeight (int)
    videoMaxWidth (int)
    videoMaxHeight (int)
    videoWidthMultiple (int)
    videoHeightMultiple (int)
    videoPAR (int[2])
    videoFramerate (int[2])
    """
    
    implements(IVideoConfigStore)
    
    base.genGetter("getMuxer",               "muxer")
    base.genGetter("getVideoEncoder",        "videoEncoder")
    base.genGetter("getVideoWidth",          "videoWidth")
    base.genGetter("getVideoHeight",         "videoHeight")
    base.genGetter("getVideoMaxWidth",       "videoMaxWidth")
    base.genGetter("getVideoMaxHeight",      "videoMaxHeight")
    base.genGetter("getVideoWidthMultiple",  "videoWidthMultiple")
    base.genGetter("getVideoHeightMultiple", "videoHeightMultiple")
    base.genGetter("getVideoPAR",            "videoPAR")
    base.genGetter("getVideoFramerate",      "videoFramerate")
    base.genGetter("getVideoScaleMethod",    "videoScaleMethod")
    
    def __init__(self, targStore, data):
        super(VideoConfigStore, self).__init__(targStore, data)


class AudioVideoConfigStore(AudioConfigStore, VideoConfigStore):
    implements(IAudioVideoConfigStore)
    
    base.genGetter("getTolerance", "tolerance")
    
    def __init__(self, targStore, data):
        super(AudioVideoConfigStore, self).__init__(targStore, data)


class ThumbnailsConfigStore(ConfigStore):
    """
    periodValue (int)
    periodUnit (str) in ['seconds', 'frames', 'keyframes', 'percent']
    maxCount (int)
    format (str) in ['png', 'jpg']
    ensureOne (bool)
    """    
    
    implements(IThumbnailsConfigStore)
    
    base.genGetter("getThumbsWidth",  "thumbsWidth")
    base.genGetter("getThumbsHeight", "thumbsHeight")
    base.genGetter("getPeriodValue",  "periodValue")
    base.genGetter("getPeriodUnit",   "periodUnit")
    base.genGetter("getMaxCount",     "maxCount")
    base.genGetter("getEnsureOne",    "ensureOne")
    base.genGetter("getFormat",       "format")
    
    def __init__(self, targStore, data):
        super(ThumbnailsConfigStore, self).__init__(targStore, data)


_configLookup = {TargetTypeEnum.audio:      AudioConfigStore,
                 TargetTypeEnum.video:      VideoConfigStore,
                 TargetTypeEnum.audiovideo: AudioVideoConfigStore,
                 TargetTypeEnum.thumbnails: ThumbnailsConfigStore,
                 TargetTypeEnum.identity:   IdentityConfigStore}

def TargetConfigFactory(targStore, data):
    assert data.type in _configLookup
    return _configLookup[data.type](targStore, data)
