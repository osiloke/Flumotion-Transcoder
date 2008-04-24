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

from flumotion.transcoder import constants
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.context import base, customer, state, notification


class IStoreContext(base.IBaseStoreContext):

    def getCustomerContextFor(self, custStore):
        pass
    
    def getCustomerContextByName(self, custName):
        pass
    
    def iterCustomerContexts(self):
        pass

    def getStateContext(self):
        pass

    def getOutputMediaTemplate(self):
        pass
    
    def getOutputThumbTemplate(self):
        pass
    
    def getLinkFileTemplate(self):
        pass
    
    def getConfigFileTemplate(self):
        pass
    
    def getReportFileTemplate(self):
        pass
    
    def getLinkTemplate(self):
        pass
    
    def getMonitoringPeriod(self):
        pass
    
    def getAccessForceUser(self):
        pass
    
    def getAccessForceGroup(self):
        pass
    
    def getAccessForceDirMode(self):
        pass
    
    def getAccessForceFileMode(self):
        pass
    
    def getProcessPriority(self):
        pass
    
    def getTranscodingPriority(self):
        pass
    
    def getTranscodingTimeout(self):
        pass
    
    def getPostprocessTimeout(self):
        pass
    
    def getPreprocessTimeout(self):
        pass
    
    def getMailSubjectTemplate(self):
        pass
    
    def getMailBodyTemplate(self):
        pass
    
    def getMailTimeout(self):
        pass
    
    def getMailRetryMax(self):
        pass
    
    def getMailRetrySleep(self):
        pass
    
    def getHTTPRequestTimeout(self):
        pass
    
    def getHTTPRequestRetryMax(self):
        pass
    
    def getHTTPRequestRetrySleep(self):
        pass


class StoreContext(base.BaseStoreContext, notification.NotifyStoreMixin):
    
    implements(IStoreContext)
    
    base.store_proxy("outputMediaTemplate",
                     default=adminconsts.DEFAULT_OUTPUT_MEDIA_TEMPLATE)
    base.store_proxy("outputThumbTemplate",
                     default=adminconsts.DEFAULT_OUTPUT_THUMB_TEMPLATE)
    base.store_proxy("linkFileTemplate",
                     default=adminconsts.DEFAULT_LINK_FILE_TEMPLATE)
    base.store_proxy("configFileTemplate",
                     default=adminconsts.DEFAULT_CONFIG_FILE_TEMPLATE)
    base.store_proxy("reportFileTemplate",
                     default=adminconsts.DEFAULT_REPORT_FILE_TEMPLATE)
    base.store_proxy("linkTemplate",
                     default=constants.LINK_TEMPLATE)
    base.store_proxy("monitoringPeriod",
                     default=adminconsts.DEFAULT_MONITORING_PERIOD)
    base.store_proxy("accessForceUser",
                     default=adminconsts.DEFAULT_ACCESS_FORCE_USER)
    base.store_proxy("accessForceGroup",
                     default=adminconsts.DEFAULT_ACCESS_FORCE_GROUP)
    base.store_proxy("accessForceDirMode",
                     default=adminconsts.DEFAULT_ACCESS_FORCE_DIR_MODE)
    base.store_proxy("accessForceFileMode",
                     default=adminconsts.DEFAULT_ACCESS_FORCE_FILE_MODE)
    base.store_proxy("processPriority",
                     default=adminconsts.DEFAULT_PROCESS_PRIORITY)
    base.store_proxy("transcodingPriority",
                     default=adminconsts.DEFAULT_TRANSCODING_PRIORITY)
    base.store_proxy("transcodingTimeout",
                     default=adminconsts.DEFAULT_TRANSCODING_TIMEOUT)
    base.store_proxy("postprocessTimeout",
                     default=adminconsts.DEFAULT_POSTPROCESS_TIMEOUT)
    base.store_proxy("preprocessTimeout",
                     default=adminconsts.DEFAULT_PREPROCESS_TIMEOUT)
    base.store_proxy("mailSubjectTemplate",
                     default=adminconsts.DEFAULT_MAIL_SUBJECT_TEMPLATE)
    base.store_proxy("mailBodyTemplate",
                     default=adminconsts.DEFAULT_MAIL_BODY_TEMPLATE)
    base.store_proxy("mailTimeout",
                     default=adminconsts.DEFAULT_MAIL_TIMEOUT)
    base.store_proxy("mailRetryMax",
                     default=adminconsts.DEFAULT_MAIL_RETRY_MAX)
    base.store_proxy("mailRetrySleep",
                     default=adminconsts.DEFAULT_MAIL_RETRY_SLEEP)
    base.store_proxy("HTTPRequestTimeout",
                     default=adminconsts.DEFAULT_HTTPREQUEST_TIMEOUT)
    base.store_proxy("HTTPRequestRetryMax",
                     default=adminconsts.DEFAULT_HTTPREQUEST_RETRY_MAX)
    base.store_proxy("HTTPRequestRetrySleep",
                     default=adminconsts.DEFAULT_HTTPREQUEST_RETRY_SLEEP)


    def __init__(self, adminContext, adminStore):
        base.BaseStoreContext.__init__(self, adminContext, adminStore)

    def getAdminContext(self):
        return self.parent

    def getCustomerContextFor(self, custStore):
        assert custStore.parent == self.store
        return customer.CustomerContext(self, custStore)
    
    def getCustomerContextByName(self, custName):
        custStore = self.store.getCustomerStoreByName(custName)
        return customer.CustomerContext(self, custStore)
    
    def iterCustomerContexts(self):
        iter = self.store.iterCustomerStores()
        return base.LazyContextIterator(self, customer.CustomerContext, iter)

    def getStateContext(self):
        stateStore = self.store.getStateStore()
        return state.StateContext(self, stateStore)
        
