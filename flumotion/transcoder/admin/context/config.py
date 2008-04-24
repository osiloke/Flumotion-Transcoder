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

import datetime

from flumotion.transcoder.admin.context import base
from flumotion.transcoder.admin.datastore import config


class IConfigContext(base.IBaseStoreContext):
    
    def getStoreContext(self):
        pass
    
    def getCustomerContext(self):
        pass
    
    def getProfileContext(self):
        pass
    
    def getTargetContext(self):
        pass

    def getType(self):
        pass


class IIdentityConfigContext(IConfigContext):
    pass


class IAudioConfigContext(IConfigContext):
    
    def getMuxer(self):
        pass

    def getAudioEncoder(self):
        pass
    
    def getAudioRate(self):
        pass
    
    def getAudioChannels(self):
        pass


class IVideoConfigContext(IConfigContext):
    
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


class IAudioVideoConfigContext(IAudioConfigContext, IVideoConfigContext):
    
    def getTolerance(self):
        pass


class IThumbnailsConfigContext(IConfigContext):
    
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


class ConfigContext(base.BaseStoreContext):

    implements(IConfigContext)

    base.genStoreProxy("getType")
    base.genStoreProxy("getIdentifier")

    def __init__(self, targCtx, confStore):
        base.BaseStoreContext.__init__(self, targCtx, confStore)

    def getAdminContext(self):
        return self.parent.getAdminContext()
    
    def getStoreContext(self):
        return self.parent.getStoreContext()
    
    def getCustomerContext(self):
        return self.parent.getCustomerContext()
    
    def getProfileContext(self):
        return self.parent.getProfileContext()
    
    def getTargetContext(self):
        return self.parent
       

class IdentityConfigContext(ConfigContext):
    
    implements(IIdentityConfigContext)
    
    def __init__(self, targCtx, confStore):
        ConfigContext.__init__(self, targCtx, confStore)


class ThumbnailsConfigContext(ConfigContext):

    implements(IThumbnailsConfigContext)

    base.genStoreProxy("getThumbsWidth")
    base.genStoreProxy("getThumbsHeight")
    base.genStoreProxy("getPeriodValue")
    base.genStoreProxy("getPeriodUnit")
    base.genStoreProxy("getMaxCount")
    base.genStoreProxy("getEnsureOne")
    base.genStoreProxy("getFormat")
    
    def __init__(self, targCtx, confStore):
        ConfigContext.__init__(self, targCtx, confStore)


class AudioConfigContext(ConfigContext):
    
    implements(IAudioConfigContext)
    
    base.genStoreProxy("getMuxer")
    base.genStoreProxy("getAudioEncoder")
    base.genStoreProxy("getAudioRate")
    base.genStoreProxy("getAudioChannels")
    
    def __init__(self, targCtx, confStore):
        ConfigContext.__init__(self, targCtx, confStore)


class VideoConfigContext(ConfigContext):

    implements(IVideoConfigContext)

    base.genStoreProxy("getMuxer")
    base.genStoreProxy("getVideoEncoder")
    base.genStoreProxy("getVideoWidth")
    base.genStoreProxy("getVideoHeight")
    base.genStoreProxy("getVideoMaxWidth")
    base.genStoreProxy("getVideoMaxHeight")
    base.genStoreProxy("getVideoWidthMultiple")
    base.genStoreProxy("getVideoHeightMultiple")
    base.genStoreProxy("getVideoPAR")
    base.genStoreProxy("getVideoFramerate")
    base.genStoreProxy("getVideoScaleMethod")
    
    def __init__(self, targCtx, confStore):
        ConfigContext.__init__(self, targCtx, confStore)


class AudioVideoConfigContext(ConfigContext):

    implements(IAudioVideoConfigContext)

    base.genStoreProxy("getMuxer")
    base.genStoreProxy("getAudioEncoder")
    base.genStoreProxy("getAudioRate")
    base.genStoreProxy("getAudioChannels")
    base.genStoreProxy("getVideoEncoder")
    base.genStoreProxy("getVideoWidth")
    base.genStoreProxy("getVideoHeight")
    base.genStoreProxy("getVideoMaxWidth")
    base.genStoreProxy("getVideoMaxHeight")
    base.genStoreProxy("getVideoWidthMultiple")
    base.genStoreProxy("getVideoHeightMultiple")
    base.genStoreProxy("getVideoPAR")
    base.genStoreProxy("getVideoFramerate")
    base.genStoreProxy("getVideoScaleMethod")
    base.genStoreProxy("getTolerance")
        
    def __init__(self, targCtx, confStore):
        ConfigContext.__init__(self, targCtx, confStore)


def ConfigContextFactory(parentCtx, confStore):
    return _contextLookup[type(confStore)](parentCtx, confStore)


## Private ##

_contextLookup = {config.IdentityConfigStore:   IdentityConfigContext,
                  config.ThumbnailsConfigStore: ThumbnailsConfigContext,
                  config.AudioConfigStore:      AudioConfigContext,
                  config.VideoConfigStore:      VideoConfigContext,
                  config.AudioVideoConfigStore: AudioVideoConfigContext}
