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

from flumotion.transcoder.i18n import _
from flumotion.component.base.admin_gtk import BaseAdminGtk
from flumotion.component.base.baseadminnode import BaseAdminGtkNode

# Column description:
COL_DISPLAY = 0
COL_STATUS = 1

class HttpMonitorAdminGtkNode(BaseAdminGtkNode):
    gladeFile = os.path.join('flumotion', 'component',
                             'monitor', 'httpmonitor.glade')
    gettext_domain = "flumotion-transcoder"

    #==========================================================================
    # BaseAdminGtkNode implied methods, 
    # UIState sync.
    #==========================================================================

    def __init__(self, *args, **kwargs):
        BaseAdminGtkNode.__init__(self, *args, **kwargs)
        self.view = None
        self.model = gtk.TreeStore(str, str)
        self.model_lookup = {}

    def stateAppend(self, state, key, value):
        """ listens to uiState's "append" event """
        if key == "monitored-profiles":
            self._add_profile(value)

    def stateRemove(self, state, key, value):
        """ listens to uiState's "remove" event """
        if key == "monitored-profiles":
            self._remove_profile(value)

    def stateSetitem(self, state, key, subkey, fileinfo):
        """ listens to uiState's "setitem" event """
        if key == "pending-files":
            self._add_file(subkey, fileinfo[0])

    def stateDelitem(self, state, key, subkey, value):
        """ listens to uiState's "delitem" event """
        if key == "pending-files":
            self._remove_file(subkey)

    def setUIState(self, state):
        BaseAdminGtkNode.setUIState(self, state)
        self.model.clear()
        for profile in self.uiState.get("monitored-profiles"):
            self.stateAppend(self.uiState, "monitored-profiles", profile)
        for subkey, fileinfo in self.uiState.get("pending-files").items():
            self.stateSetitem(self.uiState, "pending-files", subkey, fileinfo)

    #==========================================================================
    # Widget things
    #==========================================================================

    def error_dialog(self, message):
        # FIXME: dialogize
        print 'ERROR:', message

    def haveWidgetTree(self):
        self.widget = self.getWidget('monitoring-widget')
        self.setView(self.getWidget('tvMonitoredProfiles'))

    def setView(self, view):
        self.view = view
        renderer = gtk.CellRendererText()
        value_column = gtk.TreeViewColumn()
        value_column.pack_start(renderer, True)
        value_column.add_attribute(renderer, "text", COL_DISPLAY)
        status_column = gtk.TreeViewColumn()
        status_column.pack_start(renderer, True)
        status_column.add_attribute(renderer, "text", COL_STATUS)
        view.append_column(value_column)
        view.append_column(status_column)
        self.view.set_model(self.model)

    def _add_profile(self, profile):
        vdir = self.uiState.get('virtbase-map', {}).get(profile, None)
        display_name = '%s (%s)' % (profile, vdir)
        if not profile in self.model_lookup:
            self.model_lookup[profile] = self.model.append(None, (display_name, ""))
        else:
            self.warning("Profile '%s' already added", display_name)

    def _add_file(self, file, status):
        profile, name = file
        if file in self.model_lookup:
            self.model[self.model_lookup[file]][COL_STATUS] = _(status.nick)
        elif profile in self.model_lookup:
            parent = self.model_lookup[profile]
            self.model_lookup[file] = self.model.append(parent, (name, _(status.nick)))
        else:
            self.warning("Unknown profile '%s'" % profile)

    def _remove_file(self, file):
        profile, name = file
        try:
            del self.model[self.model_lookup[file]]
        except KeyError:
            if profile in self.model_lookup:
                self.warning("Unknown file '%s'" % name)
            else:
                self.warning("Unknown profile '%s'" % profile)

    def _remove_profile(self, profile):
        try:
            del self.model[self.model_lookup[profile]]
        except KeyError:
            self.warning("Unknown profile '%s'" % profile)


class HttpMonitorAdminGtk(BaseAdminGtk):
    gettext_domain = 'flumotion-transcoder'

    def setup(self):
        monitoring = HttpMonitorAdminGtkNode(self.state, self.admin,
                                             title=_('Monitoring'))
        self.nodes['Monitoring'] = monitoring
        return BaseAdminGtk.setup(self)


GUIClass = HttpMonitorAdminGtk
