# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.inhouse import annotate

from flumotion.transcoder.admin.context import base
from flumotion.transcoder.admin.datastore import notification, base as storebase


class NotificationStoreMixin(object):
    
    store = None
    
    def getNotificationContexts(self, trigger):
        notifyStore = storebase.INotifyStore(self.store)
        notifiactions = notifyStore.getNotificationStores(trigger)
        return [NotificationContextFactory(self, n) for n in notifiactions]
    
    def iterNotificationContexts(self, trigger):
        notifyStore = storebase.INotifyStore(self.store)
        iter = notifyStore.iterNotificationStores(trigger)
        return base.LazyContextIterator(self, NotificationContextFactory, iter)


class NotificationContext(base.BaseStoreContext):
    
    base.genStoreProxy("getIdentifier")
    base.genStoreProxy("getType")
    base.genStoreProxy("getTriggers")
    
    def __init__(self, parentCtx, notifStore):
        base.BaseStoreContext.__init__(self, parentCtx, notifStore)
    
    def getAdminContext(self):
        return self.parent.getAdminContext()
    
    def getStoreContext(self):
        return self.parent.getStoreContext()


class MailNotificationContext(NotificationContext):

    base.genStoreProxy("getAttachments")
    base.genStoreProxy("getRecipients")
    base.genStoreOverridingStoreProxy("getSubjectTemplate", "getMailSubjectTemplate")
    base.genStoreOverridingStoreProxy("getBodyTemplate",    "getMailBodyTemplate")
    base.genStoreOverridingStoreProxy("getTimeout",         "getMailTimeout")
    base.genStoreOverridingStoreProxy("getRetryMax",        "getMailRetryMax")
    base.genStoreOverridingStoreProxy("getRetrySleep",      "getMailRetrySleep")
    
    def __init__(self, parentCtx, notifStore):
        NotificationContext.__init__(self, parentCtx, notifStore)


class HTTPNotificationContext(NotificationContext):
    
    base.genStoreProxy("getRequestTemplate")
    base.genStoreOverridingStoreProxy("getTimeout",    "getHTTPRequestTimeout")
    base.genStoreOverridingStoreProxy("getRetryMax",   "getHTTPRequestRetryMax")
    base.genStoreOverridingStoreProxy("getRetrySleep", "getHTTPRequestRetrySleep")    
    
    def __init__(self, parentCtx, notifStore):
        NotificationContext.__init__(self, parentCtx, notifStore)


def NotificationContextFactory(parentCtx, notifStore):
    return _wrapperLookup[type(notifStore)](parentCtx, notifStore)


## Private ##

_wrapperLookup = {notification.MailNotificationStore: MailNotificationContext,
                  notification.HTTPNotificationStore: HTTPNotificationContext}
