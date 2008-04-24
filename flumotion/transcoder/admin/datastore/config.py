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
    
    base.readonly_proxy("type")

    def __init__(self, targStore, data):
        label = "%s config" % targStore.label
        base.DataStore.__init__(self, targStore, data, label=label)
    
    def getAdminStore(self):
        return self.parent.getAdminStore()
    
    def getCustomerStore(self):
        return self.parent.getCustomerStore()
    
    def getProfileStore(self):
        return self.parent.getProfileStore()
    
    def getTargetStore(self):
        return self.parent


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
    
    base.readonly_proxy("muxer")
    base.readonly_proxy("audioEncoder")
    base.readonly_proxy("audioRate")
    base.readonly_proxy("audioChannels")

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
    
    base.readonly_proxy("muxer")
    base.readonly_proxy("videoEncoder")
    base.readonly_proxy("videoWidth")
    base.readonly_proxy("videoHeight")
    base.readonly_proxy("videoMaxWidth")
    base.readonly_proxy("videoMaxHeight")
    base.readonly_proxy("videoWidthMultiple")
    base.readonly_proxy("videoHeightMultiple")
    base.readonly_proxy("videoPAR")
    base.readonly_proxy("videoFramerate")
    base.readonly_proxy("videoScaleMethod")
    
    def __init__(self, targStore, data):
        super(VideoConfigStore, self).__init__(targStore, data)


class AudioVideoConfigStore(AudioConfigStore, VideoConfigStore):
    implements(IAudioVideoConfigStore)
    
    base.readonly_proxy("tolerance")
    
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
    
    base.readonly_proxy("thumbsWidth")
    base.readonly_proxy("thumbsHeight")
    base.readonly_proxy("periodValue")
    base.readonly_proxy("periodUnit")
    base.readonly_proxy("maxCount")
    base.readonly_proxy("ensureOne")
    base.readonly_proxy("format")
    
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
