# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

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

    
