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
from flumotion.transcoder.admin.enums import NotificationTriggerEnum
from flumotion.transcoder.admin.enums import ActivityTypeEnum
from flumotion.transcoder.admin.enums import NotificationTypeEnum
from flumotion.transcoder.admin.enums import TranscodingTypeEnum
from flumotion.transcoder.admin.datastore import base, profile, notification


class IActivityStore(base.IBaseStore):
    
    def store(self):
        pass
    
    def delete(self):
        pass

    def reset(self):
        pass
        
    def getType(self):
        pass
    
    def getSubtype(self):
        pass
    
    def getStartTime(self):
        pass
    
    def getLastTime(self):
        pass
    
    def getState(self):
        pass
    
    def setState(self, state):
        pass    


class ITranscodingActivityStore(IActivityStore):
    
    def getCustomerStore(self):
        pass
    
    def getProfileStore(self):
        pass
    
    def getInputRelPath(self):
        pass


class INotificationActivityStore(IActivityStore):
    
    def incRetryCount(self):
        pass
    
    def getTrigger(self):
        pass
    
    def getTimeout(self):
        pass
    
    def getRetryCount(self):
        pass
    
    def getRetryMax(self):
        pass
    
    def getRetrySleep(self):
        pass

    def setTimeout(self):
        pass
    
    def setRetryCount(self):
        pass
    
    def setRetryMax(self):
        pass
    
    def setRetrySleep(self):
        pass


class IHTTPActivityStore(INotificationActivityStore):

    def getRequestURL(self):
        pass
    
    def setRequestURL(self, url):
        pass


class IMailActivityStore(INotificationActivityStore):
    
    def getSenderAddr(self):
        pass
    
    def getRecipientsAddr(self):
        pass
    
    def getSubject(self):
        pass
    
    def getBody(self):
        pass
    
    def setSenderAddr(self, sender):
        pass
    
    def setRecipientsAddr(self, recipients):
        pass
    
    def setSubject(self, subject):
        pass
    
    def setBody(self, body):
        pass



## Getter Factories ##

def _setterFactory(propertyName, fieldName, setterName):
    def setter(self, value):
        assert not self._deleted
        setattr(self._data, fieldName, utils.deepCopy(value))
        self._touche()
    return setter

def _dataGetterFactory(propertyName, fieldName, getterName, default=None):
    def getter(self):
        result = self._data.data.get(fieldName, default)
        return utils.deepCopy(result)
    return getter

def _dataSetterFactory(propertyName, fieldName, setterName):
    def setter(self, value):
        assert not self._deleted
        self._data.data[fieldName] = utils.deepCopy(value)
        self._touche()
    return setter


class ActivityStore(base.DataStore, log.LoggerProxy):
    implements(IActivityStore)

    base.readonly_proxy("type")
    base.readonly_proxy("subtype")
    base.readonly_proxy("startTime")
    base.readonly_proxy("lastTime")
    base.readwrite_proxy("state", setterFactory=_setterFactory)
    
    def __init__(self, logger, stateStore, data, isNew=True):
        log.LoggerProxy.__init__(self, logger)
        base.DataStore.__init__(self, stateStore, data, label=data.label)
        self._deleted = False
        self._isNew = isNew

    def getAdminStore(self):
        return self.parent.getAdminStore()
    
    def getStateStore(self):
        return self.parent
        
    def store(self):
        assert not self._deleted
        d = self.parent._storeActivity(self, self._isNew)
        d.addErrback(self.__ebActivityStoreFailed)
        self._new = False
    
    def delete(self):
        assert not self._deleted
        self._deleted = True
        d = self.parent._deleteActivity(self)
        d.addErrback(self.__ebActivityDeleteFailed)

    def reset(self):
        assert not self._deleted
        return self.parent._resetActivity(self)
    
    
    ## Protected Methods ##
    
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


