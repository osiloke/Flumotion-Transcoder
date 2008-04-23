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

from flumotion.transcoder import virtualpath
from flumotion.transcoder.enums import TargetTypeEnum
from flumotion.transcoder.admin.context import base, notification, config


def genBaseGetter(name):
    baseGetterName = "get%sBase" % name
    storeBaseGetterName = "get%sDir" % name
    
    def getter(self):
        folder = getattr(self.store, storeBaseGetterName)()
        if folder != None:
            value = self._expandDir(folder)
            value = fileutils.ensureAbsDirPath(value)
            value = fileutils.cleanupPath(value)
            return virtualpath.VirtualPath(value)
        return getattr(self.parent, baseGetterName)()
    
    annotate.addAnnotationMethod("genBaseGetter", baseGetterName, getter)


def genGetters(name):
    baseGetterName = "get%sBase" % name
    dirGetterName = "get%sDir" % name
    storeRelGetterName = "get%sFileTemplate" % name
    relGetterName = "get%sRelPath" % name
    pathGetterName = "get%sPath" % name
    fileGetterName = "get%sFile" % name

    def relGetter(self):
        method = getattr(self, storeRelGetterName)
        template = method()
        path = self._variables.substitute(template)
        path = fileutils.ensureRelPath(path)
        return fileutils.cleanupPath(path)

    def dirGetter(self):
        folder = getattr(self, baseGetterName)()
        relPath = getattr(self, relGetterName)()
        path, file, ext = fileutils.splitPath(relPath)
        return folder.append(path)

    def fileGetter(self):
        relPath = getattr(self, relGetterName)()
        path, file, ext = fileutils.splitPath(relPath)
        return file + ext

    def pathGetter(self):
        folder = getattr(self, dirGetterName)()
        return folder.append(getattr(self, fileGetterName)())

    annotate.addAnnotationMethod("genGetters", relGetterName, relGetter)
    annotate.addAnnotationMethod("genGetters", dirGetterName, dirGetter)
    annotate.addAnnotationMethod("genGetters", fileGetterName, fileGetter)
    annotate.addAnnotationMethod("genGetters", pathGetterName, pathGetter)


class TargetContext(base.BaseStoreContext, notification.NotificationStoreMixin):
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
    
    base.genStoreProxy("getIdentifier")
    base.genStoreProxy("getName")
    base.genStoreProxy("getLabel")
    base.genParentOverridingStoreProxy("getLinkFileTemplate")
    base.genParentOverridingStoreProxy("getLinkTemplate")
    base.genParentOverridingStoreProxy("getLinkURLPrefix")
    base.genParentOverridingStoreProxy("getEnablePostprocessing")
    base.genParentOverridingStoreProxy("getEnableLinkFiles")
    base.genParentOverridingStoreProxy("getPostprocessCommand")
    base.genParentOverridingStoreProxy("getPostprocessTimeout")

    genBaseGetter("Output")
    genBaseGetter("Link")
    genBaseGetter("Work")
    genGetters("Output")
    genGetters("Link")
    
    
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

    def getOutputFileTemplate(self):
        tmpl = self.store.getOutputFileTemplate()
        if tmpl: return tmpl
        type = self.store.getConfigStore().getType()
        if type == TargetTypeEnum.thumbnails:
            return self.parent.getOutputThumbTemplate()
        else:
            return self.parent.getOutputMediaTemplate()

        
    def getSubdir(self):
        return self._variables["targetSubdir"]
    
    def getExtension(self):
        ext = self.store.getExtension()
        if ext :
            return '.' + ext.lstrip('.')
        return ""
    
    def _expandDir(self, folder):
        #FIXME: Do variable substitution here.
        return folder
