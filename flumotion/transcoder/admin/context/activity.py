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

import datetime

from flumotion.transcoder.admin.context import base
from flumotion.transcoder.admin.datastore import activity


class IActivityContext(base.IBaseStoreContext):
    
    def getStoreContext(self):
        pass
    
    def getStatecontext(self):
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


class ITranscodingActivityContext(IActivityContext):
    
    def getCustomerContext(self):
        pass
    
    def getProfileContext(self):
        pass
    
    def getInputRelPath(self):
        pass


class INotificationActivityContext(IActivityContext):
    
    def getTimeLeftBeforeRetry(self):
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


class IHTTPActivityContext(INotificationActivityContext):

    def getRequestURL(self):
        pass


class IMailActivityContext(INotificationActivityContext):
    
    def getSenderAddr(self):
        pass
    
    def getRecipientsAddr(self):
        pass
    
    def getSubject(self):
        pass
    
    def getBody(self):
        pass


class ActivityContext(base.BaseStoreContext):

    implements(IActivityContext)

    base.store_proxy("type")
    base.store_proxy("subtype")
    base.store_proxy("startTime")
    base.store_proxy("lastTime")
    base.store_proxy("state")
    
    def __init__(self, stateCtx, activStore):
        base.BaseStoreContext.__init__(self, stateCtx, activStore)

    def getAdminContext(self):
        return self.parent.getAdminContext()
    
    def getStoreContext(self):
        return self.parent.getStoreContext()
    
    def getStatecontext(self):
        return self.parent


    ## Protected Methodes ##

    def _setup(self):
        pass
    

class TranscodingActivityContext(ActivityContext):
    
    implements(ITranscodingActivityContext)
    
    base.store_proxy("inputRelPath")
    
    def __init__(self, stateCtx, activStore):
        ActivityContext.__init__(self, stateCtx, activStore)
    
    def getCustomerContext(self):
        custStore = self.store.getCustomerStore()
        if not custStore: return None
        storeCtx = self.getStoreContext()
        return storeCtx.getCustomerContextFor(custStore)
    
    def getProfileContext(self):
        custCtx = self.getCustomerContext()
        if not custCtx: return None
        profStore = self.store.getProfileStore()
        if not profStore: return None
        relPath = self.inputRelPath
        if relPath:
            return custCtx.getProfileContextFor(profStore, relPath)
        return custCtx.getUnboundProfileContextFor(profStore)


    ## Protected Methodes ##

    def _setup(self, profCtx):
        ActivityContext._setup(self)
                

class NotificationActivityContext(ActivityContext):
    
    implements(INotificationActivityContext)
    
    base.store_proxy("trigger")
    base.store_proxy("timeout")
    base.store_proxy("retryCount")
    base.store_proxy("retryMax")
    base.store_proxy("retrySleep")
    
    def __init__(self, stateCtx, activStore):
        ActivityContext.__init__(self, stateCtx, activStore)

    def getTimeLeftBeforeRetry(self):
        now = datetime.datetime.now()
        expected = self.lastTime + datetime.timedelta(0, self.retrySleep)
        if expected < now:
            return 0
        delta = expected - now
        # We ignore the days
        return delta.seconds


    ## Protected Methodes ##
    
    def _setup(self, notifCtx):
        ActivityContext._setup(self)
        self.store.timeout = notifCtx.timeout
        self.store.retryMax = notifCtx.retryMax
        self.store.retrySleep = notifCtx.retrySleep


class MailActivityContext(NotificationActivityContext):
    
    implements(IMailActivityContext)
    
    base.store_proxy("senderAddr")
    base.store_proxy("recipientsAddr")
    base.store_proxy("subject")
    base.store_proxy("body")
    
    def __init__(self, stateCtx, activStore):
        NotificationActivityContext.__init__(self, stateCtx, activStore)
    

class HTTPActivityContext(NotificationActivityContext):
    
    implements(IHTTPActivityContext)
    
    base.store_proxy("url")
    
    def __init__(self, stateCtx, activStore):
        NotificationActivityContext.__init__(self, stateCtx, activStore)


def ActivityContextFactory(parentCtx, activStore):
    return _contextLookup[type(activStore)](parentCtx, activStore)
 

## Private ##

_contextLookup = {activity.TranscodingActivityStore: TranscodingActivityContext,
                  activity.MailActivityStore:        MailActivityContext,
                  activity.HTTPActivityStore:        HTTPActivityContext}
