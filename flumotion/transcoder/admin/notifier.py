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
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from cStringIO import StringIO

from zope.interface import Interface, implements
from twisted.python.failure import Failure
from twisted.internet import reactor
from twisted.web import client
from twisted.mail.smtp import ESMTPSenderFactory

from flumotion.inhouse import log, defer, utils

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

## Global info for emergency and debug notification ##
# Should have working default values in case 
# an emergency mail should be send before
# the configuration is loaded and setup

_smtpServer = "mail.fluendo.com"
_smtpPort = 25
_smtpRequireTLS = False
_emergencySender = "Transcoder Emergency <transcoder-emergency@fluendo.com>"
_debugSender = "Transcoder Debug <transcoder-debug@fluendo.com>"
_emergencyRecipients = "sebastien@fluendo.com"
_debugRecipients = "sebastien@fluendo.com"
_shutingDown = False


## Disable notifications when shuting down
def _disableNotification():
    global _shutingDown
    _shutingDown = True
    log.info("Disabling notifications during shutdown",
             category=adminconsts.NOTIFIER_LOG_CATEGORY)
    
reactor.addSystemEventTrigger("before", "shutdown", _disableNotification)

## Notification Function ###

def _buildBody(sender, recipients, subject, msg, info=None, debug=None,
               failure=None, exception=None, documents=None):
    body = [msg]
    if info:
        body.append("Information:\n\n%s" % info)
    if debug:
        body.append("Additional Debug Info:\n\n%s" % debug)
    if exception:
        body.append("Exception Message: %s\n\nException Traceback:\n\n%s"
                    % (log.getExceptionMessage(exception),
                       log.getExceptionTraceback(exception)))
    if failure:
        body.append("Failure Message: %s\n\nFailure Traceback:\n%s"
                    % (log.getFailureMessage(failure),
                       log.getFailureTraceback(failure)))
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipients
    txt = MIMEText("\n\n\n".join(body))
    msg.attach(txt)
    if documents:
        for doc in documents:
            mimeType = doc.getMimeType()
            mainType, subType = mimeType.split('/', 1)
            data = MIMEBase(mainType, subType)
            data.set_payload(doc.asString())
            email.Encoders.encode_base64(data)
            data.add_header('Content-Disposition', 'attachment', 
                            filename=doc.getLabel())
            msg.attach(data)
    return str(msg)

def _postNotification(smtpServer, smtpPort, requireTLS, sender, recipients, body):
    senderAddr = utils.splitMailAddress(sender)[1]
    recipientsAddr = [f[1] for f in utils.splitMailRecipients(recipients)]
    return Notifier._postMail(smtpServer, smtpPort, None, None, senderAddr,
                              recipientsAddr, StringIO(body),
                              requireTLS=requireTLS,
                              timeout=adminconsts.GLOBAL_MAIL_NOTIFY_TIMEOUT,
                              retries=adminconsts.GLOBAL_MAIL_NOTIFY_RETRIES)

def _cbNotificationDone(result, kind):
    log.info("%s notification sent", kind,
             category=adminconsts.NOTIFIER_LOG_CATEGORY)

def _ebNotificationFailed(failure, kind):
    log.warning("%s notification failed: %s", kind,
                log.getFailureMessage(failure),
                category=adminconsts.NOTIFIER_LOG_CATEGORY)

def notifyEmergency(msg, info=None, debug=None, failure=None,
                    exception=None, documents=None):
    """
    This function can be used from anywere to notify
    emergency situations when no Notifier reference
    is available.
    Do not raise any exception.
    """
    global _shutingDown
    if _shutingDown: return
    try:
        sender = _emergencySender
        recipients = _emergencyRecipients
        log.info("Try sending an emergency notification to %s", recipients,
                 category=adminconsts.NOTIFIER_LOG_CATEGORY)
        body = _buildBody(sender, recipients, msg, msg, info, debug,
                          failure, exception, documents)
        d = _postNotification(_smtpServer, _smtpPort, _smtpRequireTLS, 
                              sender, recipients, body)
        args = ("Emergency",)
        d.addCallbacks(_cbNotificationDone, _ebNotificationFailed,
                       callbackArgs=args, errbackArgs=args)
    except Exception, e:
        log.warning("Emergency Notification Failed: %s",
                    log.getExceptionMessage(e),
                    category=adminconsts.NOTIFIER_LOG_CATEGORY)

