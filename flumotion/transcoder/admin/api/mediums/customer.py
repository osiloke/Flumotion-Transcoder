# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import implements

from flumotion.transcoder.admin.datastore import customer
from flumotion.transcoder.admin.api import interfaces, api
from flumotion.transcoder.admin.api.mediums import named


class CustomerMedium(named.NamedMedium):
    implements(interfaces.ICustomerMedium)
    api.registerMedium(interfaces.ICustomerMedium,
                       customer.ICustomerStore)
#    api.proxy("getName",
#              "getSubdir",
#              "getInputDir",
#              "getOutputDir",
#              "getFailedDir",
#              "getDoneDir",
#              "getLinkDir",
#              "getWorkDir",
#              "getConfigDir",
#              "getTempRepDir",
#              "getFailedRepDir",
#              "getDoneRepDir",
#              "getCustomerPriority",
#              "getOutputMediaTemplate",
#              "getOutputThumbTemplate",
#              "getLinkFileTemplate",
#              "getConfigFileTemplate",
#              "getReportFileTemplate",
#              "getLinkTemplate",
#              "getLinkURLPrefix",
#              "getEnablePostprocessing",
#              "getEnablePreprocessing",
#              "getEnableLinkFiles",
#              "getTranscodingPriority",
#              "getProcessPriority",
#              "getPreprocessCommand",
#              "getPostprocessCommand",
#              "getPreprocessTimeout",
#              "getPostprocessTimeout",
#              "getTranscodingTimeout",
#              "getMonitoringPeriod",
#              "getAccessForceUser",
#              "getAccessForceGroup",
#              "getAccessForceDirMode",
#              "getAccessForceFileMode")
    
    def __init__(self, customer):
        named.NamedMedium.__init__(self, customer)
    
    
    ## ICustomerMedium Methodes ##

    @api.remote()
    def getProfiles(self):
        return self._reference.getProfileStores()
    
    @api.remote()
    def getProfile(self, identifier):
        return self._reference.getProfileStore(identifier)
