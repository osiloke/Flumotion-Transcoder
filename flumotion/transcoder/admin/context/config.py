# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import implements, Attribute

from flumotion.transcoder.admin.context import base
from flumotion.transcoder.admin.datastore import config


class IConfigContext(base.IBaseStoreContext):

    type = Attribute("The type of taget config")

    def getStoreContext(self):
        pass

    def getCustomerContext(self):
        pass

    def getProfileContext(self):
        pass

    def getTargetContext(self):
        pass


class IIdentityConfigContext(IConfigContext):
    pass


class IAudioConfigContext(IConfigContext):

    muxer         = Attribute("Muxing pipeline")
    audioEncoder  = Attribute("Audio encoding pipeline")
    audioResampler= Attribute("Audio resampler")
    audioRate     = Attribute("Audio rate")
    audioChannels = Attribute("Audio channels count")


class IVideoConfigContext(IConfigContext):

    muxer               = Attribute("Muxing pipeline")
    videoEncoder        = Attribute("Video encoding pipeline")
    videoWidth          = Attribute("Video width")
    videoHeight         = Attribute("Video height")
    videoMaxWidth       = Attribute("Video maximum width")
    videoMaxHeight      = Attribute("Video maximum height")
    videoWidthMultiple  = Attribute("Video width multiple")
    videoHeightMultiple = Attribute("Video height multiple")
    videoPAR            = Attribute("Video pixel-aspect-ratio")
    videoFramerate      = Attribute("Video frame-rate")
    videoScaleMethod    = Attribute("Video scalling method")


class IAudioVideoConfigContext(IAudioConfigContext, IVideoConfigContext):

    tolerance = Attribute("Audio/Video tolerance")


class IThumbnailsConfigContext(IConfigContext):

    thumbsWidth  = Attribute("Thumbnails' width")
    thumbsHeight = Attribute("Thumbnails' height")
    periodValue  = Attribute("Period between thumbnails snapshots")
    periodUnit   = Attribute("Unit of the snapshot period value")
    maxCount     = Attribute("Maximum number of snapshots to take")
    ensureOne    = Attribute("Ensure they will be at least on thumbnail")
    format       = Attribute("Thumbnails image format")


class ConfigContext(base.BaseStoreContext):

    implements(IConfigContext)

    type = base.StoreProxy("type")

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

    thumbsWidth  = base.StoreProxy("thumbsWidth")
    thumbsHeight = base.StoreProxy("thumbsHeight")
    periodValue  = base.StoreProxy("periodValue")
    periodUnit   = base.StoreProxy("periodUnit")
    maxCount     = base.StoreProxy("maxCount")
    ensureOne    = base.StoreProxy("ensureOne")
    format       = base.StoreProxy("format")

    def __init__(self, targCtx, confStore):
        ConfigContext.__init__(self, targCtx, confStore)


class AudioConfigContext(ConfigContext):

    implements(IAudioConfigContext)

    muxer         = base.StoreProxy("muxer")
    audioEncoder  = base.StoreProxy("audioEncoder")
    audioResampler= base.StoreProxy("audioResampler")
    audioRate     = base.StoreProxy("audioRate")
    audioChannels = base.StoreProxy("audioChannels")

    def __init__(self, targCtx, confStore):
        ConfigContext.__init__(self, targCtx, confStore)


class VideoConfigContext(ConfigContext):

    implements(IVideoConfigContext)

    muxer               = base.StoreProxy("muxer")
    videoEncoder        = base.StoreProxy("videoEncoder")
    videoWidth          = base.StoreProxy("videoWidth")
    videoHeight         = base.StoreProxy("videoHeight")
    videoMaxWidth       = base.StoreProxy("videoMaxWidth")
    videoMaxHeight      = base.StoreProxy("videoMaxHeight")
    videoWidthMultiple  = base.StoreProxy("videoWidthMultiple")
    videoHeightMultiple = base.StoreProxy("videoHeightMultiple")
    videoPAR            = base.StoreProxy("videoPAR")
    videoFramerate      = base.StoreProxy("videoFramerate")
    videoScaleMethod    = base.StoreProxy("videoScaleMethod")

    def __init__(self, targCtx, confStore):
        ConfigContext.__init__(self, targCtx, confStore)


class AudioVideoConfigContext(ConfigContext):

    implements(IAudioVideoConfigContext)

    muxer               = base.StoreProxy("muxer")
    audioEncoder        = base.StoreProxy("audioEncoder")
    audioResampler      = base.StoreProxy("audioResampler")
    audioRate           = base.StoreProxy("audioRate")
    audioChannels       = base.StoreProxy("audioChannels")
    videoEncoder        = base.StoreProxy("videoEncoder")
    videoWidth          = base.StoreProxy("videoWidth")
    videoHeight         = base.StoreProxy("videoHeight")
    videoMaxWidth       = base.StoreProxy("videoMaxWidth")
    videoMaxHeight      = base.StoreProxy("videoMaxHeight")
    videoWidthMultiple  = base.StoreProxy("videoWidthMultiple")
    videoHeightMultiple = base.StoreProxy("videoHeightMultiple")
    videoPAR            = base.StoreProxy("videoPAR")
    videoFramerate      = base.StoreProxy("videoFramerate")
    videoScaleMethod    = base.StoreProxy("videoScaleMethod")
    tolerance           = base.StoreProxy("tolerance")

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
