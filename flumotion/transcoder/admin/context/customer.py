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

from flumotion.inhouse import fileutils

from flumotion.transcoder import constants, virtualpath
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.context import base, profile, notification

#TODO: Do some value caching

class ICustomerContext(base.IBaseStoreContext):

    name                 = Attribute("Name of the customer")
    subdir               = Attribute("Customer files sub-directory")
    customerPriority     = Attribute("Customer transcoding priority")
    outputMediaTemplate  = Attribute("Output media file template")
    outputThumbTemplate  = Attribute("Output thumbnail file temaplte")
    linkFileTemplate     = Attribute("Link file template")
    configFileTemplate   = Attribute("Configuration file template")
    reportFileTemplate   = Attribute("Report file template")
    linkTemplate         = Attribute("Link template")
    linkURLPrefix        = Attribute("link URL prefix")
    enablePostprocessing = Attribute("Enable post-processing")
    enablePreprocessing  = Attribute("Enable pre-processing")
    enableLinkFiles      = Attribute("Enable link file generation")
    transcodingPriority  = Attribute("Transcoding priority")
    processPriority      = Attribute("Transcoding process priority")
    preprocessCommand    = Attribute("Pre-processing command line")
    postprocessCommand   = Attribute("Post-processing command line")
    preprocessTimeout    = Attribute("Pre-processing timeout")
    postprocessTimeout   = Attribute("Post-processing timeout")
    transcodingTimeout   = Attribute("Transcoding timeout")
    monitoringPeriod     = Attribute("Monitoring period")
    accessForceUser      = Attribute("Force user of new files and directories")
    accessForceGroup     = Attribute("Force group of new files and directories")
    accessForceDirMode   = Attribute("Force rights of new directories")
    accessForceFileMode  = Attribute("Force rights of new files")
    pathAttributes       = Attribute("Path rights, user and group specifications")
    monitorLabel         = Attribute("Monitor components label")
    inputBase            = Attribute("Input file base directory")
    outputBase           = Attribute("Output file base directory")
    failedBase           = Attribute("Failed transcoding base directory")
    doneBase             = Attribute("Succeed transocding base directory")
    linkBase             = Attribute("Link files base directory")
    workBase             = Attribute("Temporary files directory")
    configBase           = Attribute("Transcoding configuration files base directory")
    tempRepBase          = Attribute("Temporary reports base directory")
    failedRepBase        = Attribute("Failed reports base directory")
    doneRepBase          = Attribute("Succeed reports base directory")

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
                inputBase: default:/fluendo/files/incoming/
                outputBase: default:/fluendo/files/outgoing/
                failedBase: default:/fluendo/files/failed/
                doneBase: default:/fluendo/files/done/
                linkBase: default:/fluendo/files/links/
                workBase: temp:/fluendo/working/
                confBase: default:/fluendo/configs/
                tempRepBase: default:/fluendo/reports/pending/
                failedRepBase: default:/fluendo/reports/failed/
                doneRepBase: default:/fluendo/reports/done/
    
        Ex: customer data => store.xxxDir()=None
                             name="Big/Comp (1)"
                             subdir=None
                inputBase: default:/big_comp_(1)/files/incoming/
                outputBase: default:/big_comp_(1)/files/outgoing/
                workBase: temp:/big_comp_(1)/working/
                ...
    
        Ex: customer data => store.xxxDir()=None
                             name="RTVE"
                             subdir="rtve/l2n"
                inputBase: default:/rtve/l2n/files/incoming/
                outputBase: default:/rtve/l2n/files/outgoing/
                workBase: temp:/rtve/l2n/working/
                ...
    """
    
    implements(ICustomerContext)
    
    name                 = base.StoreProxy("name")
    customerPriority     = base.StoreProxy("customerPriority",
                                           adminconsts.DEFAULT_CUSTOMER_PRIORITY)
    preprocessCommand    = base.StoreProxy("preprocessCommand")
    postprocessCommand   = base.StoreProxy("postprocessCommand")
    enablePostprocessing = base.StoreProxy("enablePostprocessing")
    enablePreprocessing  = base.StoreProxy("enablePreprocessing")
    enableLinkFiles      = base.StoreProxy("enableLinkFiles")
    outputMediaTemplate  = base.StoreParentProxy("outputMediaTemplate")
    outputThumbTemplate  = base.StoreParentProxy("outputThumbTemplate")
    linkFileTemplate     = base.StoreParentProxy("linkFileTemplate")
    configFileTemplate   = base.StoreParentProxy("configFileTemplate")
    reportFileTemplate   = base.StoreParentProxy("reportFileTemplate")
    linkTemplate         = base.StoreParentProxy("linkTemplate")
    linkURLPrefix        = base.StoreParentProxy("linkURLPrefix")
    transcodingPriority  = base.StoreParentProxy("transcodingPriority")
    processPriority      = base.StoreParentProxy("processPriority")
    preprocessTimeout    = base.StoreParentProxy("preprocessTimeout")
    postprocessTimeout   = base.StoreParentProxy("postprocessTimeout")
    transcodingTimeout   = base.StoreParentProxy("transcodingTimeout")
    monitoringPeriod     = base.StoreParentProxy("monitoringPeriod")
    accessForceUser      = base.StoreParentProxy("accessForceUser")
    accessForceGroup     = base.StoreParentProxy("accessForceGroup")
    accessForceDirMode   = base.StoreParentProxy("accessForceDirMode")
    accessForceFileMode  = base.StoreParentProxy("accessForceFileMode")

    
    def __init__(self, storeCtx, custStore):
        base.BaseStoreContext.__init__(self, storeCtx, custStore)
        self._variables.addVar("customerName", self.name)

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
    
    @property
    def pathAttributes(self):
        return fileutils.PathAttributes(self.accessForceUser,
                                        self.accessForceGroup,
                                        self.accessForceDirMode,
                                        self.accessForceFileMode)

    @property
    def monitorLabel(self):
        template = self.getAdminContext().config.monitorLabelTemplate
        return self._variables.substitute(template)
    
    @property
    def subdir(self):
        subdir = self.store.subdir
        if subdir != None:
            subdir = fileutils.str2path(subdir)
            subdir = fileutils.ensureRelDirPath(subdir)
            return fileutils.cleanupPath(subdir)
        subdir = fileutils.str2filename(self.store.name)
        return fileutils.ensureDirPath(subdir)
            
    @property
    def inputBase(self):
        return self._getDir(constants.DEFAULT_ROOT,
                            self.store.inputDir, 
                            adminconsts.DEFAULT_INPUT_DIR)

    @property
    def outputBase(self):
        return self._getDir(constants.DEFAULT_ROOT,
                            self.store.outputDir, 
                            adminconsts.DEFAULT_OUTPUT_DIR)
    
    @property
    def failedBase(self):
        return self._getDir(constants.DEFAULT_ROOT,
                            self.store.failedDir, 
                            adminconsts.DEFAULT_FAILED_DIR)
    
    @property
    def doneBase(self):
        return self._getDir(constants.DEFAULT_ROOT,
                            self.store.doneDir, 
                            adminconsts.DEFAULT_DONE_DIR)
    
    @property
    def linkBase(self):
        return self._getDir(constants.DEFAULT_ROOT,
                            self.store.linkDir,
                            adminconsts.DEFAULT_LINK_DIR)
    
    @property
    def workBase(self):
        return self._getDir(constants.TEMP_ROOT,
                            self.store.workDir, 
                            adminconsts.DEFAULT_WORK_DIR)
    
    @property
    def configBase(self):
        return self._getDir(constants.DEFAULT_ROOT,
                            self.store.configDir, 
                            adminconsts.DEFAULT_CONFIG_DIR)
    
    @property
    def tempRepBase(self):
        return self._getDir(constants.DEFAULT_ROOT,
                            self.store.tempRepDir, 
                            adminconsts.DEFAULT_TEMPREP_DIR)

    @property
    def failedRepBase(self):
        return self._getDir(constants.DEFAULT_ROOT,
                            self.store.failedRepDir, 
                            adminconsts.DEFAULT_FAILEDREP_DIR)
    
    @property
    def doneRepBase(self):
        return self._getDir(constants.DEFAULT_ROOT,
                            self.store.doneRepDir, 
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
        folder = fileutils.ensureAbsDirPath(template % self.subdir)
        folder = fileutils.cleanupPath(folder)
        return virtualpath.VirtualPath(folder, rootName)
