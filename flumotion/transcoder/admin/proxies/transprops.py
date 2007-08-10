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

from flumotion.transcoder import log, inifile, constants, utils
from flumotion.transcoder.enums import TargetTypeEnum
from flumotion.transcoder.transconfig import TranscodingConfig, TargetConfig
from flumotion.transcoder.virtualpath import VirtualPath
from flumotion.transcoder.utils import digestParameters
from flumotion.transcoder.admin.errors import PropertiesError
from flumotion.transcoder.admin.proxies.compprops import IComponentProperties
from flumotion.transcoder.admin.proxies.compprops import ComponentPropertiesMixin


def createTranscodingConfigFromContext(profileCtx):
    # PyChecker doesn't like dynamic attributes
    __pychecker__ = "no-objattrs"
    conf = TranscodingConfig()
    conf.touch()
    prof = profileCtx
    conf.customer.name = prof.customer.store.getLabel()
    conf.transcodingTimeout = prof.store.getTranscodingTimeout()
    conf.postProcessTimeout = prof.store.getPostprocessTimeout()
    conf.preProcessTimeout = prof.store.getPreprocessTimeout()
    conf.profile.label = prof.store.getName()
    conf.profile.inputDir = prof.getInputBase()
    conf.profile.outputDir = prof.getOutputBase()
    conf.profile.linkDir = prof.getLinkBase()
    conf.profile.workDir = prof.getWorkBase()
    conf.profile.doneDir = prof.getDoneBase()
    conf.profile.failedDir = prof.getFailedBase()
    conf.profile.failedReportsDir = prof.getFailedRepBase()
    conf.profile.doneReportsDir = prof.getDoneRepBase()
    conf.profile.linkTemplate = prof.store.getLinkTemplate()
    conf.source.inputFile = prof.getInputRelPath()
    #FIXME: getFailedRepRelPath is not used
    conf.source.reportTemplate = prof.getDoneRepRelPath()
    conf.source.preProcess = prof.store.getPreprocessCommand()
    for targ in prof.iterTargetContexts():
        tc = TargetConfig()
        label = targ.store.getLabel()
        conf.targets[label] = tc
        tc.label = label
        tc.outputFile = targ.getOutputRelPath()
        ob = targ.getOutputBase()
        if ob != conf.profile.outputDir:
            tc.outputDir = ob
        lb = targ.getLinkBase()
        if lb != conf.profile.linkDir:
            tc.linkDir = lb
        wb = targ.getWorkBase()
        if wb != conf.profile.workDir:
            tc.workDir = wb
        if targ.store.getEnablePostprocessing():
            tc.postProcess = targ.store.getPostprocessCommand()
        if targ.store.getEnableLinkFiles():
            tc.linkFile = targ.getLinkRelPath()
            tc.linkUrlPrefix = targ.store.getLinkURLPrefix()
        cs = targ.store.getConfig()
        tt = cs.getType()
        tc.type = tt
        if tt in [TargetTypeEnum.audio, TargetTypeEnum.audiovideo]:
            tc.config.audioEncoder = cs.getAudioEncoder()
            tc.config.audioRate = cs.getAudioRate()
            tc.config.audioChannels = cs.getAudioChannels()
            tc.config.muxer = cs.getMuxer()
        if tt in [TargetTypeEnum.video, TargetTypeEnum.audiovideo]:
            tc.config.videoEncoder = cs.getVideoEncoder()
            tc.config.videoFramerate = cs.getVideoFramerate()
            tc.config.videoPAR = cs.getVideoPAR()
            tc.config.videoWidth = cs.getVideoWidth()
            tc.config.videoHeight = cs.getVideoHeight()
            tc.config.videoMaxWidth = cs.getVideoMaxWidth()
            tc.config.videoMaxHeight = cs.getVideoMaxHeight()
            tc.config.videoWidthMultiple = cs.getVideoWidthMultiple()
            tc.config.videoHeightMultiple = cs.getVideoHeightMultiple()
            tc.config.videoScaleMethod = cs.getVideoScaleMethod()
            tc.config.muxer = cs.getMuxer()            
        if tt == TargetTypeEnum.audiovideo:
            tc.config.tolerance = cs.getTolerance()
        if tt == TargetTypeEnum.thumbnails:
            tc.config.periodValue = cs.getPeriodValue()
            tc.config.periodUnit = cs.getPeriodUnit()
            tc.config.maxCount = cs.getMaxCount()
            tc.config.thumbsWidth = cs.getThumbsWidth()
            tc.config.thumbsHeight = cs.getThumbsHeight()
            tc.config.outputFormat = cs.getFormat()
    return conf