class TranscodingActivityStore(ActivityStore):
    implements(ITranscodingActivityStore)
    
    base.readonly_proxy("inputRelPath")
    
    def __init__(self, logger, stateStore, data, isNew=True):
        ActivityStore.__init__(self, logger, stateStore, data, isNew)
        
    def getCustomerStore(self):
        assert not self._deleted
        custIdent = self._data.customerIdentifier
        adminStore = self.getAdminStore()
        return adminStore.getCustomerStore(custIdent, None)
    
    def getProfileStore(self):
        custStore = self.getCustomerStore()
        if not custStore:
            return None
        profIdent = self._data.profileIdentifier
        profStore = custStore.getProfileStore(profIdent, None)
        return profStore

    ## Protected Methods ##
    
    def _setup(self, profStore, relPath):
        assert isinstance(profStore, profile.ProfileStore)
        assert (not relPath) or isinstance(relPath, str)
        custStore = profStore.getCustomerStore()
        self._data.customerIdentifier = custStore.identifier
        self._data.profileIdentifier = profStore.identifier
        self._data.inputRelPath = relPath       
        self._touche()


class NotificationActivityStore(ActivityStore):
    implements(INotificationActivityStore)
    
    base.readonly_proxy("trigger")
    base.readwrite_proxy("timeout",    setterFactory=_setterFactory)
    base.readwrite_proxy("retryCount", setterFactory=_setterFactory)
    base.readwrite_proxy("retryMax",   setterFactory=_setterFactory)
    base.readwrite_proxy("retrySleep", setterFactory=_setterFactory)
    
    def __init__(self, logger, stateStore, data, isNew=True):
        ActivityStore.__init__(self, logger, stateStore, data, isNew)

    def incRetryCount(self):
        assert not self._deleted
        self._data.retryCount += 1
        self._touche()
    

    ## Protected Methods ##

    def _setup(self, notifStore, trigger):
        assert isinstance(notifStore, notification.NotificationStore)
        assert isinstance(trigger, NotificationTriggerEnum)
        self._data.trigger = trigger
        custStore = notifStore.getCustomerStore()
        profStore = notifStore.getProfileStore()
        targStore = notifStore.getTargetStore()
        self._data.customerName = custStore and custStore.getName()
        self._data.profileName = profStore and profStore.getName()
        self._data.targetName = targStore and targStore.getName()
        self._data.retryCount = 0
        self._touche()
    
class HTTPActivityStore(NotificationActivityStore):
    implements(IHTTPActivityStore)

    base.readwrite_proxy("requestURL",
                         getterFactory=_dataGetterFactory,
                         setterFactory=_dataSetterFactory)

    def __init__(self, logger, stateStore, data, isNew=True):
        NotificationActivityStore.__init__(self, logger, stateStore, data, isNew)


class MailActivityStore(NotificationActivityStore):
    implements(IMailActivityStore)

    base.readwrite_proxy("senderAddr",
                         getterFactory=_dataGetterFactory,
                         setterFactory=_dataSetterFactory)
    base.readwrite_proxy("subject",
                         getterFactory=_dataGetterFactory,
                         setterFactory=_dataSetterFactory)
    base.readwrite_proxy("body",
                         getterFactory=_dataGetterFactory,
                         setterFactory=_dataSetterFactory)

    def __init__(self, logger, stateStore, data, isNew=True):
        NotificationActivityStore.__init__(self, logger, stateStore, data, isNew)

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

    recipientsAddr = property(getRecipientsAddr, setRecipientsAddr)


_activityLookup = {ActivityTypeEnum.transcoding: 
                   {TranscodingTypeEnum.normal:        TranscodingActivityStore},
                   ActivityTypeEnum.notification: 
                   {NotificationTypeEnum.http_request: HTTPActivityStore,
                    NotificationTypeEnum.email:        MailActivityStore}}


def ActivityFactory(logger, parent, data, isNew=True):
    assert data.type in _activityLookup
    return _activityLookup[data.type][data.subtype](logger, parent, data, isNew)
