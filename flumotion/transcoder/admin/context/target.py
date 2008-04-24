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

from flumotion.transcoder import virtualpath
from flumotion.transcoder.enums import TargetTypeEnum
from flumotion.transcoder.admin.context import base, notification, config


class ITargetContext(base.IBaseStoreContext):

    def getStoreContext(self):
        pass
    
    def getCustomerContext(self):
        pass
    
    def getProfileContext(self):
        pass

    def getConfigContext(self):
        pass

    def getName(self):
        pass
    
    def getExtension(self):
        pass
    
    def getOutputFileTemplate(self):
        pass
    
    def getLinkFileTemplate(self):
        pass
    
    def getLinkTemplate(self):
        pass
    
    def getLinkURLPrefix(self):
        pass
    
    def getEnablePostprocessing(self):
        pass
    
    def getEnableLinkFiles(self):
        pass
    
    def getPostprocessCommand(self):
        pass
    
    def getPostprocessTimeout(self):
        pass

    def getOutputBase(self):
        pass
    
    def getLinkBase(self):
        pass
    
    def getWorkBase(self):
        pass

    def getOutputRelPath(self):
        pass
    
    def getLinkRelPath(self):
        pass

    def getOutputDir(self):
        pass
    
    def getLinkDir(self):
        pass

    def getOutputPath(self):
        pass
    
    def getLinkPath(self):
        pass

    def getOutputFile(self):
        pass
    
    def getLinkFile(self):
        pass


## Getter Factories ##

def _baseGetterFactory(getterName, basePropertyName, storePropertyName):
    def getter(self):
        folder = getattr(self.store, storePropertyName)
        if folder != None:
            value = self._expandDir(folder)
            value = fileutils.ensureAbsDirPath(value)
            value = fileutils.cleanupPath(value)
            return virtualpath.VirtualPath(value)
        return getattr(self.parent, basePropertyName)
    return getter

def _relGetterFactory(getterName, templatePropertyName):
    def getter(self):
        template = getattr(self, templatePropertyName)
        path = self._variables.substitute(template)
        path = fileutils.ensureRelPath(path)
        return fileutils.cleanupPath(path)
    return getter

def _dirGetterFactory(getterName, basePropertyName, relPropertyName):
    def getter(self):
        folder = getattr(self, basePropertyName)
        relPath = getattr(self, relPropertyName)
        path, file = fileutils.splitPath(relPath)[:2]
        return folder.append(path)
    return getter

def _fileGetterFactory(getterName, relPropertyName):
    def getter(self):
        relPath = getattr(self, relPropertyName)
        file, ext = fileutils.splitPath(relPath)[1:3]
        return file + ext
    return getter

def _pathGetterFactory(getterName, dirPropertyName, filePropertyName):
    def getter(self):
        folder = getattr(self, dirPropertyName)
        file = getattr(self, filePropertyName)
        return folder.append(file)
    return getter


## Class Annotations ##

def base_getters(*names):
    for name in names:
        storePropertyName = name + "Dir"
        basePropertyName = name + "Base"
        propertyName = name + "Base"
        getterName = "get" + name[0].upper() + name[1:] + "Base"
        getter = _baseGetterFactory(getterName, basePropertyName, storePropertyName)
        annotate.injectMethod("base_getters", getterName, getter)
        annotate.injectProperty("base_getters", propertyName, getter)

def rel_getters(*names):
    for name in names:
        templatePropertyName = name + "FileTemplate"
        propertyName = name + "RelPath"
        getterName = "get" + name[0].upper() + name[1:] + "RelPath"
        getter = _relGetterFactory(getterName, templatePropertyName)        
        annotate.injectMethod("rel_getters", getterName, getter)
        annotate.injectProperty("rel_getters", propertyName, getter)

def dir_getters(*names):
    for name in names:
        relPropertyName = name + "RelPath"
        basePropertyName = name + "Base"
        propertyName = name + "Dir"
        getterName = "get" + name[0].upper() + name[1:] + "Dir"
        getter = _dirGetterFactory(getterName, basePropertyName, relPropertyName)        
        annotate.injectMethod("dir_getters", getterName, getter)
        annotate.injectProperty("dir_getters", propertyName, getter)

