# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from twisted.internet import reactor, defer
from flumotion.twisted.compat import Interface

from flumotion.transcoder.admin.proxies import componentset
from flumotion.transcoder.admin.proxies import transcoderproxy


class ITranscoderSetListener(Interface):
    def onTranscoderAddedToSet(self, transcoderset, transcoder):
        pass
    
    def onTranscoderRemovedFromSet(self, transcoderset, transcoder):
        pass

    
class TranscoderSet(componentset.BaseComponentSet):
    
    def __init__(self, mgrset):
        componentset.BaseComponentSet.__init__(self, mgrset,
                                               ITranscoderSetListener)
        self._components = {} # Identifier => TranscoderProxy
        
    ## Public Methods ##
    
    def startupTranscoder(self, config, niceLevel=None):
        d = defer.Deferred()
        
        return d
        
    ## Overriden Methods ##
    
    def _doSyncListener(self, listener):
        self._syncProxies("_components", listener, "TranscoderAddedToSet")

    def _doFilterComponent(self, component):
        return isinstance(component, transcoderproxy.TranscoderProxy)

    def _doAddComponent(self, component):
        identifier = component.getIdentifier()
        assert not (identifier in self._components)
        self._components[identifier] = component
        self._fireEvent(component, "TranscoderAddedToSet")
    
    def _doRemoveComponent(self, component):
        identifier = component.getIdentifier()
        assert identifier in self._components
        assert self._components[identifier] == component
        del self._components[identifier]
        self._fireEvent(component, "TranscoderRemovedFromSet")
