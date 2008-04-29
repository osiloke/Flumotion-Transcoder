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
from flumotion.transcoder.admin.context import base, target, notification

#TODO: Do some value caching

class IUnboundProfileContext(base.IBaseStoreContext):

    name                 = Attribute("Name of the profile")
    subdir               = Attribute("Profile's sub-directory")
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
    
    def getCustomerContext(self):
        pass

    def isBound(self):
        pass


class IProfileContext(IUnboundProfileContext):
    
    transcoderLabel  = Attribute("Transcoding component's label")
    activityLabel    = Attribute("Transcoding activities' label")
    inputRelPath     = Attribute("Input file relative path")
    failedRelPath    = Attribute("Failed file relative path")
    doneRelPath      = Attribute("Transcoded file relative path")
    configRelPath    = Attribute("Configuration file relative path")
    tempRepRelPath   = Attribute("Temporary report relative path")
    failedRepRelPath = Attribute("Failed report relative path")
    doneRepRelPath   = Attribute("Succeed report relative path")
    inputDir         = Attribute("Input file directory")
    failedDir        = Attribute("Failed file directory")
    doneDir          = Attribute("Transcoded file directory")
    configDir        = Attribute("Transocding configuration file directory")
    tempRepDir       = Attribute("Report temporary directory")
    failedRepDir     = Attribute("Failed report directory")
    doneRepDir       = Attribute("Succeed report directory")
    inputFile        = Attribute("Input file name")
    failedFile       = Attribute("Failed file name")
    doneFile         = Attribute("Succeed file name")
    configFile       = Attribute("Transocding configuration file name")
    tempRepFile      = Attribute("Temporary report file name")
    failedRepFile    = Attribute("Failed report file name")
    doneRepFile      = Attribute("Succeed report file name")    
    inputPath        = Attribute("Input file path")
    failedPath       = Attribute("Failed file path")
    donePath         = Attribute("Transcoded file path")
    configPath       = Attribute("Transcoding configuration file path")
    tempRepPath      = Attribute("Temporary report file path")
    failedRepPath    = Attribute("Failed report file path")
    doneRepPath      = Attribute("Succeed report file path")
    
    def getTargetContextByName(self, targName):
        pass

    def getTargetContextFor(self, targStore):
        pass

    def iterTargetContexts(self):
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
        parentValue = getattr(obj.parent, self._basePropertyName)
        storeValue = getattr(obj.store, self._storePropertyName)
        if storeValue != None:
            value = obj._expandDir(storeValue)
            value = fileutils.ensureAbsDirPath(value)
            value = fileutils.cleanupPath(value)
            return virtualpath.VirtualPath(value, parentValue.getRoot())
        return parentValue.append(obj.subdir)


