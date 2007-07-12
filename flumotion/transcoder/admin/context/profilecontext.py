# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder import utils
from flumotion.transcoder.virtualpath import VirtualPath
from flumotion.transcoder.utils import LazyEncapsulationIterator
from flumotion.transcoder.admin.substitution import Variables
from flumotion.transcoder.admin.context.targetcontext import TargetContext

#TODO: Do some value caching

def _buildBaseGetter(baseGetterName, storeGetterName):
    def getter(self):
        folder = getattr(self.store, storeGetterName)()
        parent = getattr(self.customer, baseGetterName)()
        if folder != None:
            value = self._expandDir(folder)
            value = utils.ensureAbsDirPath(value)
            value = utils.cleanupPath(value)
            return VirtualPath(value, parent.getRoot())
        return parent.append(self.getSubdir())
    return getter

def _buildDirGetter(baseGetterName, relGetterName):
    def getter(self):
        folder = getattr(self, baseGetterName)()
        relPath = getattr(self, relGetterName)()
        path, file, ext = utils.splitPath(relPath)
        return folder.append(path)
    return getter

def _buildFileGetter(relGetterName):
    def getter(self):
        relPath = getattr(self, relGetterName)()
        path, file, ext = utils.splitPath(relPath)
        return file + ext
    return getter

def _buildPathGetter(dirGetterName, fileGetterName):
    def getter(self):
        folder = getattr(self, dirGetterName)()
        return folder.append(getattr(self, fileGetterName)())
    return getter


class UnboundProfileContext(object):
    """
    A profile context independent of the input file.
    
    The profile context define the base directories.
    the source relative path and the source contextual path.
    
        Ex: customer data => store.get...Dir()=None
                             name="Fluendo"
                             subdir=None
            profile data => store.get...Dir()=None
                            name="OGG/Theora-Vorbis"
                            subdir="ogg"
                
                getInputBase: default:/fluendo/files/incoming/ogg/
                getoutputBase: default:/fluendo/files/outgoing/ogg/
                getFailedBase: default:/fluendo/files/failed/ogg/
                getDoneBase: default:/fluendo/files/done/ogg/
                getLinkBase: default:/fluendo/files/links/ogg/
                getWorkBase: temp:/fluendo/working/ogg/
                getConfBase: default:/fluendo/configs/ogg/
                getFailedRepBase: default:/fluendo/reports/failed/ogg/
                getDoneRepBase: default:/fluendo/reports/done/ogg/
    """
    
    # Getters get...Base()
    # will be created by the metaclass
    __base_getters__ = ["Output", "Link", "Work",
                        "Input", "Failed", "Done", 
                        "Config", "FailedRep", "DoneRep"]
    
    class __metaclass__(type):
        def __init__(cls, classname, bases, dct):
            props = getattr(cls, "__base_getters__", [])
            for name in props:
                storeGetterName = "get%sDir" % name
                baseGetterName = "get%sBase" % name
                baseGetter = _buildBaseGetter(baseGetterName, storeGetterName)
                setattr(cls, baseGetterName, baseGetter)
            props = getattr(cls, "__file_getters__", [])
            for name in props:
                dirGetterName = "get%sDir" % name
                relGetterName = "get%sRelPath" % name
                baseGetterName = "get%sBase" % name
                pathGetterName = "get%sPath" % name
                fileGetterName = "get%sFile" % name
                dirGetter = _buildDirGetter(baseGetterName, relGetterName)
                fileGetter = _buildFileGetter(relGetterName)
                pathGetter = _buildPathGetter(dirGetterName, fileGetterName)
                if not hasattr(cls, fileGetterName):
                    setattr(cls, fileGetterName, fileGetter)
                if not hasattr(cls, pathGetterName):
                    setattr(cls, pathGetterName, pathGetter)
                if not hasattr(cls, dirGetterName):
                    setattr(cls, dirGetterName, dirGetter)

    def __init__(self, profileStore, customerContext):
        self.customer = customerContext
        self.store = profileStore
        self._vars = Variables(customerContext._vars)
        self._vars.addVar("sourceSubdir", self.getSubdir())
        self._vars.addVar("profileName", self.store.getName())

    def getIdentifier(self):
        """
        Gives an identifier that should uniquely identify a profile.
        It should not change event if profile configuration changed.
        """
        # For now return only the customer and profile name
        return "%s/%s" % (self.customer.getIdentifier(), self.store.getName())

    def getSubdir(self):
        subdir = self.store.getSubdir()
        if subdir != None:
            subdir = utils.str2path(subdir)
            subdir = utils.ensureRelDirPath(subdir)
            return utils.cleanupPath(subdir)
        subdir = utils.str2filename(self.store.getName())
        return utils.ensureDirPath(subdir)

    def _expandDir(self, folder):
        #FIXME: Do variable substitution here.
        return folder
    

