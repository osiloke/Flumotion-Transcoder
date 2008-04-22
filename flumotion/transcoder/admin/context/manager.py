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

from flumotion.transcoder.admin.context import base


class ManagerContext(base.BaseContext):
    
    def __init__(self, adminCtx, managerConfig):
        base.BaseContext.__init__(self, adminCtx)
        self.config = managerConfig

    def getAdminContext(self):
        return self.parent
    
    def getHost(self):
        return str(self.config.host)
    
    def getPort(self):
        return self.config.port
    
    def getUseSSL(self):
        return self.config.useSSL
    
    def getAuthenticator(self):
        return pb.Authenticator(username=self.config.username,
                                password=self.config.password)

    ## Simulate Flow, atmosphere and component contexts ##

    def getManagerContext(self):
        return self

    def getFlowContext(self):
        return self.parent
    
    def getAtmosphereContext(self):
        return self.parent

    def getFlowContextByName(self, name):
        return self
    
    def getAtmosphereContextByName(self, name):
        return self
    
    def getComponentContextByName(self, name):
        return self
    