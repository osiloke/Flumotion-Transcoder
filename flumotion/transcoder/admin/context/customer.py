# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.inhouse import fileutils, annotate

from flumotion.transcoder import constants, virtualpath
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.context import base, profile, notification

#TODO: Do some value caching


class CustomerContext(base.BaseStoreContext, notification.NotificationStoreMixin):
    """
    The customer context define the default base directories.
    They are directly taken and expanded from the store get...Dir getter,
    or deduced from constants and customer name/subdir values.
    The return values are virtualpath.VirtualPath instances that abstract
    local filesystems root points.
    
        Ex: customer data => store.get...Dir()=None
                             name="Fluendo"
                             subdir=None
                getInputBase: default:/fluendo/files/incoming/
                getoutputBase: default:/fluendo/files/outgoing/
                getFailedBase: default:/fluendo/files/failed/
                getDoneBase: default:/fluendo/files/done/
                getLinkBase: default:/fluendo/files/links/
                getWorkBase: temp:/fluendo/working/
                getConfBase: default:/fluendo/configs/
                getTempRepBase: default:/fluendo/reports/pending/
                getFailedRepBase: default:/fluendo/reports/failed/
                getDoneRepBase: default:/fluendo/reports/done/
    
        Ex: customer data => store.get...Dir()=None
                             name="Big/Comp (1)"
                             subdir=None
                getInputBase: default:/big_comp_(1)/files/incoming/
                getoutputBase: default:/big_comp_(1)/files/outgoing/
                getWorkBase: temp:/big_comp_(1)/working/
                ...
    
        Ex: customer data => store.get...Dir()=None
                             name="RTVE"
                             subdir="rtve/l2n"
                getInputBase: default:/rtve/l2n/files/incoming/
                getoutputBase: default:/rtve/l2n/files/outgoing/
                getWorkBase: temp:/rtve/l2n/working/
                ...
    """
    
    base.genStoreProxy("getName")
    base.genStoreProxy("getCustomerPriority",
                       adminconsts.DEFAULT_CUSTOMER_PRIORITY)
    base.genStoreProxy("getPreprocessCommand")
    base.genStoreProxy("getPostprocessCommand")
    base.genStoreProxy("getEnablePostprocessing")
    base.genStoreProxy("getEnablePreprocessing")
    base.genStoreProxy("getEnableLinkFiles")
    base.genParentOverridingStoreProxy("getOutputMediaTemplate")
    base.genParentOverridingStoreProxy("getOutputThumbTemplate")
    base.genParentOverridingStoreProxy("getLinkFileTemplate")
    base.genParentOverridingStoreProxy("getConfigFileTemplate")
    base.genParentOverridingStoreProxy("getReportFileTemplate")
    base.genParentOverridingStoreProxy("getLinkTemplate")
    base.genParentOverridingStoreProxy("getLinkURLPrefix")
    base.genParentOverridingStoreProxy("getTranscodingPriority")
    base.genParentOverridingStoreProxy("getProcessPriority")
    base.genParentOverridingStoreProxy("getPreprocessTimeout")
    base.genParentOverridingStoreProxy("getPostprocessTimeout")
    base.genParentOverridingStoreProxy("getTranscodingTimeout")
    base.genParentOverridingStoreProxy("getMonitoringPeriod")
    base.genParentOverridingStoreProxy("getAccessForceUser")
    base.genParentOverridingStoreProxy("getAccessForceGroup")
    base.genParentOverridingStoreProxy("getAccessForceDirMode")
    base.genParentOverridingStoreProxy("getAccessForceFileMode")
    
    def __init__(self, storeCtx, custStore):
        base.BaseStoreContext.__init__(self, storeCtx, custStore)
        self._variables.addVar("customerName", self.getName())

    def getAdminContext(self):
        return self.parent.getAdminContext()
    
    def getStoreContext(self):
        return self.parent

    def getUnboundProfileContextByName(self, profName):
        profStore = self.store.getProfileStoreByName(profName)
        return profile.UnboundProfileContext(self, profStore)
    
    def getUnboundProfileContextFor(self, profStore):
        assert profStore.parent == self.store
        return profile.UnboundProfileContext(self, profStore)
    
    def iterUnboundProfileContexts(self):
        profIter = self.store.iterProfileStores()
        return base.LazyContextIterator(self, profile.UnboundProfileContext, profIter)
        
    def getProfileContextByName(self, profName, input):
        profStore = self.store.getProfileStoreByName(profName)
        return profile.ProfileContext(self, profStore, input)
    
    def getProfileContextFor(self, profStore, input):
        assert profStore.parent == self.store
        return profile.ProfileContext(self, profStore, input)

    def iterProfileContexts(self, input):
        profIter = self.store.iterProfileStores()
        return base.LazyContextIterator(self, profile.ProfileContext, profIter, input)
        
    def getPathAttributes(self):
        forceUser = self.getAccessForceUser()
        forceGroup = self.getAccessForceGroup()
        forceDirMode = self.getAccessForceDirMode()
        forceFileMode = self.getAccessForceFileMode()
        return fileutils.PathAttributes(forceUser, forceGroup,
                                        forceDirMode, forceFileMode)
    
    def getSubdir(self):
        subdir = self.store.getSubdir()
        if subdir != None:
            subdir = fileutils.str2path(subdir)
            subdir = fileutils.ensureRelDirPath(subdir)
            return fileutils.cleanupPath(subdir)
        subdir = fileutils.str2filename(self.store.getName())
        return fileutils.ensureDirPath(subdir)
        
    def _expandDir(self, folder):
        #FIXME: Do variable substitution here.
        return folder
        
    def _getDir(self, rootName, folder, template):
        if folder != None:
            folder = self._expandDir(folder)
            folder = fileutils.ensureAbsDirPath(folder)
            folder = fileutils.cleanupPath(folder)
            return virtualpath.VirtualPath(folder, rootName)
        subdir = self.getSubdir()
        folder = fileutils.ensureAbsDirPath(template % subdir)
        folder = fileutils.cleanupPath(folder)
        return virtualpath.VirtualPath(folder, rootName)
        
    def getInputBase(self):
        folder = self.store.getInputDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                            adminconsts.DEFAULT_INPUT_DIR)

    def getOutputBase(self):
        folder = self.store.getOutputDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                            adminconsts.DEFAULT_OUTPUT_DIR)
    
    def getFailedBase(self):
        folder = self.store.getFailedDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                            adminconsts.DEFAULT_FAILED_DIR)
    
    def getDoneBase(self):
        folder = self.store.getDoneDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                            adminconsts.DEFAULT_DONE_DIR)
    
    def getLinkBase(self):
        folder = self.store.getLinkDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                            adminconsts.DEFAULT_LINK_DIR)
    
    def getWorkBase(self):
        folder = self.store.getWorkDir()
        return self._getDir(constants.TEMP_ROOT, folder, 
                            adminconsts.DEFAULT_WORK_DIR)
    
    def getConfigBase(self):
        folder = self.store.getConfigDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                            adminconsts.DEFAULT_CONFIG_DIR)
    
    def getTempRepBase(self):
        folder = self.store.getTempRepDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                            adminconsts.DEFAULT_TEMPREP_DIR)

    def getFailedRepBase(self):
        folder = self.store.getFailedRepDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                            adminconsts.DEFAULT_FAILEDREP_DIR)
    
    def getDoneRepBase(self):
        folder = self.store.getDoneRepDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                            adminconsts.DEFAULT_DONEREP_DIR)

    def getMonitorLabel(self):
        template = self.getAdminContext().config.monitorLabelTemplate
        return self._variables.substitute(template)
    
