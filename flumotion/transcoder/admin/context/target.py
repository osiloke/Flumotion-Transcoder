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

from flumotion.transcoder import virtualpath
from flumotion.transcoder.enums import TargetTypeEnum
from flumotion.transcoder.admin.context import base, notification, config


class ITargetContext(base.IBaseStoreContext):

    name                 = Attribute("Target's name")
    subdir               = Attribute("Target's sub-directory")
    extension            = Attribute("Output file extension")
    outputFileTemplate   = Attribute("Output file template")
    linkFileTemplate     = Attribute("Link file template")
    linkTemplate         = Attribute("Link template")
    linkURLPrefix        = Attribute("Link URL prefix")
    enablePostprocessing = Attribute("Enable post-processing")
    enableLinkFiles      = Attribute("Enable link file generation")
    postprocessCommand   = Attribute("Post-processing command line")
    postprocessTimeout   = Attribute("Post-processing timeout")
    outputBase           = Attribute("Output file base directory")
    linkBase             = Attribute("Link files base directory")
    workBase             = Attribute("Temporary files directory")
    outputRelPath        = Attribute("output file relative path")
    linkRelPath          = Attribute("Link file relative path")
    outputDir            = Attribute("output file directory")
    linkDir              = Attribute("Link file directory")
    outputFile           = Attribute("Output file name")
    linkFile             = Attribute("Link file name")
    outputPath           = Attribute("Output file path")
    linkPath             = Attribute("Link file path")

    def getStoreContext(self):
        pass
    
    def getCustomerContext(self):
        pass
    
    def getProfileContext(self):
        pass

    def getConfigContext(self):
        pass


### Getter Factories ##
#
#def _baseGetterFactory(getterName, basePropertyName, storePropertyName):
#    def getter(self):
#        folder = getattr(self.store, storePropertyName)
#        if folder != None:
#            value = self._expandDir(folder)
#            value = fileutils.ensureAbsDirPath(value)
#            value = fileutils.cleanupPath(value)
#            return virtualpath.VirtualPath(value)
#        return getattr(self.parent, basePropertyName)
#    getter.__name__ = getterName
#    return getter
#
#def _relGetterFactory(getterName, templatePropertyName):
#    def getter(self):
#        template = getattr(self, templatePropertyName)
#        path = self._variables.substitute(template)
#        path = fileutils.ensureRelPath(path)
#        return fileutils.cleanupPath(path)
#    getter.__name__ = getterName
#    return getter
#
#def _dirGetterFactory(getterName, basePropertyName, relPropertyName):
#    def getter(self):
#        folder = getattr(self, basePropertyName)
#        relPath = getattr(self, relPropertyName)
#        path, file = fileutils.splitPath(relPath)[:2]
#        return folder.append(path)
#    getter.__name__ = getterName
#    return getter
#
#def _fileGetterFactory(getterName, relPropertyName):
#    def getter(self):
#        relPath = getattr(self, relPropertyName)
#        file, ext = fileutils.splitPath(relPath)[1:3]
#        return file + ext
#    getter.__name__ = getterName
#    return getter
#
#def _pathGetterFactory(getterName, dirPropertyName, filePropertyName):
#    def getter(self):
#        folder = getattr(self, dirPropertyName)
#        file = getattr(self, filePropertyName)
#        return folder.append(file)
#    getter.__name__ = getterName
#    return getter


## Descriptors ##

class ReadOnlyProperty(object):
    def __set__(self, obj, value):
        raise AttributeError("Attribute is read-only")
    def __delete__(self, obj):
        raise AttributeError("Attribute cannot be deleted")    


class BaseDir(ReadOnlyProperty):
    def __init__(self, name):
        self._basePropertyName = name + "Base"
        self._storePropertyName = name + "Dir"
    def __get__(self, obj, type=None):
        storeValue = getattr(obj.store, self._storePropertyName)
        if storeValue != None:
            value = obj._expandDir(storeValue)
            value = fileutils.ensureAbsDirPath(value)
            value = fileutils.cleanupPath(value)
            return virtualpath.VirtualPath(value)
        return getattr(obj.parent, self._basePropertyName)


class RelPath(ReadOnlyProperty):
    def __init__(self, name):
        self._templatePropertyName = name + "FileTemplate"
    def __get__(self, obj, type=None):
        template = getattr(obj, self._templatePropertyName)
        path = obj._variables.substitute(template)
        path = fileutils.ensureRelPath(path)
        return fileutils.cleanupPath(path)


class FileDir(ReadOnlyProperty):
    def __init__(self, name):
        self._basePropertyName = name + "Base"
        self._relPropertyName = name + "RelPath"
    def __get__(self, obj, type=None):
        baseDir = getattr(obj, self._basePropertyName)
        relPath = getattr(obj, self._relPropertyName)
        path, file = fileutils.splitPath(relPath)[:2]
        return baseDir.append(path)


class FileName(ReadOnlyProperty):
    def __init__(self, name):
        self._relPropertyName = name + "RelPath"
    def __get__(self, obj, type=None):
        relPath = getattr(obj, self._relPropertyName)
        file, ext = fileutils.splitPath(relPath)[1:3]
        return file + ext


class FilePath(ReadOnlyProperty):
    def __init__(self, name):
        self._dirPropertyName = name + "Dir"
        self._filePropertyName = name + "File"
    def __get__(self, obj, type=None):
        folder = getattr(obj, self._dirPropertyName)
        file = getattr(self, self._filePropertyName)
        return folder.append(file)


