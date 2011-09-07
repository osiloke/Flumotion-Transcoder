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

import datetime

from flumotion.inhouse import properties

from flumotion.transcoder import constants, virtualpath
from flumotion.transcoder.enums import VideoScaleMethodEnum
from flumotion.transcoder.enums import PeriodUnitEnum
from flumotion.transcoder.enums import ThumbOutputTypeEnum
from flumotion.transcoder.enums import TargetTypeEnum
from flumotion.transcoder.enums import AudioVideoToleranceEnum


class CustomerConfig(properties.PropertyBag):
    name = properties.String('name', None, True)


class ProfileConfig(properties.PropertyBag):
    """
        Changes from version 1.0 to 1.1:
            Added temp-reports-dir
    """
    label = properties.String('label', None, True)
    inputDir = virtualpath.VirtualPathProperty('input-dir', None, True)
    outputDir = virtualpath.VirtualPathProperty('output-dir', None, True)
    linkDir = virtualpath.VirtualPathProperty('link-dir', None)
    workDir = virtualpath.VirtualPathProperty('work-dir', None, True)
    tempReportsDir = virtualpath.VirtualPathProperty('temp-reports-dir', None, True)
    failedDir = virtualpath.VirtualPathProperty('failed-dir', None, True)
    failedReportsDir = virtualpath.VirtualPathProperty('failed-reports-dir', None, True)
    doneDir = virtualpath.VirtualPathProperty('done-dir', None, True)
    doneReportsDir = virtualpath.VirtualPathProperty('done-reports-dir', None, True)
    linkTemplate = properties.String('link-template', constants.LINK_TEMPLATE)


class SourceConfig(properties.PropertyBag):
    inputFile = properties.String('input-file', None, True)
    reportTemplate = properties.String('report-template', None, True)
    preProcess = properties.String('pre-process', None)
    cuePoints = properties.String('cue-points', None)


class AudioConfig(properties.PropertyBag):
    audioEncoder = properties.String('audio-encoder', None, True)
    audioResampler = properties.String('audio-resampler', None)
    audioRate = properties.Integer('audio-rate', None, False, True)
    audioChannels = properties.Integer('audio-channels', None, False, True)
    muxer = properties.String('muxer', None, True)


class VideoConfig(properties.PropertyBag):
    videoEncoder = properties.String('video-encoder', None, True)
    videoFramerate = properties.Fraction('video-framerate', None, False, True)
    videoPAR = properties.Fraction('video-par', None, False, True)
    videoWidth = properties.Integer('video-width', None, False, True)
    videoHeight = properties.Integer('video-height', None, False, True)
    videoMaxWidth = properties.Integer('video-maxwidth', None, False, True)
    videoMaxHeight = properties.Integer('video-maxheight', None, False, True)
    videoWidthMultiple = properties.Integer('video-width-multiple', None, False, True)
    videoHeightMultiple = properties.Integer('video-height-multiple', None, False, True)
    videoScaleMethod = properties.Enum('video-scale-method',
                                       VideoScaleMethodEnum,
                                       VideoScaleMethodEnum.height)
    muxer = properties.String('muxer', None, True)


class AudioVideoConfig(AudioConfig, VideoConfig):
    tolerance = properties.Enum('tolerance',
                                AudioVideoToleranceEnum,
                                AudioVideoToleranceEnum.strict)

class ThumbnailsConfig(properties.PropertyBag):
    periodValue = properties.Integer('period-value', None, True, True)
    thumbsWidth = properties.Integer('thumbs-width', None, False, True)
    thumbsHeight = properties.Integer('thumbs-height', None, False, True)
    periodUnit = properties.Enum('period-unit',
                                   PeriodUnitEnum,
                                   PeriodUnitEnum.seconds)
    maxCount = properties.Integer('max-count', 1, False, True)
    outputFormat = properties.Enum('output-format',
                                   ThumbOutputTypeEnum,
                                   ThumbOutputTypeEnum.jpg)
    ensureOne = properties.Boolean('ensure-one', True)


class TargetConfig(properties.PropertyBag):
    label = properties.String('label', None, True)
    type = properties.Enum('type', TargetTypeEnum, None, True)
    outputFile = properties.String('output-file', None, True)
    outputDir = virtualpath.VirtualPathProperty('output-dir', None)
    linkDir = virtualpath.VirtualPathProperty('link-dir', None)
    workDir = virtualpath.VirtualPathProperty('work-dir', None)
    linkFile = properties.String('link-file', None, False)
    postProcess = properties.String('post-process', None)
    linkUrlPrefix = properties.String('link-url-prefix', None)
    config = properties.DynEnumChild('config', 'type',
                                     {TargetTypeEnum.audio: AudioConfig,
                                      TargetTypeEnum.video: VideoConfig,
                                      TargetTypeEnum.audiovideo: AudioVideoConfig,
                                      TargetTypeEnum.thumbnails: ThumbnailsConfig,
                                      TargetTypeEnum.identity: None})


class TranscodingConfig(properties.RootPropertyBag):

    VERSION = (1,1)

    creationTime = properties.DateTime('creation-time')
    transcodingTimeout = properties.Integer('transcoding-timeout', 4)
    postProcessTimeout = properties.Integer('post-process-timeout', 60)
    preProcessTimeout = properties.Integer('pre-process-timeout', 60)
    customer = properties.Child('customer', CustomerConfig)
    profile = properties.Child('profile', ProfileConfig)
    source = properties.Child('source', SourceConfig)
    targets = properties.ChildDict('targets', TargetConfig)

    def touch(self):
        self.creationTime = datetime.datetime.now()

