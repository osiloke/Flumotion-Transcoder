# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import datetime

from zope.interface import implements

from flumotion.inhouse import log, utils, annotate

from flumotion.transcoder.admin import interfaces
from flumotion.transcoder.admin.enums import ActivityTypeEnum
from flumotion.transcoder.admin.enums import NotificationTypeEnum
from flumotion.transcoder.admin.enums import TranscodingTypeEnum
from flumotion.transcoder.admin.enums import ActivityStateEnum
from flumotion.transcoder.admin.datastore import activity


class IStateStore(interfaces.IAdminInterface):
    
    def retrieveTranscodingStores(self, states):
        pass

    def retrieveNotificationStores(self, states):
        pass
    
    def newTranscodingStore(self, label, state, profStore, 
                            inputRelPath, startTime=None):
        pass
    
    def newNotificationStore(self, subtype, label, state, notifStore,
                             trigger, startTime=None):
        pass


class StateStore(log.LoggerProxy):
    implements(IStateStore)
    
    def __init__(self, logger, adminStore, dataSource):
        log.LoggerProxy.__init__(self, logger)
        self._parent = adminStore
        self._dataSource = dataSource
    
    def getAdminStore(self):
        return self._parent
    
    def getLabel(self):
        return "State Store"
    
    def getIdentifier(self):
        return self.getLabel()
        
    def retrieveTranscodingStores(self, states):
        t = ActivityTypeEnum.transcoding
        return self.__getActivities(t, states)

    def retrieveNotificationStores(self, states):
        t = ActivityTypeEnum.notification
        return self.__getActivities(t, states)
    
    def newTranscodingStore(self, label, state, profStore, 
                            inputRelPath, startTime=None):
        t = ActivityTypeEnum.transcoding
        a = self.__newActivity(t, TranscodingTypeEnum.normal,
                               label, state, startTime)
        a._setup(profStore, inputRelPath)
        return a
    
    def newNotificationStore(self, subtype, label, state, notifStore,
                             trigger, startTime=None):
        assert isinstance(subtype, NotificationTypeEnum)
        t = ActivityTypeEnum.notification
        a = self.__newActivity(t, subtype, label, state, startTime)
        a._setup(notifStore, trigger)
        return a

    
    ## Protected Methods ##
    
    def _storeActivity(self, activStore, new):
        data = activStore._getData()
        return self._dataSource.store(data)
    
    def _resetActivity(self, activStore):
        data = activStore._getData()
        return self._dataSource.reset(data)

    def _deleteActivity(self, activStore):
        data = activStore._getData()
        return self._dataSource.delete(data)

    
    ## Private Methods ##

    def __getActivities(self, type, states):
        d = self._dataSource.retrieveActivities(type, states)
        d.addCallback(self.__cbWrapActivities)
        return d
    
    def __newActivity(self, type, subtype, label, state, startTime=None):
        assert isinstance(type, ActivityTypeEnum)
        assert isinstance(state, ActivityStateEnum)
        assert isinstance(label, str)
        assert (startTime == None) or isinstance(startTime, datetime.datetime)
        a = self._dataSource.newActivity(type, subtype)
        a.state = state
        a.label = label
        a.startTime = startTime or datetime.datetime.now()
        return activity.ActivityFactory(self, self, a, True)

    def __cbWrapActivities(self, activDataList):
        return [activity.ActivityFactory(self, self, d, False) for d in activDataList]
