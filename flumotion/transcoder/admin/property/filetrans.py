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
    conf.customer.name = custCtx.label
    conf.transcodingTimeout = profCtx.transcodingTimeout
    conf.postProcessTimeout = profCtx.postprocessTimeout
    conf.preProcessTimeout = profCtx.preprocessTimeout
    conf.profile.label = profCtx.name
    conf.profile.inputDir = profCtx.inputBase
    conf.profile.outputDir = profCtx.outputBase
    conf.profile.linkDir = profCtx.linkBase
    conf.profile.workDir = profCtx.workBase
    conf.profile.doneDir = profCtx.doneBase
    conf.profile.failedDir = profCtx.failedBase
    conf.profile.tempReportsDir = profCtx.tempRepBase
    conf.profile.failedReportsDir = profCtx.failedRepBase
    conf.profile.doneReportsDir = profCtx.doneRepBase
    conf.profile.linkTemplate = profCtx.linkTemplate
    conf.source.inputFile = profCtx.inputRelPath
    #FIXME: getFailedRepRelPath is not used
    conf.source.reportTemplate = profCtx.doneRepRelPath
    conf.source.preProcess = profCtx.preprocessCommand
    for targCtx in profCtx.iterTargetContexts():
        tc = transconfig.TargetConfig()
        label = targCtx.label
        conf.targets[label] = tc
        tc.label = label
        tc.outputFile = targCtx.outputRelPath
        ob = targCtx.outputBase
        if ob != conf.profile.outputDir:
            tc.outputDir = ob
        lb = targCtx.linkBase
        if lb != conf.profile.linkDir:
            tc.linkDir = lb
        wb = targCtx.workBase
        if wb != conf.profile.workDir:
            tc.workDir = wb
        if targCtx.enablePostprocessing:
            tc.postProcess = targCtx.postprocessCommand
        if targCtx.enableLinkFiles:
            targCtx.linkFile = targCtx.linkRelPath
            tc.linkUrlPrefix = targCtx.linkURLPrefix
        confCtx = targCtx.getConfigContext()
        tt = confCtx.type
        tc.type = tt
        if tt in [TargetTypeEnum.audio, TargetTypeEnum.audiovideo]:
            tc.config.audioEncoder = confCtx.audioEncoder
            tc.config.audioRate = confCtx.audioRate
            tc.config.audioChannels = confCtx.audioChannels
            tc.config.muxer = confCtx.muxer
        if tt in [TargetTypeEnum.video, TargetTypeEnum.audiovideo]:
            tc.config.videoEncoder = confCtx.videoEncoder
            tc.config.videoFramerate = confCtx.videoFramerate
            tc.config.videoPAR = confCtx.videoPAR
            tc.config.videoWidth = confCtx.videoWidth
            tc.config.videoHeight = confCtx.videoHeight
            tc.config.videoMaxWidth = confCtx.videoMaxWidth
            tc.config.videoMaxHeight = confCtx.videoMaxHeight
            tc.config.videoWidthMultiple = confCtx.videoWidthMultiple
            tc.config.videoHeightMultiple = confCtx.videoHeightMultiple
            tc.config.videoScaleMethod = confCtx.videoScaleMethod
            tc.config.muxer = confCtx.muxer
        if tt == TargetTypeEnum.audiovideo:
            tc.config.tolerance = confCtx.tolerance
        if tt == TargetTypeEnum.thumbnails:
            tc.config.periodValue = confCtx.periodValue
            tc.config.periodUnit = confCtx.periodUnit
            tc.config.maxCount = confCtx.maxCount
            tc.config.thumbsWidth = confCtx.thumbsWidth
            tc.config.thumbsHeight = confCtx.thumbsHeight
            tc.config.outputFormat = confCtx.format
            tc.config.ensureOne = confCtx.ensureOne
    return conf

def update_config(config, params):
    if params.has_key("cue-points"):
        config.source.cuePoints = params["cue-points"]


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
    def createFromContext(cls, profCtx, params=None):
        custCtx = profCtx.getCustomerContext()
        name = "%s/%s" % (custCtx.name, profCtx.name)
        configPath = profCtx.configPath
        pathAttr = custCtx.pathAttributes
        config = createTranscodingConfigFromContext(profCtx)
        log.debug("PARAMS %r", params)
        if params:
            update_config(config, params)
        priority = profCtx.processPriority
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
        # The .ini file is created here...
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
        if self._niceLevel is not None:
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
