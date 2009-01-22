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

import datetime

from flumotion.transcoder.admin.context import base
from flumotion.transcoder.admin.datastore import activity


class IActivityContext(base.IBaseStoreContext):

    type      = Attribute("The type of activity")
    subtype   = Attribute("The sub-type of activity")
    startTime = Attribute("The time the activity was started")
    lastTime  = Attribute("The last time the activity was attempted")
    state     = Attribute("Activity's state")

    def getStoreContext(self):
        pass

    def getStatecontext(self):
        pass


class ITranscodingActivityContext(IActivityContext):

    inputRelPath = Attribute("Transcoded file relative path")

    def getCustomerContext(self):
        pass

    def getProfileContext(self):
        pass


class INotificationActivityContext(IActivityContext):

    trigger    = Attribute("What has triggered this notification")
    timeout    = Attribute("Timeout to perform the notification")
    retryCount = Attribute("How many times the notification has been attempted")
    retryMax   = Attribute("Maximum time the notification should be attempted")
    retrySleep = Attribute("Time to wait between notification attempts")

    def getTimeLeftBeforeRetry(self):
        pass


class IHTTPActivityContext(INotificationActivityContext):

    url = Attribute("URL used to notify over HTTP")


class IMailActivityContext(INotificationActivityContext):

    senderAddr = Attribute("Sender e-mail addresse")
    subject    = Attribute("Mail subject")
    body       = Attribute("Mail body")


class ISQLActivityContext(INotificationActivityContext):

    databaseURI  = Attribute("Database connection URI")
    sqlStatement = Attribute("SQL statement to execute")


class ActivityContext(base.BaseStoreContext):

    implements(IActivityContext)

    type      = base.StoreProxy("type")
    subtype   = base.StoreProxy("subtype")
    startTime = base.StoreProxy("startTime")
    lastTime  = base.StoreProxy("lastTime")
    state     = base.StoreProxy("state")

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

    inputRelPath = base.StoreProxy("inputRelPath")

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

    trigger    = base.StoreProxy("trigger")
    timeout    = base.StoreProxy("timeout")
    retryCount = base.StoreProxy("retryCount")
    retryMax   = base.StoreProxy("retryMax")
    retrySleep = base.StoreProxy("retrySleep")

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

    senderAddr     = base.StoreProxy("senderAddr")
    recipientsAddr = base.StoreProxy("recipientsAddr")
    subject        = base.StoreProxy("subject")
    body           = base.StoreProxy("body")

    def __init__(self, stateCtx, activStore):
        NotificationActivityContext.__init__(self, stateCtx, activStore)


class HTTPActivityContext(NotificationActivityContext):

    implements(IHTTPActivityContext)

    url = base.StoreProxy("url")

    def __init__(self, stateCtx, activStore):
        NotificationActivityContext.__init__(self, stateCtx, activStore)


class SQLActivityContext(NotificationActivityContext):

    implements(ISQLActivityContext)

    databaseURI  = base.StoreProxy("databaseURI")
    sqlStatement = base.StoreProxy("sqlStatement")

    def __init__(self, stateCtx, activStore):
        NotificationActivityContext.__init__(self, stateCtx, activStore)


def ActivityContextFactory(parentCtx, activStore):
    return _contextLookup[type(activStore)](parentCtx, activStore)


## Private ##

_contextLookup = {activity.TranscodingActivityStore: TranscodingActivityContext,
                  activity.MailActivityStore:        MailActivityContext,
                  activity.HTTPActivityStore:        HTTPActivityContext,
                  activity.SQLActivityStore:         SQLActivityContext}
