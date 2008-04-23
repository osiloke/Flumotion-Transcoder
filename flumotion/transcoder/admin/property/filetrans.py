# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import os

from zope.interface import implements

from flumotion.common import common

from flumotion.inhouse import log, inifile, utils, fileutils

from flumotion.transcoder import constants, transconfig, virtualpath
from flumotion.transcoder.enums import TargetTypeEnum
from flumotion.transcoder.admin import admerrs
from flumotion.transcoder.admin.property import base


def createTranscodingConfigFromContext(profCtx):
    # PyChecker doesn't like dynamic attributes
    __pychecker__ = "no-objattrs"
    conf = transconfig.TranscodingConfig()
    conf.touch()
    custCtx = profCtx.getCustomerContext()
    conf.customer.name = custCtx.getLabel()
    conf.transcodingTimeout = profCtx.getTranscodingTimeout()
    conf.postProcessTimeout = profCtx.getPostprocessTimeout()
    conf.preProcessTimeout = profCtx.getPreprocessTimeout()
    conf.profile.label = profCtx.getName()
    conf.profile.inputDir = profCtx.getInputBase()
    conf.profile.outputDir = profCtx.getOutputBase()
    conf.profile.linkDir = profCtx.getLinkBase()
    conf.profile.workDir = profCtx.getWorkBase()
    conf.profile.doneDir = profCtx.getDoneBase()
    conf.profile.failedDir = profCtx.getFailedBase()
    conf.profile.tempReportsDir = profCtx.getTempRepBase()
    conf.profile.failedReportsDir = profCtx.getFailedRepBase()
    conf.profile.doneReportsDir = profCtx.getDoneRepBase()
    conf.profile.linkTemplate = profCtx.getLinkTemplate()
    conf.source.inputFile = profCtx.getInputRelPath()
    #FIXME: getFailedRepRelPath is not used
    conf.source.reportTemplate = profCtx.getDoneRepRelPath()
    conf.source.preProcess = profCtx.getPreprocessCommand()
    for targCtx in profCtx.iterTargetContexts():
        tc = transconfig.TargetConfig()
        label = targCtx.getLabel()
        conf.targets[label] = tc
        tc.label = label
        tc.outputFile = targCtx.getOutputRelPath()
        ob = targCtx.getOutputBase()
        if ob != conf.profile.outputDir:
            tc.outputDir = ob
        lb = targCtx.getLinkBase()
        if lb != conf.profile.linkDir:
            tc.linkDir = lb
        wb = targCtx.getWorkBase()
        if wb != conf.profile.workDir:
            tc.workDir = wb
        if targCtx.getEnablePostprocessing():
            tc.postProcess = targCtx.getPostprocessCommand()
        if targCtx.getEnableLinkFiles():
            targCtx.linkFile = targCtx.getLinkRelPath()
            tc.linkUrlPrefix = targCtx.getLinkURLPrefix()
        confCtx = targCtx.getConfigContext()
        tt = confCtx.getType()
        tc.type = tt
        if tt in [TargetTypeEnum.audio, TargetTypeEnum.audiovideo]:
            tc.config.audioEncoder = confCtx.getAudioEncoder()
            tc.config.audioRate = confCtx.getAudioRate()
            tc.config.audioChannels = confCtx.getAudioChannels()
            tc.config.muxer = confCtx.getMuxer()
        if tt in [TargetTypeEnum.video, TargetTypeEnum.audiovideo]:
            tc.config.videoEncoder = confCtx.getVideoEncoder()
            tc.config.videoFramerate = confCtx.getVideoFramerate()
            tc.config.videoPAR = confCtx.getVideoPAR()
            tc.config.videoWidth = confCtx.getVideoWidth()
            tc.config.videoHeight = confCtx.getVideoHeight()
            tc.config.videoMaxWidth = confCtx.getVideoMaxWidth()
            tc.config.videoMaxHeight = confCtx.getVideoMaxHeight()
            tc.config.videoWidthMultiple = confCtx.getVideoWidthMultiple()
            tc.config.videoHeightMultiple = confCtx.getVideoHeightMultiple()
            tc.config.videoScaleMethod = confCtx.getVideoScaleMethod()
            tc.config.muxer = confCtx.getMuxer()            
        if tt == TargetTypeEnum.audiovideo:
            tc.config.tolerance = confCtx.getTolerance()
        if tt == TargetTypeEnum.thumbnails:
            tc.config.periodValue = confCtx.getPeriodValue()
            tc.config.periodUnit = confCtx.getPeriodUnit()
            tc.config.maxCount = confCtx.getMaxCount()
            tc.config.thumbsWidth = confCtx.getThumbsWidth()
            tc.config.thumbsHeight = confCtx.getThumbsHeight()
            tc.config.outputFormat = confCtx.getFormat()
            tc.config.ensureOne = confCtx.getEnsureOne()
    return conf


