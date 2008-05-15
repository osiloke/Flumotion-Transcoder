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

from flumotion.transcoder import constants
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.context import base, customer, state, notification


class IStoreContext(base.IBaseStoreContext):

    outputMediaTemplate   = Attribute("Output media file template")
    outputThumbTemplate   = Attribute("Output thumbnail file temaplte")
    linkFileTemplate      = Attribute("Link file template")
    configFileTemplate    = Attribute("Configuration file template")
    reportFileTemplate    = Attribute("Report file template")
    linkTemplate          = Attribute("Link template")
    monitoringPeriod      = Attribute("Monitoring period")
    accessForceUser       = Attribute("Force user of new files and directories")
    accessForceGroup      = Attribute("Force group of new files and directories")
    accessForceDirMode    = Attribute("Force rights of new directories")
    accessForceFileMode   = Attribute("Force rights of new files")
    processPriority       = Attribute("Transcoding process priority")
    transcodingPriority   = Attribute("Transcoding priority")
    transcodingTimeout    = Attribute("Transcoding timeout")
    postprocessTimeout    = Attribute("Post-processing timeout")
    preprocessTimeout     = Attribute("Pre-processing timeout")
    mailSubjectTemplate   = Attribute("Mail notifications subject template")
    mailBodyTemplate      = Attribute("Mail notifications body template")
    mailTimeout           = Attribute("Mail notifications timeout")
    mailRetryMax          = Attribute("Maximum mail notification attempts")
    mailRetrySleep        = Attribute("Time to wait between mail notification attempts")
    HTTPRequestTimeout    = Attribute("HTTP notifications timeout")
    HTTPRequestRetryMax   = Attribute("HTTP notifications maximum attempt count")
    HTTPRequestRetrySleep = Attribute("Time to wait between HTTP notification attempts")
    sqlTimeout            = Attribute("SQL notifications timeout")
    sqlRetryMax           = Attribute("Maximum SQL notification attempts")
    sqlRetrySleep         = Attribute("Time to wait between SQL notification attempts")

    def getCustomerContexts(self):
        pass

    def getCustomerContextFor(self, custStore):
        pass

    def getCustomerContext(self, identifier):
        pass
    
    def getCustomerContextByName(self, custName):
        pass
    
    def iterCustomerContexts(self):
        pass

    def getStateContext(self):
        pass


