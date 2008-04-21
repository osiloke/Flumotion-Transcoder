# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder.admin.context import base, activity, profile


class StateContext(base.BaseStoreContext):
    
    def __init__(self, storeContext, stateStore):
        base.BaseStoreContext.__init__(self, storeContext, stateStore)

    def getAdminContext(self):
        return self._parent.getAdminContext()
    
    def getStoreContext(self):
        return self._parent

    def getActivityContextFor(self, activStore):
        assert activStore.getParent() == self._store
        return activity.ActivityContextFactory(self, activStore)

    def retrieveTranscodingContexts(self, states):
        d = self._store.retrieveTranscodingStores(states)
        d.addCallback(self.__wrappActivities)
        return d
    
    def retrieveNotificationContexts(self, states):
        d = self._store.retrieveNotificationStores(states)
        d.addCallback(self.__wrappActivities)
        return d
    
    def newTranscodingContext(self, label, state, profCtx, startTime=None):
        assert isinstance(profCtx, profile.ProfileContext)
        inputRelPath = profCtx.getInputRelPath()
        profStore = profCtx.getStore()
        activStore = self._store.newTranscodingStore(label, state, profStore,
                                                     inputRelPath, startTime)
        activCtx = self.getActivityContextFor(activStore)
        activCtx._setup(profCtx)
        return activCtx
     
    def newNotificationContext(self, subtype, label, state, notifCtx, trigger, startTime=None):
        notifStore = notifCtx.getStore()
        activStore = self._store.newNotificationStore(subtype, label, state,
                                                      notifStore, trigger, startTime)
        activCtx = self.getActivityContextFor(activStore)
        activCtx._setup(notifCtx)
        return activCtx
    
    
    ## Private Methodes ##
    
    def __wrappActivities(self, activities):
        return [activity.ActivityContextFactory(self, a) for a in activities]
