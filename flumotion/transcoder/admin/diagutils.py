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

from flumotion.inhouse import utils, fileutils


## Public Functions ##

def formatFileSize(bytes, default=None):
    if bytes == None: return default
    if bytes < (8 * 1024):
        return "%d B" % bytes
    if bytes < (8 * 1024**2):
        return "%d KB" % (bytes / 1024)
    return "%d MB" % (bytes / 1024**2)

def formatDuration(sec, default=None):
    if (sec == None) or (sec < 0):
        return default
    tm = int(sec) / 60
    s = int(sec) % 60
    h = tm / 60
    m = tm % 60
    ms =  int((sec - int(sec)) * 1000)
    result = []
    if h: result.append("%dh" % h)
    if m: result.append("%dm" % m)
    result.append("%ds" % s)
    if ms: result.append("%d" % ms)
    return " ".join(result)

def extractAudioBrief(analysis):
    if not analysis.hasAudio:
        return None
    otherCodec = analysis.otherTags.get("audio-codec", "Unknown Codec")
    audioCodec = analysis.audioTags.get("audio-codec", None)
    brief = audioCodec or otherCodec
    brief += ", %s" % formatDuration(analysis.audioDuration,
                                     "Unknown Duration")
    brief += ", %d channels(s) : %dHz @ %dbits" % (analysis.audioChannels,
                                                  analysis.audioRate,
                                                  analysis.audioDepth)
    for tag, val in analysis.audioTags.items():
        if tag in set(["bitrate"]):
            brief += ", %s: %s" % (tag, val)
    return brief

def extractVideoBrief(analysis):
    if not analysis.hasVideo:
        return None
    otherCodec = analysis.otherTags.get("video-codec", "Unknown Codec")
    audioCodec = analysis.audioTags.get("video-codec", None)
    brief = audioCodec or otherCodec
    brief += ", %s" % formatDuration(analysis.videoDuration,
                                     "Unknown Duration")
    rate = ""
    if analysis.videoRate:
        rate += "@ %d/%d fps" % analysis.videoRate
        if analysis.videoRate[1] != 1:
            rate +=  " (~ %d fps)" % int(round(analysis.videoRate[0]
                                               / analysis.videoRate[1]))
    brief += ", %d x %d %s" % (analysis.videoWidth,
                              analysis.videoHeight,
                              rate)
    for tag, val in analysis.audioTags.items():
        if tag in set(["bitrate"]):
            brief += ", %s: %s" % (tag, val)
    return brief

def extractPlayPipeline(config, report, fromAudit=False,
                        playAudio=True, playVideo=True,
                        sourcePath=None, sourceFileTemplate=None):
    sourceInfo = dict()
    if fromAudit:
        sourceData = report.source.pipelineAudit
        if not (sourceData and ('demuxer' in sourceData)):
            return None
        sourceInfo.update(sourceData)
    sourcePath = sourcePath or config.source.inputFile
    filename = __applyFileTemplate(sourceFileTemplate, sourcePath)
    sourceInfo['filename'] = filename
    return __buildPipeline(sourceInfo,
                           withAudio=playAudio,
                           withVideo=playVideo)

def extractTransPipeline(config, report, onlyForTargets=None,
                         fromAudit=False, sourcePath=None,
                         sourceFileTemplate=None, targetFileTemplate=None):
    sourceInfo = dict()
    if fromAudit:
        sourceData = report.source.pipelineAudit
        if not (sourceData and ('demuxer' in sourceData)):
            return None
        sourceInfo.update(sourceData)
    sourcePath = sourcePath or config.source.inputFile
    filename = __applyFileTemplate(sourceFileTemplate, sourcePath)
    sourceInfo['filename'] = filename
    targetsInfo = []
    for name, targetReport in report.targets.iteritems():
        if onlyForTargets and not (name in onlyForTargets):
            continue
        targetConfig = config.targets.get(name, None)
        if not targetConfig:
            continue
        targetInfo = dict()
        if fromAudit:
            targetData = targetReport.pipelineAudit
        else:
            targetData = targetReport.pipelineInfo
        targetInfo.update(targetData)
        targetInfo['tag'] = name
        targetInfo['filename'] = __applyFileTemplate(targetFileTemplate,
                                                     targetConfig.outputFile)
        targetsInfo.append(targetInfo)

    if not targetsInfo:
        return None

    return __buildPipeline(sourceInfo, targetsInfo)


## Private Functions ##

def __applyFileTemplate(tmpl, path):
    if not tmpl: return path
    p, b, e = fileutils.splitPath(path)
    vars = {"path": p, "basename": b, "extension": e, "filename": (b + e)}
    format = utils.filterFormat(tmpl, vars)
    return format % vars


