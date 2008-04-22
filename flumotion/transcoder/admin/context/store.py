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

from flumotion.transcoder import constants
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.context import base, customer, state, notification


class StoreContext(base.BaseStoreContext, notification.NotificationStoreMixin):
    
    base.genStoreProxy("getOutputMediaTemplate",
                       adminconsts.DEFAULT_OUTPUT_MEDIA_TEMPLATE)
    base.genStoreProxy("getOutputThumbTemplate",
                       adminconsts.DEFAULT_OUTPUT_THUMB_TEMPLATE)
    base.genStoreProxy("getLinkFileTemplate",
                       adminconsts.DEFAULT_LINK_FILE_TEMPLATE)
    base.genStoreProxy("getConfigFileTemplate",
                       adminconsts.DEFAULT_CONFIG_FILE_TEMPLATE)
    base.genStoreProxy("getReportFileTemplate",
                       adminconsts.DEFAULT_REPORT_FILE_TEMPLATE)
    base.genStoreProxy("getLinkTemplate",
                       constants.LINK_TEMPLATE)
    base.genStoreProxy("getMonitoringPeriod",
                       adminconsts.DEFAULT_MONITORING_PERIOD)
    base.genStoreProxy("getAccessForceUser",
                       adminconsts.DEFAULT_ACCESS_FORCE_USER)
    base.genStoreProxy("getAccessForceGroup",
                       adminconsts.DEFAULT_ACCESS_FORCE_GROUP)
    base.genStoreProxy("getAccessForceDirMode",
                       adminconsts.DEFAULT_ACCESS_FORCE_DIR_MODE)
    base.genStoreProxy("getAccessForceFileMode",
                       adminconsts.DEFAULT_ACCESS_FORCE_FILE_MODE)
    base.genStoreProxy("getProcessPriority",
                       adminconsts.DEFAULT_PROCESS_PRIORITY)
    base.genStoreProxy("getTranscodingPriority",
                       adminconsts.DEFAULT_TRANSCODING_PRIORITY)
    base.genStoreProxy("getTranscodingTimeout",
                       adminconsts.DEFAULT_TRANSCODING_TIMEOUT)
    base.genStoreProxy("getPostprocessTimeout",
                       adminconsts.DEFAULT_POSTPROCESS_TIMEOUT)
    base.genStoreProxy("getPreprocessTimeout",
                       adminconsts.DEFAULT_PREPROCESS_TIMEOUT)
    base.genStoreProxy("getMailSubjectTemplate",
                       adminconsts.DEFAULT_MAIL_SUBJECT_TEMPLATE)
    base.genStoreProxy("getMailBodyTemplate",
                       adminconsts.DEFAULT_MAIL_BODY_TEMPLATE)
    base.genStoreProxy("getMailTimeout",
                       adminconsts.DEFAULT_MAIL_TIMEOUT)
    base.genStoreProxy("getMailRetryMax",
                       adminconsts.DEFAULT_MAIL_RETRY_MAX)
    base.genStoreProxy("getMailRetrySleep",
                       adminconsts.DEFAULT_MAIL_RETRY_SLEEP)
    base.genStoreProxy("getHTTPRequestTimeout",
                        adminconsts.DEFAULT_HTTPREQUEST_TIMEOUT)
    base.genStoreProxy("getHTTPRequestRetryMax",
                       adminconsts.DEFAULT_HTTPREQUEST_RETRY_MAX)
    base.genStoreProxy("getHTTPRequestRetrySleep",
                       adminconsts.DEFAULT_HTTPREQUEST_RETRY_SLEEP)

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
        
