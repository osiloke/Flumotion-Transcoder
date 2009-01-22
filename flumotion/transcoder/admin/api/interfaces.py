# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.inhouse.spread import mediums


class IMedium(mediums.IServerMedium):
    pass


class IIdentifiedMedium(IMedium):

    def getIdentifier(self):
        pass

    def getLabel(self):
        pass


class ITranscoderGateway(IMedium):

    def getWorkerSet(self):
        pass

    def getStore(self):
        pass

    def getScheduler(self):
        pass


class ISchedulerMedium(IMedium):
    pass


class IWorkerSetMedium(IMedium):

    def getWorkers(self):
        pass

    def getWorker(self, identifier):
        pass


class IWorkerMedium(IIdentifiedMedium):

    def getName(self):
        pass

    def getHost(self):
        pass


class IStoreMedium(IMedium):

    def getDefaults(self):
        pass

    def getCustomers(self):
        pass

    def getCustomer(self, identifier):
        pass


class ICustomerMedium(IIdentifiedMedium):

    def getProfiles(self):
        pass

    def getProfile(self, identifier):
        pass

    def getName(self):
        pass

    def getSubdir(self):
        pass

    def getInputDir(self):
        pass

    def getOutputDir(self):
        pass

    def getFailedDir(self):
        pass

    def getDoneDir(self):
        pass

    def getLinkDir(self):
        pass

    def getWorkDir(self):
        pass

    def getConfigDir(self):
        pass

    def getTempRepDir(self):
        pass

    def getFailedRepDir(self):
        pass

    def getDoneRepDir(self):
        pass

    def getCustomerPriority(self):
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

    def getAccessForceUser(self):
        pass

    def getAccessForceGroup(self):
        pass

    def getAccessForceDirMode(self):
        pass

    def getAccessForceFileMode(self):
        pass


class IProfileMedium(IIdentifiedMedium):

    def getTargets(self):
        pass

    def getTarget(self, identifier):
        pass

    def getName(self):
        pass

    def getSubdir(self):
        pass

    def getInputDir(self):
        pass

    def getOutputDir(self):
        pass

    def getFailedDir(self):
        pass

    def getDoneDir(self):
        pass

    def getLinkDir(self):
        pass

    def getWorkDir(self):
        pass

    def getConfigDir(self):
        pass

    def getTempRepDir(self):
        pass

    def getFailedRepDir(self):
        pass

    def getDoneRepDir(self):
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


class ITargetMedium(IIdentifiedMedium):

    def getConfig(self):
        pass

    def getName(self):
        pass

    def getSubdir(self):
        pass

    def getOutputDir(self):
        pass

    def getLinkDir(self):
        pass

    def getWorkDir(self):
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


class IConfigMedium(IMedium):

    def getType(self):
        pass


class IIdentityConfigMedium(IConfigMedium):
    pass


class IAudioConfigMedium(IConfigMedium):

    def getMuxer(self):
        pass

    def getAudioEncoder(self):
        pass

    def getAudioRate(self):
        pass

    def getAudioChannels(self):
        pass


class IVideoConfigMedium(IConfigMedium):

    def getMuxer(self):
        pass

    def getVideoEncoder(self):
        pass

    def getVideoWidth(self):
        pass

    def getVideoHeight(self):
        pass

    def getVideoMaxWidth(self):
        pass

    def getVideoMaxHeight(self):
        pass

    def getVideoWidthMultiple(self):
        pass

    def getVideoHeightMultiple(self):
        pass

    def getVideoPAR(self):
        pass

    def getVideoFramerate(self):
        pass

    def getVideoScaleMethod(self):
        pass


class IAudioVideoConfigMedium(IAudioConfigMedium, IVideoConfigMedium):

    def getTolerance(self):
        pass


class IThumbnailsConfigMedium(IConfigMedium):

    def getThumbsWidth(self):
        pass

    def getThumbsHeight(self):
        pass

    def getPeriodValue(self):
        pass

    def getPeriodUnit(self):
        pass

    def getMaxCount(self):
        pass

    def getEnsureOne(self):
        pass

    def getFormat(self):
        pass
