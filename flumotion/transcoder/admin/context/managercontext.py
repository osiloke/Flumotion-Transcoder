# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.twisted import pb

from flumotion.transcoder.admin.context.workercontext import WorkerContext


class ManagerContext(object):
    
    def __init__(self, config):
        self._config = config

    def getHost(self):
        return str(self._config.manager.host)
    
    def getPort(self):
        return self._config.manager.port
    
    def getUseSSL(self):
        return self._config.manager.useSSL
    
    def getAuthenticator(self):
        return pb.Authenticator(username=self._config.manager.username,
                                password=self._config.manager.password)

    def getWorkerContext(self, workername):
        return WorkerContext(workername, 
                             self._config.workers.get(workername, None),
                             self._config.workerDefaults)

    #There is no flow context
    def getFlowContext(self, name):
        return self
    
    #There is no atmosphere context
    def getAtmosphereContext(self, name):
        return self
    
    #There is no component context
    def getComponentContext(self, name):
        return self
    