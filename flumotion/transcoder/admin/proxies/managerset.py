# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import implements

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


class ManagerSet(RootFlumotionProxy):
    
    def __init__(self, adminContext):
        RootFlumotionProxy.__init__(self, FlumotionProxiesLogger())
        self._context = adminContext
        self._multi = multi.MultiAdminModel()
        self._multi.addListener(self)
        self._managers = AssignWaiters("Manager Set Assignment", {})
        self._setIdleTarget(1)
        # Registering Events
        self._register("manager-added")
        self._register("manager-removed")
        self._register("attached")
        self._register("detached")
        
        
    ## Public Methods ##
    
    def getManagers(self):
        return self._managers.getValue().values()
    
    def iterManagers(self):
        return self._managers.getValue().itervalues()
    
    def waitManagers(self, timeout=None):
        return self._managers.wait(timeout)

    
    ## Overriden Methods ##
    
    def update(self, listener):
        self._updateProxies("_managers", listener, "manager-added")

    def _doGetChildElements(self):
        return self.getManagers()
    
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
            self.emit("attached")
        self._addProxyState(managerproxy, "_managers", 
                            self.__getManagerUniqueId,
                            "manager-added", 
                            admin, managerContext, planet)
    
    def model_removePlanet(self, admin, planet):
        assert planet != None
        self.log("Manager state %s removed", planet.get('name'))
        managerContext = self._context.getManagerContext()
        managers = self._managers.getValue()
        if len(managers) == 1:
            ident = self.__getManagerUniqueId(admin, managerContext, planet)
            if ident in managers:
                self.emit("detached")
        self._removeProxyState("_managers", self.__getManagerUniqueId,
                               "manager-removed", 
                               admin, managerContext, planet)
    
    
    ## Private Methods ##
    
    def __getManagerUniqueId(self, admin, managerContext, planet):
        if admin == None:
            return None
        # We do not use admin.managerId, because it contains private data,
        # and the identifier can be published by the API.
        id = _managerIdentifiers.get(admin.managerId, None)
        if id is None:
            id = len(_managerIdentifiers) + 1
            _managerIdentifiers[admin.managerId] = str(id)
        return id


## Private ##

_managerIdentifiers = {}