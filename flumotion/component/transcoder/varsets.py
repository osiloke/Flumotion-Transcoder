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

import os

CORTADO_DEFAULT_WIDTH = 320
CORTADO_DEFAULT_HEIGHT = 40


def getPreProcessVars(context):
    reporter = context.reporter
    config = context.config
    sourceCtx = context.getSourceContext()        
    sourceAnalysis = reporter.report.source.analysis
    vars = dict()
    
    vars['outputBase'] = context.getOutputDir()
    vars['inputBase'] = context.getInputDir()
    vars['linkBase'] = context.getLinkDir()
    vars['outputWorkBase'] = context.getOutputWorkDir()
    vars['linkWorkBase'] = context.getLinkWorkDir()
    vars['doneBase'] = context.getDoneDir()
    vars['failedBase'] = context.getFailedDir()

    vars['inputRelPath'] = sourceCtx.getInputFile()
    vars['inputFile'] = os.path.basename(vars['inputRelPath'])
    vars['inputPath'] = sourceCtx.getInputPath()
    vars['inputDir'] = os.path.basename(os.path.join(vars['inputBase'],
                                                     vars['inputRelPath']))
    vars['customerName'] = config.customer.name
    vars['profileName'] = config.profile.label
    vars['sourceMime'] = sourceAnalysis.mimeType
    if sourceAnalysis.hasVideo:
        vars['sourceHasVideo'] = 1
        vars['sourceVideoWidth'] = sourceAnalysis.videoWidth
        vars['sourceVideoHeight'] = sourceAnalysis.videoHeight
    else:
        vars['sourceHasVideo'] = 0
        vars['sourceVideoWidth'] = 0
        vars['sourceVideoHeight'] = 0
    if sourceAnalysis.hasAudio:
        vars['sourceHasAudio'] = 1
    else:
        vars['sourceHasAudio'] = 0

    duration = sourceCtx.reporter.getMediaDuration() or -1
    length = sourceCtx.reporter.getMediaLength()
    vars['sourceDuration'] = duration
    vars['sourceLength'] = length
    # PyChecker isn't smart enough to see I first convert to int
    __pychecker__ = "no-intdivide"
    s = int(round(duration))
    m = s / 60
    s -= m * 60
    h = m / 60
    m -= h * 60        
    vars['sourceHours'] = h
    vars['sourceMinutes'] = m
    vars['sourceSeconds'] = s
    return vars

def getPostProcessVars(targetCtx):
    targetConfig = targetCtx.config
    targetReporter = targetCtx.reporter
    targetAnalysis = targetCtx.reporter.report.analysis
    
    vars = getPreProcessVars(targetCtx.context)

    vars['outputRelPath'] = targetCtx.getOutputFile()
    vars['outputFile'] = os.path.basename(vars['outputRelPath'])
    vars['outputPath'] = targetCtx.getOutputPath()
    vars['outputDir'] = os.path.basename(os.path.join(vars['outputBase'],
                                                      vars['outputRelPath']))
    
    vars['outputWorkRelPath'] = targetCtx.getOutputWorkFile()
    vars['outputWorkFile'] = os.path.basename(vars['outputWorkRelPath'])
    vars['outputWorkPath'] = targetCtx.getOutputWorkPath()
    vars['outputWorkDir'] = os.path.basename(os.path.join(vars['outputWorkBase'],
                                                          vars['outputWorkRelPath']))
    
    vars['linkRelPath'] = targetCtx.getLinkFile()
    vars['linkFile'] = os.path.basename(vars['linkRelPath'])
    vars['linkPath'] = targetCtx.getLinkPath()
    vars['linkDir'] = os.path.basename(os.path.join(vars['linkBase'],
                                                      vars['linkRelPath']))
    
    vars['linkWorkRelPath'] = targetCtx.getLinkWorkFile()
    vars['linkWorkFile'] = os.path.basename(vars['linkWorkRelPath'])
    vars['linkWorkPath'] = targetCtx.getLinkWorkPath()
    vars['linkWorkDir'] = os.path.basename(os.path.join(vars['linkWorkBase'],
                                                          vars['linkWorkRelPath']))
    
    vars['targetName'] = targetConfig.label
    vars['targetType'] = targetConfig.type.name
    vars['targetMime'] = targetAnalysis.mimeType
    if targetAnalysis.hasVideo:
        vars['targetHasVideo'] = 1
        vars['targetVideoWidth'] = targetAnalysis.videoWidth
        vars['targetVideoHeight'] = targetAnalysis.videoHeight
    else:
        vars['targetHasVideo'] = 0
        vars['targetVideoWidth'] = 0
        vars['targetVideoHeight'] = 0
    if targetAnalysis.hasAudio:
        vars['targetHasAudio'] = 1
    else:
        vars['targetHasAudio'] = 0

    duration = targetReporter.getMediaDuration() or 0.0
    length = targetReporter.getMediaLength() or 0
    vars['targetDuration'] = duration
    vars['targetLength'] = length
    # PyChecker isn't smart enough to see I first convert to int
    __pychecker__ = "no-intdivide"
    s = int(round(duration))
    m = s / 60
    s -= m * 60
    h = m / 60
    m -= h * 60        
    vars['targetHours'] = h
    vars['targetMinutes'] = m
    vars['targetSeconds'] = s
    
    if duration > 0:
        vars['mediaDuration'] = vars["targetDuration"]
        vars['mediaLength'] = vars["targetLength"]
        vars['mediaHours'] = vars["targetHours"]
        vars['mediaMinutes'] = vars["targetMinutes"]
        vars['mediaSeconds'] = vars["targetSeconds"]
    else:
        vars['mediaDuration'] = vars["sourceDuration"]
        vars['mediaLength'] = vars["sourceLength"]
        vars['mediaHours'] = vars["sourceHours"]
        vars['mediaMinutes'] = vars["sourceMinutes"]
        vars['mediaSeconds'] = vars["sourceSeconds"]
    
    return vars

def getLinkTemplateVars(targetCtx):
    return getPostProcessVars(targetCtx)
    
def getCortadoArgs(targetCtx):
    targetAnalysis = targetCtx.reporter.report.analysis
    args = dict()
    duration = targetCtx.reporter.getMediaDuration()
    if duration and (duration > 0):
        # let buffer time be at least 5 seconds
        output = targetCtx.getOutputWorkPath()
        bytesPerSecond = os.stat(output).st_size / duration
        # specified in Kb
        bufferSize = int(bytesPerSecond * 5 / 1024)
    else:
        # Default if we couldn't figure out duration
        bufferSize = 128
    args['c-bufferSize'] = str(bufferSize)
    # cortado doesn't handle Theora cropping, so we need to round
    # up width and height for display
    rounder = lambda i: (i + (16 - 1)) / 16 * 16
    if targetAnalysis.videoWidth:
        args['c-width'] = str(rounder(targetAnalysis.videoWidth))
    else:
        args['c-width'] = CORTADO_DEFAULT_WIDTH
    if targetAnalysis.videoHeight:
        args['c-height'] = str(rounder(targetAnalysis.videoHeight))
    else:
        args['c-height'] = CORTADO_DEFAULT_HEIGHT
    if duration:
        args['c-duration'] = str(duration)
        args['c-seekable'] = 'true'
    if targetAnalysis.audioCaps:
        args['c-audio'] = 'true'
    else:
        args['c-audio'] = 'false'
    if targetAnalysis.videoCaps:
        args['c-video'] = 'true'
    else:
        args['c-video'] = 'false'
    return args