def notifyDebug(msg, info=None, debug=None, failure=None,
                exception=None, documents=None):
    """
    This function can be used from anywere to notify
    debug information (like traceback) when no 
    Notifier reference is available.
    Do not raise any exception.
    """
    global _shutingDown
    if _shutingDown: return
    try:
        sender = _debugSender
        recipients = _debugRecipients
        log.info("Try sending a debug notification to %s from %s", 
                 recipients, sender,
                 category=adminconsts.NOTIFIER_LOG_CATEGORY)
        body = _buildBody(sender, recipients, msg, msg, info, debug,
                          failure, exception, documents)
        d = _postNotification(_smtpServer, _smtpPort, _smtpRequireTLS,
                              sender, recipients, body)
        args = ("Debug",)
        d.addCallbacks(_cbNotificationDone, _ebNotificationFailed,
                       callbackArgs=args, errbackArgs=args)
    except Exception, e:
        log.warning("Debug Notification Failed: %s",
                    log.getExceptionMessage(e),
                    category=adminconsts.NOTIFIER_LOG_CATEGORY)


class Notifier(log.Loggable, EventSource):
    
    logCategory = adminconsts.NOTIFIER_LOG_CATEGORY
    
    def __init__(self, notifierContext, activityStore):
        EventSource.__init__(self)
        self._activities = activityStore
        self._context = notifierContext
        self._paused = True
        self._awaitingActivities = []
        self._retries = {} # {BaseNotifyActivity: IDelayedCall}
        self._results = {} # {BaseNotifyActivity: Deferred}
        # Setup global notification info
        global _smtpServer, _smtpRequireTLS
        global _emergencySender, _debugSender
        global _emergencyRecipients, _debugRecipients
        _smtpServer = notifierContext.config.smtpServer
        _smtpRequireTLS = notifierContext.config.smtpRequireTLS
        _emergencySender = notifierContext.config.mailEmergencySender
        _debugSender = notifierContext.config.mailDebugSender
        _emergencyRecipients = notifierContext.config.mailEmergencyRecipients
        _debugRecipients = notifierContext.config.mailDebugRecipients

    ## Public Methods ##
    
    def initialize(self):
        self.debug("Retrieve notification activities")
        states = [ActivityStateEnum.started]
        d = self._activities.getNotifications(states)
        d.addCallback(self.__cbRestoreNotifications)
        d.addErrback(self.__ebInitializationFailed)
        return d
    
    def start(self, timeout=None):
        for activity in self._awaitingActivities:
            left = activity.getTimeLeftBeforeRetry()
            d = self.__startupNotification(activity, left)
            d.addErrback(defer.resolveFailure)
        del self._awaitingActivities[:]
        return defer.succeed(self)
        
    def notify(self, label, trigger, notification, variables, documents):
        self.info("%s notification '%s' for trigger '%s' initiated", 
                  notification.getType().nick, label, trigger.nick)
        activity = self.__prepareNotification(label, trigger, notification, 
                                              variables, documents)
        activity.store()
        return self.__startupNotification(activity)
    
    
    ## Protected Static Methods ##

    @staticmethod
    def _postMail(smtpServer, smtpPort, smtpUsername, smtpPassword, 
                  senderAddr, recipientsAddr, bodyFile, 
                  requireTLS=True, timeout=None, retries=0):
        d = defer.Deferred()
        authenticate = (smtpUsername != None) and (smtpUsername != "")
        factory = ESMTPSenderFactory(username=smtpUsername,
                                     password=smtpPassword,
                                     requireAuthentication=authenticate,
                                     requireTransportSecurity=requireTLS,
                                     fromEmail=senderAddr, 
                                     toEmail=recipientsAddr,
                                     file=bodyFile, 
                                     deferred=d,
                                     retries=retries,
                                     timeout=timeout)
        reactor.connectTCP(smtpServer, smtpPort, factory)
        return d

    @staticmethod
    def _performGetRequest(url, timeout=None):
        return client.getPage(url, timeout=timeout,
                              agent=adminconsts.GET_REQUEST_AGENT)
    
    ## Private Methods ##
    
    def __cbRestoreNotifications(self, activities):
        self.debug("Restoring %d notification activities", len(activities))
        for activity in activities:
            self._awaitingActivities.append(activity)
    
    def __ebInitializationFailed(self, failure):
        return failure    
    
    def __doPrepareGetRequest(self, label, trigger, notif, vars, docs):
        store = self._activities
        activity = store.newNotification(NotificationTypeEnum.get_request,
                                         label, ActivityStateEnum.started,
                                         notif, trigger)
        url = vars.substituteURL(notif.getRequestTemplate())
        activity.setRequestURL(url)
        return activity

    def __doPrepareMailPost(self, label, trigger, notif, vars, docs):
        store = self._activities
        activity = store.newNotification(NotificationTypeEnum.email,
                                         label, ActivityStateEnum.started,
                                         notif, trigger)
        sender = self._context.config.mailNotifySender
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
        
        body = vars.substitute(notif.getBodyTemplate())
        
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = toRecipients
        msg['cc'] = ccRecipients
        txt = MIMEText(body)
        msg.attach(txt)
        
        attachments = notif.getAttachments()
        if docs:
            for doc in docs:
                if doc.getType() in attachments:
                    mimeType = doc.getMimeType()
                    mainType, subType = mimeType.split('/', 1)
                    data = MIMEBase(mainType, subType)
                    data.set_payload(doc.asString())
                    email.Encoders.encode_base64(data)
                    data.add_header('Content-Disposition', 'attachment', 
                                    filename=doc.getLabel())
                    msg.attach(data)
        activity.setBody(str(msg))
        
        return activity

    def __startupNotification(self, activity, delay=0):
        global _shutingDown
        d = defer.Deferred()
        self._results[activity] = d
        self._retries[activity] = None
        if delay > 0:
            self.debug("Delaying notification '%s' for %d seconds",
                       activity.getLabel(), delay)
            reactor.callLater(delay, self.__performNotification, activity)
        else:
            self.__performNotification(activity)
        return d
    
    
    
    def __getRetriesLeftDesc(self, activity):
        left = activity.getRetryMax() - activity.getRetryCount()
        if left > 1: return "%d retries left" % left
        if left == 1: return "1 retry left"
        return "no retry left"
    
    def __doPerformGetRequest(self, activity):
        assert isinstance(activity, GETRequestNotifyActivity)
        self.debug("GET request '%s' initiated with URL %s" 
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
        retryLeftDesc = self.__getRetriesLeftDesc(activity)
        self.debug("GET request '%s' failed (%s): %s",
                   activity.getLabel(), retryLeftDesc,
                   log.getFailureMessage(failure))
        self.__retryNotification(activity)

    def __doPerformMailPost(self, activity):
        assert isinstance(activity, MailNotifyActivity)
        self.debug("Mail posting '%s' initiated for %s" 
                   % (activity.getLabel(), activity.getRecipientsAddr()))
        senderAddr = activity.getSenderAddr()
        recipientsAddr = activity.getRecipientsAddr()
        self.log("Posting mail from %s to %s",
                 senderAddr, ", ".join(recipientsAddr))
        d = self._postMail(self._context.config.smtpServer,
                           self._context.config.smtpPort,
                           self._context.config.smtpUsername,
                           self._context.config.smtpPassword,
                           senderAddr, recipientsAddr,
                           StringIO(activity.getBody()),
                           self._context.config.smtpRequireTLS,
                           activity.getTimeout())
        args = (activity,)
        d.addCallbacks(self.__cbPostMailSucceed, self.__ebPostMailFailed,
                       callbackArgs=args, errbackArgs=args)
        return d

    def __cbPostMailSucceed(self, results, activity):
        self.debug("Mail post '%s' succeed", activity.getLabel())
        self.log("Mail post '%s' responses; %s",
                 activity.getLabel(), ", ".join(["'%s': '%s'" % (m, r) 
                                                for m, c, r in results[1]]))
        self.__notificationSucceed(activity)
    
    def __ebPostMailFailed(self, failure, activity):
        retryLeftDesc = self.__getRetriesLeftDesc(activity)
        self.debug("Mail post '%s' failed (%s): %s",
                   activity.getLabel(), retryLeftDesc,
                   log.getFailureMessage(failure))
        self.__retryNotification(activity)

    def __retryNotification(self, activity):
        activity.incRetryCount()
        if activity.getRetryCount() > activity.getRetryMax():
            desc = "Retry count exceeded %d" % activity.getRetryMax()
            self.__notificationFailed(activity, desc)
            return
        activity.store()
        dc = reactor.callLater(activity.getRetrySleep(),
                               self.__performNotification,
                               activity)
        self._retries[activity] = dc
        
    def __notificationSucceed(self, activity):
        self.info("%s notification '%s' for trigger '%s' succeed", 
                  activity.getSubType().nick, activity.getLabel(), 
                  activity.getTrigger().nick)
        activity.setState(ActivityStateEnum.done)
        activity.store()
        self._results[activity].callback(activity)
        self.__notificationTerminated(activity)
        
    
    def __notificationFailed(self, activity, desc=None):
        message = ("%s notification '%s' for trigger '%s' failed: %s"
                   % (activity.getSubType().nick,
                      activity.getLabel(), 
                      activity.getTrigger().nick, desc))
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
        message = ("Unsuported type '%s' for "
                   "notification '%s'; cannot prepare"
                   % (notif.getType().name, label))
        self.warning("%s", message)
        raise NotificationError(message)
    
    def __cannotPerform(self, activity):
        message = ("Unsuported type '%s' for "
                   "notification '%s'; cannot perform"
                   % (activity.getSubType().name, activity.getLabel()))
        self.warning("%s", message)
        raise NotificationError(message)
    
    def __prepareNotification(self, label, trigger, notif, vars, docs):
        type = notif.getType()
        prep = self._prepareLookup.get(type, self.__cannotPrepare)
        return prep(self, label, trigger, notif, vars, docs)
        
    def __performNotification(self, activity):
        if _shutingDown: return
        self._retries[activity] = None
        type = activity.getSubType()
        prep = self._performLookup.get(type, self.__cannotPerform)
        prep(self, activity)
        
