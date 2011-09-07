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

from zope.interface import classProvides, implements

from flumotion.inhouse.spread import avatars

from flumotion.transcoder.admin.api import interfaces, api, mediums


class Avatar(avatars.Avatar):

    classProvides(avatars.IAvatarFactory)
    implements(interfaces.ITranscoderGateway)

    def __init__(self, service, avatarId, mind):
        avatars.Avatar.__init__(self, service, avatarId, mind)
        self._admin = service.getAdmin()


    ## ITranscoderGateway Methodes ##

    def getWorkerSet(self):
        return api.adapt(self._admin.getWorkerProxySet())

    def getStore(self):
        return api.adapt(self._admin.getStoreContext())

    def getScheduler(self):
        return api.adapt(self._admin.getScheduler())


    ## Make the method remote ##

    perspective_getWorkerSet = getWorkerSet
    perspective_getStore = getStore
    perspective_getScheduler = getScheduler