def __buildPipeline(sourceInfo, targetsInfo=[], withAudio=True, withVideo=True):

    def changeLoc(s, f):
        l = utils.mkCmdArg(f, "location=")
        return s.replace("location=$FILE_PATH", l)

    sourceDemuxer = sourceInfo.get("demuxer", None)
    sourceVideo = sourceInfo.get("video", None)
    sourceAudio = sourceInfo.get("audio", None)

    if len(targetsInfo) > 0:
        # Transcoding Pipeline
        hasAudioTarget = reduce(bool.__or__, [bool(t.get("audio", None))
                                              for t in targetsInfo])
        hasVideoTarget = reduce(bool.__or__, [bool(t.get("video", None))
                                              for t in targetsInfo])
        isMultiTarget = len(targetsInfo) > 1
        isTranscodingPipline = True
    else:
        # Playing Pipeline
        hasAudioTarget = True
        hasVideoTarget = True
        isMultiTarget = False
        isTranscodingPipline = False

    audioReference = None
    videoReference = None
    muxerReference = "muxer."
    lastReference = None
    pipe = " ! "
    space = " "
    vplay = "ffmpegcolorspace ! videoscale ! autovideosink"
    aplay = "audioconvert ! autoaudiosink"
    pipeline = ""

    sourceFile = sourceInfo['filename']
    if sourceDemuxer:
        pipeline += changeLoc(sourceDemuxer, sourceFile)
        if sourceAudio and withAudio and sourceVideo and withVideo:
            pipeline += " name=demuxer"
            demuxerReference = "demuxer."
        if sourceVideo and withVideo:
            videoReference = ""
            pipeline += pipe + sourceVideo
            if isTranscodingPipline:
                if hasVideoTarget:
                    if isMultiTarget:
                        pipeline += pipe + "tee name=vtee"
                        videoReference = "vtee."
                    elif sourceAudio:
                        pipeline += " name=vsrc"
                        videoReference = "vsrc."
                lastReference = videoReference
            else:
                pipeline += pipe + vplay
        if sourceAudio and withAudio:
            audioReference = ""
            if sourceVideo:
                pipeline += space + demuxerReference
            pipeline += pipe + sourceAudio
            if isTranscodingPipline:
                if hasAudioTarget:
                    if isMultiTarget:
                        pipeline += pipe + "tee name=atee"
                        audioReference = "atee."
                    elif sourceVideo:
                        pipeline += " name=asrc"
                        audioReference = "asrc."
                lastReference = audioReference
            else:
                pipeline += pipe + aplay
    else:
        audioReference = ""
        videoReference = ""
        sourceLocation = utils.mkCmdArg(sourceFile, "location=")
        pipeline += "filesrc " + sourceLocation + " ! decodebin2"
        if not isTranscodingPipline:
            if withVideo:
                if withAudio:
                    pipeline += " name=decoder"
                pipeline += pipe + vplay
            if withAudio:
                if withVideo:
                    pipeline += space + "decoder."
                pipeline += pipe + aplay
        elif isMultiTarget:
            if hasAudioTarget and withAudio and hasVideoTarget and withVideo:
                pipeline += " name=decoder"
            if hasVideoTarget and withVideo:
                pipeline += pipe + "'video/x-raw-yuv;video/x-raw-rgb'"
                pipeline += pipe + "tee name=vtee"
                videoReference = "vtee."
                lastReference = videoReference
            if hasAudioTarget and withAudio:
                if hasVideoTarget:
                    pipeline += space + "decoder."
                pipeline += pipe + "'audio/x-raw-int;audio/x-raw-float'"
                pipeline += pipe + "tee name=atee"
                audioReference = "atee."
                lastReference = audioReference
        elif hasAudioTarget and withAudio and hasVideoTarget and withVideo:
            pipeline += " name=decoder"
            videoReference = "decoder."

    if not isTranscodingPipline:
        return pipeline

    for targetInfo in targetsInfo:
        muxerName = "muxer"
        tag = targetInfo.get("tag", None)
        if isMultiTarget and tag:
            muxerName = "muxer-%s" % tag
        muxerReference = muxerName + "."

        targMuxer = targetInfo.get("muxer", None)
        targVideo = targetInfo.get("video", None)
        targAudio = targetInfo.get("audio", None)
        targFile = targetInfo['filename']

        if targAudio and withAudio:
            if audioReference and (lastReference != audioReference):
                pipeline += space + audioReference
            pipeline += pipe + changeLoc(targAudio, targFile)
            if targVideo and targMuxer:
                pipeline += pipe + muxerReference
            lastReference = None

        if targVideo and withVideo:
            if videoReference and (lastReference != videoReference):
                pipeline += space + videoReference
            pipeline += pipe + changeLoc(targVideo, targFile)
            lastReference = None

        if targMuxer:
            if targAudio and targVideo:
                targMuxer = targMuxer.replace(" ! ", " name=%s ! " % muxerName, 1)
            pipeline += pipe + changeLoc(targMuxer, targFile)
            lastReference = None

    return pipeline
