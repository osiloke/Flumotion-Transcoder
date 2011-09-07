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


import gst

from zope.interface import Interface, implements

from flumotion.inhouse import defer

from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.enums import AudioVideoToleranceEnum
from flumotion.component.transcoder.basetargets import TranscodingTarget
from flumotion.component.transcoder.binmaker import makeMuxerEncodeBin
from flumotion.component.transcoder.binmaker import makeAudioEncodeBin
from flumotion.component.transcoder.binmaker import makeVideoEncodeBin


class AudioTarget(TranscodingTarget):

    def __init__(self, targetContext):
        """
        targetContext's transcoding config should
        have the following attributes:
            audioEncoder
            audioRate
            audioChannels
            muxer
        """
        TranscodingTarget.__init__(self, targetContext)
        self._checkConfAttr("audioEncoder", True)
        self._checkConfAttr("muxer", True)
        self._checkConfAttr("audioRate")
        self._checkConfAttr("audioChannels")


    ## ITranscoderProducer Overriden Methods ##

    def getMonitoredFiles(self):
        return self.getOutputFiles()

    def checkSourceMedia(self, sourcePath, sourceAnalysis):
        if not sourceAnalysis.hasAudio:
            self.raiseError("Source media doesn't have audio stream")
        return True

    def updatePipeline(self, pipeline, analysis, tees, timeout=None):
        tag = self._getTranscodingTag()
        config = self._getTranscodingConfig()
        outputPath = self._getOutputPath()
        audioEncBin = makeAudioEncodeBin(config, analysis, tag,
                                         pipelineInfo=self._pipelineInfo,
                                         logger=self)
        encBin = makeMuxerEncodeBin(outputPath, config, analysis, tag,
                                    audioEncBin, None,
                                    pipelineInfo=self._pipelineInfo,
                                    logger=self)
        pipeline.add(encBin)
        tees['audiosink'].get_pad('src%d').link(encBin.get_pad('audiosink'))
        self._bins["audio-encoder"] = audioEncBin


class VideoTarget(TranscodingTarget):

    def __init__(self, targetContext):
        """
        targetContext's transcoding config should
        have the following attributes:
            videoEncoder
            videoFramerate
            videoPAR
            videoWidth
            videoHeight
            videoMaxWidth
            videoMaxHeight
            videoScaleMethod
            videoWidthMultiple
            videoHeightMultiple
            muxer
        """
        TranscodingTarget.__init__(self, targetContext)
        self._checkConfAttr("videoEncoder", True)
        self._checkConfAttr("muxer", True)
        self._checkConfAttr("videoFramerate")
        self._checkConfAttr("videoPAR")
        self._checkConfAttr("videoWidth")
        self._checkConfAttr("videoHeight")
        self._checkConfAttr("videoMaxWidth")
        self._checkConfAttr("videoMaxHeight")
        self._checkConfAttr("videoWidthMultiple")
        self._checkConfAttr("videoHeightMultiple")
        self._checkConfAttr("videoScaleMethod")


    ## ITranscoderProducer Overriden Methods ##

    def getMonitoredFiles(self):
        return self.getOutputFiles()

    def checkSourceMedia(self, sourcePath, sourceAnalysis):
        if not sourceAnalysis.hasVideo:
            self.raiseError("Source media doesn't have video stream")
        return True

    def updatePipeline(self, pipeline, analysis, tees, timeout=None):
        tag = self._getTranscodingTag()
        config = self._getTranscodingConfig()
        outputPath = self._getOutputPath()
        videoEncBin = makeVideoEncodeBin(config, analysis, tag,
                                         pipelineInfo=self._pipelineInfo,
                                         logger=self)
        encBin = makeMuxerEncodeBin(outputPath, config, analysis, tag,
                                    None, videoEncBin,
                                    pipelineInfo=self._pipelineInfo,
                                    logger=self)
        pipeline.add(encBin)
        tees['videosink'].get_pad('src%d').link(encBin.get_pad('videosink'))
        self._bins["video-encoder"] = videoEncBin


class AudioVideoTarget(TranscodingTarget):

    def __init__(self, targetContext):
        """
        targetContext's transcoding config should
        have the following attributes:
            audioEncoder
            audioRate
            audioChannels
            muxer
            videoEncoder
            videoFramerate
            videoPAR
            videoWidth
            videoHeight
            videoMaxWidth
            videoMaxHeight
            videoWidthMultiple
            videoHeightMultiple
            videoScaleMethod
        """
        TranscodingTarget.__init__(self, targetContext)
        self._checkConfAttr("audioEncoder", True)
        self._checkConfAttr("videoEncoder", True)
        self._checkConfAttr("muxer", True)
        self._checkConfAttr("audioRate")
        self._checkConfAttr("audioChannels")
        self._checkConfAttr("videoFramerate")
        self._checkConfAttr("videoPAR")
        self._checkConfAttr("videoWidth")
        self._checkConfAttr("videoHeight")
        self._checkConfAttr("videoMaxWidth")
        self._checkConfAttr("videoMaxHeight")
        self._checkConfAttr("videoWidthMultiple")
        self._checkConfAttr("videoHeightMultiple")
        self._checkConfAttr("videoScaleMethod")


    ## ITranscoderProducer Overriden Methods ##

    def getMonitoredFiles(self):
        return self.getOutputFiles()

    def checkSourceMedia(self, sourcePath, sourceAnalysis):
        tolerance = self._getTranscodingConfig().tolerance
        if not sourceAnalysis.hasAudio:
            if tolerance == AudioVideoToleranceEnum.allow_without_audio:
                self.info("Source media doesn't have audio stream, "
                          "but we tolerate it")
            else:
                self.raiseError("Source media doesn't have audio stream")
        if not sourceAnalysis.hasVideo:
            if tolerance == AudioVideoToleranceEnum.allow_without_video:
                self.info("Source media doesn't have video stream, "
                          "but we tolerate it")
            else:
                self.raiseError("Source media doesn't have video stream")
        return True

    def updatePipeline(self, pipeline, analysis, tees, timeout=None):
        tag = self._getTranscodingTag()
        config = self._getTranscodingConfig()
        outputPath = self._getOutputPath()
        if analysis.hasAudio:
            audioEncBin = makeAudioEncodeBin(config, analysis, tag,
                                             pipelineInfo=self._pipelineInfo,
                                             logger=self)
        else:
            audioEncBin = None
        if analysis.hasVideo:
            videoEncBin = makeVideoEncodeBin(config, analysis, tag,
                                             pipelineInfo=self._pipelineInfo,
                                             logger=self)
        else:
            videoEncBin = None
        encBin = makeMuxerEncodeBin(outputPath, config, analysis, tag,
                                    audioEncBin, videoEncBin,
                                    pipelineInfo=self._pipelineInfo,
                                    logger=self)
        pipeline.add(encBin)
        if videoEncBin:
            tees['videosink'].get_pad('src%d').link(encBin.get_pad('videosink'))
            self._bins["video-encoder"] = videoEncBin
        if audioEncBin:
            tees['audiosink'].get_pad('src%d').link(encBin.get_pad('audiosink'))
            self._bins["audio-encoder"] = audioEncBin
