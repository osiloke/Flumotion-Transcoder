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

from zope.interface import implements, Attribute

from flumotion.inhouse import log

from flumotion.transcoder.admin import interfaces
from flumotion.transcoder.admin.proxy import base


class IWorkerDefinition(interfaces.IAdminInterface):

    def getName(self):
        pass

    def getWorkerContext(self):
        pass


class IWorkerProxy(IWorkerDefinition, base.IBaseProxy):

    def getHost(self):
        pass


class WorkerDefinition(object):
    """
    Used to represent non-running workers.
    """

    implements(IWorkerDefinition)

    def __init__(self, workerName, workerCtx):
        self.name = workerName
        self._workerCtx = workerCtx


    ## IWorkerDefinition Methodes ##

    def getName(self):
        return self._name

    def getWorkerContext(self):
        return self._workerCtx


class WorkerProxy(base.BaseProxy):
    implements(IWorkerProxy)

    def __init__(self, logger, parentPxy, identifier,
                 managerPxy, workerCtx, workerState):
        base.BaseProxy.__init__(self, logger, parentPxy, identifier, managerPxy)
        self._workerState = workerState
        self._workerCtx = workerCtx


    ## IWorkerDefinition and IFlumotionProxxyRO Methods ##

    def getName(self):
        assert self._workerState, "Worker has been removed"
        return self._workerState.get('name')

    def getHost(self):
        assert self._workerState, "Worker has been removed"
        return self._workerState.get('host')

    def getWorkerContext(self):
        return self._workerCtx


    ## Overriden Methods ##

    def _onRemoved(self):
        assert self._workerState, "Worker has already been removed"

    def _doDiscard(self):
        assert self._workerState, "Worker has already been discarded"
        self._workerState = None


    ## Protected Methods ##

    def _callRemote(self, methodName, *args, **kwargs):
        assert self._workerState, "Worker has been removed"
        workerName = self._workerState.get('name')
        return self._managerPxy._workerCallRemote(workerName,
                                                  methodName,
                                                  *args, **kwargs)


def instantiate(logger, parentPxy, identifier, managerPxy,
                workerContext, workerState, *args, **kwargs):
    return WorkerProxy(logger, parentPxy, identifier, managerPxy,
                       workerContext, workerState, *args, **kwargs)
