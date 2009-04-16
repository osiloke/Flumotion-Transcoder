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

import gst

from flumotion.inhouse import log

from flumotion.component.transcoder import videosize
from flumotion.component.transcoder import gstutils

DEFAULT_WIDTH_MULTIPLE = 2
DEFAULT_HEIGHT_MULTIPLE = 2

def makeMuxerEncodeBin(file, config, analysis, tag,
                       audioEncodeBin, videoEncodeBin,
                       pipelineInfo=None, logger=None):
    logger = logger or log
    pipelineParts = list()
    encBin = gst.Bin("encoding-%s" % tag)

    # muxer elements
    muxer = gst.parse_launch(config.muxer)
    pipelineParts.extend(map(str.strip, config.muxer.split('!')))

    # filesink element
    filesink = gst.element_factory_make("filesink", "filesink-%s" % tag)
    if file:
        filesink.props.location = file
        pipelineParts.append("filesink location=$FILE_PATH")
    else:
        pipelineParts.append("filesink")

    # Add and link elements
    encBin.add(muxer, filesink)
    muxer.link(filesink)

    if audioEncodeBin:
        encBin.add(audioEncodeBin)
        audioEncodeBin.link(muxer)
        pad = gst.GhostPad("audiosink", audioEncodeBin.get_pad("sink"))
        encBin.add_pad(pad)

    if videoEncodeBin:
        encBin.add(videoEncodeBin)
        videoEncodeBin.link(muxer)
        pad = gst.GhostPad("videosink", videoEncodeBin.get_pad("sink"))
        encBin.add_pad(pad)

    pipelineDesc = ' ! '.join(pipelineParts)
    logger.debug("Muxer pipeline: %s", pipelineDesc)

    if pipelineInfo != None:
       pipelineInfo["muxer"] = pipelineDesc

    return encBin

def makeAudioEncodeBin(config, analysis, tag, withRateControl=True,
                       pipelineInfo=None, logger=None):
    logger = logger or log
    pipelineParts = list()
    bin = gst.Bin()

    # input queue element
    inqueue = gst.element_factory_make("queue", "audioinqueue-%s" % tag)
    # Cannot specify max_size_time property because of some buggy buffers
    # with invalid time that make the queue lock
    inqueue.props.max_size_time = 0
    inqueue.props.max_size_buffers = 200
    pipelineParts.append("queue")

    # audiorate element
    if withRateControl:
        rate = gst.element_factory_make("audiorate", "audiorate-%s" % tag)
        pipelineParts.append("audiorate")
    else:
        rate = None

    # audioconvert element
    convert = gst.element_factory_make("audioconvert",
                                       "audioconvert-%s" % tag)
    pipelineParts.append("audioconvert")


    # audioresample element
    resample = gst.element_factory_make("audioresample",
                                        "audioresample-%s" % tag)
    pipelineParts.append("audioresample")

    # capsfilter element
    capsfilter = gst.element_factory_make("capsfilter",
                                          "audiocapsfilter-%s" % tag)
    # Because the analysis not reliably give channel
    # and rate info, do not not rely on it.
    if config.audioRate or config.audioChannels:
        capsList = []
        if config.audioRate:
            capsList.append("rate=%d" % config.audioRate)
        elif analysis.audioRate:
            capsList.append("rate=%d" % analysis.audioRate)
        if config.audioChannels:
            capsList.append("channels=%d" % config.audioChannels)
        elif analysis.audioChannels:
            capsList.append("channels=%d" % analysis.audioChannels)
        caps = ", ".join(capsList)
        if caps:
            fullcaps = ("audio/x-raw-int, %s;audio/x-raw-float, %s"
                        % (caps, caps))
            logger.debug("Audio capsfilter: '%s'", fullcaps)
            pipelineParts.append("'%s'" % fullcaps)
            capsfilter.props.caps = gst.caps_from_string(fullcaps)
        else:
            logger.debug("No audio capsfilter")

    # encoder elements
    encode = gstutils.parse_bin_from_description(config.audioEncoder, True)
    pipelineParts.extend(map(str.strip, config.audioEncoder.split('!')))

    # output queue element
    outqueue = gst.element_factory_make("queue", "audioutqueue-%s" % tag)
    outqueue.props.max_size_time = gst.SECOND * 20
    outqueue.props.max_size_buffers = 0
    pipelineParts.append("queue")

    if rate:
        bin.add(inqueue, rate, convert, resample,
                capsfilter, encode, outqueue)
        gst.element_link_many(inqueue, rate, convert, resample,
                              capsfilter, encode, outqueue)
    else:
        bin.add(inqueue, convert, resample,
                capsfilter, encode, outqueue)
        gst.element_link_many(inqueue, convert, resample,
                              capsfilter, encode, outqueue)

    bin.add_pad(gst.GhostPad("sink", inqueue.get_pad("sink")))
    bin.add_pad(gst.GhostPad("src", outqueue.get_pad("src")))

    pipelineDesc = ' ! '.join(pipelineParts)
    logger.debug("Audio pipeline: %s", pipelineDesc)

    if pipelineInfo != None:
        pipelineInfo["audio"] = pipelineDesc

    return bin

