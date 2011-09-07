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

import os
import re

from flumotion.common import i18n

from flumotion.inhouse import log, defer, utils, decorators

from flumotion.transcoder.enums import TargetTypeEnum, TranscodingFailureEnum
from flumotion.transcoder.admin import diagutils, document, adminconsts
from flumotion.transcoder.admin.enums import DocumentTypeEnum
from flumotion.transcoder.admin.proxy import monitor, transcoder


class Diagnostician(object):

    def __init__(self, adminCtx, managerPxySet, workerPxySet, compPxySet):
        self._adminCtx = adminCtx
        self._managerPxySet = managerPxySet
        self._workerPxySet = workerPxySet
        self._compPxySet = compPxySet
        self._translator = i18n.Translator()


    ## Public Methods ##

    def initialize(self):
        return defer.succeed(self)

    _debugFilter = {None: # Any message level
                      ("twisted.internet.error.ConnectionLost",
                       "twisted.internet.error.ConnectionDone"),
                    1: # ERROR level
                      ("Source file not found",),
                    2: # WARNING level
                      ("is not a known media type",
                       "output file stalled during transcoding",
                       "Source file not found",
                       "Source media doesn't have audio stream",
                       "Source media doesn't have video stream",
                       "flumotion.common.errors.SleepingComponentError",
                       "flumotion.transcoder.errors.TranscoderError: Expected video, and got no video"
                       "flumotion.transcoder.errors.TranscoderError: Source media doesn't have video stream",
                       "flumotion.transcoder.errors.TranscoderError: Transcoder pipeline stalled at prerolling")}

    def filterComponentMessage(self, message):
        debug = message.debug
        if not debug: return False
        for level in self._debugFilter:
            if (level == None) or (level == message.level):
                for substr in self._debugFilter[level]:
                    if substr in debug:
                        return True
        return False

    _crashMessagePattern = re.compile("The core dump is '([^']*)' on the host running '([^']*)'")

    @decorators.ensureDeferred
    def diagnoseComponentMessage(self, compPxy, message):
        diagnostic = []
        d = defer.succeed(diagnostic)
        if isinstance(compPxy, transcoder.TranscoderProxy):
            # Ensure we have the last report path
            d.addCallback(self.__waitReportPath, compPxy)
        d.addCallback(self.__componentDiagnostic, compPxy)
        text = self._translator.translate(message)
        isCrashMessage = self._crashMessagePattern.search(text)
        workerName = None
        if isCrashMessage:
            corePath, workerName = isCrashMessage.groups()
            d.addCallback(self.__crashDiagnostic, workerName, corePath)

        if isinstance(compPxy, monitor.MonitorProxy):
            d.addCallback(self.__monitorDiagnostic, compPxy, workerName)

        if isinstance(compPxy, transcoder.TranscoderProxy):
            d.addCallback(self.__sourceFileDiagnostic, compPxy, workerName)
            d.addCallback(self.__transcoderDiagnostic, compPxy, workerName)
            d.addCallback(self.__pipelineDiagnostic, compPxy, workerName)

        d.addCallback(self.__finishComponentMessageDiagnostic)
        return d

    @decorators.ensureDeferred
    def diagnoseTranscodingFailure(self, task, transPxy):
        diagnostic = []
        d = defer.succeed(diagnostic)
        # Ensure we have the last report path
        d.addCallback(self.__waitReportPath, transPxy)
        d.addCallback(self.__componentDiagnostic, transPxy)
        d.addCallback(self.__sourceFileDiagnostic, transPxy)
        d.addCallback(self.__transcoderDiagnostic, transPxy)
        d.addCallback(self.__pipelineDiagnostic, transPxy)

        d.addCallback(self.__finishTranscodingFailureDiagnostic)
        return d


    ## Private Methods ##

    def __buildSUCommand(self, command, args):
        cmd = "%s %s" % (command, " ".join(args))
        return "su -s /bin/bash - flumotion -c" + utils.mkCmdArg(cmd)

    def __buildSCPCommand(self, host, file, dest='.'):
        remote = utils.mkCmdArg(file, '')
        source = utils.mkCmdArg(remote, host + ':')
        dest = utils.mkCmdArg(dest)
        return "scp " + source + dest

    def __lookupProperties(self, compPxy):
        if not compPxy: return None
        return compPxy.getProperties()

    def __waitReportPath(self, diagnostic, transPxy):
        if not transPxy: return None
        d = transPxy.retrieveReportPath()
        d.addCallback(defer.overrideResult, diagnostic)
        return d

    def __lookupReport(self, transPxy):
        if not transPxy: return None
        return transPxy.getReport()

    def __lookupConfig(self, transPxy):
        if not transPxy: return None
        props = self.__lookupProperties(transPxy)
        return props and props.getConfig()

    def __lookupWorker(self, compPxy, workerName=None):
        workerPxy = None
        if compPxy:
            workerPxy = compPxy.getWorkerProxy()
        if (not workerPxy and not workerName
           and isinstance(compPxy, transcoder.TranscoderProxy)):
            report = self.__lookupReport(compPxy)
            workerName = report and report.local.name
        if not workerPxy and workerName:
            workerPxy = self._workerPxySet.getWorkerProxyByName(workerName)
        workerHost = workerPxy and workerPxy.getHost()
        return (workerPxy, workerName, workerHost)

    def __lookupInputPath(self, transPxy, workerName=None):
        virtPath, localPath, remotePath = None, None, None
        if not transPxy: return (virtPath, localPath, remotePath)
        report = self.__lookupReport(transPxy)
        if not report: return (virtPath, localPath, remotePath)
        virtPath = report.source.lastPath
        config = self.__lookupConfig(transPxy)
        if not config: return (virtPath, localPath, remotePath)
        transPxy = self.__lookupWorker(transPxy, workerName)[0]
        workerLocal = transPxy and transPxy.getWorkerContext().getLocal()
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

    def __componentDiagnostic(self, diagnostic, compPxy, workerName=None):
        if not compPxy: return diagnostic
        diagnostic.append("COMPONENT INFO\n--------------")
        workerName, workerHost = self.__lookupWorker(compPxy)[1:3]
        pid = compPxy.getPID()
        diagnostic.append("Component PID:  %s" % (pid or "Unknown"))
        diagnostic.append("Worker Name:    %s" % (workerName or "Unknown"))
        diagnostic.append("Worker Host:    %s" % (workerHost or "Unknown"))
        if workerHost:
            diagnostic.append("Go to Worker:   ssh -At %s" % workerHost)
        return diagnostic

    def __monitorDiagnostic(self, diagnostic, monPxy, workerName=None):
        if not monPxy: return diagnostic
        workerPxy, workerName = self.__lookupWorker(monPxy, workerName)[0:2]
        if not workerPxy: return diagnostic
        props = self.__lookupProperties(monPxy)
        if not props: return diagnostic
        diagnostic.append("MANUAL LAUNCH\n-------------")
        args = props.asLaunchArguments(workerPxy.getWorkerContext())
        origCmd = self.__buildSUCommand("flumotion-launch -d 4 "
                                        "file-monitor", args)

        diagnostic.append("  Original Command:")
        diagnostic.append("    " + origCmd)
        return diagnostic

    def __transcoderDiagnostic(self, diagnostic, transPxy, workerName=None):
        if not transPxy: return diagnostic
        workerPxy, workerName = self.__lookupWorker(transPxy, workerName)[0:2]
        if not transcoder: return diagnostic
        # Use retrieveReportPath because getReportPath sometime fail
        # because to the report file has been moved
        d = transPxy.retrieveReportPath()
        d.addCallback(self.__cbGotReportForTranscoderDiagnostic, diagnostic,
                      transPxy, workerPxy, workerName)
        return d

    def __cbGotReportForTranscoderDiagnostic(self, reportVirtPath, diagnostic,
                                             transPxy, workerPxy, workerName):
        props = self.__lookupProperties(transPxy)
        if not (props or reportVirtPath): return diagnostic
        workerCtx = workerPxy.getWorkerContext()
        workerLocal = workerCtx.getLocal()
        diagnostic.append("MANUAL LAUNCH\n-------------")
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

    def __crashDiagnostic(self, diagnostic, workerName, corePath):
        if not workerName: return diagnostic
        diagnostic.append("CRASH DEBUG\n-----------")
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

    def __sourceFileDiagnostic(self, diagnostic, transPxy, workerName=None):
        if not transPxy: return diagnostic
        report = self.__lookupReport(transPxy)
        if not report: return diagnostic
        pathInfo = self.__lookupInputPath(transPxy, workerName)
        inputVirtPath, inputLocalPath, inputRemotePath = pathInfo
        workerInfo = self.__lookupWorker(transPxy, workerName)
        workerName, workerHost = workerInfo[1:3]

        diagnostic.append("SOURCE FILE INFO\n----------------")

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
                          + (report.source.analysis.mimeType or "Unknown"))
        # Discovered Audio
        audioBrief = diagutils.extractAudioBrief(report.source.analysis)
        diagnostic.append("Audio Info:     " + (audioBrief or "Not Discovered"))
        # Discovered Video
        videoBrief = diagutils.extractVideoBrief(report.source.analysis)
        diagnostic.append("Video Info:     " + (videoBrief or "Not Discovered"))
        # Source Header
        if report.source.fileHeader:
            header = '    ' + '\n    '.join(report.source.fileHeader)
            diagnostic.append("File Header:")
            diagnostic.append(header)
        else:
            diagnostic.append("Unknown File Header")

        return diagnostic

    def __pipelineDiagnostic(self, diagnostic, transPxy, workerName=None):
        if not transPxy: return diagnostic
        report = self.__lookupReport(transPxy)
        config = self.__lookupConfig(transPxy)
        if not (config and report): return diagnostic
        pathInfo = self.__lookupInputPath(transPxy, workerName)
        virtInputPath = pathInfo[0]
        targetFileTemplate = "diag_%(filename)s"
        gstlaunch = "GST_DEBUG=2 gst-launch -v "
        inputPath = os.path.basename(virtInputPath.getPath())

        pipeDiag = []
        analysis = report.source.analysis
        # If the discover fail, assume the source has audio and video
        sourceHasAudio = analysis.hasAudio or (not analysis.mimeType)
        sourceHasVideo = analysis.hasVideo or (not analysis.mimeType)
        pipeInfo = diagutils.extractPlayPipeline(config, report,
                                                 sourcePath=inputPath,
                                                 playAudio=sourceHasAudio,
                                                 playVideo=sourceHasVideo)
        pipeAudit = diagutils.extractPlayPipeline(config, report, fromAudit=True,
                                                  sourcePath=inputPath,
                                                  playAudio=sourceHasAudio,
                                                  playVideo=sourceHasVideo)
        if pipeInfo or pipeAudit:
            pipeDiag.append("PLAY SOURCE")
            if pipeInfo:
                pipeDiag.append("  Pipeline Command:")
                pipeDiag.append("    " + gstlaunch + pipeInfo)
            if pipeAudit:
                pipeDiag.append("  Pipeline Audit:")
                pipeDiag.append("    " + gstlaunch + pipeAudit)

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
                    pipeDiag.append("TRANSCODE TARGET " + name)
                    if pipeInfo:
                        pipeDiag.append("  Pipeline Command:")
                        pipeDiag.append("    " + gstlaunch + pipeInfo)
                    if pipeAudit:
                        pipeDiag.append("  Pipeline Audit:")
                        pipeDiag.append("    " + gstlaunch + pipeAudit)

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
                pipeDiag.append("TRANSCODE ALL TARGETS")
                if pipeInfo:
                    pipeDiag.append("  Pipeline Command:")
                    pipeDiag.append("    " + gstlaunch + pipeInfo)
                if pipeAudit:
                    pipeDiag.append("  Pipeline Audit:")
                    pipeDiag.append("    " + gstlaunch + pipeAudit)

        if pipeDiag:
            diagnostic.append("PIPELINE INFO\n-------------")
            diagnostic.extend(pipeDiag)
        return diagnostic


    def __finishComponentMessageDiagnostic(self, diagnostic):
        if not diagnostic: return []
        text = "DIAGNOSTIC\n==========\n\n" + '\n\n'.join(diagnostic) + '\n'
        label = "Component Message Diagnostic"
        return [document.StringDocument(DocumentTypeEnum.diagnostic, label, text)]

    def __finishTranscodingFailureDiagnostic(self, diagnostic):
        if not diagnostic: return []
        text = "DIAGNOSTIC\n==========\n\n" + '\n\n'.join(diagnostic) + '\n'
        label = "Transcoding Failure Diagnostic"
        return [document.StringDocument(DocumentTypeEnum.diagnostic, label, text)]

