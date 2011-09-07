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

from zope.interface import Interface, implements

from flumotion.inhouse import utils

from flumotion.transcoder.admin.proxy import componentset, transcoder


class TranscoderSet(componentset.BaseComponentSet):

    def __init__(self, managerPxySet):
        componentset.BaseComponentSet.__init__(self, managerPxySet)
        # Registering Events
        self._register("transcoder-added")
        self._register("transcoder-removed")


    ## Public Method ##


    ## Overriden Methods ##

    def refreshListener(self, listener):
        self._refreshProxiesListener("_compPxys", listener, "transcoder-added")

    def _doAcceptComponent(self, compPxy):
        if not isinstance(compPxy, transcoder.TranscoderProxy):
            return False
        return True

    def _doAddComponent(self, compPxy):
        componentset.BaseComponentSet._doAddComponent(self, compPxy)
        self.debug("Transcoder component '%s' added to set",
                   compPxy.label)
        self.emit("transcoder-added", compPxy)

    def _doRemoveComponent(self, compPxy):
        componentset.BaseComponentSet._doRemoveComponent(self, compPxy)
        self.debug("Transcoder component '%s' removed from set",
                   compPxy.label)
        self.emit("transcoder-removed", compPxy)


