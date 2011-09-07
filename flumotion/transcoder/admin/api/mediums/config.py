# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007,2008,2009 Fluendo, S.L.
# Copyright (C) 2010,2011 Flumotion Services, S.A.
# All rights reserved.
#
# This file may be distributed and/or modified under the terms of
# the GNU Lesser General Public License version 2.1 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.LGPL" in the source distribution for more information.
#
# Headers in this file shall remain intact.

from zope.interface import implements

from flumotion.transcoder.admin.datastore import config
from flumotion.transcoder.admin.api import interfaces, api


class BaseConfigMedium(api.Medium):

    implements(interfaces.IConfigMedium)

    api.readonly_property("type")

    def __init__(self, confStore):
        super(BaseConfigMedium, self).__init__(confStore)


class IdentityConfigMedium(BaseConfigMedium):

    implements(interfaces.IIdentityConfigMedium)

    api.register_medium(interfaces.IIdentityConfigMedium,
                        config.IIdentityConfigStore)

    def __init__(self, confStore):
        super(IdentityConfigMedium, self).__init__(confStore)


class AudioConfigMedium(BaseConfigMedium):

    implements(interfaces.IAudioConfigMedium)

    api.register_medium(interfaces.IAudioConfigMedium,
                        config.IAudioConfigStore)

    api.readonly_property("muxer")
    api.readonly_property("audioEncoder")
    api.readonly_property("audioRate")
    api.readonly_property("audioChannels")

    def __init__(self, confStore):
        super(AudioConfigMedium, self).__init__(confStore)


class VideoConfigMedium(BaseConfigMedium):

    implements(interfaces.IVideoConfigMedium)

    api.register_medium(interfaces.IVideoConfigMedium,
                        config.IVideoConfigStore)

    api.readonly_property("muxer")
    api.readonly_property("videoEncoder")
    api.readonly_property("videoWidth")
    api.readonly_property("videoHeight")
    api.readonly_property("videoMaxWidth")
    api.readonly_property("videoMaxHeight")
    api.readonly_property("videoWidthMultiple")
    api.readonly_property("videoHeightMultiple")
    api.readonly_property("videoPAR")
    api.readonly_property("videoFramerate")
    api.readonly_property("videoScaleMethod")

    def __init__(self, confStore):
        super(VideoConfigMedium, self).__init__(confStore)


class AudioVideoConfigMedium(AudioConfigMedium, VideoConfigMedium):

    implements(interfaces.IAudioVideoConfigMedium)

    api.register_medium(interfaces.IAudioVideoConfigMedium,
                        config.IAudioVideoConfigStore)

    api.readonly_property("tolerance")

    def __init__(self, confStore):
        super(AudioVideoConfigMedium, self).__init__(confStore)


class ThumbnailsConfigMedium(BaseConfigMedium):

    implements(interfaces.IThumbnailsConfigMedium)

    api.register_medium(interfaces.IThumbnailsConfigMedium,
                        config.IThumbnailsConfigStore)

    api.readonly_property("thumbsWidth")
    api.readonly_property("thumbsHeight")
    api.readonly_property("periodValue")
    api.readonly_property("periodUnit")
    api.readonly_property("maxCount")
    api.readonly_property("ensureOne")
    api.readonly_property("format")

    def __init__(self, confStore):
        super(ThumbnailsConfigMedium, self).__init__(confStore)
