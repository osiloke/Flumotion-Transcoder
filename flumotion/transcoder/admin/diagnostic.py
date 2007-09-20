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

from flumotion.common import messages

from flumotion.transcoder import log, defer, utils
from flumotion.transcoder.enums import TargetTypeEnum
from flumotion.transcoder.admin import diagutils
from flumotion.transcoder.admin.enums import DocumentTypeEnum
from flumotion.transcoder.admin.document import StringDocument
from flumotion.transcoder.admin.proxies.monitorproxy import MonitorProxy
from flumotion.transcoder.admin.proxies.transcoderproxy import TranscoderProxy

class Diagnostician(object):
    
    def __init__(self, adminContext, managers, workers, components):
        self._adminCtx = adminContext
        self._managers = managers
        self._workers = workers
        self._components = components
        self._translator = messages.Translator()
        
    
    ## Public Methods ##
    
    def initialize(self):
        return defer.succeed(self)
        
    def filterComponentMessage(self, message):
        debug = message.debug
        if "twisted.internet.error.ConnectionLost" in debug:
            return True
        if "twisted.internet.error.ConnectionLost" in debug:
            return True
        if message.level == 2: # WARNING
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
        
    def diagnoseComponentMessage(self, component, message):
        diagnostic = []
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
            diagnostic.extend(self.__sourceFileDiagnostic(component, workerName))
            diagnostic.extend(self.__transcoderDiagnostic(component, workerName))
            diagnostic.extend(self.__pipelineDiagnostic(component, workerName))
            
        
        if not diagnostic: return []
        text = "DIAGNOSTIC\n==========\n\n" + '\n\n'.join(diagnostic) + '\n'
        label = "Component Message Diagnostic"
        return [StringDocument(DocumentTypeEnum.diagnostic, label, text)]
        

    def diagnoseTranscodingFailure(self, task, transcoder):
        diagnostic = []
        diagnostic.extend(self.__componentDiagnostic(transcoder))
        diagnostic.extend(self.__sourceFileDiagnostic(transcoder))
        diagnostic.extend(self.__transcoderDiagnostic(transcoder))
        diagnostic.extend(self.__pipelineDiagnostic(transcoder))
        
        if not diagnostic: return []
        text = "DIAGNOSTIC\n==========\n\n" + '\n\n'.join(diagnostic) + '\n'
        label = "Transcoding Failure Diagnostic"
        return [StringDocument(DocumentTypeEnum.diagnostic, label, text)]


    ## Private Methods ##
    
    def __buildSUCommand(self, command, args):
        cmd = "%s %s" % (command, " ".join(args))
        return "su -s /bin/bash - flumotion -c" + utils.mkCmdArg(cmd)
    
    def __buildSCPCommand(self, host, file, dest='.'):
        remote = utils.mkCmdArg(file, '')
        source = utils.mkCmdArg(remote, host + ':')
        dest = utils.mkCmdArg(dest)
        return "scp " + source + dest
    
    def __lookupProperties(self, component):
        if not component: return None
        return component.getProperties()
    
    def __lookupReport(self, transcoder):
        if not transcoder: return None
        return transcoder.getReport()
    
    def __lookupConfig(self, transcoder):
        if not transcoder: return None
        props = self.__lookupProperties(transcoder)
        return props and props.getConfig()
    
    def __lookupWorker(self, component, workerName=None):
        worker = None
        if component:
            worker = component.getWorker()
        if (not worker and not workerName
           and isinstance(component, TranscoderProxy)):
            report = self.__lookupReport(component)
            workerName = report and report.local.name
        if not worker and workerName:
            worker = self._workers.getWorker(workerName)
        workerHost = worker and worker.getHost()
        return (worker, workerName, workerHost)
    
    def __lookupInputPath(self, transcoder, workerName=None):
        virtPath, localPath, remotePath = None, None, None
        if not transcoder: return (virtPath, localPath, remotePath)
        report = self.__lookupReport(transcoder)
        if not report: return (virtPath, localPath, remotePath)
        virtPath = report.source.lastPath
        config = self.__lookupConfig(transcoder)
        if not config: return (virtPath, localPath, remotePath)
        worker = self.__lookupWorker(transcoder, workerName)[0]
        workerLocal = worker and worker.getContext().getLocal()
        adminLocal = self._adminCtx.getLocal()
        alternatives = [report.source.lastPath,
                        report.source.failedPath,
                        report.source.donePath,
                        report.source.inputPath]
        for vp in alternatives:
            lp = vp.localize(adminLocal)
            if os.path.isfile(lp):
                virtPath = vp
                localPath = lp
                if workerLocal:
                    remotePath = vp.localize(workerLocal)
                break
        return (virtPath, localPath, remotePath)
    
    def __componentDiagnostic(self, component, workerName=None):
        if not component: return []
        diagnostic = ["COMPONENT INFO\n--------------"]
        workerName, workerHost = self.__lookupWorker(component)[1:3]
        pid = component.getPID()
        diagnostic.append("Component PID:  %s" % (pid or "Unknown"))
        diagnostic.append("Worker Name:    %s" % (workerName or "Unknown"))
        diagnostic.append("Worker Host:    %s" % (workerHost or "Unknown"))
        if workerHost:
            diagnostic.append("Go to Worker:   ssh -At %s" % workerHost)
        return diagnostic
    
    def __monitorDiagnostic(self, monitor, workerName=None):
        if not monitor: return []
        worker, workerName = self.__lookupWorker(monitor, workerName)[0:2]
        if not worker: return []
        props = self.__lookupProperties(monitor)
        if not props: return []
        diagnostic = ["MANUAL LAUNCH\n-------------"]
        args = props.asLaunchArguments(worker.getContext())
        origCmd = self.__buildSUCommand("flumotion-launch -d 4 "
                                        "file-monitor", args)
        
        diagnostic.append("  Original Command:")
        diagnostic.append("    " + origCmd)
        return diagnostic

    def __transcoderDiagnostic(self, transcoder, workerName=None):
        if not transcoder: return []
        worker, workerName = self.__lookupWorker(transcoder, workerName)[0:2]
        if not worker: return []
        workerCtx = worker.getContext()
        workerLocal = workerCtx.getLocal()
        props = self.__lookupProperties(transcoder)
        reportVirtPath = transcoder.getReportPath()
        if not (props or reportVirtPath): return []
        diagnostic = ["MANUAL LAUNCH\n-------------"]
        if props:
            args = props.asLaunchArguments(workerCtx)
            origCmd = self.__buildSUCommand("GST_DEBUG=2 flumotion-launch -d 4 "
                                            "file-transcoder", args)
            diagnostic.append("  Original Command:")
            diagnostic.append("    " + origCmd)
        
        if reportVirtPath:
            reportPath = reportVirtPath.localize(workerLocal)
            args = [utils.mkCmdArg(reportPath, "diagnose=")]
            diagCmd = self.__buildSUCommand("GST_DEBUG=2 flumotion-launch -d 4 "
                                            "file-transcoder", args)
            diagnostic.append("  Diagnose Command:")
            diagnostic.append("    " + diagCmd)
        return diagnostic
    
    def __crashDiagnostic(self, workerName, corePath):
        if not workerName: return []
        diagnostic = ["CRASH DEBUG\n-----------"]
        workerInfo = self.__lookupWorker(None, workerName)
        workerName, workerHost = workerInfo[1:3]
        
        diagnostic.append("Debug Core Inplace")
        if workerHost:            
            diagnostic.append("    Login: ssh -At " + workerHost)
        arg = utils.mkCmdArg(corePath)
        diagnostic.append("    Debug: gdb python -c" + arg)
        
        diagnostic.append("Debug Core Locally")
        if workerHost:
            scpCmd = self.__buildSCPCommand(workerHost, corePath)
            diagnostic.append("    Copy:  " + scpCmd)
        arg = utils.mkCmdArg(os.path.basename(corePath))
        diagnostic.append("    Debug: gdb python -c" + arg)

        return diagnostic

    def __sourceFileDiagnostic(self, transcoder, workerName=None):
        if not transcoder: return []
        report = self.__lookupReport(transcoder)
        if not report: return []
        pathInfo = self.__lookupInputPath(transcoder, workerName)
        inputVirtPath, inputLocalPath, inputRemotePath = pathInfo
        workerInfo = self.__lookupWorker(transcoder, workerName)
        workerName, workerHost = workerInfo[1:3]
        
        diagnostic = ["SOURCE FILE INFO\n----------------"]
        
        # File Path
        diagnostic.append("Virtual Path:   %s" % (inputVirtPath or "Unknown"))
        if inputLocalPath and ((not inputRemotePath) or (inputRemotePath != inputRemotePath)):
            diagnostic.append("Local Path:     " + inputLocalPath)
        if inputRemotePath:
            diagnostic.append("Remote Path:    " + inputRemotePath)
            if workerHost:
                scpCmd = self.__buildSCPCommand(workerHost, inputRemotePath)
                diagnostic.append("Copy Command:   " + scpCmd)

        # Source Size
        diagnostic.append("File Size:      " 
                          + diagutils.formatFileSize(report.source.fileSize,
                                                     "Unknown"))
        # Source Type        
        diagnostic.append("File Type:      " 
                          + (report.source.fileType or "Unknown"))
        # Mime Type
        diagnostic.append("Mime Type:      "
                          + (report.source.analyse.mimeType or "Unknown"))
        # Discovered Audio
        audioBrief = diagutils.extractAudioBrief(report.source.analyse)
        diagnostic.append("Audio Info:     " + (audioBrief or "Not Discovered"))
        # Discovered Video
        videoBrief = diagutils.extractVideoBrief(report.source.analyse)
        diagnostic.append("Video Info:     " + (videoBrief or "Not Discovered"))
        # Source Header
        if report.source.fileHeader:
            header = '    ' + '\n    '.join(report.source.fileHeader)
            diagnostic.append("File Header:")
            diagnostic.append(header)
        else:
            diagnostic.append("Unknown File Header")
        
        return diagnostic

    def __pipelineDiagnostic(self, transcoder, workerName=None):
        if not transcoder: return []
        report = self.__lookupReport(transcoder)
        config = self.__lookupConfig(transcoder)
        if not (config and report): return []
        pathInfo = self.__lookupInputPath(transcoder, workerName)
        virtInputPath = pathInfo[0]
        targetFileTemplate = "diag_%(filename)s"
        gstlaunch = "GST_DEBUG=2 gst-launch -v "
        inputPath = os.path.basename(virtInputPath.getPath())
        
        diagnostic = []
        analyse = report.source.analyse
        # If the discover fail, assume the source has audio and video
        sourceHasAudio = analyse.hasAudio or (not analyse.mimeType)
        sourceHasVideo = analyse.hasVideo or (not analyse.mimeType)
        pipeInfo = diagutils.extractPlayPipeline(config, report,
                                                 sourcePath=inputPath,
                                                 playAudio=sourceHasAudio,
                                                 playVideo=sourceHasVideo)
        pipeAudit = diagutils.extractPlayPipeline(config, report, fromAudit=True,
                                                  sourcePath=inputPath,
                                                  playAudio=sourceHasAudio,
                                                  playVideo=sourceHasVideo)
        if pipeInfo or pipeAudit:
            diagnostic.append("PLAY SOURCE")
            if pipeInfo:
                diagnostic.append("  Pipeline Command:")
                diagnostic.append("    " + gstlaunch + pipeInfo)
            if pipeAudit:
                diagnostic.append("  Pipeline Audit:")
                diagnostic.append("    " + gstlaunch + pipeAudit)
        
        allTargets = []
        for name, targReport in report.targets.iteritems():
            type = config.targets[name].type
            if type in set([TargetTypeEnum.audio,
                            TargetTypeEnum.video,
                            TargetTypeEnum.audiovideo]):
                if not targReport.pipelineInfo:
                    continue
                allTargets.append(name)
                pipeInfo = diagutils.extractTransPipeline(config, report,
                                                          onlyForTargets=[name],
                                                          sourcePath=inputPath,
                                                          targetFileTemplate=targetFileTemplate)
                pipeAudit = diagutils.extractTransPipeline(config, report, fromAudit=True,
                                                           onlyForTargets=[name],
                                                           sourcePath=inputPath,
                                                           targetFileTemplate=targetFileTemplate)
                if pipeInfo or pipeAudit:
                    diagnostic.append("TRANSCODE TARGET " + name)
                    if pipeInfo:
                        diagnostic.append("  Pipeline Command:")
                        diagnostic.append("    " + gstlaunch + pipeInfo)
                    if pipeAudit:
                        diagnostic.append("  Pipeline Audit:")
                        diagnostic.append("    " + gstlaunch + pipeAudit)

        if allTargets:
            pipeInfo = diagutils.extractTransPipeline(config, report,
                                                      onlyForTargets=allTargets,
                                                      sourcePath=inputPath,
                                                      targetFileTemplate=targetFileTemplate)
            pipeAudit = diagutils.extractTransPipeline(config, report, fromAudit=True,
                                                       onlyForTargets=allTargets,
                                                       sourcePath=inputPath,
                                                       targetFileTemplate=targetFileTemplate)
            if pipeInfo or pipeAudit:
                diagnostic.append("TRANSCODE ALL TARGETS")
                if pipeInfo:
                    diagnostic.append("  Pipeline Command:")
                    diagnostic.append("    " + gstlaunch + pipeInfo)
                if pipeAudit:
                    diagnostic.append("  Pipeline Audit:")
                    diagnostic.append("    " + gstlaunch + pipeAudit)

        if diagnostic:
            return ["PIPELINE INFO\n-------------"] + diagnostic
        return []
