# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import implements

from flumotion.inhouse import annotate

from flumotion.transcoder.admin.context import base
from flumotion.transcoder.admin.datastore import notification, base as storebase


class INotificationContext(base.IBaseStoreContext):

    def getStoreContext(self):
        pass

    def getType(self):
        pass
    
    def getTriggers(self):
        pass


class IMailNotificationContext(INotificationContext):

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


class IHTTPNotificationContext(INotificationContext):

    def getRequestTemplate(self):
        pass
    
    def getTimeout(self):
        pass
    
    def getRetryMax(self):
        pass
    
    def getRetrySleep(self):
        pass


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
    
    base.store_proxy("type")
    base.store_proxy("triggers")
    
    def __init__(self, parentCtx, notifStore):
        base.BaseStoreContext.__init__(self, parentCtx, notifStore)
    
    def getAdminContext(self):
        return self.parent.getAdminContext()
    
    def getStoreContext(self):
        return self.parent.getStoreContext()


class MailNotificationContext(NotificationContext):

    implements(IMailNotificationContext)

    base.store_proxy("attachments")
    base.store_proxy("recipients")
    base.store_admin_proxy("subjectTemplate", "mailSubjectTemplate")
    base.store_admin_proxy("bodyTemplate",    "mailBodyTemplate")
    base.store_admin_proxy("timeout",         "mailTimeout")
    base.store_admin_proxy("retryMax",        "mailRetryMax")
    base.store_admin_proxy("retrySleep",      "mailRetrySleep")
    
    def __init__(self, parentCtx, notifStore):
        NotificationContext.__init__(self, parentCtx, notifStore)


class HTTPNotificationContext(NotificationContext):
    
    implements(IHTTPNotificationContext)
    
    base.store_proxy("requestTemplate")
    base.store_admin_proxy("timeout",    "HTTPRequestTimeout")
    base.store_admin_proxy("retryMax",   "HTTPRequestRetryMax")
    base.store_admin_proxy("tetrySleep", "HTTPRequestRetrySleep")    
    
    def __init__(self, parentCtx, notifStore):
        NotificationContext.__init__(self, parentCtx, notifStore)


def NotificationContextFactory(parentCtx, notifStore):
    return _wrapperLookup[type(notifStore)](parentCtx, notifStore)


## Private ##

_wrapperLookup = {notification.MailNotificationStore: MailNotificationContext,
                  notification.HTTPNotificationStore: HTTPNotificationContext}
