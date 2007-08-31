# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import re

from flumotion.common import messages

from flumotion.transcoder import log, defer, utils
from flumotion.transcoder.admin.proxies.monitorproxy import MonitorProxy
from flumotion.transcoder.admin.proxies.transcoderproxy import TranscoderProxy

class DiagnoseHelper(object):
    
    def __init__(self, managers, workers, components):
        self._managers = managers
        self._workers = workers
        self._components = components
        self._translator = messages.Translator()
        
    
    ## Public Methods ##
        
    def filterComponentMessage(self, message):
        debug = message.debug
        if message.level == 2: # WARNING
            if "twisted.internet.error.ConnectionDone" in debug:
                return True
            if "twisted.internet.error.ConnectionLost" in debug:
                return True
            if "is not a media file" in debug:
                return True
        return False

    _crashMessagePattern = re.compile("The core dump is '([^']*)' on the host running '([^']*)'")
        
    def componentMessage(self, component, message):
        diagnostic = ["DIAGNOSTIC\n----------"]
        text = self._translator.translate(message)
        isCrashMessage = self._crashMessagePattern.search(text)
        workerName = None
        if isCrashMessage:
            corePath, workerName = isCrashMessage.groups()
            diagnostic.extend(self.__crashDiagnostic(workerName, corePath))
            
        if isinstance(component, MonitorProxy):
            diagnostic.extend(self.__monitorDiagnostic(component, workerName))
                
        if isinstance(component, TranscoderProxy):
            diagnostic.extend(self.__transcoderDiagnostic(component, workerName))
        
        return '\n\n'.join(diagnostic)

    def transcodingFailure(self, task, transcoder):
        diagnostic = ["DIAGNOSTIC\n----------"]
        diagnostic.extend(self.__transcoderDiagnostic(transcoder))
        report = transcoder.getReport()
        if not report:
            diagnostic.append("No report found")
            
        return '\n\n'.join(diagnostic)


    ## Private Methods ##
    
    def __workerHost(self, worker):
        if not worker:
            return "Unknown Host"
        host = worker.getHost()
        if host:
            return host
        return "Unknown Host for worker %s" % worker.getName()
    
    def __monitorDiagnostic(self, monitor, workerName=None):
        diagnostic = []
        if not monitor:
            return diagnostic
        worker = monitor.getWorker()
        if not worker and workerName:
            worker = self._workers.getWorker(workerName)
        host = self.__workerHost(worker)
        if not worker:
            diagnostic.append("file-monitor without worker")
            return diagnostic
        props = monitor.getProperties()
        if not props:
            diagnostic.append("file-monitor without properties")
            return diagnostic
        args = props.asLaunchArguments(worker.getContext())
        diagnostic.append("Manual Launch on %s:\n"
                          "   flumotion-launch -d 4 file-monitor '%s'"
                          % (host, "' '".join(args)))
        return diagnostic

    def __transcoderDiagnostic(self, transcoder, workerName=None):
        diagnostic = []
        if not transcoder:
            return diagnostic
        worker = transcoder.getWorker()
        if not worker and workerName:
            worker = self._workers.getWorker(workerName)
        host = self.__workerHost(worker)
        if not worker:
            diagnostic.append("file-transcoder without worker")
            return diagnostic
        workerCtx = worker.getContext()
        local = workerCtx.getLocal()
        props = transcoder.getProperties()
        if not props:
            diagnostic.append("file-transcoder without properties")
        else:
            args = props.asLaunchArguments(workerCtx)
            diagnostic.append("Manual Launch on %s:\n"
                              "   GST_DEBUG=2 flumotion-launch -d 4 "
                              "file-transcoder '%s'"
                              % (host, "' '".join(args)))
        reportVirtPath = transcoder.getReportPath()
        if reportVirtPath:
            diagnostic.append("Diagnose Launch on %s:\n"
                              "   GST_DEBUG=2 flumotion-launch -d 4 "
                              "file-transcoder diagnose='%s'"
                              % (host, reportVirtPath.localize(local)))
        return diagnostic
    
    def __crashDiagnostic(self, workerName, corePath):
        diagnostic = []
        worker = self._workers.getWorker(workerName)
        diagnostic.append("Debug Core:     gdb python -c '%s'" % (corePath))
        if worker:
            host = worker.getHost()
            if host:
                diagnostic.append("Copy Core:      scp %s:%s ." % (host, corePath))
        return diagnostic
