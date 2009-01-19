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

from zope.interface import implements, Attribute

from flumotion.inhouse import log, utils, annotate

from flumotion.transcoder.admin import interfaces
from flumotion.transcoder.admin.enums import NotificationTriggerEnum
from flumotion.transcoder.admin.enums import ActivityTypeEnum
from flumotion.transcoder.admin.enums import NotificationTypeEnum
from flumotion.transcoder.admin.enums import TranscodingTypeEnum
from flumotion.transcoder.admin.datastore import base, profile, notification


class IActivityStore(base.IBaseStore):
    
    type      = Attribute("The type of activity")
    subtype   = Attribute("The sub-type of activity")
    startTime = Attribute("The time the activity was started")
    lastTime  = Attribute("The last time the activity was attempted")
    state     = Attribute("Activity's state")
    
    def store(self):
        pass
    
    def delete(self):
        pass

    def reset(self):
        pass


class ITranscodingActivityStore(IActivityStore):
    
    inputRelPath = Attribute("Transcoded file relative path")
    
    def getCustomerStore(self):
        pass
    
    def getProfileStore(self):
        pass


class INotificationActivityStore(IActivityStore):
    
    trigger    = Attribute("What has triggered this notification")
    timeout    = Attribute("Timeout to perform the notification")
    retryCount = Attribute("How many times the notification has been attempted")
    retryMax   = Attribute("Maximum time the notification should be attempted")
    retrySleep = Attribute("Time to wait between notification attempts")


class IHTTPActivityStore(INotificationActivityStore):

    url = Attribute("URL used to notify over HTTP") 


class IMailActivityStore(INotificationActivityStore):
    
    senderAddr = Attribute("Sender e-mail addresse")
    subject    = Attribute("Mail subject")
    body       = Attribute("Mail body")


class ISQLActivityStore(INotificationActivityStore):
    
    databaseURI  = Attribute("Database connection URI")
    sqlStatement = Attribute("SQL statement to execute")


## Proxy Descriptors ##

class ReadWriteProxy(base.ReadOnlyProxy):
    def __init__(self, fieldName, default=None):
        base.ReadOnlyProxy.__init__(self, fieldName, default)
    def __set__(self, obj, value):
        assert not obj._deleted
        setattr(obj._data, self._fieldName, utils.deepCopy(value))
        try:
            obj._touche()
        except AttributeError:
            pass


class ReadWriteDataProxy(object):
    def __init__(self, fieldName, default=None):
        self._fieldName = fieldName
        self._default= default
    def __get__(self, obj, type=None):
        result = obj._data.data.get(self._fieldName, self._default)
        return utils.deepCopy(result)
    def __set__(self, obj, value):
        assert not obj._deleted
        obj._data.data[self._fieldName] = utils.deepCopy(value)
        try:
            obj._touche()
        except AttributeError:
            pass
    def __delete__(self, obj):
        raise AttributeError("Attribute cannot be deleted")


class ActivityStore(base.DataStore, log.LoggerProxy):
    implements(IActivityStore)

    type      = base.ReadOnlyProxy("type")
    subtype   = base.ReadOnlyProxy("subtype")
    startTime = base.ReadOnlyProxy("startTime")
    lastTime  = base.ReadOnlyProxy("lastTime")
    state     = ReadWriteProxy("state")
    
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
    
    inputRelPath = base.ReadOnlyProxy("inputRelPath")
    
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
    
    trigger    = base.ReadOnlyProxy("trigger")
    timeout    = ReadWriteProxy("timeout")
    retryCount = ReadWriteProxy("retryCount")
    retryMax   = ReadWriteProxy("retryMax")
    retrySleep = ReadWriteProxy("retrySleep")
    
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
        self._data.customerIdentifier = custStore and custStore.identifier
        self._data.profileIdentifier = profStore and profStore.identifier
        self._data.targetIdentifier = targStore and targStore.identifier
        self._data.retryCount = 0
        self._touche()

    
class HTTPActivityStore(NotificationActivityStore):
    implements(IHTTPActivityStore)

    url = ReadWriteDataProxy("requestURL")

    def __init__(self, logger, stateStore, data, isNew=True):
        NotificationActivityStore.__init__(self, logger, stateStore, data, isNew)


class MailActivityStore(NotificationActivityStore):
    implements(IMailActivityStore)

    senderAddr = ReadWriteDataProxy("senderAddr")
    subject    = ReadWriteDataProxy("subject")
    body       = ReadWriteDataProxy("body")
    
    def __init__(self, logger, stateStore, data, isNew=True):
        NotificationActivityStore.__init__(self, logger, stateStore, data, isNew)

    def _getRecipientsAddr(self):
        """
        Not created by metaclass because it convert from str to list
        """
        recipients = self._data.data.get("recipients", "")
        return [e.strip() for e  in recipients.split(", ")]

    def _setRecipientsAddr(self, recipients):
        """
        Not created by metaclass because it convert from list to str
        """
        data = ", ".join([e.strip() for e in recipients])
        self._data.data["recipients"] = data

    recipientsAddr = property(_getRecipientsAddr, _setRecipientsAddr)


class SQLActivityStore(NotificationActivityStore):
    implements(ISQLActivityStore)

    databaseURI  = ReadWriteDataProxy("uri")
    sqlStatement = ReadWriteDataProxy("sql")

    def __init__(self, logger, stateStore, data, isNew=True):
        NotificationActivityStore.__init__(self, logger, stateStore, data, isNew)


    ## Protected Methods ##
    
    def _setup(self, notifStore, trigger):
        NotificationActivityStore._setup(self, notifStore, trigger)
        uri = notifStore.databaseURI
        if uri is not None: self._data.data["uri"] = uri


_activityLookup = {ActivityTypeEnum.transcoding: 
                   {TranscodingTypeEnum.normal:        TranscodingActivityStore},
                   ActivityTypeEnum.notification: 
                   {NotificationTypeEnum.http_request: HTTPActivityStore,
                    NotificationTypeEnum.email:        MailActivityStore,
                    NotificationTypeEnum.sql:          SQLActivityStore}}


def ActivityFactory(logger, parent, data, isNew=True):
    assert data.type in _activityLookup
    return _activityLookup[data.type][data.subtype](logger, parent, data, isNew)