class TranscoderProperties(base.ComponentPropertiesMixin):
    
    implements(base.IComponentProperties)
    
    @classmethod
    def createFromComponentDict(cls, workerCtx, props):
        niceLevel = props.get("nice-level", None)
        name = props.get("admin-id", "")
        configPath = virtualpath.VirtualPath(props.get("config", None))
        pathAttr = fileutils.PathAttributes.createFromComponentProperties(props)
        adminCtx = workerCtx.getAdminContext()
        adminLocal = adminCtx.getLocal()
        localPath = configPath.localize(adminLocal)
        if not os.path.exists(localPath):
            message = ("Transcoder config file not found ('%s')" % localPath)
            log.warning("%s", message)
            raise admerrs.PropertiesError(message)
        loader = inifile.IniFile()
        config = transconfig.TranscodingConfig()
        try:
            loader.loadFromFile(config, localPath)
        except Exception, e:
            message = ("Failed to load transcoder config file '%s': %s"
                       % (localPath, log.getExceptionMessage(e)))
            log.warning("%s", message)
            raise admerrs.PropertiesError(message)
        return cls(name, configPath, config, niceLevel, pathAttr)
    
    @classmethod
    def createFromContext(cls, profCtx):
        custCtx = profCtx.getCustomerContext()
        name = "%s/%s" % (custCtx.getName(), profCtx.getName())
        configPath = profCtx.getConfigPath()
        pathAttr = custCtx.getPathAttributes()
        config = createTranscodingConfigFromContext(profCtx)
        priority = profCtx.getProcessPriority()
        # for priority in [0,100] the nice level will be in  [19,0]
        # and for priority in [100-200] the nice level will be in [0,-15]
        niceLevel = (19 - (19 * min(100, max(0, priority)) / 100) 
                     - (15 * (min(200, max(100, priority)) - 100) / 100))
        return cls(name, configPath, config, niceLevel, pathAttr)

    def __init__(self, name, configPath, config, niceLevel=None, pathAttr=None):
        assert config != None
        self._name = name
        self._configPath = configPath
        self._config = config
        self._niceLevel = niceLevel
        self._pathAttr = pathAttr
        # For now only use the configPath property in the digest
        self._digest = utils.digestParameters(self._name, 
                                              self._configPath, 
                                              self._niceLevel,
                                              self._pathAttr)

    def getConfigPath(self):
        return self._configPath

    def getConfig(self):
        return self._config


    ## base.IComponentProperties Implementation ##
        
    def getDigest(self):
        return self._digest
        
    def prepare(self, workerCtx):
        adminCtx = workerCtx.getAdminContext()
        adminLocal = adminCtx.getLocal()
        localPath = self._configPath.localize(adminLocal)
        saver = inifile.IniFile()
        # Set the datetime of file creation
        self._config.touch()
        try:            
            fileutils.ensureDirExists(os.path.dirname(localPath),
                                      "transcoding config", self._pathAttr)
            saver.saveToFile(self._config, localPath)
        except Exception, e:
            message = ("Failed to save transcoder config file '%s': %s"
                       % (localPath, log.getExceptionMessage(e)))
            log.warning("%s", message)
            raise admerrs.PropertiesError(message)
        if self._pathAttr:
            self._pathAttr.apply(localPath)
        
    def asComponentProperties(self, workerContext):
        props = []
        local = workerContext.getLocal()
        props.extend(local.asComponentProperties())
        props.append(("config", str(self._configPath)))
        if self._niceLevel:
            props.append(("nice-level", self._niceLevel))
        if self._pathAttr:
            props.extend(self._pathAttr.asComponentProperties())
        props.append(("admin-id", self._name))
        props.append(("wait-acknowledge", True))
        return props

    def asLaunchArguments(self, workerContext):
        args = []
        local = workerContext.getLocal()
        args.append(utils.mkCmdArg(str(self._configPath), "config="))
        if self._niceLevel:
            args.append(utils.mkCmdArg(str(self._niceLevel), "nice-level="))
        if self._pathAttr:
            args.extend(self._pathAttr.asLaunchArguments())
        args.append("wait-acknowledge=True")
        args.extend(local.asLaunchArguments())
        return args