class ProfileContext(UnboundProfileContext):
    """
    The profile context define the base directories, 
    the source-specific directories, the source files,
    the source relative path and the source contextual path.
    
        Ex: customer data => store.get...Dir()=None
                             name="Fluendo"
                             subdir=None
            profile data => store.get...Dir()=None
                            name="OGG/Theora-Vorbis"
                            subdir="ogg"
            source path => "/subdir/file.avi"
                
                getInputBase: default:/fluendo/files/incoming/ogg/
                getoutputBase: default:/fluendo/files/outgoing/ogg/
                getFailedBase: default:/fluendo/files/failed/ogg/
                getDoneBase: default:/fluendo/files/done/ogg/
                getLinkBase: default:/fluendo/files/links/ogg/
                getWorkBase: temp:/fluendo/working/ogg/
                getConfBase: default:/fluendo/configs/ogg/
                getFailedRepBase: default:/fluendo/reports/failed/ogg/
                getDoneRepBase: default:/fluendo/reports/done/ogg/
                
                getInputDir: default:/fluendo/files/incoming/ogg/subdir/
                getFailedDir: default:/fluendo/files/failed/ogg/subdir/
                getDoneDir: default:/fluendo/files/done/ogg/subdir/
                getConfDir: default:/fluendo/configs/ogg/subdir/
                getFailedRepDir: default:/fluendo/reports/failed/ogg/subdir/
                getDoneRepDir: default:/fluendo/reports/done/ogg/subdir/
                
                getInputFile: file.avi
                getConfFile: file.avi.conf
                getFailedRepFile: file.avi.rep
                getDoneRepFile: file.avi.rep
                
                getInputRelPath: /subdir/file.avi
                getConfRelPath: /subdir/file.avi.conf
                getFailedRepRelPath: /subdir/file.avi.rep
                getDoneRepRelPath: /subdir/file.avi.rep
                
                getInputPath: default:/fluendo/files/incoming/ogg/subdir/file.avi
                getConfPath: default:/fluendo/configs/ogg/subdir/file.avi.conf
                getFailedRepPath: default:/fluendo/reports/failed/ogg/subdir/file.avi.rep
                getDoneRepPath: default:/fluendo/reports/done/ogg/subdir/file.avi.rep
    """
    
    # Getters get...Dir(), get...File(), get...Path()
    # will be created by the metaclass
    __file_getters__ = ["Input", "Failed", "Done", 
                        "Config", "FailedRep", "DoneRep"]


    def __init__(self, profileStore, customerContext, inputAbstractPath):
        UnboundProfileContext.__init__(self, profileStore, customerContext)
        self._vars.addFileVars(inputAbstractPath, "source")        

    def getIdentifier(self):
        """
        Gives an identifier that should uniquely identify a profile.
        It should not change event if profile configuration changed.
        """
        # For now return only the customer and profile name
        return "%s:%s" % (UnboundProfileContext.getIdentifier(self),
                          self._vars["sourcePath"])

    def getTargetContextByName(self, targetName):
        return TargetContext(self.store[targetName], self)

    def getTargetContext(self, target):
        assert target.getParent() == self.store
        return TargetContext(target, self)

    def iterTargetContexts(self):
        return LazyEncapsulationIterator(TargetContext, 
                                         self.store.iterTargets(), self)

    def getInputRelPath(self):
        return self._vars["sourcePath"]
    
    def getFailedRelPath(self):
        return self._vars["sourcePath"]
    
    def getDoneRelPath(self):
        return self._vars["sourcePath"]
    
    def getConfigRelPath(self):
        path = self._vars.substitute(self.store.getConfigFileTemplate())
        path = utils.ensureRelPath(path)
        return utils.cleanupPath(path)
    
    def getFailedRepRelPath(self):
        path = self._vars.substitute(self.store.getReportFileTemplate())
        path = utils.ensureRelPath(path)
        return utils.cleanupPath(path)
    
    def getDoneRepRelPath(self):
        path = self._vars.substitute(self.store.getReportFileTemplate())
        path = utils.ensureRelPath(path)
        return utils.cleanupPath(path)
    
    def getTranscoderLabel(self):
        #FIXME: Dependency too deep 
        tmpl = self.customer.transcoding.admin.config.transcoderLabelTemplate
        return self._vars.substitute(tmpl)

    def getActivityLabel(self):
        #FIXME: Dependency too deep 
        tmpl = self.customer.transcoding.admin.config.activityLabelTemplate
        return self._vars.substitute(tmpl)
    
    