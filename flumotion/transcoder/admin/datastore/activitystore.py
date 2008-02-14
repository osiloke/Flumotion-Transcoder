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
from cStringIO import StringIO

from flumotion.inhouse import log, utils

from flumotion.transcoder.admin.enums import ActivityTypeEnum
from flumotion.transcoder.admin.enums import ActivityStateEnum
from flumotion.transcoder.admin.enums import TranscodingTypeEnum
from flumotion.transcoder.admin.enums import NotificationTypeEnum
from flumotion.transcoder.admin.enums import NotificationTriggerEnum
from flumotion.transcoder.admin.datastore.basestore import MetaStore
from flumotion.transcoder.admin.datastore.profilestore import ProfileStore
from flumotion.transcoder.admin.datastore.notifystore import BaseNotification



class ActivityStore(log.LoggerProxy):
    
    def __init__(self, logger, parent, dataSource):
        log.LoggerProxy.__init__(self, logger)
        self._parent = parent
        self._dataSource = dataSource
        
    def getLabel(self):
        return "Activity Store"
    
    def getIdentifier(self):
        return self.getLabel()
        
    def getTranscodings(self, states):
        t = ActivityTypeEnum.transcoding
        return self.__getActivities(t, states)

    def getNotifications(self, states):
        t = ActivityTypeEnum.notification
        return self.__getActivities(t, states)
    
    def newTranscoding(self, label, state, profile, 
                       inputRelPath, startTime=None):
        t = ActivityTypeEnum.transcoding
        a = self.__newActivity(t, TranscodingTypeEnum.normal,
                               label, state, startTime)
        a._setup(profile, inputRelPath)
        return a
    
    def newNotification(self, subtype, label, state, notification,
                        trigger, startTime=None):
        assert isinstance(subtype, NotificationTypeEnum)
        t = ActivityTypeEnum.notification
        a = self.__newActivity(t, subtype, label, state, startTime)
        a._setup(notification, trigger)
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
    
    def __newActivity(self, type, subtype, label, state, startTime=None):
        assert isinstance(type, ActivityTypeEnum)
        assert isinstance(state, ActivityStateEnum)
        assert isinstance(label, str)
        assert (startTime == None) or isinstance(startTime, datetime.datetime)
        a = self._dataSource.newActivity(type, subtype)
        a.state = state
        a.label = label
        a.startTime = startTime or datetime.datetime.now()
        return ActivityFactory(self, self, a, True)

    def __cbWrapActivities(self, dataList):
        return [ActivityFactory(self, self, d, False) for d in dataList]
        
        
def _buildPropertyGetter(propertyName, default):
    def getter(self):
        assert not self._deleted
        result = getattr(self._data, propertyName, default)
        return utils.deepCopy(result)
    return getter

        
        
class BaseActivity(log.LoggerProxy):

    __metaclass__ = MetaStore
    
    # MetaStore metaclass will create getters for these properties
    __getters__ = {"basic":
                       {"getLabel":      ("label",      None),
                        "getIdentifier": ("identifier", None),
                        "getType":       ("type",       None),
                        "getSubType":    ("subtype",    None),
                        "getStartTime":  ("startTime",  None),
                        "getLastTime":   ("lastTime",   None),
                        "getState":      ("state",      None)}}
    
    # MetaStore metaclass will create setters for these properties
    __setters__ = {"basic":
                       {"setState": ("state",)}}

    @staticmethod
    def _data_getter_builder(getterName, dataKey, default):
        def getter(self):
            result = self._data.data.get(dataKey, default)
            return utils.deepCopy(result)
        return getter

    @staticmethod
    def _basic_setter_builder(settername, propertyName):
        def setter(self, value):
            assert not self._deleted
            setattr(self._data, propertyName, utils.deepCopy(value))
            self._touche()
        return setter
    
    @staticmethod
    def _data_setter_builder(setterName, dataKey):
        def setter(self, value):
            assert not self._deleted
            self._data.data[dataKey] = utils.deepCopy(value)
            self._touche()
        return setter

    
    def __init__(self, logger, parent, data, isNew=True):
        log.LoggerProxy.__init__(self, logger)
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
        

    ## Protected Methods ##
    
    def _getAdminStore(self):
        return self._parent._parent
    
    def _touche(self):
        self._data.lastTime = datetime.datetime.now()
    
    def _getData(self):
        return self._data


    ## Private Methods ##
    
    def __ebActivityStoreFailed(self, failure):
        log.notifyFailure(self, failure,
                          "Fail to store %s activity '%s'",
                          self._data and self._data.type and self._data.type.nick,
                          self._data and self._data.label)
        
    def __ebActivityDeleteFailed(self, failure):
        log.notifyFailure(self, failure,
                          "Fail to delete %s activity '%s'",
                          self._data and self._data.type and self._data.type.nick,
                          self._data and self._data.label)


