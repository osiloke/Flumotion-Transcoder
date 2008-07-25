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
import shutil

from twisted.internet import reactor, error, threads
from twisted.python.failure import Failure

from flumotion.common import messages
from flumotion.common.i18n import gettexter, N_
from flumotion.component import component
from flumotion.component.component import moods

from flumotion.inhouse import log, defer, fileutils
from flumotion.inhouse.errors import FlumotionError

from flumotion.transcoder import constants
from flumotion.transcoder.local import Local
from flumotion.transcoder.virtualpath import VirtualPath
from flumotion.transcoder.enums import MonitorFileStateEnum
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.errors import TranscoderConfigError
from flumotion.component.transcoder import compconsts
from flumotion.component.transcoder.watcher import DirectoryWatcher

T_ = gettexter('flumotion-transcoder')


class FileMonitorMedium(component.BaseComponentMedium):
    
    def remote_setFileState(self, virtBase, relFile, status):
        self.comp.setFileState(virtBase, relFile, status)
        
    def remote_setFilesState(self, states):
        for virtBase, relFile, status in states:
            self.comp.setFileState(virtBase, relFile, status)
        
    def remote_moveFiles(self, virtSrcBase, virtDestBase, relFiles):
        self.comp.moveFiles(virtSrcBase, virtDestBase, relFiles)
        