def file_getters(*names):
    for name in names:
        relPropertyName = name + "RelPath"
        propertyName = name + "File"
        getterName = "get" + name[0].upper() + name[1:] + "File"
        getter = _fileGetterFactory(getterName, relPropertyName)        
        annotate.injectMethod("file_getters", getterName, getter)
        annotate.injectProperty("file_getters", propertyName, getter)

def path_getters(*names):
    for name in names:
        dirPropertyName = name + "Dir"
        filePropertyName = name + "File"
        propertyName = name + "Path"
        getterName = "get" + name[0].upper() + name[1:] + "Path"
        getter = _pathGetterFactory(getterName, dirPropertyName, filePropertyName)        
        annotate.injectMethod("path_getters", getterName, getter)
        annotate.injectProperty("path_getters", propertyName, getter)


class TargetContext(base.BaseStoreContext, notification.NotifyStoreMixin):
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

                getOutputBase: default:/fluendo/files/outgoing/ogg/
                getLinkBase: default:/fluendo/files/links/ogg/
                getWorkBase: temp:/fluendo/files/links/ogg/
                
                getOutputDir: default:/fluendo/files/outgoing/ogg/subdir/high/
                getLinkDir: default:/fluendo/files/links/ogg/subdir/high/
                
                getOutputFile: file.avi.ogg
                getLinkFile: file.avi.link
                
                getOutputRelPath: /subdir/high/file.avi.ogg
                getLinkRelPath: /subdir/high/file.avi.link
                
                getOutputPath: default:/fluendo/files/outgoing/ogg/subdir/file.avi.ogg
                getLinkPath: default:/fluendo/files/link/ogg/subdir/file.avi.link
    """
    
    implements(ITargetContext)
    
    base.store_proxy("name")
    base.store_parent_proxy("linkFileTemplate")
    base.store_parent_proxy("linkTemplate")
    base.store_parent_proxy("linkURLPrefix")
    base.store_parent_proxy("enablePostprocessing")
    base.store_parent_proxy("enableLinkFiles")
    base.store_parent_proxy("postprocessCommand")
    base.store_parent_proxy("postprocessTimeout")

    base_getters("output", "link", "work")
    rel_getters("output", "link")
    dir_getters("output", "link")
    file_getters("output", "link")
    path_getters("output", "link")
    
    def __init__(self, profCtx, targStore):
        base.BaseStoreContext.__init__(self, profCtx, targStore)
        self._variables.addVar("targetName", self.getName())
        subdir = self.store.getSubdir() or ""
        subdir = fileutils.str2path(subdir)
        subdir = fileutils.ensureRelDirPath(subdir)
        subdir = fileutils.cleanupPath(subdir)
        self._variables.addVar("targetSubdir", subdir)
        targPath = (fileutils.joinPath(self._variables["sourceDir"], subdir)
                    + self._variables["sourceFile"])
        self._variables.addFileVars(fileutils.ensureRelPath(targPath),
                                    "target", extension=self.getExtension())
        
    def getAdminContext(self):
        return self.parent.getAdminContext()

    def getStoreContext(self):
        return self.parent.getStoreContext()
    
    def getCustomerContext(self):
        return self.parent.getCustomerContext()
    
    def getProfileContext(self):
        return self.parent

    def getConfigContext(self):
        confStore = self.store.getConfigStore()
        return config.ConfigContextFactory(self, confStore)

    @base.property_getter("outputFileTemplate")
    def getOutputFileTemplate(self):
        tmpl = self.store.getOutputFileTemplate()
        if tmpl: return tmpl
        type = self.store.getConfigStore().getType()
        if type == TargetTypeEnum.thumbnails:
            return self.parent.getOutputThumbTemplate()
        else:
            return self.parent.getOutputMediaTemplate()

    @base.property_getter("subdir")
    def getSubdir(self):
        return self._variables["targetSubdir"]
    
    @base.property_getter("extension")
    def getExtension(self):
        ext = self.store.getExtension()
        if ext :
            return '.' + ext.lstrip('.')
        return ""
    
    
    # Private Methodes ## 
    
    def _expandDir(self, folder):
        #FIXME: Do variable substitution here.
        return folder
