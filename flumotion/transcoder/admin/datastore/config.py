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

from zope.interface import implements, Attribute

from flumotion.transcoder.enums import TargetTypeEnum
from flumotion.transcoder.admin import interfaces
from flumotion.transcoder.admin.datastore import base


class IConfigStore(base.IBaseStore):

    type = Attribute("The type of taget config")

    def getCustomerStore(self):
        pass

    def getProfileStore(self):
        pass

    def getTargetStore(self):
        pass


class IIdentityConfigStore(IConfigStore):
    pass


class IAudioConfigStore(IConfigStore):

    muxer         = Attribute("Muxing pipeline")
    audioEncoder  = Attribute("Audio encoding pipeline")
    audioResampler= Attribute("Audio resampler")
    audioRate     = Attribute("Audio rate")
    audioChannels = Attribute("Audio channels count")


class IVideoConfigStore(IConfigStore):

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


class IAudioVideoConfigStore(IAudioConfigStore, IVideoConfigStore):

    tolerance = Attribute("Audio/Video tolerance")


class IThumbnailsConfigStore(IConfigStore):

    thumbsWidth  = Attribute("Thumbnails width")
    thumbsHeight = Attribute("Thumbnails height")
    periodValue  = Attribute("Period between thumbnails snapshots")
    periodUnit   = Attribute("Unit of the snapshot period value")
    maxCount     = Attribute("Maximum number of snapshots to take")
    ensureOne    = Attribute("Ensure they will be at least on thumbnail")
    format       = Attribute("Thumbnails image format")


class ConfigStore(base.DataStore):
    implements(IConfigStore)

    type = base.ReadOnlyProxy("type")

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
    audioResampler (str)
    audioRate (str)
    audioChannels (str)
    """

    implements(IAudioConfigStore)

    muxer         = base.ReadOnlyProxy("muxer")
    audioEncoder  = base.ReadOnlyProxy("audioEncoder")
    audioResampler= base.ReadOnlyProxy("audioResampler")
    audioRate     = base.ReadOnlyProxy("audioRate")
    audioChannels = base.ReadOnlyProxy("audioChannels")

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

    muxer               = base.ReadOnlyProxy("muxer")
    videoEncoder        = base.ReadOnlyProxy("videoEncoder")
    videoWidth          = base.ReadOnlyProxy("videoWidth")
    videoHeight         = base.ReadOnlyProxy("videoHeight")
    videoMaxWidth       = base.ReadOnlyProxy("videoMaxWidth")
    videoMaxHeight      = base.ReadOnlyProxy("videoMaxHeight")
    videoWidthMultiple  = base.ReadOnlyProxy("videoWidthMultiple")
    videoHeightMultiple = base.ReadOnlyProxy("videoHeightMultiple")
    videoPAR            = base.ReadOnlyProxy("videoPAR")
    videoFramerate      = base.ReadOnlyProxy("videoFramerate")
    videoScaleMethod    = base.ReadOnlyProxy("videoScaleMethod")

    def __init__(self, targStore, data):
        super(VideoConfigStore, self).__init__(targStore, data)


class AudioVideoConfigStore(AudioConfigStore, VideoConfigStore):
    implements(IAudioVideoConfigStore)

    tolerance = base.ReadOnlyProxy("tolerance")

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

    thumbsWidth  = base.ReadOnlyProxy("thumbsWidth")
    thumbsHeight = base.ReadOnlyProxy("thumbsHeight")
    periodValue  = base.ReadOnlyProxy("periodValue")
    periodUnit   = base.ReadOnlyProxy("periodUnit")
    maxCount     = base.ReadOnlyProxy("maxCount")
    ensureOne    = base.ReadOnlyProxy("ensureOne")
    format       = base.ReadOnlyProxy("format")

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
