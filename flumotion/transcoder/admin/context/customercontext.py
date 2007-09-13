# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder import fileutils
from flumotion.transcoder.virtualpath import VirtualPath
from flumotion.transcoder import constants
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.substitution import Variables
from flumotion.transcoder.utils import LazyEncapsulationIterator
from flumotion.transcoder.admin.context.profilecontext import ProfileContext
from flumotion.transcoder.admin.context.profilecontext import UnboundProfileContext

#TODO: Do some value caching

class CustomerContext(object):
    """
    The customer context define the default base directories.
    They are directly taken and expanded from the store get...Dir getter,
    or deduced from constants and customer name/subdir values.
    The return values are VirtualPath instances that abstract
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
    
    def __init__(self, customerStore, transcodingContext):
        self.transcoding = transcodingContext
        self.store = customerStore
        self._vars = Variables(transcodingContext._vars)
        self._vars.addVar("customerName", self.store.getName())

    def getIdentifier(self):
        """
        Gives an identifier that should uniquely identify a customer.
        It should not change event if customer configuration changed.
        """
        # For now return only the customer name
        return self.store.getName()

    def getTranscodingContext(self):
        return self.transcoding

    def getUnboundProfileContextByName(self, profileName):
        return UnboundProfileContext(self.store[profileName], self)
    
    def getUnboundProfileContext(self, profile):
        return UnboundProfileContext(profile, self)
    
    def iterUnboundProfileContexts(self):
        return LazyEncapsulationIterator(UnboundProfileContext, 
                                         self.store.iterProfiles(), self)
        
    def getProfileContextByName(self, profileName, input):
        return ProfileContext(self.store[profileName], self, input)
    
    def getProfileContext(self, profile, input):
        assert profile.getParent() == self.store
        return ProfileContext(profile, self, input)

    def iterProfileContexts(self, input):
        return LazyEncapsulationIterator(ProfileContext,
                                         self.store.iterProfiles(),
                                         self, input)
        
    def getPathAttributes(self):
        forceUser = self.store.getAccessForceUser()
        forceGroup = self.store.getAccessForceGroup()
        forceDirMode = self.store.getAccessForceDirMode()
        forceFileMode = self.store.getAccessForceFileMode()
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
            return VirtualPath(folder, rootName)
        subdir = self.getSubdir()
        folder = fileutils.ensureAbsDirPath(template % subdir)
        folder = fileutils.cleanupPath(folder)
        return VirtualPath(folder, rootName)
        
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
    
    def getFailedRepBase(self):
        folder = self.store.getFailedRepDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                            adminconsts.DEFAULT_FAILEDREP_DIR)
    
    def getDoneRepBase(self):
        folder = self.store.getDoneRepDir()
        return self._getDir(constants.DEFAULT_ROOT, folder, 
                            adminconsts.DEFAULT_DONEREP_DIR)

    def getMonitorLabel(self):
        template = self.transcoding.admin.config.monitorLabelTemplate
        return self._vars.substitute(template)
    
