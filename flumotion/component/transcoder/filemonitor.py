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

from flumotion.common import messages, log
from flumotion.component import component
from flumotion.component.component import moods

from flumotion.transcoder.enums import MonitorFileStateEnum
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
    logCategory = 'file-monitor'

    
    ## Overriden Methods ##

    def init(self):
        self.uiState.addListKey('monitored-directories', [])
        self.uiState.addDictKey('pending-files', {})
        self.watchers = []
        
    def do_setup(self):
        props = self.config["properties"]
        self.uiState.set('monitored-directories', props["directory"])
        return component.BaseComponent.do_setup(self)

    def do_start(self, *args, **kwargs):
        props = self.config["properties"]
        period = props["scan-period"]
        for d in props["directory"]:
            watcher = DirectoryWatcher(d, timeout=period)
            watcher.connect('file-added', self._file_added, d)
            watcher.connect('file-completed', self._file_completed, d)
            watcher.connect('file-removed', self._file_removed, d)
            watcher.start()
            self.watchers.append(watcher)
        return component.BaseComponent.do_start(self)
    
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
        self.debug("File added : '%s'" % os.path.join(base, file))
        self.uiState.setitem('pending-files', (base, file), 
                             MonitorFileStateEnum.downloading)
    
    def _file_completed(self, watcher, file, base):
        self.debug("File completed '%s'" % os.path.join(base, file))
        self.uiState.setitem('pending-files', (base, file), 
                             MonitorFileStateEnum.pending)
    
    def _file_removed(self, watcher, file, base):
        self.debug("File removed '%s'" % os.path.join(base, file))
        self.uiState.delitem('pending-files', (base, file))
        
    