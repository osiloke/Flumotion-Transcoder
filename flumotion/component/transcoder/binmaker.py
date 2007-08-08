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

from flumotion.transcoder import log
from flumotion.component.transcoder import videosize
from flumotion.component.transcoder import gstutils

def makeEncodeBin(file, config, dicoverer, tag,
                  audioEncodeBin, videoEncodeBin):
    encBin = gst.Bin("encoding-%s" % tag)
    filesink = gst.element_factory_make("filesink", "filesink-%s" % tag)
    filesink.props.location = file
    muxer = gst.parse_launch(config.muxer)
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
    return encBin

def makeAudioEncodeBin(config, discoverer, tag, withRateControl=True):
    bin = gst.Bin()
    inqueue = gst.element_factory_make("queue", "audioinqueue-%s" % tag)
    #Cannot specify max_size_time property because of some buggy buffers
    #with invalid time that make the queue lock
    inqueue.props.max_size_time = 0
    inqueue.props.max_size_buffers = 200
    convert = gst.element_factory_make("audioconvert", 
                                       "audioconvert-%s" % tag)
    resample = gst.element_factory_make("audioresample", 
                                        "audioresample-%s" % tag)
    capsfilter = gst.element_factory_make("capsfilter", 
                                          "audiocapsfilter-%s" % tag)
    encode = gstutils.parse_bin_from_description(config.audioEncoder, True)
    outqueue = gst.element_factory_make("queue", "audioutqueue-%s" % tag)
    outqueue.props.max_size_time = gst.SECOND * 20
    outqueue.props.max_size_buffers = 0
    
    # Because the discoverer not reliably give channel
    # and rate info, do not not rely on it.
    if config.audioRate or config.audioChannels:
        capsList = []
        if config.audioRate:
            capsList.append("rate=%d" % config.audioRate)
        elif discoverer.audiorate:
            capsList.append("rate=%d" % discoverer.audiorate)
        if config.audioChannels:
            capsList.append("channels=%d" % config.audioChannels)
        elif discoverer.audiochannels:
            capsList.append("channels=%d" % discoverer.audiochannels)
        caps = ",".join(capsList)
        if caps:
            fullcaps = ("audio/x-raw-int,%s;audio/x-raw-float,%s" 
                        % (caps, caps))
            capsfilter.props.caps = gst.caps_from_string(fullcaps)

    if withRateControl:
        rate = gst.element_factory_make("audiorate", "audiorate-%s" % tag)
        bin.add(inqueue, convert, rate, resample, 
                capsfilter, encode, outqueue)
        gst.element_link_many(inqueue, convert, rate, resample, 
                              capsfilter, encode, outqueue)
    else:
        bin.add(inqueue, convert, resample, 
                capsfilter, encode, outqueue)
        gst.element_link_many(inqueue, convert, resample, 
                              capsfilter, encode, outqueue)
    
    bin.add_pad(gst.GhostPad("sink", inqueue.get_pad("sink")))
    bin.add_pad(gst.GhostPad("src", outqueue.get_pad("src")))

    return bin

def _logPreferredSize(msg, config):
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
    log.info("%s %sx%s%s%s" % (msg, ws, hs, maxs, pars))