"""
Tries to determine whether or not a file should fail, e.g. by checking its mime
type or its size. Its configuration is a single editable file containing
a list of values such as regular expressions. The location of this file is
specified in transcoder-admin.ini, in the field 'prognosis-file'.
"""
class Prognostician(log.Loggable):

    logCategory = adminconsts.ADMIN_LOG_CATEGORY

    mime_key = '[mime-type]'
    type_key = '[file-type]'
    min_video_size_key = '[min-video-size]'
    min_audio_size_key = '[min-audio-size]'
    file_size_key = '[file-size]'
    has_video_key = '[has-video]'

    def __init__(self, config):
        if config:
            self.parse(config)

    """
    Returns a list of reasons (strings) why this file should fail.
    file_data is a dictionary containing information about the file that
    matters to the Prognostician, e.g. file_size, mime_type, file_type,
    has_video.
    """
    def prognose(self, file_data):
        if self.check_mime_type(file_data):
            return TranscodingFailureEnum.wrong_mime_type
        if self.check_file_type(file_data):
            return TranscodingFailureEnum.wrong_file_type
        # this happens when the file is not a known media type. In this case,
        # the size check is skipped
        if file_data[self.has_video_key] is None:
            return None
        if file_data[self.has_video_key]:
            if self.check_video_size(file_data):
                return TranscodingFailureEnum.video_too_small
        else:
            if self.check_audio_size(file_data):
                return TranscodingFailureEnum.audio_too_small
        return None

    def check_mime_type(self, data):
        file_mime = data[self.mime_key]
        if not file_mime:
            #FIXME: not sure at all about this
            return False
        for mime in self.mime_types:
            pattern=re.compile(mime)
            if(pattern.match(file_mime)):
                return True
        return False

    def check_file_type(self, data):
        file_type = data[self.type_key]
        if not file_type:
            return False
        for t in self.file_types:
            pattern=re.compile(t)
            if(pattern.match(file_type)):
                return True
        return False

    def check_video_size(self, data):
        video_size = data[self.file_size_key]
        if not video_size:
            return False
        if video_size < int(self.min_video_size):
            return True
        return False

    def check_audio_size(self, data):
        audio_size = data[self.file_size_key]
        if not audio_size:
            return False
        if audio_size < int(self.min_audio_size):
            return True
        return False

    def parse(self, path):
        headers = {self.mime_key: [],
                   self.type_key: [],
                   self.min_audio_size_key: 0,
                   self.min_video_size_key: 0}
        f = open(path, 'r')
        current_type = None
        for l in f.readlines():
            l=l.rstrip('\n \t')
            if len(l) == 0 or l.startswith('#'):
                continue
            header = self.extract_header(l, headers)
            if header is not None:
                current_type = header
                continue
            #it's not a header line and there is no current category
            if current_type is None:
                self.debug("Prognosis: Ignoring line %s", l)
            #it's a config line and and we are inside a category
            else:
                self.set_config_element(current_type, l, headers)
        f.close()

        self.mime_types = headers[self.mime_key]
        self.file_types = headers[self.type_key]
        self.min_audio_size = headers[self.min_audio_size_key]
        self.min_video_size = headers[self.min_video_size_key]

        self.debug("Mime Types: %s", self.mime_types)
        self.debug("File Types: %s", self.file_types)
        self.debug("Min Audio Size: %s", self.min_audio_size)
        self.debug("Min Video Size: %s", self.min_video_size)

    def extract_header(self, s, headers):
        if s in headers:
            value = headers[s]
            return s
        return None

    def set_config_element(self, t, element, headers):
        current_value = headers[t]
        header_type = type(current_value)
        if header_type == type([]):
            headers[t].append(element)
        else:
            headers[t] = element

    def append(self, result, list):
        if result:
            list.append(result)
