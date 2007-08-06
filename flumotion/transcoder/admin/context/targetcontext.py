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
from flumotion.transcoder.admin.substitution import Variables


def _buildRelPathGetter(storeGetterName):
    def getter(self):
        template = getattr(self.store, storeGetterName)()
        path = self._vars.substitute(template)
        path = utils.ensureRelPath(path)
        return utils.cleanupPath(path)
    return getter

def _buildBaseGetter(baseGetterName, storeGetterName):
    def getter(self):
        folder = getattr(self.store, storeGetterName)()
        if folder != None:
            value = self._expandDir(folder)
            value = utils.ensureAbsDirPath(value)
            value = utils.cleanupPath(value)
            return VirtualPath(value)
        parent = getattr(self.profile, baseGetterName)()
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


class TargetContext(object):
    """
    The target context define the target-specific directories, files, 
    relative path and contextual path.
    
        Ex: customer data => store.get...Dir()=None
                             name = "Fluendo"
                             subdir = None
            profile data => store.get...Dir()=None
                            name = "OGG/Theora-Vorbis"
                            subdir = "ogg"
            target data => name = "High Quality" (Ignored)
                           subdir = "high"
                           extension = ".ogg"
            source path => "/subdir/file.avi"

                getOutputBase: default:/fluendo/files/outgoing/ogg/subdir/high/
                getLinkBase: default:/fluendo/files/links/ogg/subdir/high/
                getWorkBase: temp:/fluendo/files/links/ogg/subdir/high/
                
                getOutputDir: default:/fluendo/files/outgoing/ogg/subdir/high/
                getLinkDir: default:/fluendo/files/links/ogg/subdir/high/
                
                getOutputFile: file.avi.ogg
                getLinkFile: file.avi.link
                
                getOutputRelPath: /subdir/high/file.avi.ogg
                getLinkRelPath: /subdir/high/file.avi.link
                
                getOutputPath: default:/fluendo/files/outgoing/ogg/subdir/file.avi.ogg
                getLinkPath: default:/fluendo/files/link/ogg/subdir/file.avi.link
    """
    
    # Getters get...Base(), get...RelPath(), get...File(), get...Dir() and get...Path()
    # will be created by the metaclass
    __getters__ = ["Output", "Link"]
    __base_overrides__ = ["Output", "Link", "Work"]
    
    class __metaclass__(type):
        def __init__(cls, name, bases, dct):
            for name in cls.__base_overrides__:
                baseGetterName = "get%sBase" % name
                storeBaseGetterName = "get%sDir" % name
                baseGetter = _buildBaseGetter(baseGetterName, storeBaseGetterName)
                if not hasattr(cls, baseGetterName):
                    setattr(cls, baseGetterName, baseGetter)
            for name in cls.__getters__:
                baseGetterName = "get%sBase" % name
                dirGetterName = "get%sDir" % name
                storeRelGetterName = "get%sFileTemplate" % name
                relGetterName = "get%sRelPath" % name
                pathGetterName = "get%sPath" % name
                fileGetterName = "get%sFile" % name
                relGetter = _buildRelPathGetter(storeRelGetterName)
                dirGetter = _buildDirGetter(baseGetterName, relGetterName)
                fileGetter = _buildFileGetter(relGetterName)
                pathGetter = _buildPathGetter(dirGetterName, fileGetterName)
                if not hasattr(cls, relGetterName):
                    setattr(cls, relGetterName, relGetter)
                if not hasattr(cls, dirGetterName):
                    setattr(cls, dirGetterName, dirGetter)
                if not hasattr(cls, fileGetterName):
                    setattr(cls, fileGetterName, fileGetter)
                if not hasattr(cls, pathGetterName):
                    setattr(cls, pathGetterName, pathGetter)
                
    
    def __init__(self, targetStore, profileContext):
        self.profile = profileContext
        self.store = targetStore
        self._vars = Variables(self.profile._vars)
        self._vars.addVar("targetName", self.store.getName())
        subdir = self.store.getSubdir() or ""
        subdir = utils.str2path(subdir)
        subdir = utils.ensureRelDirPath(subdir)
        subdir = utils.cleanupPath(subdir)
        self._vars.addVar("targetSubdir", subdir)
        targPath = (utils.joinPath(self._vars["sourceDir"], subdir)
                    + self._vars["sourceFile"])
        self._vars.addFileVars(targPath, "target", 
                               extension=self.getExtension())
        
    def getTranscodingContext(self):
        return self.profile.getTranscodingContext()
    
    def getCustomerContext(self):
        return self.profile.getCustomerContext()
    
    def getProfileContext(self):
        return self.profile
        
    def getSubdir(self):
        return self._vars["targetSubdir"]
    
    def getExtension(self):
        ext = self.store.getExtension()
        if ext :
            return '.' + ext
        return ""
    
    def getOutputRelPath(self):
        template = self.store.getOutputFileTemplate()
        path = self._vars.substitute(template)
        path = utils.ensureRelPath(path)
        return utils.cleanupPath(path)

    def _expandDir(self, folder):
        #FIXME: Do variable substitution here.
        return folder
