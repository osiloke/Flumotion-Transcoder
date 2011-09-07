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

from zope.interface import implements

from flumotion.transcoder.admin.context import base, activity, profile


class IStateContext(base.IBaseStoreContext):

    def getStoreContext(self):
        pass

    def getActivityContextFor(self, activStore):
        pass

    def retrieveTranscodingContexts(self, states):
        pass

    def retrieveNotificationContexts(self, states):
        pass

    def newTranscodingContext(self, label, state, profCtx, startTime=None):
        pass


class StateContext(base.BaseStoreContext):

    implements(IStateContext)

    def __init__(self, storeContext, stateStore):
        base.BaseStoreContext.__init__(self, storeContext, stateStore)

    def getAdminContext(self):
        return self.parent.getAdminContext()

    def getStoreContext(self):
        return self.parent

    def getActivityContextFor(self, activStore):
        assert activStore.parent == self.store
        return activity.ActivityContextFactory(self, activStore)

    def retrieveTranscodingContexts(self, states):
        d = self.store.retrieveTranscodingStores(states)
        d.addCallback(self.__wrappActivities)
        return d

    def retrieveNotificationContexts(self, states):
        d = self.store.retrieveNotificationStores(states)
        d.addCallback(self.__wrappActivities)
        return d

    def newTranscodingContext(self, label, state, profCtx, startTime=None):
        assert isinstance(profCtx, profile.ProfileContext)
        inputRelPath = profCtx.inputRelPath
        activStore = self.store.newTranscodingStore(label, state, profCtx.store,
                                                    inputRelPath, startTime)
        activCtx = self.getActivityContextFor(activStore)
        activCtx._setup(profCtx)
        return activCtx

    def newNotificationContext(self, subtype, label, state, notifCtx, trigger, startTime=None):
        activStore = self.store.newNotificationStore(subtype, label, state,
                                                     notifCtx.store, trigger, startTime)
        activCtx = self.getActivityContextFor(activStore)
        activCtx._setup(notifCtx)
        return activCtx


    ## Private Methodes ##

    def __wrappActivities(self, activities):
        return [activity.ActivityContextFactory(self, a) for a in activities]
