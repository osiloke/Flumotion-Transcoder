# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import email
import mimetypes

from zope.interface import Interface, implements
from twisted.python.failure import Failure
from twisted.internet import reactor
from twisted.web import client
from twisted.mail.smtp import ESMTPSenderFactory

from flumotion.transcoder import log, defer, utils
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.errors import NotificationError
from flumotion.transcoder.admin.enums import ActivityTypeEnum
from flumotion.transcoder.admin.enums import ActivityStateEnum
from flumotion.transcoder.admin.enums import NotificationTypeEnum
from flumotion.transcoder.admin.enums import MailAddressTypeEnum
from flumotion.transcoder.admin.eventsource import EventSource
from flumotion.transcoder.admin.datastore.activitystore import BaseNotifyActivity
from flumotion.transcoder.admin.datastore.activitystore import MailNotifyActivity
from flumotion.transcoder.admin.datastore.activitystore import GETRequestNotifyActivity


## Notification Function ###

def notifyEmergency(msg, failure=None):
    """
    This function can be used from anywere to notify
    emergency situations when no Notifier reference
    is available.
    Do not raise any exception.
    """

def notifyDebug(msg, failure=None, traceback=None):
    """
    This function can be used from anywere to notify
    debug information (like traceback) when no 
    Notifier reference is available.
    Do not raise any exception.
    """

class INotifierListener(Interface):
    pass
        

class NotifierListener(object):
    
    implements(INotifierListener)
    

