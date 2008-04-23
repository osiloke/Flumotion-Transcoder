# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.inhouse import log, utils

from zope.interface import implements

from flumotion.transcoder.admin import interfaces
from flumotion.transcoder.admin.enums import NotificationTypeEnum
from flumotion.transcoder.admin.datastore import base


class INotificationStore(base.IBaseStore):

    def getType(self):
        pass
    
    def getTriggers(self):
        pass


class IMailNotificationStore(INotificationStore):

    def getAttachments(self):
        pass
    
    def getRecipients(self):
        pass
    
    def getSubjectTemplate(self):
        pass
    
    def getBodyTemplate(self):
        pass
    
    def getTimeout(self):
        pass
    
    def getRetryMax(self):
        pass
    
    def getRetrySleep(self):
        pass


class IHTTPNotificationStore(INotificationStore):

    def getRequestTemplate(self):
        pass
    
    def getTimeout(self):
        pass
    
    def getRetryMax(self):
        pass
    
    def getRetrySleep(self):
        pass


class NotificationStore(base.DataStore):
    implements(INotificationStore)
    
    base.genGetter("getIdentifier", "identifier")
    base.genGetter("getType",       "type")
    base.genGetter("getTriggers",   "triggers")
    
    def __init__(self, parentStore, data, adminStore,
                 custStore, profStore, targStore, label=None):
        base.DataStore.__init__(self, parentStore, data, label)
        self._adminStore = adminStore
        self._custStore = custStore
        self._profStore = profStore
        self._targStore = targStore

    def getAdmiStore(self):
        return self._adminStore

    def getCustomerStore(self):
        return self._custStore
    
    def getProfileStore(self):
        return self._profStore
    
    def getTargetStore(self):
        return self._targStore
    

class MailNotificationStore(NotificationStore):
    implements(IMailNotificationStore)
    
    base.genGetter("getAttachments", "attachments", set([]))
    base.genGetter("getRecipients", "recipients", dict())
    base.genGetter("getSubjectTemplate", "subjectTemplate")
    base.genGetter("getBodyTemplate", "bodyTemplate")
    base.genGetter("getTimeout", "timeout")
    base.genGetter("getRetryMax", "retryMax")
    base.genGetter("getRetrySleep", "retrySleep")
    
    def __init__(self, parentStore, data, adminStore,
                 custStore, profStore, targStore):
        emails = [e[1] for v in data.recipients.values() for e in v]
        label = "Mail Notification to %s" % ", ".join(emails)
        NotificationStore.__init__(self, parentStore, data, adminStore,
                                   custStore, profStore, targStore, label=label)
        
        
class HTTPNotificationStore(NotificationStore):
    implements(IHTTPNotificationStore)
    
    base.genGetter("getRequestTemplate", "requestTemplate", set([]))
    base.genGetter("getTimeout", "timeout")
    base.genGetter("getRetryMax", "retryMax")
    base.genGetter("getRetrySleep", "retrySleep")
    
    def __init__(self, parentStore, data, adminStore, custStore, profStore, targStore):
        label = "HTTP Notification to %s" % data.requestTemplate
        NotificationStore.__init__(self, parentStore, data, adminStore,
                                   custStore, profStore, targStore, label=label)
    

_notifLookup = {NotificationTypeEnum.http_request: HTTPNotificationStore,
                NotificationTypeEnum.email:        MailNotificationStore}


def NotificationFactory(parentStore, data, adminStore,
                        custStore, profStore, targStore):
    assert data.type in _notifLookup
    return _notifLookup[data.type](parentStore, data, adminStore,
                                   custStore, profStore, targStore)
