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

from flumotion.inhouse import fileutils, annotate

from flumotion.transcoder import constants, virtualpath
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.context import base, profile, notification

#TODO: Do some value caching

class ICustomerContext(base.IBaseStoreContext):

    def getStoreContext(self):
        pass

    def getUnboundProfileContextByName(self, profName):
        pass
    
    def getUnboundProfileContextFor(self, profStore):
        pass
    
    def iterUnboundProfileContexts(self):
        pass
        
    def getProfileContextByName(self, profName, input):
        pass
    
    def getProfileContextFor(self, profStore, input):
        pass

    def iterProfileContexts(self, input):
        pass
        
    def getPathAttributes(self):
        pass
    
    def getMonitorLabel(self):
        pass
    
    def getName(self):
        pass
    
    def getCustomerPriority(self):
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
    
    def getLinkURLPrefix(self):
        pass
    
    def getEnablePostprocessing(self):
        pass
    
    def getEnablePreprocessing(self):
        pass
    
    def getEnableLinkFiles(self):
        pass
    
    def getTranscodingPriority(self):
        pass
    
    def getProcessPriority(self):
        pass
    
    def getPreprocessCommand(self):
        pass
    
    def getPostprocessCommand(self):
        pass
    
    def getPreprocessTimeout(self):
        pass
    
    def getPostprocessTimeout(self):
        pass
    
    def getTranscodingTimeout(self):
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

    def getInputBase(self):
        pass

    def getOutputBase(self):
        pass
    
    def getFailedBase(self):
        pass
    
    def getDoneBase(self):
        pass
    
    def getLinkBase(self):
        pass
    
    def getWorkBase(self):
        pass
    
    def getConfigBase(self):
        pass
    
    def getTempRepBase(self):
        pass

    def getFailedRepBase(self):
        pass
    
    def getDoneRepBase(self):
        pass


class CustomerContext(base.BaseStoreContext, notification.NotifyStoreMixin):
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
    
    implements(ICustomerContext)
    
    base.store_proxy("name")
    base.store_proxy("customerPriority",
                     default=adminconsts.DEFAULT_CUSTOMER_PRIORITY)
    base.store_proxy("preprocessCommand")
    base.store_proxy("postprocessCommand")
    base.store_proxy("enablePostprocessing")
    base.store_proxy("enablePreprocessing")
    base.store_proxy("enableLinkFiles")
    base.store_parent_proxy("outputMediaTemplate")
    base.store_parent_proxy("outputThumbTemplate")
    base.store_parent_proxy("linkFileTemplate")
    base.store_parent_proxy("configFileTemplate")
    base.store_parent_proxy("reportFileTemplate")
    base.store_parent_proxy("linkTemplate")
    base.store_parent_proxy("linkURLPrefix")
    base.store_parent_proxy("transcodingPriority")
    base.store_parent_proxy("processPriority")
    base.store_parent_proxy("preprocessTimeout")
    base.store_parent_proxy("postprocessTimeout")
    base.store_parent_proxy("transcodingTimeout")
    base.store_parent_proxy("monitoringPeriod")
    base.store_parent_proxy("accessForceUser")
    base.store_parent_proxy("accessForceGroup")
    base.store_parent_proxy("accessForceDirMode")
    base.store_parent_proxy("accessForceFileMode")
    
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
    
    @base.property_getter("pathAttributes")
    def getPathAttributes(self):
        forceUser = self.getAccessForceUser()
        forceGroup = self.getAccessForceGroup()
        forceDirMode = self.getAccessForceDirMode()
        forceFileMode = self.getAccessForceFileMode()
        return fileutils.PathAttributes(forceUser, forceGroup,
                                        forceDirMode, forceFileMode)

    @base.property_getter("monitorLabel")
    def getMonitorLabel(self):
        template = self.getAdminContext().config.monitorLabelTemplate
        return self._variables.substitute(template)
    
    @base.property_getter("subdir")
    def getSubdir(self):
        subdir = self.store.getSubdir()
        if subdir != None:
            subdir = fileutils.str2path(subdir)
            subdir = fileutils.ensureRelDirPath(subdir)
            return fileutils.cleanupPath(subdir)
        subdir = fileutils.str2filename(self.store.getName())
        return fileutils.ensureDirPath(subdir)
            
    @base.property_getter("inputBase")
    def getInputBase(self):
        folder = self.store.getInputDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                             adminconsts.DEFAULT_INPUT_DIR)

    @base.property_getter("outputBase")
    def getOutputBase(self):
        folder = self.store.getOutputDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                             adminconsts.DEFAULT_OUTPUT_DIR)
    
    @base.property_getter("failedBase")
    def getFailedBase(self):
        folder = self.store.getFailedDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                             adminconsts.DEFAULT_FAILED_DIR)
    
    @base.property_getter("doneBase")
    def getDoneBase(self):
        folder = self.store.getDoneDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                             adminconsts.DEFAULT_DONE_DIR)
    
    @base.property_getter("linkBase")
    def getLinkBase(self):
        folder = self.store.getLinkDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                             adminconsts.DEFAULT_LINK_DIR)
    
    @base.property_getter("workBase")
    def getWorkBase(self):
        folder = self.store.getWorkDir()
        return self._getDir(constants.TEMP_ROOT, folder, 
                             adminconsts.DEFAULT_WORK_DIR)
    
    @base.property_getter("configBase")
    def getConfigBase(self):
        folder = self.store.getConfigDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                             adminconsts.DEFAULT_CONFIG_DIR)
    
    @base.property_getter("tempRepBase")
    def getTempRepBase(self):
        folder = self.store.getTempRepDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                             adminconsts.DEFAULT_TEMPREP_DIR)

    @base.property_getter("failedRepBase")
    def getFailedRepBase(self):
        folder = self.store.getFailedRepDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                            adminconsts.DEFAULT_FAILEDREP_DIR)
    
    @base.property_getter("doneRepBase")
    def getDoneRepBase(self):
        folder = self.store.getDoneRepDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                             adminconsts.DEFAULT_DONEREP_DIR)
    

    ## Private Methodes ##
    
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