def _logPreferredSize(logFunc, config, msg):
    if config.videoWidth:
        ws = str(config.videoWidth)
    else:
        ws = "???"
    if config.videoHeight:
        hs = str(config.videoHeight)
    else:
        hs = "???"
    if config.videoPAR:
        pars = " %d/%d" % config.videoPAR
    else:
        pars = " ?/?"
    if config.videoMaxWidth or config.videoMaxHeight:
        if config.videoMaxWidth:
            mws = str(config.videoMaxWidth)
        else:
            mws = "???"
        if config.videoMaxHeight:
            mhs = str(config.videoMaxHeight)
        else:
            mhs = "???"
        maxs = " (max %sx%s)" % (mws, mhs)
    else:
        maxs = ""
    logFunc("%s %sx%s%s%s", msg, ws, hs, maxs, pars)

def makeVideoEncodeBin(config, analysis, tag, withRateControl=True,
                       pipelineInfo=None, logger=None):
    logger = logger or log
    pipelineParts = list()
    bin = gst.Bin()

    # input queue element
    inqueue = gst.element_factory_make("queue", "videoinqueue-%s" % tag)
    # Cannot specify max_size_time property because of some buggy buffers
    # with invalid time that make the queue lock
    inqueue.props.max_size_time = 0
    inqueue.props.max_size_buffers = 200
    pipelineParts.append("queue")

    # ffmpegcolorspace element
    cspace = gst.element_factory_make("ffmpegcolorspace", "cspace-%s" % tag)
    pipelineParts.append("ffmpegcolorspace")

    # videorate element
    if withRateControl:
        rate = gst.element_factory_make("videorate", "videorate-%s" % tag)
        pipelineParts.append("videorate")
    else:
        rate = None

    # videoscale element
    scale = gst.element_factory_make("videoscale", "videoscale-%s" % tag)
    # use bilinear scaling for better image quality
    scale.props.method = 1
    pipelineParts.append("videoscale method=1")

    # capsfilter element
    capsfilter = gst.element_factory_make("capsfilter",
                                          "videocapsfilter-%s" % tag)
    inputSize = _getInputVideoSize(config, analysis)
    logger.debug("makeVideoEncodeBin - Input Video Size: %dx%d %d/%d"
                 % (inputSize[0], inputSize[1],
                    inputSize[2].num, inputSize[2].denom))
    _logPreferredSize(logger.debug, config,
                      "makeVideoEncodeBin - Preferred Video Size:")
    outputSize = _getOutputVideoSize(config, analysis, inputSize)
    logger.debug("makeVideoEncodeBin - Output Video Size: %dx%d %d/%d"
                 % (outputSize[0], outputSize[1],
                    outputSize[2].num, outputSize[2].denom))
    caps = _getOutputVideoCaps(config, analysis, outputSize)
    if caps:
        logger.debug("Video capsfilter: '%s'", caps)
        capsfilter.props.caps = gst.caps_from_string(caps)
        pipelineParts.append("'%s'" % caps)
    else:
        logger.debug("No video capsfilter")

    # videobox and videocrop elements
    box = _getOutputVideoBox(config, analysis, outputSize)
    videocrop = None
    videobox = None
    if box != (0, 0, 0, 0):
        #FIXME: Crop is a temporary hack to fix wrong behaviors
        #       of the platform version of videobox with odd parameteres.
        #       gstreamer-0.10.12, gstreamer-plugins-good-0.10.5
        crop = tuple([v % 2 for v in box])
        box = tuple([v - (v % 2) for v in box])
        logger.debug("makeVideoEncodeBin - Output Video Boxing: %r" % (box,))
        videobox = gst.element_factory_make("videobox", "videobox-%s" % tag)
        videobox.props.left = box[0]
        videobox.props.top = box[1]
        videobox.props.right = box[2]
        videobox.props.bottom = box[3]
        pipelineParts.append("videobox left=%d top=%d "
                             "right=%d bottom=%d" % box[:4])
        if crop != (0, 0, 0, 0):
            logger.debug("makeVideoEncodeBin - Output Video Cropping: %r" % (crop,))
            videocrop = gst.element_factory_make("videocrop",
                                                 "videocrop-%s" % tag)
            videocrop.props.left = crop[0]
            videocrop.props.top = crop[1]
            videocrop.props.right = crop[2]
            videocrop.props.bottom = crop[3]
            pipelineParts.append("videocrop left=%d top=%d "
                                 "right=%d bottom=%d" % crop[:4])


    # encoder elements
    encode = gstutils.parse_bin_from_description(config.videoEncoder, True)
    pipelineParts.extend(map(str.strip, config.videoEncoder.split('!')))

    # output queue element
    outqueue = gst.element_factory_make("queue", "videooutqueue-%s" % tag)
    outqueue.props.max_size_time = gst.SECOND * 20
    outqueue.props.max_size_buffers = 0
    pipelineParts.append("queue")

    # Add to pipeline and link all the elements
    bin.add(inqueue, cspace, scale, capsfilter, encode, outqueue)
    if rate:
        bin.add(rate)
        gst.element_link_many(inqueue, cspace, rate, scale, capsfilter)
    else:
        gst.element_link_many(inqueue, cspace, scale, capsfilter)
    if videobox:
        bin.add(videobox)
        if videocrop:
            bin.add(videocrop)
            gst.element_link_many(capsfilter, videobox, videocrop, encode)
        else:
            gst.element_link_many(capsfilter, videobox, encode)
    else:
        gst.element_link_many(capsfilter, encode)
    gst.element_link_many(encode, outqueue)

    bin.add_pad(gst.GhostPad("sink", inqueue.get_pad("sink")))
    bin.add_pad(gst.GhostPad("src", outqueue.get_pad("src")))

    pipelineDesc = ' ! '.join(pipelineParts)
    logger.debug("Video pipeline: %s", pipelineDesc)

    if pipelineInfo != None:
        pipelineInfo["video"] = pipelineDesc

    return bin