class Notifier(log.Loggable, 
               EventSource):
    
    logCategory = adminconsts.NOTIFIER_LOG_CATEGORY
    
    def __init__(self, notifierContext, activityStore):
        self._activities = activityStore
        self._context = notifierContext
        self._retries = {} # {BaseNotifyActivity: IDelayedCall}
        self._results = {} # {BaseNotifyActivity: Deferred}


    ## Public Methods ##
    
    def initialize(self):
        return defer.succeed(self)
    
    def notify(self, label, trigger, notification, variables, documents):
        self.info("%s notification '%s' [%s] initiated", 
                  notification.getType().nick, label, trigger.nick)
        activity = self.__prepareNotification(label, trigger, notification, 
                                              variables, documents)
        activity.store()
        d = defer.Deferred()
        self._results[activity] = d
        self._retries[activity] = None
        self.__performNotification(activity)
        return d
    
    
    ## Protected Static Methods ##

    @staticmethod
    def _postMail(smtpServer, smtpUsername, smtpPassword, 
                  sender, recipients, bodyFile, 
                  timeout=None, retries=0):
        d = defer.Deferred()
        authenticate = (smtpUsername != None) and (smtpUsername != "")
        factory = ESMTPSenderFactory(username=smtpUsername,
                                     password=smtpPassword,
                                     requireAuthentication=authenticate,
                                     fromEmail=sender[1], 
                                     toEmail=[m[1] for m in recipients],
                                     file=bodyFile, 
                                     deferred=d,
                                     retries=retries,
                                     timeout=timeout)
        reactor.connectTCP(smtpServer, 25, factory)
        return d

    @staticmethod
    def _performGetRequest(url, timeout=None):
        return client.getPage(url, timeout=timeout,
                              agent=adminconsts.GET_REQUEST_AGENT)
    
    ## Private Methods ##
    
    def __doPrepareGetRequest(self, label, trigger, notif, vars, docs):
        store = self._activities
        activity = store.newNotification(NotificationTypeEnum.get_request,
                                         label, ActivityStateEnum.started,
                                         notif, trigger)
        url = vars.substitute(notif.getRequestTemplate())
        activity.setRequestURL(url)
        return activity
    
    def __doPrepareMailPost(self, label, trigger, notif, vars, docs):
        store = self._activities
        activity = store.newNotification(NotificationTypeEnum.email,
                                         label, ActivityStateEnum.started,
                                         notif, trigger)
        sender = self._context.config.mailSender
        senderAddr = utils.splitMailAddress(sender)[1]
        activity.setSenderAddr(senderAddr)
        recipients = notif.getRecipients()
        allRecipientsAddr = [f[1] for l in recipients.values() for f in l]
        activity.setRecipientsAddr(allRecipientsAddr)
        subject = vars.substitute(notif.getSubjectTemplate())
        activity.setSubject(subject)
        
        toRecipientsFields = recipients.get(MailAddressTypeEnum.to, [])
        toRecipients = utils.joinMailRecipients(toRecipientsFields)
        ccRecipientsFields = recipients.get(MailAddressTypeEnum.cc, [])
        ccRecipients = utils.joinMailRecipients(ccRecipientsFields)
        
        body = vars.substitute(notif.getBodytemplate())

        msg = email.MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = toRecipients
        msg['cc'] = ccRecipients
        txt = email.MIMEText(body)
        msg.attach(txt)
        
        attachments = notif.getAttachments()
        for doc in docs:
            if doc.getType() in attachments:
                mimeType = doc.getMimeType()
                mainType, subType = mimeType.split('/', 1)
                data = email.MIMEBase(mainType, subType)
                data.set_payload(doc.asString())
                email.Encoders.encode_base64(data)
                data.add_header('Content-Disposition', 'attachment', 
                                filename=doc.getLabel())
                msg.attach(data)
        activity.setBody(str(msg))
        
        return activity
    
    def __doPerformGetRequest(self, activity):
        assert isinstance(activity, GETRequestNotifyActivity)
        self.debug("GET request '%s' initiated for URL %s" 
                   % (activity.getLabel(), activity.getRequestURL()))
        d = self._performGetRequest(activity.getRequestURL(), 
                                    timeout=activity.getTimeout())
        args = (activity,)
        d.addCallbacks(self.__cbGetPageSucceed, self.__ebGetPageFailed,
                       callbackArgs=args, errbackArgs=args)
        return d

    def __cbGetPageSucceed(self, page, activity):
        self.debug("GET request '%s' succeed", activity.getLabel())
        self.log("GET request '%s' received page:\n%s",
                 activity.getLabel(), page)
        self.__notificationSucceed(activity)

    def __ebGetPageFailed(self, failure, activity):
        self.debug("GET request '%s' failed: %s", activity.getLabel(), 
                   log.getFailureMessage(failure))
        self.__retryNotification(activity)

    def __doPerformMailPost(self, activity):
        assert isinstance(activity, MailNotifyActivity)
        self.debug("Mail posting '%s' initiated for %s" 
                   % (activity.getLabel(), activity.getRecipients()))
        sender = utils.splitMailAddress(activity.getSender())
        recipients = utils.splitMailRecipients(activity.getRecipients())
        self.log("Posting mail from %s to %s",
                 sender[1], ", ".join([r[1] for r in recipients]))
        d = self._postMail(self._context.config.smtpServer,
                           self._context.config.smtpUsername,
                           self._context.config.smtpPassword,
                           self._context.config.smtpServer,
                           sender, recipients,
                           activity.getBody(),
                           activity.getTimeout())
        args = (activity,)
        d.addCallbacks(self.__cbPostMailSucceed, self.__ebPostMailFailed,
                       callbackArgs=args, errbackArgs=args)
        return d

    def __cbPostMailSucceed(self, results, activity):
        self.debug("Mail post '%s' succeed", activity.getLabel())
        self.log("Mail post '%s' responses; %s",
                 activity.getLabel(), ", ".join("'%s': '%s'" % (m, r) 
                                                for m, c, r in results))
        self.__notificationFailed(activity)
    
    def __ebPostMailFailed(self, failure, activity):
        self.debug("Mail post '%s' failed: %s", activity.getLabel(), 
                   log.getFailureMessage(failure))
        self.__retryNotification(activity)

    def __retryNotification(self, activity):
        activity.incRetryCount()
        if activity.getRetryCount() > activity.getRetryMax():
            desc = "Retry count exceeded (%d)" % activity.getRetryMax()
            self.__notificationFailed(activity, desc)
            return
        activity.store()
        dc = reactor.callLater(activity.getRetrySleep(),
                               self.__doPerformNotification,
                               activity)
        self._retries[activity] = dc
        
    def __notificationSucceed(self, activity):
        self.info("%s notification '%s' [%s] succeed", 
                  activity.getSubType().nick, activity.getLabel(), 
                  activity.getTrigger().nick)
        activity.setState(ActivityStateEnum.done)
        activity.store()
        self._results[activity].callback(activity)
        self.__notificationTerminated(activity)
        
    
    def __notificationFailed(self, activity, desc=None):
        message = ("%s notification '%s' [%s] failed: %s", 
                   activity.getSubType().nick, activity.getLabel(), 
                   activity.getTrigger().nick, desc)
        self.info("%s", message)
        activity.setState(ActivityStateEnum.failed)
        activity.store()
        self._results[activity].errback(Failure(NotificationError(message)))
        self.__notificationTerminated(activity)
        
    def __notificationTerminated(self, activity):
        self._retries.pop(activity)
        self._results.pop(activity)
        
    _prepareLookup = {NotificationTypeEnum.get_request: __doPrepareGetRequest,
                      NotificationTypeEnum.email: __doPrepareMailPost}
    
    _performLookup = {NotificationTypeEnum.get_request: __doPerformGetRequest,
                      NotificationTypeEnum.email: __doPerformMailPost}
    
    def __cannotPrepare(self, label, trigger, notif, vars, docs):
        self.warnAndRaise(NotificationError, "Unsuported type '%s' for "
                          "notification '%s'; cannot prepare", 
                          notif.getType().name, label)
    
    def __cannotPerform(self, activity):
        self.warnAndRaise(NotificationError, "Unsuported type '%s' for "
                          "notification '%s'; cannot perform", 
                          activity.getSubtype().name, activity.getLabel())
    
    def __prepareNotification(self, label, trigger, notif, vars, docs):
        type = notif.getType()
        prep = self._prepareLookup.get(type, self.__cannotPrepare)
        return prep(label, trigger, notif, vars, docs)
        
    def __performNotification(self, activity):
        self._retries[activity] = None
        type = activity.getSubtype()
        prep = self._performLookup.get(type, self.__cannotPerform)
        prep(activity)
        