class TranscoderProperties(ComponentPropertiesMixin):
    
    implements(IComponentProperties)
    
    @classmethod
    def createFromComponentDict(cls, workerContext, props):
        niceLevel = props.get("nice-level", None)
        name = props.get("admin-id", "")
        configPath = VirtualPath(props.get("config", None))
        
        adminLocal = workerContext.admin.getLocal()
        localPath = configPath.localize(adminLocal)
        if not os.path.exists(localPath):
            message = ("Transcoder config file '%s' not found" % localPath)
            log.warning("%s", message)
            raise PropertiesError(message)
        loader = inifile.IniFile()
        config = TranscodingConfig()
        try:
            loader.loadFromFile(config, localPath)
        except Exception, e:
            message = ("Failed to load transcoder config file '%s': %s"
                       % (localPath, log.getExceptionMessage(e)))
            log.warning("%s", message)
            raise PropertiesError(message)
        return cls(name, configPath, config, niceLevel)
    
    @classmethod
    def createFromContext(cls, profileCtx):
        prof = profileCtx
        cust = prof.customer
        name = "%s/%s" % (cust.store.getName(), prof.store.getName())
        configPath = prof.getConfigPath()
        config = createTranscodingConfigFromContext(prof)
        priority = prof.store.getProcessPriority()
        return cls(name, configPath, config, priority)

    def __init__(self, name, configPath, config, niceLevel=None):
        assert config != None
        self._name = name
        self._configPath = configPath
        self._config = config
        self._niceLevel = niceLevel
        # For now only use the configPath property in the digest
        self._digest = digestParameters(self._name, 
                                        self._configPath, 
                                        self._niceLevel)

    def getConfigPath(self):
        return self._configPath


    ## IComponentProperties Implementation ##
        
    def getDigest(self):
        return self._digest
        
    def asComponentProperties(self, workerContext):
        # First save the config file
        adminLocal = workerContext.admin.getLocal()
        localPath = self._configPath.localize(adminLocal)
        saver = inifile.IniFile()
        # Set the datetime of file creation
        self._config.touch()
        try:
            utils.ensureDirExists(os.path.dirname(localPath),
                                  "transcoding config")
            saver.saveToFile(self._config, localPath)
        except Exception, e:
            message = ("Failed to save transcoder config file '%s': %s"
                       % (localPath, log.getExceptionMessage(e)))
            log.warning("%s", message)
            raise PropertiesError(message)
        
        try:
            saver.loadFromFile(self._config, localPath)
        except Exception, e:
            message = ("Failed to load transcoder config file '%s': %s"
                       % (localPath, log.getExceptionMessage(e)))
            log.warning("%s", message)
            raise PropertiesError(message)
            
        except Exception, e:
            message = ("Failed to save transcoder config file '%s': %s"
                       % (localPath, log.getExceptionMessage(e)))
            log.warning("%s", message)
            raise PropertiesError(message)
        
        
        props = []
        local = workerContext.getLocal()
        props.extend(local.asComponentProperties())
        props.append(("config", str(self._configPath)))
        if self._niceLevel:
            props.append(("nice-level", self._niceLevel))
        props.append(("admin-id", self._name))
        props.append(("wait-acknowledge", True))
        return props
