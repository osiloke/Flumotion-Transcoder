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

from flumotion.inhouse import log, defer, utils, events

from flumotion.transcoder.admin import adminconsts, admerrs
from flumotion.transcoder.admin.enums import ActivityTypeEnum
from flumotion.transcoder.admin.enums import ActivityStateEnum
from flumotion.transcoder.admin.enums import NotificationTypeEnum
from flumotion.transcoder.admin.enums import MailAddressTypeEnum
from flumotion.transcoder.admin.context import activity

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
                            filename=doc.label)
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


class Notifier(log.Loggable, events.EventSourceMixin):
    
    logCategory = adminconsts.NOTIFIER_LOG_CATEGORY
    
    def __init__(self, notifierContext, storeContext):
        self._notifierCtx = notifierContext 
        self._storeCtx = storeContext
        self._paused = True
        self._activities = [] # (NotificationActivityContext)
        self._retries = {} # {NotificationActivityContext: IDelayedCall}
        self._results = {} # {NotificationActivity: Deferred}
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
        stateCtx = self._storeCtx.getStateContext()
        d = stateCtx.retrieveNotificationContexts(states)
        d.addCallback(self.__cbRestoreNotifications)
        d.addErrback(self.__ebInitializationFailed)
        return d
    
    def start(self, timeout=None):
        for activCtx in self._activities:
            left = activCtx.getTimeLeftBeforeRetry()
            d = self.__startupNotification(activCtx, left)
            d.addErrback(defer.resolveFailure)
        del self._activities[:]
        return defer.succeed(self)
        
    def notify(self, label, trigger, notifCtx, variables, documents):
        self.info("%s notification '%s' for trigger '%s' initiated", 
                  notifCtx.getType().nick, label, trigger.nick)
        activCtx = self.__prepareNotification(label, trigger, notifCtx, 
                                              variables, documents)
        activCtx.store.store()
        return self.__startupNotification(activCtx)
    
    
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
    
    def __cbRestoreNotifications(self, activCtxs):
        self.debug("Restoring %d notification activities", len(activCtxs))
        for activCtx in activCtxs:
            self._activities.append(activCtx)
    
    def __ebInitializationFailed(self, failure):
        return failure    
    
    def __doPrepareGetRequest(self, label, trigger, notifCtx, vars, docs):
        stateCtx = self._storeCtx.getStateContext()
        activCtx = stateCtx.newNotificationContext(NotificationTypeEnum.http_request,
                                                   label, ActivityStateEnum.started,
                                                   notifCtx, trigger)
        url = vars.substituteURL(notifCtx.getRequestTemplate())
        activCtx.store.setRequestURL(url)
        return activCtx

    def __doPrepareMailPost(self, label, trigger, notifCtx, vars, docs):
        stateCtx = self._storeCtx.getStateContext()
        activCtx = stateCtx.newNotificationContext(NotificationTypeEnum.email,
                                                   label, ActivityStateEnum.started,
                                                   notifCtx, trigger)
        activStore = activCtx.store
        sender = self._notifierCtx.config.mailNotifySender
        senderAddr = utils.splitMailAddress(sender)[1]
        activStore.setSenderAddr(senderAddr)
        recipients = notifCtx.getRecipients()
        allRecipientsAddr = [f[1] for l in recipients.values() for f in l]
        activStore.setRecipientsAddr(allRecipientsAddr)
        subject = vars.substitute(notifCtx.getSubjectTemplate())
        activStore.setSubject(subject)
        
        toRecipientsFields = recipients.get(MailAddressTypeEnum.to, [])
        toRecipients = utils.joinMailRecipients(toRecipientsFields)
        ccRecipientsFields = recipients.get(MailAddressTypeEnum.cc, [])
        ccRecipients = utils.joinMailRecipients(ccRecipientsFields)
        
        body = vars.substitute(notifCtx.getBodyTemplate())
        
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = toRecipients
        msg['cc'] = ccRecipients
        txt = MIMEText(body)
        msg.attach(txt)
        
        attachments = notifCtx.getAttachments()
        if docs:
            for doc in docs:
                if doc.getType() in attachments:
                    mimeType = doc.getMimeType()
                    mainType, subType = mimeType.split('/', 1)
                    data = MIMEBase(mainType, subType)
                    data.set_payload(doc.asString())
                    email.Encoders.encode_base64(data)
                    data.add_header('Content-Disposition', 'attachment', 
                                    filename=doc.label)
                    msg.attach(data)
        activStore.setBody(str(msg))
        
        return activCtx

    def __startupNotification(self, activCtx, delay=0):
        global _shutingDown
        d = defer.Deferred()
        self._results[activCtx] = d
        self._retries[activCtx] = None
        if delay > 0:
            self.debug("Delaying notification '%s' for %d seconds",
                       activCtx.label, delay)
            reactor.callLater(delay, self.__performNotification, activCtx)
        else:
            self.__performNotification(activCtx)
        return d
    
    
    
    def __getRetriesLeftDesc(self, activCtx):
        left = activCtx.getRetryMax() - activCtx.getRetryCount()
        if left > 1: return "%d retries left" % left
        if left == 1: return "1 retry left"
        return "no retry left"
    
    def __doPerformGetRequest(self, activCtx):
        assert isinstance(activCtx, activity.HTTPActivityContext)
        self.debug("GET request '%s' initiated with URL %s" 
                   % (activCtx.label, activCtx.getRequestURL()))
        d = self._performGetRequest(activCtx.getRequestURL(), 
                                    timeout=activCtx.getTimeout())
        args = (activCtx,)
        d.addCallbacks(self.__cbGetPageSucceed, self.__ebGetPageFailed,
                       callbackArgs=args, errbackArgs=args)
        return d

    def __cbGetPageSucceed(self, page, activCtx):
        self.debug("GET request '%s' succeed", activCtx.label)
        self.log("GET request '%s' received page:\n%s",
                 activCtx.label, page)
        self.__notificationSucceed(activCtx)

    def __ebGetPageFailed(self, failure, activCtx):
        retryLeftDesc = self.__getRetriesLeftDesc(activCtx)
        self.debug("GET request '%s' failed (%s): %s",
                   activCtx.label, retryLeftDesc,
                   log.getFailureMessage(failure))
        self.__retryNotification(activCtx)

    def __doPerformMailPost(self, activCtx):
        assert isinstance(activCtx, activity.MailActivityContext)
        self.debug("Mail posting '%s' initiated for %s" 
                   % (activCtx.label, activCtx.getRecipientsAddr()))
        senderAddr = activCtx.getSenderAddr()
        recipientsAddr = activCtx.getRecipientsAddr()
        self.log("Posting mail from %s to %s",
                 senderAddr, ", ".join(recipientsAddr))
        d = self._postMail(self._notifierCtx.config.smtpServer,
                           self._notifierCtx.config.smtpPort,
                           self._notifierCtx.config.smtpUsername,
                           self._notifierCtx.config.smtpPassword,
                           senderAddr, recipientsAddr,
                           StringIO(activCtx.getBody()),
                           self._notifierCtx.config.smtpRequireTLS,
                           activCtx.getTimeout())
        args = (activCtx,)
        d.addCallbacks(self.__cbPostMailSucceed, self.__ebPostMailFailed,
                       callbackArgs=args, errbackArgs=args)
        return d

    def __cbPostMailSucceed(self, results, activCtx):
        self.debug("Mail post '%s' succeed", activCtx.label)
        self.log("Mail post '%s' responses; %s",
                 activCtx.label, ", ".join(["'%s': '%s'" % (m, r) 
                                                    for m, c, r in results[1]]))
        self.__notificationSucceed(activCtx)
    
    def __ebPostMailFailed(self, failure, activCtx):
        retryLeftDesc = self.__getRetriesLeftDesc(activCtx)
        self.debug("Mail post '%s' failed (%s): %s",
                   activCtx.label, retryLeftDesc,
                   log.getFailureMessage(failure))
        self.__retryNotification(activCtx)

    def __retryNotification(self, activCtx):
        activStore = activCtx.store
        activStore.incRetryCount()
        if activStore.getRetryCount() > activCtx.getRetryMax():
            desc = "Retry count exceeded %d" % activCtx.getRetryMax()
            self.__notificationFailed(activCtx, desc)
            return
        activStore.store()
        dc = reactor.callLater(activCtx.getRetrySleep(),
                               self.__performNotification,
                               activCtx)
        self._retries[activCtx] = dc
        
    def __notificationSucceed(self, activCtx):
        self.info("%s notification '%s' for trigger '%s' succeed", 
                  activCtx.getSubtype().nick, activCtx.label, 
                  activCtx.getTrigger().nick)
        activStore = activCtx.store
        activStore.setState(ActivityStateEnum.done)
        activStore.store()
        self._results[activCtx].callback(activCtx)
        self.__notificationTerminated(activCtx)
        
    
    def __notificationFailed(self, activCtx, desc=None):
        message = ("%s notification '%s' for trigger '%s' failed: %s"
                   % (activCtx.getSubtype().nick,
                      activCtx.label, 
                      activCtx.getTrigger().nick, desc))
        self.info("%s", message)
        activStore = activCtx.store
        activStore.setState(ActivityStateEnum.failed)
        activStore.store()
        self._results[activCtx].errback(Failure(admerrs.NotificationError(message)))
        self.__notificationTerminated(activCtx)
        
    def __notificationTerminated(self, activCtx):
        self._retries.pop(activCtx)
        self._results.pop(activCtx)
        
    _prepareLookup = {NotificationTypeEnum.http_request: __doPrepareGetRequest,
                      NotificationTypeEnum.email: __doPrepareMailPost}
    
    _performLookup = {NotificationTypeEnum.http_request: __doPerformGetRequest,
                      NotificationTypeEnum.email: __doPerformMailPost}
    
    def __cannotPrepare(self, label, trigger, notif, vars, docs):
        message = ("Unsuported type '%s' for "
                   "notification '%s'; cannot prepare"
                   % (notif.getType().name, label))
        self.warning("%s", message)
        raise admerrs.NotificationError(message)
    
    def __cannotPerform(self, activCtx):
        message = ("Unsuported type '%s' for "
                   "notification '%s'; cannot perform"
                   % (activCtx.getSubtype().name, activCtx.label))
        self.warning("%s", message)
        raise admerrs.NotificationError(message)
    
    def __prepareNotification(self, label, trigger, notifCtx, vars, docs):
        type = notifCtx.getType()
        prepare = self._prepareLookup.get(type, self.__cannotPrepare)
        return prepare(self, label, trigger, notifCtx, vars, docs)
        
    def __performNotification(self, activCtx):
        if _shutingDown: return
        self._retries[activCtx] = None
        type = activCtx.getSubtype()
        perform = self._performLookup.get(type, self.__cannotPerform)
        perform(self, activCtx)
        
