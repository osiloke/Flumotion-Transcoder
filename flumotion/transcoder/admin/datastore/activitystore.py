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

from flumotion.transcoder import log

from flumotion.transcoder.admin.enums import ActivityTypeEnum
from flumotion.transcoder.admin.enums import ActivityStateEnum
from flumotion.transcoder.admin.datastore.profilestore import ProfileStore
from flumotion.transcoder.admin.datastore.notificationstore import BaseNotification


class ActivityStore(log.LoggerProxy):
    
    def __init__(self, parent, dataSource):
        self._parent = parent
        self._dataSource = dataSource
        
    def getLabel(self):
        return "Activity Store"
        
    def getTranscodings(self, states):
        t = ActivityTypeEnum.transcoding
        return self.__getActivities(t, states)

    def getNotifications(self, states):
        t = ActivityTypeEnum.notification
        return self.__getActivities(t, states)
    
    def newTranscoding(self, label, state, profile, inputRelPath, 
                       startTime=None):
        t = ActivityTypeEnum.transcoding
        a = self.__newActivity(t, label, state, startTime)
        a._setProfile(profile)
        a._setInputRelPath(inputRelPath)
        return a
    
    def newNotification(self, label, state, notification, request,
                        startTime=None):
        t = ActivityTypeEnum.notification
        a = self.__newActivity(t, label, state, startTime)
        a._setNotification(notification)
        return a

    
    ## Protected Methods ##
    
    def _storeActivity(self, activity, new):
        data = activity._getData()
        return self._dataSource.store(data)
    
    def _resetActivity(self, activity):
        data = activity._getData()
        return self._dataSource.reset(data)

    def _deleteActivity(self, activity):
        data = activity._getData()
        return self._dataSource.delete(data)

    
    ## Private Methods ##

    def __getActivities(self, type, states):
        d = self._dataSource.retrieveActivities(type, states)
        d.addCallback(self.__cbWrapActivities)
        return d
    
    def __newActivity(self, type, label, state, startTime=None):
        assert isinstance(state, ActivityStateEnum)
        assert isinstance(label, str)
        assert (startTime == None) or isinstance(startTime, datetime.datetime)
        a = self._dataSource.newActivity(type)
        a.state = state
        a.label = label
        a.startTime = startTime or datetime.datetime.now()
        return ActivityFactory(self, a, True)

    def __cbWrapActivities(self, dataList):
        return [ActivityFactory(self, d, False) for d in dataList]
        

class BaseActivity(object):
    
    def __init__(self, parent, data, isNew=True):
        self._parent = parent
        self._data = data
        self._deleted = False
        self._isNew = isNew
        
    def store(self):
        assert not self._deleted
        d = self._parent._storeActivity(self, self._isNew)
        d.addErrback(self.__ebActivityStoreFailed)
        self._new = False
    
    def delete(self):
        assert not self._deleted
        self._deleted = True
        d = self._parent._deleteActivity(self)
        d.addErrback(self.__ebActivityDeleteFailed)

    def reset(self):
        assert not self._deleted
        return self._parent._resetActivity(self)
        
    def getLabel(self):
        assert not self._deleted
        return self._data.label
    
    def getType(self):
        assert not self._deleted
        return self._data.type
    
    def getState(self):
        assert not self._deleted
        return self._data.state

    def setState(self, state):
        assert not self._deleted
        assert isinstance(state, ActivityStateEnum)
        self._data.state = state
        self._touche()
    
    def getStartTime(self):
        assert not self._deleted
        return self._data.startTime
    
    def getLastTime(self):
        assert not self._deleted
        return self._data.lastTime
            

    ## Protected Methods ##
    
    def _getAdminStore(self):
        return self._parent._parent
    
    def _touche(self):
        self._data.lastTime = datetime.datetime.now()
    
    def _getData(self):
        return self._data


    ## Private Methods ##
    
    def __ebActivityStoreFailed(self, failure):
        self.warning("Fail to store %s activity '%s': %s",
                     self._data and self._data.type and self._data.type.nick,
                     self._data and self._data.label,
                     log.getFailureMessage(failure))
        self.debug("Activity storing traceback:\n%s",
                   log.getFailureTraceback(failure))
        
    def __ebActivityDeleteFailed(self, failure):
        self.warning("Fail to delete %s activity '%s': %s",
                     self._data and self._data.type and self._data.type.nick,
                     self._data and self._data.label,
                     log.getFailureMessage(failure))
        self.debug("Activity deletion traceback:\n%s",
                   log.getFailureTraceback(failure))


class TranscodingActivity(BaseActivity):
    
    def __init__(self, parent, data, isNew=True):
        BaseActivity.__init__(self, parent, data, isNew)
        
    def getInputRelPath(self):
        assert not self._deleted
        return self._data.inputRelPath
    
    def getCustomer(self):
        assert not self._deleted
        custName = self._data.customerName
        return self._getAdminStore().getCustomer(custName, None)
    
    def getProfile(self):
        assert not self._deleted
        custName = self._data.customerName
        cust = self._getAdminStore().getCustomer(custName, None)
        if not cust:
            return None
        prof = cust.getProfile(self._data.profileName, None)
        return prof


    ## Protected Methods ##
    
    def _setProfile(self, profile):
        assert isinstance(profile, ProfileStore)
        self._data.customerName = profile.getCustomer().getName()
        self._data.profileName = profile.getName()

    def _setInputRelPath(self, relPath):
        assert not self._deleted
        assert (not relPath) or isinstance(relPath, str)
        self._data.inputRelPath = relPath


class NotificationActivity(BaseActivity):
    
    def __init__(self, parent, data, isNew=True):
        BaseActivity.__init__(self, parent, data, isNew)

    def getRequestURL(self):
        assert not self._deleted
        return self._data.requestURL
    
    def getRetryCount(self):
        assert not self._deleted
        return self._data.retryCount
    
    def getRetryMax(self):
        assert not self._deleted
        return self._data.retryMax
    
    def getRetryNextTime(self):
        assert not self._deleted
        return self._data.retryNextTime
    
    def setRetryCount(self, count):
        assert not self._deleted
        self._data.retryCount = count
    
    def setRetryMax(self, max):
        assert not self._deleted
        self._data.retryMax = max
    
    def setRetryNextTime(self, time):
        assert not self._deleted
        self._data.retryNextTime = time
    
    ## Protected Methods ##

    def _setRequestURL(self, url):
        assert not self._deleted
        self._data.requestURL = url
    
    def _setNotification(self, notification):
        assert isinstance(notification, BaseNotification)
        #cust = notification.getCustomer()
        #prof = notification.getProfile()
        #self._data.customerName = cust and cust.getName()
        #self._data.profileName = prof and prof.getName()
    
    
_activityLookup = {ActivityTypeEnum.transcoding: TranscodingActivity,
                   ActivityTypeEnum.notification: NotificationActivity}


def ActivityFactory(parent, data, isNew=True):
    assert data.type in _activityLookup
    return _activityLookup[data.type](parent, data, isNew)
