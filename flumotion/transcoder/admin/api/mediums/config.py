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

from flumotion.transcoder.admin.datastore import config
from flumotion.transcoder.admin.api import interfaces, api  


class BaseConfigMedium(api.Medium):
    implements(interfaces.IConfigMedium)
    
    def __init__(self, configStore):
        self._reference = configStore
    
    
    ## IConfigMedium Methodes ##

    @api.remote()
    def getType(self):
        return self._reference.type


class IdentityConfigMedium(BaseConfigMedium):
    implements(interfaces.IIdentityConfigMedium)
    api.registerMedium(interfaces.IIdentityConfigMedium,
                       config.IIdentityConfigStore)
    
    def __init__(self, config):
        BaseConfigMedium.__init__(self, config)
    
    
    ## IIdentityConfigMedium Methodes ##


class AudioConfigMedium(BaseConfigMedium):
    implements(interfaces.IAudioConfigMedium)
    api.registerMedium(interfaces.IAudioConfigMedium,
                       config.IAudioConfigStore)
    
    def __init__(self, config):
        BaseConfigMedium.__init__(self, config)
    
    
    ## IAudioConfigMedium Methodes ##


class VideoConfigMedium(BaseConfigMedium):
    implements(interfaces.IVideoConfigMedium)
    api.registerMedium(interfaces.IVideoConfigMedium,
                       config.IVideoConfigStore)
    
    def __init__(self, config):
        BaseConfigMedium.__init__(self, config)
    
    
    ## IVideoConfigMedium Methodes ##


class AudioVideoConfigMedium(AudioConfigMedium, VideoConfigMedium):
    implements(interfaces.IAudioVideoConfigMedium)
    api.registerMedium(interfaces.IAudioVideoConfigMedium,
                       config.IAudioVideoConfigStore)
    
    def __init__(self, config):
        AudioConfigMedium.__init__(self, config)
        VideoConfigMedium.__init__(self, config)
    
    
    ## IAudioVideoConfigMedium Methodes ##


class ThumbnailsConfigMedium(BaseConfigMedium):
    implements(interfaces.IThumbnailsConfigMedium)
    api.registerMedium(interfaces.IThumbnailsConfigMedium,
                       config.IThumbnailsConfigStore)
    
    def __init__(self, config):
        BaseConfigMedium.__init__(self, config)
    
    
    ## IThumbnailsConfigMedium Methodes ##
