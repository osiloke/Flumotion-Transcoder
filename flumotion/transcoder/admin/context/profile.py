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
from flumotion.transcoder.admin.context import base, target, notification

#TODO: Do some value caching

class IUnboundProfileContext(base.IBaseStoreContext):

    def getStoreContext(self):
        pass
    
    def getCustomerContext(self):
        pass

    def isBound(self):
        pass

    def getName(self):
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

    def getOutputBase(self):
        pass
    
    def getLinkBase(self):
        pass
    
    def getWorkBase(self):
        pass
    
    def getInputBase(self):
        pass
    
    def getFailedBase(self):
        pass
    
    def getDoneBase(self):
        pass
    
    def getConfigBase(self):
        pass
    
    def getTempRepBase(self):
        pass
    
    def getFailedRepBase(self):
        pass
    
    def getDoneRepBase(self):
        pass


class IProfileContext(IUnboundProfileContext):
    
    def getTargetContextByName(self, targName):
        pass

    def getTargetContextFor(self, targStore):
        pass

    def iterTargetContexts(self):
        pass

    def getTranscoderLabel(self):
        pass

    def getActivityLabel(self):
        pass

    def getInputRelPath(self):
        pass
    
    def getFailedRelPath(self):
        pass
    
    def getDoneRelPath(self):
        pass
    
    def getConfigRelPath(self):
        pass
    
    def getTempRepRelPath(self):
        pass

    def getFailedRepRelPath(self):
        pass
    
    def getDoneRepRelPath(self):
        pass
    
    def getInputDir(self):
        pass
    
    def getFailedDir(self):
        pass
    
    def getDoneDir(self):
        pass
    
    def getConfigDir(self):
        pass
    
    def getTempRepDir(self):
        pass
    
    def getFailedRepDir(self):
        pass
    
    def getDoneRepDir(self):
        pass
    
    def getInputPath(self):
        pass
    
    def getFailedPath(self):
        pass
    
    def getDonePath(self):
        pass
    
    def getConfigPath(self):
        pass
    
    def getTempRepPath(self):
        pass
    
    def getFailedRepPath(self):
        pass
    
    def getDoneRepPath(self):
        pass
    
    def getInputFile(self):
        pass
    
    def getFailedFile(self):
        pass
    
    def getDoneFile(self):
        pass
    
    def getConfigFile(self):
        pass
    
    def getTempRepFile(self):
        pass
    
    def getFailedRepFile(self):
        pass
    
    def getDoneRepFile(self):
        pass
    
    

def genBaseGetter(name):
    storeGetterName = "get%sDir" % name
    baseGetterName = "get%sBase" % name
    
    def getter(self):
        folder = getattr(self.store, storeGetterName)()
        parent = getattr(self.parent, baseGetterName)()
        if folder != None:
            value = self._expandDir(folder)
            value = fileutils.ensureAbsDirPath(value)
            value = fileutils.cleanupPath(value)
            return virtualpath.VirtualPath(value, parent.getRoot())
        return parent.append(self._getSubdir())
    
    annotate.addAnnotationMethod("genBaseGetter", baseGetterName, getter)


def genGetters(name):
    dirGetterName = "get%sDir" % name
    relGetterName = "get%sRelPath" % name
    baseGetterName = "get%sBase" % name
    pathGetterName = "get%sPath" % name
    fileGetterName = "get%sFile" % name
    
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
    
    annotate.addAnnotationMethod("genGetteres", fileGetterName, fileGetter)
    annotate.addAnnotationMethod("genGetteres", pathGetterName, pathGetter)
    annotate.addAnnotationMethod("genGetteres", dirGetterName, dirGetter)
    

