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

from flumotion.admin import multi
#To register Jellyable classes
from flumotion.common import planet
from flumotion.common.connection import PBConnectionInfo as ConnectionInfo

from flumotion.inhouse import log, utils
from flumotion.inhouse.waiters import AssignWaiters

from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.proxies import managerproxy
from flumotion.transcoder.admin.proxies.fluproxy import RootFlumotionProxy



class FlumotionProxiesLogger(log.Loggable):
    logCategory = adminconsts.PROXIES_LOG_CATEGORY


class IManagerSetListener(Interface):
    def onManagerAddedToSet(self, managerset, manager):
        pass
    
    def onManagerRemovedFromSet(self, managerset, manager):
        pass
    
    def onAttached(self, managerset):
        pass

    def onDetached(self, managerset):
        """
        Called when there is no more conection to manager,
        before removing any other component.
        """
        pass
    

class ManagerSetListener(object):
    
    implements(IManagerSetListener)
    
    def onManagerAddedToSet(self, managerset, manager):
        pass
    
    def onManagerRemovedFromSet(self, managerset, manager):
        pass
    
    def onAttached(self, managerset):
        pass

    def onDetached(self, managerset):
        pass


class ManagerSet(RootFlumotionProxy):
    
    def __init__(self, adminContext):
        RootFlumotionProxy.__init__(self, FlumotionProxiesLogger(), 
                                    IManagerSetListener)
        self._context = adminContext
        self._multi = multi.MultiAdminModel()
        self._multi.addListener(self)
        self._managers = AssignWaiters("Manager Set Assignment", {})
        self._setIdleTarget(1)
        
        
    ## Public Methods ##
    
    def getManagers(self):
        return self._managers.getValue().values()
    
    def iterManagers(self):
        return self._managers.getValue().itervalues()
    
    def waitManagers(self, timeout=None):
        return self._managers.wait(timeout)

    
    ## Overriden Methods ##
    
    def _doGetChildElements(self):
        return self.getManagers()
    
    def _doSyncListener(self, listener):
        self._syncProxies("_managers", listener, "ManagerAddedToSet")

    def _doPrepareInit(self, chain):
        ctx = self._context.getManagerContext()
        info = ConnectionInfo(ctx.getHost(),
                              ctx.getPort(),
                              ctx.getUseSSL(),
                              ctx.getAuthenticator())
        self._multi.addManager(info, tenacious=True)


    ## MultiAdmin Event Handlers ##
    
    def model_addPlanet(self, admin, planet):
        assert planet != None
        self.log("Manager state %s added", planet.get('name'))
        managerContext = self._context.getManagerContext()
        managers = self._managers.getValue()
        if len(managers) == 0:
            self._fireEventWithoutPayload("Attached")
        self._addProxyState(managerproxy, "_managers", 
                            self.__getManagerUniqueId,
                            "ManagerAddedToSet", 
                            admin, managerContext, planet)
    
    def model_removePlanet(self, admin, planet):
        assert planet != None
        self.log("Manager state %s removed", planet.get('name'))
        managerContext = self._context.getManagerContext()
        managers = self._managers.getValue()
        if len(managers) == 1:
            ident = self.__getManagerUniqueId(admin, managerContext, planet)
            if ident in managers:
                self._fireEventWithoutPayload("Detached")
        self._removeProxyState("_managers", self.__getManagerUniqueId,
                               "ManagerRemovedFromSet", 
                               admin, managerContext, planet)
    
    
    ## Private Methods ##
    
    def __getManagerUniqueId(self, admin, managerContext, planet):
        if admin == None:
            return None
        return admin.managerId