class TranscodingActivity(BaseActivity):
    
    # MetaStore metaclass will create getters for these properties
    __getters__ = {"basic":
                       {"getInputRelPath": ("inputRelPath", None)}}
    
    def __init__(self, logger, parent, data, isNew=True):
        BaseActivity.__init__(self, logger, parent, data, isNew)
        
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
    
    def _setup(self, profile, relPath):
        assert isinstance(profile, ProfileStore)
        assert (not relPath) or isinstance(relPath, str)
        self._data.customerName = profile.getCustomer().getName()
        self._data.profileName = profile.getName()
        self._data.inputRelPath = relPath       
        self._touche()


class BaseNotifyActivity(BaseActivity):
    
    # MetaStore metaclass will create getters for these properties
    __getters__ = {"basic":
                       {"getTrigger":    ("trigger",    None),
                        "getTimeout":    ("timeout",    None),
                        "getRetryCount": ("retryCount", None),
                        "getRetryMax":   ("retryMax",   None),
                        "getRetrySleep": ("retrySleep", None)}}
    
    def __init__(self, logger, parent, data, isNew=True):
        BaseActivity.__init__(self, logger, parent, data, isNew)

    def getTimeLeftBeforeRetry(self):
        now = datetime.datetime.now()
        last = self.getLastTime()
        sleep = self.getRetrySleep()
        expected = last + datetime.timedelta(0, sleep)
        if expected < now:
            return 0
        delta = expected - now
        # We ignore the days
        return delta.seconds

    def incRetryCount(self):
        assert not self._deleted
        self._data.retryCount += 1
        self._touche()
    

    ## Protected Methods ##

    def _setup(self, notification, trigger):
        assert isinstance(notification, BaseNotification)
        assert isinstance(trigger, NotificationTriggerEnum)
        self._data.trigger = trigger
        self._data.timeout = notification.getTimeout()
        self._data.retryMax = notification.getRetryMax()
        self._data.retrySleep = notification.getRetrySleep()
        customer = notification.getCustomer()
        profile = notification.getProfile()
        target = notification.getTarget()
        self._data.customerName = customer and customer.getName()
        self._data.profileName = profile and profile.getName()
        self._data.targetName = target and target.getName()
        self._data.retryCount = 0
        self._touche()
    
    
class GETRequestNotifyActivity(BaseNotifyActivity):

    # MetaStore metaclass will create getters for these properties
    __getters__ = {"data":
                       {"getRequestURL": ("url", None)}}

    # MetaStore metaclass will create setters for these properties
    __setters__ = {"data":
                       {"setRequestURL": ("url",)}}

    def __init__(self, logger, parent, data, isNew=True):
        BaseNotifyActivity.__init__(self, logger, parent, data, isNew)


class MailNotifyActivity(BaseNotifyActivity):

    # MetaStore metaclass will create getters for these properties
    __getters__ = {"data":
                       {"getSenderAddr": ("sender",  None),
                        "getSubject":    ("subject", None),
                        "getBody":       ("body",    None)}}

    # MetaStore metaclass will create setters for these properties
    __setters__ = {"data":
                       {"setSenderAddr": ("sender",),
                        "setSubject":    ("subject",),
                        "setBody":       ("body",)}}

    def __init__(self, logger, parent, data, isNew=True):
        BaseNotifyActivity.__init__(self, logger, parent, data, isNew)

    def getRecipientsAddr(self):
        """
        Not created by metaclass because it convert from str to list
        """
        recipients = self._data.data.get("recipients", "")
        return [e.strip() for e  in recipients.split(", ")]

    def setRecipientsAddr(self, recipients):
        """
        Not created by metaclass because it convert from list to str
        """
        data = ", ".join([e.strip() for e in recipients])
        self._data.data["recipients"] = data


_activityLookup = {ActivityTypeEnum.transcoding: 
                   {TranscodingTypeEnum.normal: TranscodingActivity},
                   ActivityTypeEnum.notification: 
                   {NotificationTypeEnum.get_request: GETRequestNotifyActivity,
                    NotificationTypeEnum.email: MailNotifyActivity}}


def ActivityFactory(logger, parent, data, isNew=True):
    assert data.type in _activityLookup
    return _activityLookup[data.type][data.subtype](logger, parent, data, isNew)