class UnboundProfileContext(base.BaseStoreContext, notification.NotifyStoreMixin):
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
                getTempRepBase: default:/fluendo/reports/pending/ogg/
                getFailedRepBase: default:/fluendo/reports/failed/ogg/
                getDoneRepBase: default:/fluendo/reports/done/ogg/
    """
    
    implements(IUnboundProfileContext)
    
    base.genStoreProxy("getName")
    base.genParentOverridingStoreProxy("getOutputMediaTemplate")
    base.genParentOverridingStoreProxy("getOutputThumbTemplate")
    base.genParentOverridingStoreProxy("getLinkFileTemplate")
    base.genParentOverridingStoreProxy("getConfigFileTemplate")
    base.genParentOverridingStoreProxy("getReportFileTemplate")
    base.genParentOverridingStoreProxy("getLinkTemplate")
    base.genParentOverridingStoreProxy("getLinkURLPrefix")
    base.genParentOverridingStoreProxy("getEnablePostprocessing")
    base.genParentOverridingStoreProxy("getEnablePreprocessing")
    base.genParentOverridingStoreProxy("getEnableLinkFiles")
    base.genParentOverridingStoreProxy("getTranscodingPriority")
    base.genParentOverridingStoreProxy("getProcessPriority")
    base.genParentOverridingStoreProxy("getPreprocessCommand")
    base.genParentOverridingStoreProxy("getPostprocessCommand")
    base.genParentOverridingStoreProxy("getPreprocessTimeout")
    base.genParentOverridingStoreProxy("getPostprocessTimeout")
    base.genParentOverridingStoreProxy("getTranscodingTimeout")
    base.genParentOverridingStoreProxy("getMonitoringPeriod")

    genBaseGetter("Output")
    genBaseGetter("Link")
    genBaseGetter("Work")
    genBaseGetter("Input")
    genBaseGetter("Failed")
    genBaseGetter("Done")
    genBaseGetter("Config")
    genBaseGetter("TempRep")
    genBaseGetter("FailedRep")
    genBaseGetter("DoneRep")

    def __init__(self, custCtx, profStore, identifier=None):
        if identifier is None:
            identifier = "%s.%s" % (custCtx.identifier, profStore.identifier)
        base.BaseStoreContext.__init__(self, custCtx, profStore, identifier=identifier)
        self._variables.addVar("profileSubdir", self._getSubdir())
        self._variables.addVar("profileName", self.getName())

    def getAdminContext(self):
        return self.parent.getAdminContext()
    
    def getStoreContext(self):
        return self.parent.getStoreContext()
    
    def getCustomerContext(self):
        return self.parent

    def isBound(self):
        return False

    def _getSubdir(self):
        subdir = self.store.getSubdir()
        if subdir != None:
            subdir = fileutils.str2path(subdir)
            subdir = fileutils.ensureRelDirPath(subdir)
            return fileutils.cleanupPath(subdir)
        subdir = fileutils.str2filename(self.getName())
        return fileutils.ensureDirPath(subdir)

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
                getTempRepBase: default:/fluendo/reports/pending/ogg/
                getFailedRepBase: default:/fluendo/reports/failed/ogg/
                getDoneRepBase: default:/fluendo/reports/done/ogg/
                
                getInputDir: default:/fluendo/files/incoming/ogg/subdir/
                getFailedDir: default:/fluendo/files/failed/ogg/subdir/
                getDoneDir: default:/fluendo/files/done/ogg/subdir/
                getConfDir: default:/fluendo/configs/ogg/subdir/
                getTempRepDir: default:/fluendo/reports/pending/ogg/subdir/
                getFailedRepDir: default:/fluendo/reports/failed/ogg/subdir/
                getDoneRepDir: default:/fluendo/reports/done/ogg/subdir/
                
                getInputFile: file.avi
                getConfFile: file.avi.conf
                getTempRepFile: file.avi.rep
                getFailedRepFile: file.avi.rep
                getDoneRepFile: file.avi.rep
                
                getInputRelPath: /subdir/file.avi
                getConfRelPath: /subdir/file.avi.conf
                getTempRepRelPath: /subdir/file.avi.rep
                getFailedRepRelPath: /subdir/file.avi.rep
                getDoneRepRelPath: /subdir/file.avi.rep
                
                getInputPath: default:/fluendo/files/incoming/ogg/subdir/file.avi
                getConfPath: default:/fluendo/configs/ogg/subdir/file.avi.conf
                getTempRepPath: default:/fluendo/reports/pending/ogg/subdir/file.avi.rep
                getFailedRepPath: default:/fluendo/reports/failed/ogg/subdir/file.avi.rep
                getDoneRepPath: default:/fluendo/reports/done/ogg/subdir/file.avi.rep
    """
    
    implements(IProfileContext)
    
    genGetters("Input")
    genGetters("Failed")
    genGetters("Done")
    genGetters("Config")
    genGetters("TempRep")
    genGetters("FailedRep")
    genGetters("DoneRep")
    
    def __init__(self, custCtx, profStore, inputAbstractPath):
        postfix = inputAbstractPath.strip('/')
        identifier = "%s.%s.%s" % (custCtx.identifier,
                                   profStore.identifier, postfix)
        UnboundProfileContext.__init__(self, custCtx, profStore, identifier=identifier)
        self._variables.addFileVars(inputAbstractPath.strip('/'), "source")

    def isBound(self):
        return True

    def getTargetContextByName(self, targName):
        targStore = self.store.getTargetStoreByName(targName)
        return target.TargetContext(self, targStore)

    def getTargetContextFor(self, targStore):
        assert targStore.parent == self.store
        return target.TargetContext(self, targStore)

    def iterTargetContexts(self):
        targIter = self.store.iterTargetStores()
        return base.LazyContextIterator(self, target.TargetContext, targIter)

    def getInputRelPath(self):
        return self._variables["sourcePath"]
    
    def getFailedRelPath(self):
        return self._variables["sourcePath"]
    
    def getDoneRelPath(self):
        return self._variables["sourcePath"]
    
    def getConfigRelPath(self):
        path = self._variables.substitute(self.getConfigFileTemplate())
        path = fileutils.ensureRelPath(path)
        return fileutils.cleanupPath(path)
    
    def getTempRepRelPath(self):
        path = self._variables.substitute(self.getReportFileTemplate())
        path = fileutils.ensureRelPath(path)
        return fileutils.cleanupPath(path)

    def getFailedRepRelPath(self):
        path = self._variables.substitute(self.getReportFileTemplate())
        path = fileutils.ensureRelPath(path)
        return fileutils.cleanupPath(path)
    
    def getDoneRepRelPath(self):
        path = self._variables.substitute(self.getReportFileTemplate())
        path = fileutils.ensureRelPath(path)
        return fileutils.cleanupPath(path)
    
    def getTranscoderLabel(self):
        tmpl = self.getAdminContext().config.transcoderLabelTemplate
        return self._variables.substitute(tmpl)

    def getActivityLabel(self):
        tmpl = self.getAdminContext().config.activityLabelTemplate
        return self._variables.substitute(tmpl)
