# vi:si:et:sw=4:sts=4:ts=4

# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007,2008,2009 Fluendo, S.L.
# Copyright (C) 2010,2011 Flumotion Services, S.A.
# All rights reserved.
#
# This file may be distributed and/or modified under the terms of
# the GNU Lesser General Public License version 2.1 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.LGPL" in the source distribution for more information.
#
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
        file = getattr(obj, self._filePropertyName)
        return folder.append(file)


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