class FileDir(ReadOnlyProperty):
    def __init__(self, name):
        self._basePropertyName = name + "Base"
        self._relPropertyName = name + "RelPath"
    def __get__(self, obj, type=None):
        basePath = getattr(obj, self._basePropertyName)
        relPath = getattr(obj, self._relPropertyName)
        path = fileutils.splitPath(relPath)[0]
        return basePath.append(path)


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
                
                inputBase: default:/fluendo/files/incoming/ogg/
                outputBase: default:/fluendo/files/outgoing/ogg/
                failedBase: default:/fluendo/files/failed/ogg/
                doneBase: default:/fluendo/files/done/ogg/
                linkBase: default:/fluendo/files/links/ogg/
                workBase: temp:/fluendo/working/ogg/
                confBase: default:/fluendo/configs/ogg/
                tempRepBase: default:/fluendo/reports/pending/ogg/
                failedRepBase: default:/fluendo/reports/failed/ogg/
                doneRepBase: default:/fluendo/reports/done/ogg/
    """
    
    implements(IUnboundProfileContext)
    
    name                 = base.StoreProxy("name")
    outputMediaTemplate  = base.StoreParentProxy("outputMediaTemplate")
    outputThumbTemplate  = base.StoreParentProxy("outputThumbTemplate")
    linkFileTemplate     = base.StoreParentProxy("linkFileTemplate")
    configFileTemplate   = base.StoreParentProxy("configFileTemplate")
    reportFileTemplate   = base.StoreParentProxy("reportFileTemplate")
    linkTemplate         = base.StoreParentProxy("linkTemplate")
    linkURLPrefix        = base.StoreParentProxy("linkURLPrefix")
    enablePostprocessing = base.StoreParentProxy("enablePostprocessing")
    enablePreprocessing  = base.StoreParentProxy("enablePreprocessing")
    enableLinkFiles      = base.StoreParentProxy("enableLinkFiles")
    transcodingPriority  = base.StoreParentProxy("transcodingPriority")
    processPriority      = base.StoreParentProxy("processPriority")
    preprocessCommand    = base.StoreParentProxy("preprocessCommand")
    postprocessCommand   = base.StoreParentProxy("postprocessCommand")
    preprocessTimeout    = base.StoreParentProxy("preprocessTimeout")
    postprocessTimeout   = base.StoreParentProxy("postprocessTimeout")
    transcodingTimeout   = base.StoreParentProxy("transcodingTimeout")
    monitoringPeriod     = base.StoreParentProxy("monitoringPeriod")
    outputBase           = BaseDir("output")
    linkBase             = BaseDir("link")
    workBase             = BaseDir("work")
    inputBase            = BaseDir("input")
    failedBase           = BaseDir("failed")
    doneBase             = BaseDir("done")
    configBase           = BaseDir("config")
    tempRepBase          = BaseDir("tempRep")
    failedRepBase        = BaseDir("failedRep")
    doneRepBase          = BaseDir("doneRep")

    def __init__(self, custCtx, profStore, identifier=None):
        if identifier is None:
            identifier = "%s.%s" % (custCtx.identifier, profStore.identifier)
        base.BaseStoreContext.__init__(self, custCtx, profStore, identifier=identifier)
        self._variables.addVar("profileSubdir", self.subdir)
        self._variables.addVar("profileName", self.name)

    def getAdminContext(self):
        return self.parent.getAdminContext()
    
    def getStoreContext(self):
        return self.parent.getStoreContext()
    
    def getCustomerContext(self):
        return self.parent

    def isBound(self):
        return False

    @property
    def subdir(self):
        subdir = self.store.subdir
        if subdir != None:
            subdir = fileutils.str2path(subdir)
            subdir = fileutils.ensureRelDirPath(subdir)
            return fileutils.cleanupPath(subdir)
        subdir = fileutils.str2filename(self.name)
        return fileutils.ensureDirPath(subdir)


    ## Private Methodes ##

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
                
                inputBase: default:/fluendo/files/incoming/ogg/
                outputBase: default:/fluendo/files/outgoing/ogg/
                failedBase: default:/fluendo/files/failed/ogg/
                doneBase: default:/fluendo/files/done/ogg/
                linkBase: default:/fluendo/files/links/ogg/
                workBase: temp:/fluendo/working/ogg/
                confBase: default:/fluendo/configs/ogg/
                tempRepBase: default:/fluendo/reports/pending/ogg/
                failedRepBase: default:/fluendo/reports/failed/ogg/
                doneRepBase: default:/fluendo/reports/done/ogg/
                
                inputDir: default:/fluendo/files/incoming/ogg/subdir/
                failedDir: default:/fluendo/files/failed/ogg/subdir/
                doneDir: default:/fluendo/files/done/ogg/subdir/
                confDir: default:/fluendo/configs/ogg/subdir/
                tempRepDir: default:/fluendo/reports/pending/ogg/subdir/
                failedRepDir: default:/fluendo/reports/failed/ogg/subdir/
                doneRepDir: default:/fluendo/reports/done/ogg/subdir/
                
                inputFile: file.avi
                confFile: file.avi.conf
                tempRepFile: file.avi.rep
                failedRepFile: file.avi.rep
                doneRepFile: file.avi.rep
                
                inputRelPath: /subdir/file.avi
                confRelPath: /subdir/file.avi.conf
                tempRepRelPath: /subdir/file.avi.rep
                failedRepRelPath: /subdir/file.avi.rep
                doneRepRelPath: /subdir/file.avi.rep
                
                inputPath: default:/fluendo/files/incoming/ogg/subdir/file.avi
                confPath: default:/fluendo/configs/ogg/subdir/file.avi.conf
                tempRepPath: default:/fluendo/reports/pending/ogg/subdir/file.avi.rep
                failedRepPath: default:/fluendo/reports/failed/ogg/subdir/file.avi.rep
                doneRepPath: default:/fluendo/reports/done/ogg/subdir/file.avi.rep

    """
    
    implements(IProfileContext)
    
    inputDir      = FileDir("input")
    failedDir     = FileDir("failed")
    doneDir       = FileDir("done")
    configDir     = FileDir("config")
    tempRepDir    = FileDir("tempRep")
    failedRepDir  = FileDir("failedRep")
    doneRepDir    = FileDir("doneRep")
    inputFile     = FileName("input")
    failedFile    = FileName("failed")
    doneFile      = FileName("done")
    configFile    = FileName("config")
    tempRepFile   = FileName("tempRep")
    failedRepFile = FileName("failedRep")
    doneRepFile   = FileName("doneRep")    
    inputPath     = FilePath("input")
    failedPath    = FilePath("failed")
    donePath      = FilePath("done")
    configPath    = FilePath("config")
    tempRepPath   = FilePath("tempRep")
    failedRepPath = FilePath("failedRep")
    doneRepPath   = FilePath("doneRep")    
    
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

    @property
    def transcoderLabel(self):
        tmpl = self.getAdminContext().config.transcoderLabelTemplate
        return self._variables.substitute(tmpl)

    @property
    def activityLabel(self):
        tmpl = self.getAdminContext().config.activityLabelTemplate
        return self._variables.substitute(tmpl)

    @property
    def inputRelPath(self):
        return self._variables["sourcePath"]
    
    @property
    def failedRelPath(self):
        return self._variables["sourcePath"]
    
    @property
    def doneRelPath(self):
        return self._variables["sourcePath"]
    
    @property
    def configRelPath(self):
        path = self._variables.substitute(self.configFileTemplate)
        path = fileutils.ensureRelPath(path)
        return fileutils.cleanupPath(path)
    
    @property
    def tempRepRelPath(self):
        path = self._variables.substitute(self.reportFileTemplate)
        path = fileutils.ensureRelPath(path)
        return fileutils.cleanupPath(path)

    @property
    def failedRepRelPath(self):
        path = self._variables.substitute(self.reportFileTemplate)
        path = fileutils.ensureRelPath(path)
        return fileutils.cleanupPath(path)
    
    @property
    def doneRepRelPath(self):
        path = self._variables.substitute(self.reportFileTemplate)
        path = fileutils.ensureRelPath(path)
        return fileutils.cleanupPath(path)
