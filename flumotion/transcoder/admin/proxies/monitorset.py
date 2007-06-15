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

from flumotion.transcoder import utils
from flumotion.transcoder.admin.proxies.componentset import BaseComponentSet
from flumotion.transcoder.admin.proxies.monitorproxy import MonitorProxy


class IMonitorSetListener(Interface):
    def onMonitorAddedToSet(self, monitorset, monitor):
        pass
    
    def onMonitorRemovedFromSet(self, monitorset, monitor):
        pass


class MonitorSetListener(object):
    
    implements(IMonitorSetListener)
    
    def onMonitorAddedToSet(self, monitorset, monitor):
        pass
    
    def onMonitorRemovedFromSet(self, monitorset, monitor):
        pass


class MonitorSet(BaseComponentSet):
    
    def __init__(self, mgrset):
        BaseComponentSet.__init__(self, mgrset,
                                  IMonitorSetListener)
        
    ## Public Method ##
    

    ## Overriden Methods ##
    
    def _doSyncListener(self, listener):
        self._syncProxies("_components", listener, "MonitorAddedToSet")

    def _doAcceptComponent(self, component):
        if not isinstance(component, MonitorProxy):
            return False
        return True

    def _doAddComponent(self, component):
        BaseComponentSet._doAddComponent(self, component)
        self.debug("Monitor component '%s' added to set",
                   component.getLabel())
        self._fireEvent(component, "MonitorAddedToSet")
        
    def _doRemoveComponent(self, component):
        BaseComponentSet._doRemoveComponent(self, component)
        self.debug("Monitor component '%s' removed from set",
                   component.getLabel())
        self._fireEvent(component, "MonitorRemovedFromSet")

    
