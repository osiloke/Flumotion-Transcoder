# -*- Mode: Python -*-
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

from twisted.internet.defer import fail

from flumotion.component.transcoder import compconsts
from flumotion.component.transcoder.watcher import DirectoryWatcher
from flumotion.component.monitor.base import MonitorBase
from flumotion.ovp.utils import safe_mkdirs
from flumotion.transcoder.enums import MonitorFileStateEnum

class FileMonitor(MonitorBase):
    """
    Monitor a list of directory.
    """

    logCategory = compconsts.MONITOR_LOG_CATEGORY

    #=================================================================
    # BaseComponent life management. See BaseComponent.
    #=================================================================

    def init(self):
        self.watchers = []
        self._scanPeriod = None
        self._directories = []

    def do_setup(self):
        try:
            self._scanPeriod = self._properties["scan-period"]
            self.do_setup_watchers()
        except:
            return fail(self._unexpected_error(task="component setup"))

    def do_stop(self, *args, **kwargs):
        while self.watchers:
            self.watchers.pop().stop()

    def do_setup_watchers(self):
        for name, virt_dir in self._named_profiles.items():
            local_dir = virt_dir.localize(self._local)
            safe_mkdirs(local_dir, "monitored", self._pathAttr)
            watcher = DirectoryWatcher(self, local_dir, timeout=self._scanPeriod)
            watcher.connect('file-added', self._file_added, virt_dir, name)
            watcher.connect('file-completed', self._file_completed, virt_dir, name)
            watcher.connect('file-removed', self._file_removed, virt_dir, name)
            watcher.start()
            self.watchers.append(watcher)


    ## Signal Handler Methods ##

    def _file_added(self, watcher, file, fileinfo, detection_time, virt_base, profile_name):
        localFile = virt_base.append(file).localize(self._local)
        self.debug("File added : '%s'", localFile)

        # put here the parameters
        self._set_ui_item('pending-files', (profile_name, file),
                         (MonitorFileStateEnum.downloading, fileinfo,
                          detection_time, None, None, None))

    def _file_completed(self, watcher, file, fileinfo, virt_base, profile_name):
        self.get_file_info(file, fileinfo, watcher.path, virt_base,
            profile_name=profile_name, params={})
        

    def _file_removed(self, watcher, file, virtBase, profile_name):
        localFile = virtBase.append(file).localize(self._local)
        self.debug("File removed '%s'", localFile)
        self._del_ui_item('pending-files', (profile_name, file))


