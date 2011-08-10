# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.
#
# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.
#
# Headers in this file shall remain intact.

import os
import shutil

from twisted.internet import reactor
from twisted.internet.defer import fail, DeferredSemaphore, DeferredList
from twisted.internet.interfaces import IReactorThreads
from twisted.internet.threads import deferToThread
from twisted.python.failure import Failure

from flumotion.common import messages
from flumotion.common.i18n import gettexter
from flumotion.common.planet import moods

from flumotion.inhouse import log
from flumotion.inhouse.errors import FlumotionError

from flumotion.ovp.utils import safe_mkdirs

from flumotion.component.component import BaseComponentMedium, BaseComponent
from flumotion.transcoder.enums import MonitorFileStateEnum
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.local import Local
from flumotion.transcoder.virtualpath import VirtualPath
from flumotion.ovp.fileutils import checksum, magic_mimetype
from flumotion.inhouse.fileutils import PathAttributes


_ = gettexter('flumotion-transcoder')

IReactorThreads(reactor).suggestThreadPoolSize(2)
#---------------------- prevents from computing too many md5 at the same time




class MonitorMedium(BaseComponentMedium):

    def remote_setFileState(self, profile_name, relFile, status):
        self.comp.setFileState(profile_name, relFile, status)

    def remote_setFilesState(self, states):
        for state in states:
            self.comp.setFileState(*state)

    # called when a file is moved to the failed directory
    def remote_moveFiles(self, virtSrcBase, virtDestBase, relFiles):
        self.comp.moveFiles(virtSrcBase, virtDestBase, relFiles)



