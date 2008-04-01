# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import implements, classProvides

from flumotion.component.bouncers import saltsha256

from flumotion.inhouse import defer, log
from flumotion.inhouse.spread import bouncers, pbserver

from flumotion.transcoder.admin import errors
from flumotion.transcoder.admin.api import gateway
from flumotion.transcoder.admin.enums import APIBouncerEnum


class Server(log.Loggable):
    
    logCategory = "api-server"
    
    def __init__(self, context, admin):
        self._context = context
        self._admin = admin
        self._server = None
        
    def initialize(self):
        self.debug("Initializing API Server")
        d = self._createBouncer(self._context.config.bouncer)
        d.addCallback(self.__cbCreateServer)
        d.addCallback(self.__cbRegisterGatewayService)
        d.addCallback(self.__cbInitializeServer)
        d.addCallback(defer.overrideResult, self) 
        return d


    ## Private Methods ##

    def __cbCreateServer(self, bouncer):
        conf = self._context.config
        self._server = pbserver.Server(conf.host, conf.port, conf.useSSL,
                                       conf.certificate, bouncer)
        return self._server 

    def __cbRegisterGatewayService(self, server):
        server.registerService(_ServiceFactory(self))
        return server
        
    def __cbInitializeServer(self, server):
        return server.initialize()


    ## Private Methodes ##

    def _createBouncer(self, config):
        factory = _bouncerFactories.get(config.type, None)
        if factory is None:
            raise errors.APIError("Unknown bouncer type '%s'" % config.type)
        return factory(config) 



## Private ##

def _saltedSha256BouncerFactory(config):
    data = '\n'.join(["%s:%s" % i for i in config.users.items()])
    return bouncers.create(saltsha256.SaltSha256, 'transcoder-api-bouncer', data=data)


_bouncerFactories = {APIBouncerEnum.saltedsha256: _saltedSha256BouncerFactory}


class _Service(pbserver.Service):
    
    avatarFactory = gateway.Avatar
    
    def __init__(self, server, admin, identifier=None):
        pbserver.Service.__init__(self, server, identifier=identifier)
        self._admin = admin
        
    def getAdmin(self):
        return self._admin
    

class _ServiceFactory(object):
    
    implements(pbserver.IServiceFactory)
    
    def __init__(self, admin):
        self._admin = admin
        
    
    ## IServiceFactory Methodes ##
    
    def createService(self, server, identifier=None):
        ident = identifier or "api-server"
        return _Service(server, self._admin, identifier=ident)
 
    def getServiceInterfaces(self):
        return gateway.Avatar.getMediumInterfaces()
