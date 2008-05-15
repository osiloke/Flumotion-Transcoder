# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.inhouse import log, utils, database

from zope.interface import implements, Attribute

from flumotion.transcoder.admin import interfaces
from flumotion.transcoder.admin.enums import NotificationTypeEnum
from flumotion.transcoder.admin.datastore import base


class INotificationStore(base.IBaseStore):

    type       = Attribute("Type of notification")
    triggers   = Attribute("What's trigger the notification")
    timeout    = Attribute("Maximum time to perform the notification") 
    retryMax   = Attribute("How many times the notification should be attempted")
    retrySleep = Attribute("Time to sleep between notification attempts") 

    def getCustomerStore(self):
        pass
    
    def getProfileStore(self):
        pass
    
    def getTargetStore(self):
        pass


class IMailNotificationStore(INotificationStore):

    attachments     = Attribute("What should be attached to the mail")
    recipients      = Attribute("The recipients of the notification mail")
    subjectTemplate = Attribute("Template of the mail subject")
    bodyTemplate    = Attribute("Template of the mail body")



class IHTTPNotificationStore(INotificationStore):

    urlTemplate = Attribute("URL of the HTTP notification")


class ISQLNotificationStore(INotificationStore):
    
    databaseModule   = Attribute("DBAPI 2.0 Python Module")
    databaseHost     = Attribute("Database host")
    databasePort     = Attribute("Database port")
    databaseUsername = Attribute("Database username")
    databasePassword = Attribute("Database password")
    databaseName     = Attribute("Database name")
    sqlTemplate      = Attribute("SQL statement template")


class NotificationStore(base.DataStore):
    implements(INotificationStore)
    
    type       = base.ReadOnlyProxy("type")
    triggers   = base.ReadOnlyProxy("triggers")
    timeout    = base.ReadOnlyProxy("timeout")
    retryMax   = base.ReadOnlyProxy("retryMax")
    retrySleep = base.ReadOnlyProxy("retrySleep")
    
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
    
    attachments     = base.ReadOnlyProxy("attachments", set([]))
    recipients      = base.ReadOnlyProxy("recipients", dict())
    subjectTemplate = base.ReadOnlyProxy("subjectTemplate")
    bodyTemplate    = base.ReadOnlyProxy("bodyTemplate")
    
    def __init__(self, parentStore, data, adminStore,
                 custStore, profStore, targStore):
        emails = [e[1] for v in data.recipients.values() for e in v]
        label = "Mail Notification to %s" % ", ".join(emails)
        NotificationStore.__init__(self, parentStore, data, adminStore,
                                   custStore, profStore, targStore, label=label)
        
        
class HTTPNotificationStore(NotificationStore):
    implements(IHTTPNotificationStore)
    
    urlTemplate = base.ReadOnlyProxy("requestTemplate")
    
    def __init__(self, parentStore, data, adminStore, custStore, profStore, targStore):
        label = "HTTP Notification to %s" % data.urlTemplate
        NotificationStore.__init__(self, parentStore, data, adminStore,
                                   custStore, profStore, targStore, label=label)


class SQLNotificationStore(NotificationStore):
    implements(ISQLNotificationStore)
    
    databaseURI = base.ReadOnlyProxy("databaseURI")
    sqlTemplate = base.ReadOnlyProxy("sqlTemplate")
    
    def __init__(self, parentStore, data, adminStore, custStore, profStore, targStore):
        label = "SQL Notification to %s" % database.filter_uri(data.databaseURI)
        NotificationStore.__init__(self, parentStore, data, adminStore,
                                   custStore, profStore, targStore, label=label)
    

_notifLookup = {NotificationTypeEnum.http_request: HTTPNotificationStore,
                NotificationTypeEnum.email:        MailNotificationStore,
                NotificationTypeEnum.sql:          SQLNotificationStore}


def NotificationFactory(parentStore, data, adminStore,
                        custStore, profStore, targStore):
    assert data.type in _notifLookup
    return _notifLookup[data.type](parentStore, data, adminStore,
                                   custStore, profStore, targStore)