class MonitorBase(BaseComponent):

    componentMediumClass = MonitorMedium

    def __init__(self, *args, **kwargs):
        BaseComponent.__init__(self, *args, **kwargs)


    #=================================================================
    # BaseComponent life management. See BaseComponent.
    #=================================================================

    def init(self):
        log.setDebugNotifier(self._notifyDebug)
        log.setDefaultCategory(self.logCategory)
        self.uiState.addListKey('monitored-profiles', [])
        self.uiState.addListKey('active-profiles', [])
        self.uiState.addListKey('http-profiles', [])
        self.uiState.addDictKey('pending-files', {})
        self.uiState.addDictKey('virtbase-map', {})
        self._local = None
        self._pathAttr = None
        self.active_profiles = []
        self.watchers = []
        self.http_profiles = []
        self.profiles_virtualbase = {}

    def do_setup(self):
        try:
            properties = self.config['properties']
            self._local = Local.createFromComponentProperties(properties)
            self._pathAttr = PathAttributes.createFromComponentProperties(properties)
            for s in properties.get("named-profile", []):
                profile, path, active = s.split('!')
                vpath = VirtualPath(path)
                active = bool(int(active))
                self.profiles_virtualbase[profile] = vpath
                self.uiState.setitem('virtbase-map', profile, str(vpath))
                self.uiState.append('monitored-profiles', profile)
                if active:
                    self.active_profiles.append(profile)
                    self.uiState.append('active-profiles', profile)
                else:
                    self.http_profiles.append(profile)
                    self.uiState.append('http-profiles', profile)
        except:
            return fail(self._unexpected_error(task="component setup"))

    def do_stop(self):
        pass

    #=================================================================
    # UIState update methods
    #=================================================================



    def _set_ui_item(self, key, subkey, value):
        try:
            self.uiState.setitem(key, subkey, value)
        except KeyError:
            pass

    def _del_ui_item(self, key, subkey):
        try:
            self.uiState.delitem(key, subkey)
        except KeyError:
            pass

    def _update_ui_item(self, key, subkey, value):
        try:
            if self.uiState[key][subkey] != value:
                self.uiState.setitem(key, subkey, value)
        except KeyError:
            pass


    #=================================================================
    # Public methods
    #=================================================================

    def setFileState(self, virtBase, relFile, status):
        key = (virtBase, relFile)
        state = self.uiState.get('pending-files')
        substate = state.get(key)
        # substate can be None, probably because it has already been
        # added to the internal dictionaries, but has not been updated
        # in the UIState. In that case don't bother with updating the
        # UIState - we don't want to overwrite the file state in the
        # smooth update structure.
        if substate is None:
            return
        substate = list(substate)
        substate[0] = status
        substate = tuple(substate)
        self._update_ui_item('pending-files', key, substate)


    def moveFiles(self, virtSrcBase, virtDestBase, relFiles):
        self.debug("MOVING: %r, %r, %r", virtSrcBase, virtDestBase, relFiles)
        if not self._local:
            raise TranscoderError("Component not properly setup yet")

        def move_failed(failure, src, dest):
            msg = ("Fail to move file '%s' to '%s': %s"
                   % (src, dest, log.getFailureMessage(failure)))
            self.warning("%s", msg)
            raise TranscoderError(msg, cause=failure)

        def move_file(src, dest, attr=None):
            self.debug("Moving file '%s' to '%s'", src, dest)
            dest_dir = os.path.dirname(dest)
            safe_mkdirs(dest_dir, "input file destination", attr)
            d = deferToThread(shutil.move, src, dest)
            d.addErrback(move_failed, src, dest)
            return d

        def move_files_failed(results):
            first_failure = None
            for ok, result in results:
                if not ok:
                    if not first_failure:
                        first_failure = result
            return first_failure

        sem = DeferredSemaphore(1)
        move_tasks = []

        for file in relFiles:
            source_path = virtSrcBase.append(file).localize(self._local)
            dest_path = virtDestBase.append(file).localize(self._local)
            source_path = os.path.realpath(source_path)
            dest_path = os.path.realpath(dest_path)
            d = sem.run(move_file, source_path, dest_path, self._pathAttr)
            move_tasks.append(d)

        dl = DeferredList(move_tasks, consumeErrors=True)
        dl.addErrback(move_files_failed)
        return d


    #=================================================================
    # Protected methods
    #=================================================================

    def get_file_info(self, file, fileinfo, incoming_folder,
                                  virt_base, profile_name=None, params={}):
        d = deferToThread(
            self.get_mime_and_checksum, incoming_folder + file
        ).addErrback(
            self.fallback_mime_and_checksum_none
        ).addCallback(
            self.check_whether_not_removed, file, virt_base
        ).addCallback(
            self.set_file_as_pending, fileinfo, file, profile_name, params
        ).addErrback(
            # ignore th errors from 'check_whether_not_removed'
            lambda failure: None
        )
        return d

    #=================================================================
    # Private methods and callbacks. Subclasses might not use them
    #=================================================================

    def get_mime_and_checksum(self, path):
        self.debug("Computing checksum: %r", path)
        mime = magic_mimetype(path)
        chksum = checksum(path)
        return (mime, chksum)

    def fallback_mime_and_checksum_none(self, failure):
        log.notifyFailure(self, failure, "Failure during checksum / mime type")
        return (None, None)

    def check_whether_not_removed(self, result, filename, virt_base):
        local_file = virt_base.append(filename).localize(self._local)
        if not os.path.exists(local_file):
            self.debug("File: %s has been removed while computing the "
                "checksum.", local_file)
            raise ValueError("File: %s has been removed" % local_file)
        self.debug("File completed '%s'", local_file)
        return result

    def set_file_as_pending(self, result, file_info, filename, profile, params):
        self.warning('%r %r %r %r %r' % (result, file_info, filename, profile, params))
        mime, chksum = result
        self.warning('mime = %(mime)r, chksum = %(chksum)r' % dict(mime=mime, chksum=chksum))
        self.warning('%r %r' % (profile, filename))
        key = (profile, filename)
        self.warning('%r' % (key,))
        try:
            detection_time = self.uiState['pending-files'][key][2]
        except (TypeError, KeyError):
            detection_time = None
        except Exception, e:
            self.warning('Unexpected %r' % e)
        substate = (MonitorFileStateEnum.pending, file_info, detection_time,
                    mime, chksum, params)
        self.warning('%r' % (substate,))
        self._set_ui_item('pending-files', key, substate)

    def _notifyDebug(self, msg, info=None, debug=None, failure=None,
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
        m = messages.Warning(_("\n\n".join(infoMsg)),
                             debug="\n\n".join(debugMsg))
        self.addMessage(m)

    def _ebErrorFilter(self, failure, task=None):
        if failure.check(FlumotionError):
            return self._monitorError(failure, task)
        return self._unexpected_error(failure, task)

    def _monitorError(self, failure=None, task=None):
        if not failure:
            failure = Failure()
        log.notifyFailure(self, failure,
                          "Monitoring error%s",
                          (task and " during %s" % task) or "",
                          cleanTraceback=True)
        self.setMood(moods.sad)
        return failure

    def _unexpected_error(self, failure=None, task=None):
        if not failure:
            failure = Failure()
        log.notifyFailure(self, failure,
                          "Unexpected error%s",
                          (task and " during %s" % task) or "",
                          cleanTraceback=True)
        m = messages.Error(_(failure.getErrorMessage()),
                           debug=log.getFailureMessage(failure))
        self.addMessage(m)
        return failure