def _getInputVideoSize(config, analysis):
    icaps = dict(analysis.videoCaps[0])
    ipar = icaps.get('pixel-aspect-ratio', gst.Fraction(1,1))
    iw = analysis.videoWidth
    ih = analysis.videoHeight
    return iw, ih, ipar

def _getOutputVideoSize(config, analysis, inputSize):
    """
    Returns the output video (width, height, PAR)
    according to the information from the analysis.
    """
    iw, ih, ipar = inputSize
    ow, oh, opar = videosize.getVideoSize(iw, ih, (ipar.num, ipar.denom),
                                          config.videoWidth,
                                          config.videoHeight,
                                          config.videoPAR,
                                          config.videoMaxWidth,
                                          config.videoMaxHeight,
                                          config.videoScaleMethod)
    return ow, oh, gst.Fraction(*opar)

def _getOutputVideoBox(config, analysis, outputSize):
    """
    Returns the ouput video box according
    to the information from the analysis
    and the configuration as (left, top, right, bottom).
    """
    width, height = outputSize[:2]
    wdiff, hdiff = 0, 0
    if config.videoWidth:
        if width != config.videoWidth:
            wdiff = width - config.videoWidth
    else:
        wm = int(config.videoWidthMultiple or DEFAULT_WIDTH_MULTIPLE)
        if width % wm:
            wdiff = width -(((width / wm) + 1) * wm)
    if config.videoHeight:
        if height != config.videoHeight:
            hdiff = height - config.videoHeight
    else:
        hm = int(config.videoHeightMultiple or DEFAULT_HEIGHT_MULTIPLE)
        if height % hm:
            hdiff = height - (((height / hm) + 1) * hm)
    right = wdiff / 2
    left = wdiff - right
    bottom = hdiff / 2
    top = hdiff - bottom
    return (left, top, right, bottom)

def _getOutputVideoCaps(config, analysis, outputSize):
    """
    Returns the output video caps according
    to the information from the analysis
    and the configuration.
    """
    width, height, par = outputSize

    # rate is straightforward
    if config.videoFramerate:
        rate = gst.Fraction(*config.videoFramerate)
    else:
        rate = analysis.videoRate

    svtempl = ("width=%d, height=%d, pixel-aspect-ratio=%d/%d, framerate=%d/%d"
               % (width, height, par.num, par.denom, rate.num, rate.denom))
    fvtempl = "video/x-raw-yuv, %s;video/x-raw-rgb, %s" % (svtempl, svtempl)
    return fvtempl
