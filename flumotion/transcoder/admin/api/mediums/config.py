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

from zope.interface import implements

from flumotion.transcoder.admin.context import config
from flumotion.transcoder.admin.api import interfaces, api  


class BaseConfigMedium(api.Medium):
    
    implements(interfaces.IConfigMedium)
    
    api.readonly_store_property("type")
    
    def __init__(self, confCtx):
        super(BaseConfigMedium, self).__init__(confCtx)


class IdentityConfigMedium(BaseConfigMedium):

    implements(interfaces.IIdentityConfigMedium)
    
    api.register_medium(interfaces.IIdentityConfigMedium,
                        config.IIdentityConfigContext)
    
    def __init__(self, confCtx):
        super(IdentityConfigMedium, self).__init__(confCtx)


class AudioConfigMedium(BaseConfigMedium):
    
    implements(interfaces.IAudioConfigMedium)
    
    api.register_medium(interfaces.IAudioConfigMedium,
                        config.IAudioConfigContext)
    
    api.readonly_store_property("muxer")
    api.readonly_store_property("audioEncoder")
    api.readonly_store_property("audioRate")
    api.readonly_store_property("audioChannels")

    def __init__(self, confCtx):
        super(AudioConfigMedium, self).__init__(confCtx)


class VideoConfigMedium(BaseConfigMedium):
    
    implements(interfaces.IVideoConfigMedium)
    
    api.register_medium(interfaces.IVideoConfigMedium,
                        config.IVideoConfigContext)

    api.readonly_store_property("muxer")
    api.readonly_store_property("videoEncoder")
    api.readonly_store_property("videoWidth")
    api.readonly_store_property("videoHeight")
    api.readonly_store_property("videoMaxWidth")
    api.readonly_store_property("videoMaxHeight")
    api.readonly_store_property("videoWidthMultiple")
    api.readonly_store_property("videoHeightMultiple")
    api.readonly_store_property("videoPAR")
    api.readonly_store_property("videoFramerate")
    api.readonly_store_property("videoScaleMethod")
    
    def __init__(self, confCtx):
        super(VideoConfigMedium, self).__init__(confCtx)


class AudioVideoConfigMedium(AudioConfigMedium, VideoConfigMedium):
    
    implements(interfaces.IAudioVideoConfigMedium)
    
    api.register_medium(interfaces.IAudioVideoConfigMedium,
                        config.IAudioVideoConfigContext)
    
    api.readonly_store_property("tolerance")
    
    def __init__(self, confCtx):
        super(AudioVideoConfigMedium, self).__init__(confCtx)


class ThumbnailsConfigMedium(BaseConfigMedium):
    
    implements(interfaces.IThumbnailsConfigMedium)
    
    api.register_medium(interfaces.IThumbnailsConfigMedium,
                        config.IThumbnailsConfigContext)
    
    api.readonly_store_property("thumbsWidth")
    api.readonly_store_property("thumbsHeight")
    api.readonly_store_property("periodValue")
    api.readonly_store_property("periodUnit")
    api.readonly_store_property("maxCount")
    api.readonly_store_property("ensureOne")
    api.readonly_store_property("format")
    
    def __init__(self, confCtx):
        super(ThumbnailsConfigMedium, self).__init__(confCtx)
