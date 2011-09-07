# vi:si:et:sw=4:sts=4:ts=4

# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007,2008,2009 Fluendo, S.L.
# Copyright (C) 2010,2011 Flumotion Services, S.A.
# All rights reserved.
#
# This file may be distributed and/or modified under the terms of
# the GNU Lesser General Public License version 2.1 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.LGPL" in the source distribution for more information.
#
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
