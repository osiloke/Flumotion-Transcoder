# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from twisted.internet import defer

from flumotion.twisted.compat import Interface

from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.admin.proxies import componentset
from flumotion.transcoder.admin.proxies import monitorproxy
from flumotion.transcoder.admin.proxies import managerproxy


class IMonitorSetListener(Interface):
    def onMonitorAddedToSet(self, monitorset, monitor):
        pass
    
    def onMonitorRemovedFromSet(self, monitorset, monitor):
        pass

    
class MonitorSet(componentset.ComponentSetHelper):
    
    def __init__(self, mgrset):
        componentset.ComponentSetHelper.__init__(self, mgrset,
                                                 IMonitorSetListener)
        
    ## Public Method ##
    
    def startMonitor(self, name, worker, props):
        manager = worker.getParent()
        assert isinstance(manager, managerproxy.ManagerProxy)
        atmosphere = manager.getAtmosphere()
        d = atmosphere._loadComponent('file-monitor', 
                                      name, worker.getName(),
                                      props.getComponentProperties())
        d.addCallback(self.__onMonitorLoaded)
        return d

        
    ## Overriden Methods ##
    
    def _doSyncListener(self, listener):
        self._syncProxies("_components", listener, "MonitorAddedToSet")

    def _doFilterComponent(self, component):
        return isinstance(component, monitorproxy.MonitorProxy)

    def _doAddComponent(self, component):
        componentset.ComponentSetHelper._doAddComponent(self, component)
        self._fireEvent(component, "MonitorAddedToSet")
    
    def _doRemoveComponent(self, component):
        componentset.ComponentSetHelper._doRemoveComponent(self, component)
        self._fireEvent(component, "MonitorRemovedFromSet")

    
    ## Private Methods ##
    
    def __onMonitorLoaded(self, monitor):
        """
        Ensure the set contain the component before continuing.
        """
        return self.waitComponent(monitor.getIdentifier())
    
