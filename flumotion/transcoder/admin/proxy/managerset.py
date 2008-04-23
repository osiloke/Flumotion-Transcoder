# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import re

from zope.interface import implements

from flumotion.admin import multi
#To register Jellyable classes
from flumotion.common import planet
from flumotion.common.connection import PBConnectionInfo as ConnectionInfo

from flumotion.inhouse import log, utils, waiters

from flumotion.transcoder import errors
from flumotion.transcoder.admin import adminconsts, interfaces
from flumotion.transcoder.admin.proxy import base, manager


class IManagerSet(interfaces.IAdminInterface):

    def getManagerProxies(self):
        pass
    
    def iterManagerProxies(self):
        pass
    
    def waitManagerProxies(self, timeout=None):
        pass


class FlumotionProxiesLogger(log.Loggable):
    logCategory = adminconsts.PROXIES_LOG_CATEGORY


class ManagerSet(base.RootProxy):
    
    def __init__(self, adminContext):
        base.RootProxy.__init__(self, FlumotionProxiesLogger())
        self._context = adminContext
        self._multi = multi.MultiAdminModel()
        self._multi.addListener(self)
        self._managerPxys = waiters.AssignWaiters("Manager Set Assignment", {})
        self._setIdleTarget(1)
        # Registering Events
        self._register("manager-added")
        self._register("manager-removed")
        self._register("attached")
        self._register("detached")
        
        
    ## Public Methods ##
    
    def getManagerProxies(self):
        return self._managerPxys.getValue().values()
    
    def iterManagerProxies(self):
        return self._managerPxys.getValue().itervalues()
    
    def waitManagerProxies(self, timeout=None):
        return self._managerPxys.wait(timeout)

    
    ## Overriden Methods ##
    
    def refreshListener(self, listener):
        self._refreshProxiesListener("_managerPxys", listener, "manager-added")

    def _doGetChildElements(self):
        return self.getManagerProxies()
    
    def _doPrepareInit(self, chain):
        managerCtx = self._context.getManagerContext()
        info = ConnectionInfo(managerCtx.getHost(),
                              managerCtx.getPort(),
                              managerCtx.getUseSSL(),
                              managerCtx.getAuthenticator())
        self._multi.addManager(info, tenacious=True)


    ## MultiAdmin Event Handlers ##
    
    def model_addPlanet(self, admin, planet):
        assert planet != None
        self.log("Manager state %s added", planet.get('name'))
        managerCtx = self._context.getManagerContext()
        managerPxys = self._managerPxys.getValue()
        if len(managerPxys) == 0:
            self.emit("attached")
        else:
            raise NotImplementedError("More than one Manager is not yet supported")
        self._addProxyState(manager, "_managerPxys",  self.__getManagerUniqueId,
                            "manager-added", admin, managerCtx, planet)
        
    def model_removePlanet(self, admin, planet):
        assert planet != None
        self.log("Manager state %s removed", planet.get('name'))
        managerCtx = self._context.getManagerContext()
        managerPxys = self._managerPxys.getValue()
        if len(managerPxys) == 1:
            ident = self.__getManagerUniqueId(admin, managerCtx, planet)
            if ident in managerPxys:
                self.emit("detached")
        self._removeProxyState("_managerPxys", self.__getManagerUniqueId,
                               "manager-removed",  admin, managerCtx, planet)
    
    
    ## Private Methods ##
    
    _identPtrn = re.compile("([^@]*)@([^:]*):(.*)")
    
    def __getManagerUniqueId(self, admin, managerCtx, planet):
        if admin == None:
            return None
        # We want to remove the username from the managerId for privacy
        # because the identifier is published by the API
        #FIXME: Should we hide the host and port too ?
        match = self._identPtrn.match(admin.managerId)
        if not match:
            raise errors.TranscoderError("Unknown manager identifier format '%s', "
                                         "maybe it changed ?" % admin.managerId)
        identifier = "%s.%s" % (match.group(2), match.group(3)) 
        return identifier