class StoreContext(base.BaseStoreContext, notification.NotifyStoreMixin):
    
    implements(IStoreContext)
    
    outputMediaTemplate   = base.StoreProxy("outputMediaTemplate",
                                            adminconsts.DEFAULT_OUTPUT_MEDIA_TEMPLATE)
    outputThumbTemplate   = base.StoreProxy("outputThumbTemplate",
                                            adminconsts.DEFAULT_OUTPUT_THUMB_TEMPLATE)
    linkFileTemplate      = base.StoreProxy("linkFileTemplate",
                                            adminconsts.DEFAULT_LINK_FILE_TEMPLATE)
    configFileTemplate    = base.StoreProxy("configFileTemplate",
                                            adminconsts.DEFAULT_CONFIG_FILE_TEMPLATE)
    reportFileTemplate    = base.StoreProxy("reportFileTemplate",
                                            adminconsts.DEFAULT_REPORT_FILE_TEMPLATE)
    linkTemplate          = base.StoreProxy("linkTemplate",
                                            constants.LINK_TEMPLATE)
    monitoringPeriod      = base.StoreProxy("monitoringPeriod",
                                            adminconsts.DEFAULT_MONITORING_PERIOD)
    accessForceUser       = base.StoreProxy("accessForceUser",
                                            adminconsts.DEFAULT_ACCESS_FORCE_USER)
    accessForceGroup      = base.StoreProxy("accessForceGroup",
                                            adminconsts.DEFAULT_ACCESS_FORCE_GROUP)
    accessForceDirMode    = base.StoreProxy("accessForceDirMode",
                                            adminconsts.DEFAULT_ACCESS_FORCE_DIR_MODE)
    accessForceFileMode   = base.StoreProxy("accessForceFileMode",
                                            adminconsts.DEFAULT_ACCESS_FORCE_FILE_MODE)
    processPriority       = base.StoreProxy("processPriority",
                                            adminconsts.DEFAULT_PROCESS_PRIORITY)
    transcodingPriority   = base.StoreProxy("transcodingPriority",
                                            adminconsts.DEFAULT_TRANSCODING_PRIORITY)
    transcodingTimeout    = base.StoreProxy("transcodingTimeout",
                                            adminconsts.DEFAULT_TRANSCODING_TIMEOUT)
    postprocessTimeout    = base.StoreProxy("postprocessTimeout",
                                            adminconsts.DEFAULT_POSTPROCESS_TIMEOUT)
    preprocessTimeout     = base.StoreProxy("preprocessTimeout",
                                            adminconsts.DEFAULT_PREPROCESS_TIMEOUT)
    mailSubjectTemplate   = base.StoreProxy("mailSubjectTemplate",
                                            adminconsts.DEFAULT_MAIL_SUBJECT_TEMPLATE)
    mailBodyTemplate      = base.StoreProxy("mailBodyTemplate",
                                            adminconsts.DEFAULT_MAIL_BODY_TEMPLATE)
    mailTimeout           = base.StoreProxy("mailTimeout",
                                            adminconsts.DEFAULT_MAIL_TIMEOUT)
    mailRetryMax          = base.StoreProxy("mailRetryMax",
                                            adminconsts.DEFAULT_MAIL_RETRY_MAX)
    mailRetrySleep        = base.StoreProxy("mailRetrySleep",
                                            adminconsts.DEFAULT_MAIL_RETRY_SLEEP)
    HTTPRequestTimeout    = base.StoreProxy("HTTPRequestTimeout",
                                            adminconsts.DEFAULT_HTTPREQUEST_TIMEOUT)
    HTTPRequestRetryMax   = base.StoreProxy("HTTPRequestRetryMax",
                                            adminconsts.DEFAULT_HTTPREQUEST_RETRY_MAX)
    HTTPRequestRetrySleep = base.StoreProxy("HTTPRequestRetrySleep",
                                            adminconsts.DEFAULT_HTTPREQUEST_RETRY_SLEEP)
    sqlTimeout            = base.StoreProxy("sqlTimeout",
                                            adminconsts.DEFAULT_SQL_TIMEOUT)
    sqlRetryMax           = base.StoreProxy("sqlRetryMax",
                                            adminconsts.DEFAULT_SQL_RETRY_MAX)
    sqlRetrySleep         = base.StoreProxy("sqlRetrySleep",
                                            adminconsts.DEFAULT_SQL_RETRY_SLEEP)

    def __init__(self, adminContext, adminStore):
        base.BaseStoreContext.__init__(self, adminContext, adminStore)

    def getAdminContext(self):
        return self.parent

    def getCustomerContexts(self):
        return [customer.CustomerContext(self, s)
                for s in self.store.getCustomerStores()] 
    
    def getCustomerContext(self, identifier):
        custStore = self.store.getCustomerStore(identifier)
        if custStore is None: return None
        return customer.CustomerContext(self, custStore)
    
    def getCustomerContextFor(self, custStore):
        assert custStore.parent == self.store
        return customer.CustomerContext(self, custStore)
    
    def getCustomerContextByName(self, custName):
        custStore = self.store.getCustomerStoreByName(custName)
        if custStore is None: return None
        return customer.CustomerContext(self, custStore)
    
    def iterCustomerContexts(self):
        iter = self.store.iterCustomerStores()
        return base.LazyContextIterator(self, customer.CustomerContext, iter)

    def getStateContext(self):
        stateStore = self.store.getStateStore()
        return state.StateContext(self, stateStore)
        
