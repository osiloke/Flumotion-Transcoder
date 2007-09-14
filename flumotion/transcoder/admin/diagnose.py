# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import os
import re
import commands

from flumotion.common import messages

from flumotion.transcoder import log, defer, utils
from flumotion.transcoder.enums import TargetTypeEnum
from flumotion.transcoder.admin.enums import DocumentTypeEnum
from flumotion.transcoder.admin.document import StringDocument
from flumotion.transcoder.admin.proxies.monitorproxy import MonitorProxy
from flumotion.transcoder.admin.proxies.transcoderproxy import TranscoderProxy

class DiagnoseHelper(object):
    
    def __init__(self, managers, workers, components):
        self._managers = managers
        self._workers = workers
        self._components = components
        self._translator = messages.Translator()
        
    
    ## Public Methods ##
    
    def initialize(self):
        return defer.succeed(self)
        
    def filterComponentMessage(self, message):
        debug = message.debug
        if message.level == 2: # WARNING
            if "twisted.internet.error.ConnectionDone" in debug:
                return True
            if "twisted.internet.error.ConnectionLost" in debug:
                return True
            if "is not a known media" in debug:
                return True
            if "output file stalled during transcoding" in debug:
                return True
            if "Source file not found" in debug:
                return True
            if "flumotion.transcoder.errors.TranscoderError: Expected video, and got no video" in debug:
                return True
            if "flumotion.transcoder.errors.TranscoderError: Source media doesn't have video stream" in debug:
                return True
        if message.level == 1: # ERROR
            if "Source file not found" in debug:
                return True
        return False

    _crashMessagePattern = re.compile("The core dump is '([^']*)' on the host running '([^']*)'")
        
    def componentMessage(self, component, message):
        diagnostic = ["DIAGNOSTIC\n=========="]
        diagnostic.extend(self.__componentDiagnostic(component))
        text = self._translator.translate(message)
        isCrashMessage = self._crashMessagePattern.search(text)
        workerName = None
        if isCrashMessage:
            corePath, workerName = isCrashMessage.groups()
            diagnostic.extend(self.__crashDiagnostic(workerName, corePath))
            
        if isinstance(component, MonitorProxy):
            diagnostic.extend(self.__monitorDiagnostic(component, workerName))
                
        if isinstance(component, TranscoderProxy):
            diagnostic.extend(self.__reportDiagnostic(component))
            diagnostic.extend(self.__transcoderDiagnostic(component, workerName))
        
        diagnostic.append("")
        text = '\n\n'.join(diagnostic)
        label = "Component Message Diagnostic"
        return StringDocument(DocumentTypeEnum.diagnostic, label, text)

    def transcodingFailure(self, task, transcoder):
        if not transcoder: return None
        diagnostic = ["DIAGNOSTIC\n=========="]
        diagnostic.extend(self.__componentDiagnostic(transcoder))
        diagnostic.extend(self.__reportDiagnostic(transcoder))
        diagnostic.extend(self.__transcoderDiagnostic(transcoder))
        
        diagnostic.append("")
        text = '\n\n'.join(diagnostic)
        label = "Transcoding Failure Diagnostic"
        return StringDocument(DocumentTypeEnum.diagnostic, label, text)


    ## Private Methods ##
    
    def __workerHost(self, worker):
        if not worker:
            return "Unknown Host"
        host = worker.getHost()
        if host:
            return host
        return "Unknown Host for worker %s" % worker.getName()
    
    def __componentDiagnostic(self, component):
        diagnostic = ["COMPONENT INFO\n--------------"]
        worker = component.getWorker()
        
        if not worker:
            diagnostic.append("## No Worker Reference ##")
        else:
            host = worker.getHost()
            name = worker.getName()
            pid = component.getPID()
            diagnostic.append("Component PID:  %s" % (pid or "Unknown"))
            diagnostic.append("Worker Name:    %s" % name)
            diagnostic.append("Worker Host:    %s" % (host or "Unknown"))
            if host:
                diagnostic.append("Go to Worker:   ssh -At %s" % host)
        return diagnostic
    
    def __monitorDiagnostic(self, monitor, workerName=None):
        diagnostic = ["MANUAL     \n-------------"]
        if not monitor:
            return diagnostic
        worker = monitor.getWorker()
        if not worker and workerName:
            worker = self._workers.getWorker(workerName)
        if not worker: return diagnostic
        props = monitor.getProperties()
        if not props:
            diagnostic.append("## No Component Properties ##")
            return diagnostic
        args = props.asLaunchArguments(worker.getContext())
        cmd = self.__buildSUCommand("flumotion-launch -d 4 file-monitor", args)
        diagnostic.append("Normal Launch:\n\n    %s" % cmd)
        return diagnostic

    def __transcoderDiagnostic(self, transcoder, workerName=None):
        diagnostic = ["MANUAL LAUNCH\n-------------"]
        if not transcoder:
            return diagnostic
        worker = transcoder.getWorker()
        if not worker and workerName:
            worker = self._workers.getWorker(workerName)
        if not workerName:
            workerName = (worker and worker.getName()) or "Unknown Worker"
        if worker: 
            workerCtx = worker.getContext()
            local = workerCtx.getLocal()
            props = transcoder.getProperties()
            if not props:
                diagnostic.append("## No Component Properties ##")
            else:
                args = props.asLaunchArguments(workerCtx)
                cmd = self.__buildSUCommand("GST_DEBUG=2 flumotion-launch -d 4 "
                                            "file-transcoder", args)
                diagnostic.append("Normal Launch:\n\n    %s" % cmd)
            reportVirtPath = transcoder.getReportPath()
            if not reportVirtPath:
                diagnostic.append("## No Transcoding Report ##")
            else:
                args = ["diagnose=" + reportVirtPath.localize(local)]
                cmd = self.__buildSUCommand("GST_DEBUG=2 flumotion-launch -d 4 "
                                            "file-transcoder", args)
                diagnostic.append("Diagnose Launch:\n\n    %s" % cmd)
        return diagnostic
    
    def __crashDiagnostic(self, workerName, corePath):
        diagnostic = ["CRASH DEBUG\n-----------"]
        worker = self._workers.getWorker(workerName)
        host = (worker and worker.getHost()) or None
        inplace = "Debug Core Inplace:"
        if host:            
            inplace += "\n    Login: ssh -At %s" % host
        inplace += "\n    Debug: gdb python -c" + commands.mkarg(corePath)
        diagnostic.append(inplace)
        local = "Debug Core Locally:"
        if host:
            local += "\n    Copy:  scp" + commands.mkarg("%s:%s" % (host, corePath)) + " ."
        local += "\n    Debug: gdb python -c" + commands.mkarg(os.path.basename(corePath))
        diagnostic.append(local)
        return diagnostic

    def __reportDiagnostic(self, transcoder, workerName=None):
        
        def formatDuration(sec):
            if sec == None:
                return "Unknown Duration"
            return "%dm %ds %d" % (int(sec / 60),
                                   int(sec % 60),
                                   int((sec - int(sec)) * 1000))
        
        diagnostic = ["SOURCE FILE INFO\n----------------"]
        if not transcoder:
            return diagnostic
        report = transcoder.getReport()
        if not report:
            diagnostic.append("## No Transcoding Report ##")
            return diagnostic
        props = transcoder.getProperties()
        if not props:
            diagnostic.append("## No Component Properties ##")
            return diagnostic
        config = props.getConfig()
        if not config:
            diagnostic.append("## No Component Configuration ##")
            return diagnostic
        worker = transcoder.getWorker()
        if not worker and workerName:
            worker = self._workers.getWorker(workerName)
        if not workerName:
            workerName = (worker and worker.getName()) or "Unknown Worker"
        workerLocal = None
        adminLocal = None
        host = None
        if worker:
            host = worker.getHost()
            workerCtx = worker.getContext()
            workerLocal = workerCtx.getLocal()
            adminCtx = workerCtx.admin
            adminLocal = adminCtx.getLocal()
            
        # Select the proper Source File        
        if not adminLocal:
            sourceFile = report.source.lastPath
        else:
            alternatives = [report.source.lastPath,
                            report.source.failedPath,
                            report.source.donePath,
                            report.source.inputPath]
            for virtPath in alternatives:
                sourceFile = virtPath
                localPath = sourceFile.localize(adminLocal)
                if os.path.isfile(localPath):
                    break
            else:
                sourceFile = report.source.lastPath

        if workerLocal:
            sourcePath = sourceFile.localize(workerLocal)
            diagnostic.append("Source File:    %s" % sourcePath)
            if host:
                diagnostic.append("Copy Command:   scp" +
                                  commands.mkarg("%s:%s" % (host, sourcePath)) + " .")
        else:
            diagnostic.append("Virtual File:   %s" % sourceFile)
        # Source Size
        sourceSize = report.source.fileSize
        if sourceSize != None:
            diagnostic.append("File Size:      %s KB" % (sourceSize / 1024))
        else:
            diagnostic.append("File Size:      Unknwon")
        # Source Type        
        sourceType = report.source.fileType
        if sourceType:
            diagnostic.append("File Type:      %s" % sourceType)
        else:
            diagnostic.append("File Type:      Unknown")
        # Mime Type
        if report.source.analyse.mimeType:
            diagnostic.append("Mime Type:      %s" % report.source.analyse.mimeType)
        else:
            diagnostic.append("Mime Type:      Unknown")
        # Discovered Audio
        analyse = report.source.analyse
        if analyse.hasAudio:
            otherCodec = analyse.otherTags.get("audio-codec", "Unknown Codec")
            audioCodec = analyse.audioTags.get("audio-codec", None)
            info = audioCodec or otherCodec
            info += ", %s" % formatDuration(analyse.audioDuration)
            info += ", %d channels(s) : %dHz @ %dbits" % (analyse.audioChannels,
                                                        analyse.audioRate,
                                                        analyse.audioDepth)
            for tag, val in analyse.audioTags.items():
                if tag in set(["bitrate"]):
                    info += ", %s: %s" % (tag, val)
            diagnostic.append("Audio Info:     %s" % info)
        else:
            diagnostic.append("Audio Info:     Not Discovered")
        # Discovered Video
        if analyse.hasVideo:
            otherCodec = analyse.otherTags.get("video-codec", "Unknown Codec")
            audioCodec = analyse.audioTags.get("video-codec", None)
            info = audioCodec or otherCodec
            info += ", %s" % formatDuration(analyse.videoDuration)
            if not analyse.videoRate:
                rate = ""
            else:
                rate = "@ %d/%d fps" % analyse.videoRate
                rate +=  " (~ %d fps)" % int(round(analyse.videoRate[0]
                                                   / analyse.videoRate[1]))
            info += ", %d x %d %s" % (analyse.videoWidth,
                                      analyse.videoHeight,
                                      rate)
            for tag, val in analyse.audioTags.items():
                if tag in set(["bitrate"]):
                    info += ", %s: %s" % (tag, val)
            diagnostic.append("Video Info:     %s" % info)
        else:
            diagnostic.append("Video Info:     Not Discovered")
        # Source Header
        if report.source.fileHeader:
            sourceHeader = '\n    '.join(report.source.fileHeader)
            diagnostic.append("File Header:\n\n    %s" % sourceHeader)
        else:
            diagnostic.append("Unknwon Header")
        
        diagnostic.append("PIPELINE INFO\n-------------")
        # Pipelines
        if not report.source.pipeline:
            diagnostic.append("## No Pipeline Information ##")
        elif not "demuxer" in report.source.pipeline:
            diagnostic.append("## No Pipeline Section for Source Demuxer ##")
        else:
            gstlaunch = "GST_DEBUG=2 gst-launch -v "
            sourceFile = config.source.inputFile
            sourceLocation = commands.mkarg("location=" + sourceFile)
            demux = report.source.pipeline["demuxer"] + " name=demuxer"
            play1Pipeline = gstlaunch + "filesrc" + sourceLocation + " ! decodebin name=decoder"
            play2Pipeline = gstlaunch + demux.replace(" location=$FILE_PATH", sourceLocation)
            trans1Pipeline = gstlaunch + "filesrc" +  sourceLocation + " ! decodebin name=decoder"
            trans2Pipeline = gstlaunch + demux.replace(" location=$FILE_PATH", sourceLocation)
            base1Pipeline = trans1Pipeline
            base2Pipeline = trans2Pipeline
            if "video" in report.source.pipeline:
                videoSource = " demuxer. ! " + report.source.pipeline["video"]
                play1Pipeline += " decoder. ! ffmpegcolorspace ! videoscale ! autovideosink"
                play2Pipeline += videoSource + " ! ffmpegcolorspace ! videoscale ! autovideosink"
                trans1Pipeline += " decoder. ! 'video/x-raw-yuv;video/x-raw-rgb' ! tee name=vtee"
                trans2Pipeline += videoSource + " ! tee name=vtee"
                base2Pipeline += videoSource + " name=vsrc"
            if "audio" in report.source.pipeline:
                audioSource = " demuxer. ! " + report.source.pipeline["audio"]
                play1Pipeline += " decoder. ! audioconvert ! autoaudiosink"
                play2Pipeline += audioSource + " ! audioconvert ! autoaudiosink"
                trans1Pipeline += " decoder. ! 'audio/x-raw-int;audio/x-raw-float' ! tee name=atee"
                trans2Pipeline += audioSource + " ! tee name=atee"
                base2Pipeline += audioSource + " name=asrc"
            targetsPipelines = {}
            for name, target in report.targets.iteritems():
                type = config.targets[name].type
                if type in set([TargetTypeEnum.audio, TargetTypeEnum.video,
                                TargetTypeEnum.audiovideo]):
                    if target.pipeline:
                        targetFile = config.targets[name].outputFile
                        targetFile = os.path.join(os.path.dirname(targetFile),
                                                  "diagnostic_"
                                                  + os.path.basename(targetFile))
                        targetLocation = commands.mkarg("location=" + targetFile)
                        muxed = "muxer" in target.pipeline
                        if muxed:
                            # Target with muxer
                            muxerName = "muxer-%s" % name
                            muxer = " " + target.pipeline["muxer"]
                            muxer = muxer.replace(" ! ", " name=%s ! " % muxerName, 1)
                            muxer = muxer.replace(" location=$FILE_PATH", targetLocation)
                            trans1Pipeline += muxer
                            trans2Pipeline += muxer
                            targ1Pipeline = base1Pipeline + muxer
                            targ2Pipeline = base2Pipeline + muxer
                        if "video" in target.pipeline:
                            if muxed:
                                videoTarget = target.pipeline["video"] + " ! %s." % muxerName
                            else:
                                videoTarget = target.pipeline["video"]
                                videoTarget = videoTarget.replace(" location=$FILE_PATH", targetLocation)
                            trans1Pipeline += " vtee. ! " + videoTarget
                            trans2Pipeline += " vtee. ! " + videoTarget
                            targ1Pipeline += " decoder. ! " + videoTarget
                            targ2Pipeline += " vsrc. ! " + videoTarget
                        if "audio" in target.pipeline:
                            if muxed:
                                audioTarget = target.pipeline["audio"] + " ! %s." % muxerName
                            else:
                                audioTarget = target.pipeline["audio"]
                                audioTarget = audioTarget.replace(" location=$FILE_PATH", targetLocation)
                            trans1Pipeline += " atee. ! " + audioTarget
                            trans2Pipeline += " atee. ! " + audioTarget
                            targ1Pipeline += " decoder. ! " + audioTarget
                            targ2Pipeline += " asrc. ! " + audioTarget
                        targetsPipelines[name] = (targ1Pipeline, targ2Pipeline)
            diagnostic.append("PLAY SOURCE")
            diagnostic.append("  Dynamic:\n\n    " + play1Pipeline)
            diagnostic.append("  Static:\n\n    " + play2Pipeline)
            for name, (pipeline1, pipeline2) in targetsPipelines.iteritems():
                diagnostic.append("TRANSCODE TARGET " + name)
                diagnostic.append("  Dynamic:\n\n    " + pipeline1)
                diagnostic.append("  Static:\n\n    " + pipeline2)
            diagnostic.append("TRANSCODE ALL TARGETS")
            diagnostic.append("  Dynamic:\n\n    " + trans1Pipeline)
            diagnostic.append("  Static:\n\n    " + trans2Pipeline)

        return diagnostic


    def __buildSUCommand(self, command, args):
        cmd = "%s %s" % (command, reduce(str.__add__, map(commands.mkarg, args)))
        return "su -s /bin/bash - flumotion -c %s" % commands.mkarg(cmd)
