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
import gtk

from flumotion.common import errors

from flumotion.transcoder import enums
from flumotion.transcoder.i18n import _
from flumotion.transcoder.enums import MonitorFileStateEnum
from flumotion.transcoder.virtualpath import VirtualPath
from flumotion.component.base.admin_gtk import BaseAdminGtk
from flumotion.component.base.baseadminnode import BaseAdminGtkNode


class FileMonitorAdminGtkNode(BaseAdminGtkNode):
    gladeFile = os.path.join('flumotion', 'component',
                             'transcoder', 'filemonitor.glade')
    gettext_domain = "flumotion-transcoder"

    def __init__(self, *args, **kwargs):
        BaseAdminGtkNode.__init__(self, *args, **kwargs)
        self.view = None
        self.model = gtk.TreeStore(str, str)
        self.directories = {}

    def error_dialog(self, message):
        # FIXME: dialogize
        print 'ERROR:', message

    def haveWidgetTree(self):
        self.widget = self.getWidget('monitoring-widget')
        self.setView(self.getWidget('tvMonitoredDirectories'))

    def setUIState(self, state):
        BaseAdminGtkNode.setUIState(self, state)
        self.refreshUIState()

    def setView(self, view):
        self.view = view
        renderer = gtk.CellRendererText()
        valueCol = gtk.TreeViewColumn()
        valueCol.pack_start(renderer, True)
        valueCol.add_attribute(renderer, "text", 0)
        statusCol = gtk.TreeViewColumn()
        statusCol.pack_start(renderer, True)
        statusCol.add_attribute(renderer, "text", 1)
        view.append_column(valueCol)
        view.append_column(statusCol)
        self.view.set_model(self.model)

    def refreshUIState(self):
        self.directories.clear()
        self.model.clear()
        for d in self.uiState.get("monitored-directories"):
            self._addDirectory(d)
        for i, fileinfo in self.uiState.get("pending-files").iteritems():
            self._addFile(i, fileinfo[0])

    def _addDirectory(self, dir):
        if self.directories.has_key(dir):
            self.warning("Directory '%s' already added", dir)
            return
        self.directories[dir] = [{}, self.model.append(None, (str(dir), ""))]

    def _removeDirectory(self, dir):
        if not self.directories.has_key(dir):
            self.warning("Cannot remove unknown directory '%s'", dir)
            return
        del self.model[self.directories[dir][1]]
        del self.directories[dir]

    def _addFile(self, file, status):
        base, name = file
        if not self.directories.has_key(base):
            self.warning("Cannot add file '%s' to the unkown directory '%s'"
                         % (name, base))
            return
        files, parent = self.directories[base]
        if files.has_key(name):
            self.model[files[name]][1] = _(status.nick)
        else:
            files[name] = self.model.append(parent, (name, status.nick))

    def _removeFile(self, file):
        base, name = file
        if not self.directories.has_key(base):
            self.warning("Cannot remove file '%s' from the unkown directory '%s'"
                         % (name, base))
            return
        files, parent = self.directories[base]
        if not files.has_key(name):
            self.warning("Directory '%s' do not contain file '%s'"
                         % (base, name))
            return
        del self.model[files[name]]
        del files[name]

    def stateAppend(self, state, key, value):
        if key == "monitored-directories":
            self._addDirectory(value)

    def stateRemove(self, state, key, value):
        if key == "monitored-directories":
            self._removeDirectory(value)

    def stateSetitem(self, state, key, subkey, fileinfo):
        # FIXME This function seems unused...
        if key == "pending-files":
            self._addFile(subkey, fileinfo[0])

    def stateDelitem(self, state, key, subkey, value):
        # FIXME This function seems unused...
        if key == "pending-files":
            self._removeFile(subkey)


class FileMonitorAdminGtk(BaseAdminGtk):
    gettext_domain = 'flumotion-transcoder'

    def setup(self):
        monitoring = FileMonitorAdminGtkNode(self.state, self.admin,
                                             title=_('Monitoring'))
        self.nodes['Monitoring'] = monitoring
        return BaseAdminGtk.setup(self)


GUIClass = FileMonitorAdminGtk
