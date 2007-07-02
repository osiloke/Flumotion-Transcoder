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

import os.path

from twisted.internet import reactor, error, defer
from twisted.python.failure import Failure

from flumotion.common import common, messages
from flumotion.component import component
from flumotion.component.component import moods

from flumotion.transcoder import log
from flumotion.transcoder.enums import MonitorFileStateEnum
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.errors import TranscoderConfigError
from flumotion.component.transcoder import compconsts
from flumotion.component.transcoder.watcher import DirectoryWatcher

from flumotion.common.messages import N_
T_ = messages.gettexter('flumotion-transcoder')


class FileMonitorMedium(component.BaseComponentMedium):
    
    def remote_setFileState(self, base, file, status):
        self.comp.setFileState(base, file, status)


class FileMonitor(component.BaseComponent):
    """
    Monitor a list of directory.
    """
    
    componentMediumClass = FileMonitorMedium
    logCategory = compconsts.MONITOR_LOG_CATEGORY

    
    ## Overriden Methods ##

    def init(self):
        log.setDefaultCategory(compconsts.MONITOR_LOG_CATEGORY)
        self.uiState.addListKey('monitored-directories', [])
        self.uiState.addDictKey('pending-files', {})
        self.watchers = []

    def do_setup(self):
        
        def monitor_setup(result):
            props = self.config["properties"]
            directories = props.get("directory", [])
            self.uiState.set('monitored-directories', directories)
            for directory in directories:
                common.ensureDir(directory, "monitored")
            return result
    
        d = component.BaseComponent.do_setup(self)
        d.addCallback(monitor_setup)
        d.addErrback(self.__ebErrorFilter, "component setup")
        return d

    def do_start(self, *args, **kwargs):
        
        def monitor_startup(result):
            props = self.config["properties"]
            period = props["scan-period"]
            directories = props.get("directory", [])
            for d in directories:
                watcher = DirectoryWatcher(self, d, timeout=period)
                watcher.connect('file-added', self._file_added, d)
                watcher.connect('file-completed', self._file_completed, d)
                watcher.connect('file-removed', self._file_removed, d)
                watcher.start()
                self.watchers.append(watcher)
            return result
        
        d = component.BaseComponent.do_start(self)
        d.addCallback(monitor_startup)
        d.addErrback(self.__ebErrorFilter, "component startup")
        return d
        
    
    def do_stop(self, *args, **kwargs):
        for w in self.watchers:
            w.stop()
        self.watchers = []
        return component.BaseComponent.do_stop(self)
    

    ## Public Methods ##
                
    def setFileState(self, base, file, status):        
        self.uiState.setitem('pending-files', (base, file), status)


    ## Signal Handler Methods ##

    def _file_added(self, watcher, file, base):
        self.debug("File added : '%s'", os.path.join(base, file))
        self.uiState.setitem('pending-files', (base, file), 
                             MonitorFileStateEnum.downloading)
    
    def _file_completed(self, watcher, file, base):
        self.debug("File completed '%s'", os.path.join(base, file))
        self.uiState.setitem('pending-files', (base, file), 
                             MonitorFileStateEnum.pending)
    
    def _file_removed(self, watcher, file, base):
        self.debug("File removed '%s'", os.path.join(base, file))
        self.uiState.delitem('pending-files', (base, file))
    
    
    ## Private Methods ##
    
    def __ebErrorFilter(self, failure, task=None):
        if failure.check(TranscoderError):
            return self.__transcodingError(failure, task)
        return self.__unexpectedError(failure, task)

    def __monitorError(self, failure=None, task=None):
        if not failure:
            failure = Failure()
        self.warning("Monitoring error%s: %s", 
                     (task and " during %s" % task) or "",
                     log.getFailureMessage(failure))
        self.debug("Traceback with filenames cleaned up:\n%s", 
                   log.getFailureTraceback(failure, True))
        self.setMood(moods.sad)
        return failure
        
    def __unexpectedError(self, failure=None, task=None):
        if not failure:
            failure = Failure()
        self.warning("Unexpected error%s: %s", 
                     (task and " during %s" % task) or "",
                     log.getFailureMessage(failure))
        self.debug("Traceback with filenames cleaned up:\n%s", 
                   log.getFailureTraceback(failure, True))
        m = messages.Error(T_(failure.getErroMessage()), 
                           debug=log.getFailureMessage(failure))
        self.addMessage(m)
        return failure

    