def makeVideoEncodeBin(config, discoverer, tag, withRateControl=True):
    bin = gst.Bin()
    inqueue = gst.element_factory_make("queue", "videoinqueue-%s" % tag)
    #Cannot specify max_size_time property because of some buggy buffers
    #with invalid time that make the queue lock
    inqueue.props.max_size_time = 0
    inqueue.props.max_size_buffers = 200
    cspace = gst.element_factory_make("ffmpegcolorspace", "cspace-%s" % tag)
    scale = gst.element_factory_make("videoscale", "videoscale-%s" % tag)
    capsfilter = gst.element_factory_make("capsfilter", 
                                          "videocapsfilter-%s" % tag)
    encode = gstutils.parse_bin_from_description(config.videoEncoder, True)
    outqueue = gst.element_factory_make("queue", "videooutqueue-%s" % tag)
    outqueue.props.max_size_time = gst.SECOND * 20
    outqueue.props.max_size_buffers = 0

    # use bilinear scaling for better image quality
    scale.props.method = 1
    
    inputSize = _getInputVideoSize(config, discoverer)
    log.info("makeVideoEncodeBin - Input Video Size: %dx%d %d/%d"
             % (inputSize[0], inputSize[1], 
                inputSize[2].num, inputSize[2].denom))
    _logPreferredSize("makeVideoEncodeBin - Preferred Video Size:",
                      config)                    
    outputSize = _getOutputVideoSize(config, discoverer, inputSize)
    log.info("makeVideoEncodeBin - Output Video Size: %dx%d %d/%d"
             % (outputSize[0], outputSize[1], 
                outputSize[2].num, outputSize[2].denom))
    bin.add(inqueue, cspace, scale, capsfilter, encode, outqueue)

    if withRateControl:
        rate = gst.element_factory_make("videorate", "videorate-%s" % tag)
        bin.add(rate)
        gst.element_link_many(inqueue, cspace, rate, scale, capsfilter)
    else:
        gst.element_link_many(inqueue, cspace, scale, capsfilter)
    
    caps = _getOutputVideoCaps(config, discoverer, outputSize)
    box = _getOutputVideoBox(config, discoverer, outputSize)
    #FIXME: Temporary hack to fix wrong behavior of the platform version
    #       of GStreamer when the input size of videobox is odd
    caps, box = __hackForInputStreamWithOddSize(caps, box)
    if box[0] or box[1] or box[2] or box[3]:
        log.info("makeVideoEncodeBin - Output Video Boxing: %d %d %d %d" 
                 % box)
        videobox = gst.element_factory_make("videobox", "videobox-%s" % tag)
        videobox.props.left = box[0]
        videobox.props.top = box[1]
        videobox.props.right = box[2]
        videobox.props.bottom = box[3]
        #To fill with green
        #videobox.props.fill = 1
        bin.add(videobox)
        gst.element_link_many(capsfilter, videobox, encode, outqueue)
    else:
        gst.element_link_many(capsfilter, encode, outqueue)
    
    capsfilter.props.caps = caps    
    bin.add_pad(gst.GhostPad("sink", inqueue.get_pad("sink")))
    bin.add_pad(gst.GhostPad("src", outqueue.get_pad("src")))

    return bin

def __hackForInputStreamWithOddSize(caps, box):
    """
    Hack to prevent input streams with odd width or height.
    The current platform version of GStreamer doesn't handle
    it properly and make the last line green/garbage.
    """
    bl, bt, br, bb = box
    if not (bl or bt or br or bb):
        # videobox will not be used so forget it
        return
    wdiff, hdiff = 0, 0
    if caps[0]["width"] % 2:
        if bl or br:
            if bl < br:
                bl += 1
            else:
                br += 1
            wdiff = 1
        else:
            br -= 1
            wdiff = -1
    if caps[0]["height"] % 2:
        if bt or bt:
            if bt < bb:
                bt += 1
            else:
                bb += 1
            hdiff = 1
        else:
            bb -= 1
            hdiff = -1
    for c in caps:
        c["width"] = c["width"] + wdiff
        c["height"] = c["height"] + hdiff
    return caps, (bl, bt, br, bb)

def _getInputVideoSize(config, discoverer):
    icaps = dict(discoverer.videocaps[0])
    ipar = icaps.get('pixel-aspect-ratio', gst.Fraction(1,1))
    iw = discoverer.videowidth
    ih = discoverer.videoheight
    return iw, ih, ipar
    
def _getOutputVideoSize(config, discoverer, inputSize):
    """
    Returns the output video (width, height, PAR)
    according to the information from the discoverer.
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

def _getOutputVideoBox(config, discoverer, outputSize):
    """
    Returns the ouput video box according 
    to the information from the discoverer 
    and the configuration as (left, top, right, bottom).
    """
    width, height = outputSize[:2]
    wdiff, hdiff = 0, 0
    if config.videoWidth:
        if width != config.videoWidth:
            wdiff = width - config.videoWidth
    elif config.videoWidthMultiple:
        wm = int(config.videoWidthMultiple)
        if width % wm:
            wdiff = width -(((width / wm) + 1) * wm)
    if config.videoHeight:
        if height != config.videoHeight:
            hdiff = height - config.videoHeight
    elif config.videoHeightMultiple:
        hm = int(config.videoHeightMultiple)
        if height % hm:
            hdiff = height - (((height / hm) + 1) * hm)
    left = wdiff / 2
    right = wdiff - left
    top = hdiff / 2
    bottom = hdiff - top
    return (left, top, right, bottom)

def _getOutputVideoCaps(config, discoverer, outputSize):
    """
    Returns the output video caps according 
    to the information from the discoverer 
    and the configuration.    
    """
    width, height, par = outputSize

    # rate is straightforward
    if config.videoFramerate:
        rate = gst.Fraction(*config.videoFramerate)
    else:
        rate = discoverer.videorate
        
    svtempl = ("width=%d,height=%d,pixel-aspect-ratio=%d/%d,framerate=%d/%d" 
               % (width, height, par.num, par.denom, rate.num, rate.denom))
    fvtempl = "video/x-raw-yuv,%s;video/x-raw-rgb,%s" % (svtempl, svtempl)
    return gst.caps_from_string(fvtempl)