class FileMonitor(component.BaseComponent):
    """
    Monitor a list of directory.
    """
    
    componentMediumClass = FileMonitorMedium
    logCategory = compconsts.MONITOR_LOG_CATEGORY


    ## Public Methods ##

    def moveFiles(self, virtSrcBase, virtDestBase, relFiles):
        if not self._local:
            raise TranscoderError("Component not properly setup yet")
        if not (virtSrcBase in self._directories):
                self.warning("Forbidden to move files from '%s'", virtSrcBase)
                raise TranscoderError("Forbidden to move a file from other "
                                      "directories than the monitored ones")
        
        def moveFile(result, src, dest, attr=None):

            def moveFailed(failure):
                msg = ("Fail to move file '%s' to '%s': %s" 
                       % (src, dest, log.getFailureMessage(failure)))
                self.warning("%s", msg)
                if isinstance(result, Failure):
                    return result
                raise TranscoderError(msg, cause=failure)

            self.debug("Moving file '%s' to '%s'", src, dest)
            destDir = os.path.dirname(dest)
            fileutils.ensureDirExists(destDir, "input file destination", attr)
            d = threads.deferToThread(shutil.move, src, dest)
            d.addCallbacks(defer.overrideResult, moveFailed,
                           callbackArgs=(result,))
            return d

        def moveFailed(failure, src, dest):
            msg = ("Fail to move file '%s' to '%s': %s" 
                   % (src, dest, log.getFailureMessage(failure)))
            self.warning("%s", msg)
            raise TranscoderError(msg, cause=e)
        
        d = defer.succeed(self)
        for relFile in relFiles:
            locSrcPath = virtSrcBase.append(relFile).localize(self._local)
            locDestPath = virtDestBase.append(relFile).localize(self._local)
            locSrcPath = os.path.realpath(locSrcPath)
            locDestPath = os.path.realpath(locDestPath)
            d.addBoth(moveFile, locSrcPath, locDestPath, self._pathAttr)
        return d
    
    ## Overriden Methods ##

    def init(self):
        log.setDefaultCategory(compconsts.MONITOR_LOG_CATEGORY)
        log.setDebugNotifier(self.__notifyDebug)
        self.uiState.addListKey('monitored-directories', [])
        self.uiState.addDictKey('pending-files', {})
        self.watchers = []
        self._local = None
        self._scanPeriod = None
        self._directories = []
        self._uiItemDelta = {}
        self._uiItemDelay = None
        self._pathAttr = None

    def do_check(self):
        
        def monitor_checks(result):
            props = self.config["properties"]
            self._local = Local.createFromComponentProperties(props)
            return result
        
        try:
            d = component.BaseComponent.do_check(self)
            d.addCallback(monitor_checks)
            d.addErrback(self.__ebErrorFilter, "component checking")
            return d
        except:
            self.__unexpectedError(task="component checking")

    def do_setup(self):
        try:
            props = self.config["properties"]
            self._scanPeriod = props["scan-period"]
            self._pathAttr = fileutils.PathAttributes.createFromComponentProperties(props)
            strDirs = props.get("directory", [])
            self._directories = map(VirtualPath, strDirs)
            self.uiState.set('monitored-directories', self._directories)
            for virtDir in self._directories:
                localDir = virtDir.localize(self._local)
                fileutils.ensureDirExists(localDir, "monitored",
                                          self._pathAttr)
                watcher = DirectoryWatcher(self, localDir, 
                                           timeout=self._scanPeriod)
                watcher.connect('file-added', 
                                self._file_added, virtDir)
                watcher.connect('file-completed', 
                                self._file_completed, virtDir)
                watcher.connect('file-removed', 
                                self._file_removed, virtDir)
                watcher.start()
                self.watchers.append(watcher)
            return None
        except:
            self.__unexpectedError(task="component setup")

    def do_stop(self, *args, **kwargs):
        for w in self.watchers:
            w.stop()
        self.watchers = []
        return component.BaseComponent.do_stop(self)
    

    ## Public Methods ##
                
    def setFileState(self, virtBase, relFile, status):        
        key = (virtBase, relFile)
        self.__updateUIItem('pending-files', key, status)


    ## Signal Handler Methods ##

    def _file_added(self, watcher, file, virtBase):
        localFile = virtBase.append(file).localize(self._local)
        self.debug("File added : '%s'", localFile)
        self.__setUIItem('pending-files', (virtBase, file), 
                         MonitorFileStateEnum.downloading)
    
    def _file_completed(self, watcher, file, virtBase):
        localFile = virtBase.append(file).localize(self._local)
        self.debug("File completed '%s'", localFile)
        self.__setUIItem('pending-files', (virtBase, file), 
                         MonitorFileStateEnum.pending)
    
    def _file_removed(self, watcher, file, virtBase):
        localFile = virtBase.append(file).localize(self._local)
        self.debug("File removed '%s'", localFile)
        self.__delUIItem('pending-files', (virtBase, file))
    
    
    ## Private Methods ##
    
    def __updateUIItem(self, key, subkey, value):
        self._uiItemDelta[(key, subkey)] = ("file state updating",
                                            self.__doUpdateItem, (value,))
        self.__smoothUpdate()
    
    def __setUIItem(self, key, subkey, value):
        self._uiItemDelta[(key, subkey)] = ("file state setting",
                                            self.uiState.setitem, (value,))
        self.__smoothUpdate()
    
    def __delUIItem(self, key, subkey):
        if (subkey in self.uiState.get(key)):
            self.uiState.delitem(key, subkey)
        if (key, subkey) in self._uiItemDelta:
            del self._uiItemDelta[(key, subkey)]
    
    def __doUpdateItem(self, key, subkey, value):
        state = self.uiState.get(key)
        if (subkey in state) and (state.get(subkey) != value):
            self.uiState.setitem(key, subkey, value)

    def __smoothUpdate(self):
        if (not self._uiItemDelay) and self._uiItemDelta:
            delay = compconsts.SMOOTH_UPTDATE_DELAY
            self._uiItemDelay = reactor.callLater(delay, self.__doSmoothUpdate)
    
    def __doSmoothUpdate(self):
        self._uiItemDelay = None
        if self._uiItemDelta:
            itemKey = self._uiItemDelta.iterkeys().next()
            key, subkey = itemKey
            desc, func, args = self._uiItemDelta.pop(itemKey)
            try:
                func(key, subkey, *args)
            except Exception, e:
                log.notifyException(self, e, "Failed during %s", desc,
                                    cleanTraceback=True)
        self.__smoothUpdate()
    
    def __notifyDebug(self, msg, info=None, debug=None, failure=None,
                      exception=None, documents=None):
        infoMsg = ["File Monitor Debug Notification: %s" % msg]
        debugMsg = []
        if info:
            infoMsg.append("Information:\n\n%s" % info)
        if debug:
            debugMsg.append("Additional Debug Info:\n\n%s" % debug)
        if failure:
            debugMsg.append("Failure Message: %s\nFailure Traceback:\n%s"
                            % (log.getFailureMessage(failure),
                               log.getFailureTraceback(failure)))
        if exception:
            debugMsg.append("Exception Message: %s\n\nException Traceback:\n%s"
                            % (log.getExceptionMessage(exception),
                               log.getExceptionTraceback(exception)))
        m = messages.Warning(T_("\n\n".join(infoMsg)),
                             debug="\n\n".join(debugMsg))
        self.addMessage(m)
    
    def __ebErrorFilter(self, failure, task=None):
        if failure.check(FlumotionError):
            return self.__monitorError(failure, task)
        return self.__unexpectedError(failure, task)

    def __monitorError(self, failure=None, task=None):
        if not failure:
            failure = Failure()
        log.notifyFailure(self, failure,
                          "Monitoring error%s",
                          (task and " during %s" % task) or "",
                          cleanTraceback=True)
        self.setMood(moods.sad)
        return failure
        
    def __unexpectedError(self, failure=None, task=None):
        if not failure:
            failure = Failure()
        log.notifyFailure(self, failure,
                          "Unexpected error%s",
                          (task and " during %s" % task) or "",
                          cleanTraceback=True)
        m = messages.Error(T_(failure.getErrorMessage()), 
                           debug=log.getFailureMessage(failure))
        self.addMessage(m)
        return failure

    
