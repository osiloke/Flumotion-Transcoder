# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.twisted.compat import Interface

from flumotion.transcoder.admin.proxies import componentset
from flumotion.transcoder.admin.proxies import monitorproxy


class IMonitorSetListener(Interface):
    def onMonitorAddedToSet(self, monitorset, monitor):
        pass
    
    def onMonitorRemovedFromSet(self, monitorset, monitor):
        pass

    
class MonitorSet(componentset.BaseComponentSet):
    
    def __init__(self, mgrset):
        componentset.BaseComponentSet.__init__(self, mgrset,
                                               IMonitorSetListener)
        self._components = {} # Identifier => MonitorProxy
        
        
    ## Overriden Methods ##
    
    def _doSyncListener(self, listener):
        self._syncProxies("_components", listener, "MonitorAddedToSet")

    def _doFilterComponent(self, component):
        return isinstance(component, monitorproxy.MonitorProxy)

    def _doAddComponent(self, component):
        identifier = component.getIdentifier()
        assert not (identifier in self._components)
        self._components[identifier] = component
        self._fireEvent(component, "MonitorAddedToSet")
    
    def _doRemoveComponent(self, component):
        identifier = component.getIdentifier()
        assert identifier in self._components
        assert self._components[identifier] == component
        del self._components[identifier]
        self._fireEvent(component, "MonitorRemovedFromSet")