### Class Annotations ##
#
#def base_getters(*names):
#    for name in names:
#        storePropertyName = name + "Dir"
#        basePropertyName = name + "Base"
#        propertyName = name + "Base"
#        getterName = "get" + name[0].upper() + name[1:] + "Base"
#        getter = _baseGetterFactory(getterName, basePropertyName, storePropertyName)
#        annotate.injectAttribute("base_getters", getterName, getter)
#        prop = property(getter)
#        annotate.injectAttribute("base_getters", propertyName, prop)
#
#def rel_getters(*names):
#    for name in names:
#        templatePropertyName = name + "FileTemplate"
#        propertyName = name + "RelPath"
#        getterName = "get" + name[0].upper() + name[1:] + "RelPath"
#        getter = _relGetterFactory(getterName, templatePropertyName)        
#        annotate.injectAttribute("rel_getters", getterName, getter)
#        prop = property(getter)
#        annotate.injectAttribute("rel_getters", propertyName, prop)
#
#def dir_getters(*names):
#    for name in names:
#        relPropertyName = name + "RelPath"
#        basePropertyName = name + "Base"
#        propertyName = name + "Dir"
#        getterName = "get" + name[0].upper() + name[1:] + "Dir"
#        getter = _dirGetterFactory(getterName, basePropertyName, relPropertyName)        
#        annotate.injectAttribute("dir_getters", getterName, getter)
#        prop = property(getter)
#        annotate.injectAttribute("dir_getters", propertyName, prop)
#
#def file_getters(*names):
#    for name in names:
#        relPropertyName = name + "RelPath"
#        propertyName = name + "File"
#        getterName = "get" + name[0].upper() + name[1:] + "File"
#        getter = _fileGetterFactory(getterName, relPropertyName)        
#        annotate.injectAttribute("file_getters", getterName, getter)
#        prop = property(getter)
#        annotate.injectAttribute("file_getters", propertyName, prop)
#
#def path_getters(*names):
#    for name in names:
#        dirPropertyName = name + "Dir"
#        filePropertyName = name + "File"
#        propertyName = name + "Path"
#        getterName = "get" + name[0].upper() + name[1:] + "Path"
#        getter = _pathGetterFactory(getterName, dirPropertyName, filePropertyName)        
#        annotate.injectAttribute("path_getters", getterName, getter)
#        prop = property(getter)
#        annotate.injectAttribute("path_getters", propertyName, prop)


class TargetContext(base.BaseStoreContext, notification.NotifyStoreMixin):
    """
    The target context define the target-specific directories, files, 
    relative path and contextual path.
    
        Ex: customer data => store.xxxDir()=None
                             name = "Fluendo"
                             subdir = None
            profile data => store.xxxDir()=None
                            name = "OGG/Theora-Vorbis"
                            subdir = "ogg"
            target data => name = "High Quality" (Ignored)
                           subdir = "high"
                           extension = ".ogg"
            source path => "/subdir/file.avi"

                outputBase: default:/fluendo/files/outgoing/ogg/
                linkBase: default:/fluendo/files/links/ogg/
                workBase: temp:/fluendo/files/links/ogg/
                
                outputDir: default:/fluendo/files/outgoing/ogg/subdir/high/
                linkDir: default:/fluendo/files/links/ogg/subdir/high/
                
                outputFile: file.avi.ogg
                linkFile: file.avi.link
                
                outputRelPath: /subdir/high/file.avi.ogg
                linkRelPath: /subdir/high/file.avi.link
                
                outputPath: default:/fluendo/files/outgoing/ogg/subdir/file.avi.ogg
                linkPath: default:/fluendo/files/link/ogg/subdir/file.avi.link
    """
    
    implements(ITargetContext)
    
    name                 = base.StoreProxy("name")
    linkFileTemplate     = base.StoreParentProxy("linkFileTemplate")
    linkTemplate         = base.StoreParentProxy("linkTemplate")
    linkURLPrefix        = base.StoreParentProxy("linkURLPrefix")
    enablePostprocessing = base.StoreParentProxy("enablePostprocessing")
    enableLinkFiles      = base.StoreParentProxy("enableLinkFiles")
    postprocessCommand   = base.StoreParentProxy("postprocessCommand")
    postprocessTimeout   = base.StoreParentProxy("postprocessTimeout")

    outputBase    = BaseDir("output")
    linkBase      = BaseDir("link")
    workBase      = BaseDir("work")
    outputRelPath = RelPath("output")
    linkRelPath   = RelPath("link")
    outputDir     = FileDir("output")
    linkDir       = FileDir("link")
    outputFile    = FileName("output")
    linkFile      = FileName("link")
    outputPath    = FilePath("output")
    linkPath      = FilePath("link")
    
    def __init__(self, profCtx, targStore):
        base.BaseStoreContext.__init__(self, profCtx, targStore)
        self._variables.addVar("targetName", self.name)
        subdir = self.store.subdir or ""
        subdir = fileutils.str2path(subdir)
        subdir = fileutils.ensureRelDirPath(subdir)
        subdir = fileutils.cleanupPath(subdir)
        self._variables.addVar("targetSubdir", subdir)
        targPath = (fileutils.joinPath(self._variables["sourceDir"], subdir)
                    + self._variables["sourceFile"])
        self._variables.addFileVars(fileutils.ensureRelPath(targPath),
                                    "target", extension=self.extension)
        
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

    @property
    def outputFileTemplate(self):
        tmpl = self.store.outputFileTemplate
        if tmpl: return tmpl
        type = self.store.getConfigStore().type
        if type == TargetTypeEnum.thumbnails:
            return self.parent.outputThumbTemplate
        else:
            return self.parent.outputMediaTemplate

    @property
    def subdir(self):
        return self._variables["targetSubdir"]
    
    @property
    def extension(self):
        ext = self.store.extension
        if ext :
            return '.' + ext.lstrip('.')
        return ""
    
    
    # Private Methodes ## 
    
    def _expandDir(self, folder):
        #FIXME: Do variable substitution here.
        return folder
