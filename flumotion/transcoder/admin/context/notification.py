# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import implements, Attribute

from flumotion.inhouse import annotate

from flumotion.transcoder.admin.context import base
from flumotion.transcoder.admin.datastore import notification, base as storebase


class INotificationContext(base.IBaseStoreContext):

    type       = Attribute("Type of notification")
    triggers   = Attribute("What's trigger the notification")
    timeout    = Attribute("Maximum time to perform the notification") 
    retryMax   = Attribute("How many times the notification should be attempted")
    retrySleep = Attribute("Time to sleep between notification attempts") 

    def getStoreContext(self):
        pass


class IMailNotificationContext(INotificationContext):

    attachments     = Attribute("What should be attached to the mail")
    recipients      = Attribute("The recipients of the notification mail")
    subjectTemplate = Attribute("Template of the mail subject")
    bodyTemplate    = Attribute("Template of the mail body")


class IHTTPNotificationContext(INotificationContext):

    urlTemplate = Attribute("URL of the HTTP notification")


class ISQLNotificationContext(INotificationContext):
    
    databaseURI = Attribute("Database connection URI")
    sqlTemplate = Attribute("SQL statement template")


class NotifyStoreMixin(object):
    
    store = None
    
    def getNotificationContexts(self, trigger):
        notifyStore = storebase.INotificationProvider(self.store)
        notifiactions = notifyStore.getNotificationStores(trigger)
        return [NotificationContextFactory(self, n) for n in notifiactions]
    
    def iterNotificationContexts(self, trigger):
        notifyStore = storebase.INotificationProvider(self.store)
        iter = notifyStore.iterNotificationStores(trigger)
        return base.LazyContextIterator(self, NotificationContextFactory, iter)


class NotificationContext(base.BaseStoreContext):
    
    implements(INotificationContext)
    
    type       = base.StoreProxy("type")
    triggers   = base.StoreProxy("triggers")
    
    def __init__(self, parentCtx, notifStore):
        base.BaseStoreContext.__init__(self, parentCtx, notifStore)
    
    def getAdminContext(self):
        return self.parent.getAdminContext()
    
    def getStoreContext(self):
        return self.parent.getStoreContext()


class MailNotificationContext(NotificationContext):

    implements(IMailNotificationContext)

    attachments     = base.StoreProxy("attachments")
    recipients      = base.StoreProxy("recipients")
    subjectTemplate = base.StoreAdminProxy("subjectTemplate", "mailSubjectTemplate")
    bodyTemplate    = base.StoreAdminProxy("bodyTemplate",    "mailBodyTemplate")
    timeout         = base.StoreAdminProxy("timeout",         "mailTimeout")
    retryMax        = base.StoreAdminProxy("retryMax",        "mailRetryMax")
    retrySleep      = base.StoreAdminProxy("retrySleep",      "mailRetrySleep")
    
    def __init__(self, parentCtx, notifStore):
        NotificationContext.__init__(self, parentCtx, notifStore)


class HTTPNotificationContext(NotificationContext):
    
    implements(IHTTPNotificationContext)
    
    urlTemplate = base.StoreProxy("urlTemplate")
    timeout     = base.StoreAdminProxy("timeout",    "HTTPRequestTimeout")
    retryMax    = base.StoreAdminProxy("retryMax",   "HTTPRequestRetryMax")
    retrySleep  = base.StoreAdminProxy("retrySleep", "HTTPRequestRetrySleep")    
    
    def __init__(self, parentCtx, notifStore):
        NotificationContext.__init__(self, parentCtx, notifStore)


class SQLNotificationContext(NotificationContext):
    
    implements(ISQLNotificationContext)
    
    databaseURI = base.StoreProxy("databaseURI")
    sqlTemplate = base.StoreProxy("sqlTemplate")    
    timeout     = base.StoreAdminProxy("timeout",    "sqlTimeout")
    retryMax    = base.StoreAdminProxy("retryMax",   "sqlRetryMax")
    retrySleep  = base.StoreAdminProxy("retrySleep", "sqlRetrySleep")    
    
    def __init__(self, parentCtx, notifStore):
        NotificationContext.__init__(self, parentCtx, notifStore)


def NotificationContextFactory(parentCtx, notifStore):
    return _wrapperLookup[type(notifStore)](parentCtx, notifStore)


## Private ##

_wrapperLookup = {notification.MailNotificationStore: MailNotificationContext,
                  notification.HTTPNotificationStore: HTTPNotificationContext,
                  notification.SQLNotificationStore:  SQLNotificationContext}
