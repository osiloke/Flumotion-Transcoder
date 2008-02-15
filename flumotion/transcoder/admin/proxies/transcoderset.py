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

from flumotion.transcoder.admin.proxies.componentset import BaseComponentSet
from flumotion.transcoder.admin.proxies.transcoderproxy import TranscoderProxy


class TranscoderSet(BaseComponentSet):
    
    def __init__(self, mgrset):
        BaseComponentSet.__init__(self, mgrset)
        # Registering Events
        self._register("transcoder-added")
        self._register("transcoder-removed")

        
    ## Public Method ##
    

    ## Overriden Methods ##
    
    def update(self, listener):
        self._updateProxies("_components", listener, "transcoder-added")

    def _doAcceptComponent(self, component):
        if not isinstance(component, TranscoderProxy):
            return False
        return True

    def _doAddComponent(self, component):
        BaseComponentSet._doAddComponent(self, component)
        self.debug("Transcoder component '%s' added to set",
                   component.getLabel())
        self.emit("transcoder-added", component)
        
    def _doRemoveComponent(self, component):
        BaseComponentSet._doRemoveComponent(self, component)
        self.debug("Transcoder component '%s' removed from set",
                   component.getLabel())
        self.emit("transcoder-removed", component)

    
