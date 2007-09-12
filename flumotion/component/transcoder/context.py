# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import os
import re
import urllib
import random

from flumotion.transcoder import utils
from flumotion.transcoder.enums import TargetTypeEnum
from flumotion.transcoder.enums import AudioVideoToleranceEnum
from flumotion.transcoder.log import LoggerProxy
from flumotion.component.transcoder.reporter import Reporter


WORK_FILE_TEMPLATE = "%s.%s.tmp"
WORK_FILE_PATTERN = "(.*)\.%s\.tmp"

class BaseContext(LoggerProxy):
    
    def __init__(self, logger, tag=None):
        LoggerProxy.__init__(self, logger, context=self)
        self.tag = tag
        
    def getTag(self):
        return self.tag


class TaskContext(BaseContext):
    
    def __init__(self, logger, reporter, tag):
        BaseContext.__init__(self, logger, tag)
        self.reporter = reporter
    

class SourceContext(BaseContext):
    
    def __init__(self, context):
        tag = "(%s:%s) " % (context.config.customer.name, 
                            context.config.profile.label)
        BaseContext.__init__(self, context._logger, tag)
        self.local = context.local
        self._profile = context.config.profile
        self.config = context.config.source    
        self.reporter = context.reporter.getSourceReporter()
        self._altInputDir = None
        self._random = os.getpid()

    def setAltInputDir(self, altInputDir):
        self._altInputDir = altInputDir
    
    def getInputFile(self):
        return self.config.inputFile
    
    def getReportFile(self):
        vars = {"id": self._random}
        template = self.config.reportTemplate
        format = utils.filterFormat(template, vars)
        return format % vars
        
    def getFailedReportPath(self):
        file = self.getReportFile()
        path = self._profile.failedReportsDir.append(file)
        return path.localize(self.local)

    def getDoneReportPath(self):
        file = self.getReportFile()
        path = self._profile.doneReportsDir.append(file)
        return path.localize(self.local)
        
    def getInputPath(self):
        if self._altInputDir:
            return os.path.join(self._altInputDir, self.config.inputFile)
        path = self._profile.inputDir.append(self.config.inputFile)
        return path.localize(self.local)
        
    def getDoneInputPath(self):
        path = self._profile.doneDir.append(self.config.inputFile)
        return path.localize(self.local)

    def getFailedInputPath(self):
        path = self._profile.failedDir.append(self.config.inputFile)
        return path.localize(self.local)
        
        
class TargetContext(TaskContext):
    # {TargetTypeEnum: (HAVE_AUDIO, HAVE_VIDEO, ANALYSE, GEN_LINK)}
    _typeInfo = {TargetTypeEnum.audio:      (True,  False, True,  True),
                 TargetTypeEnum.video:      (False, True,  True,  True),
                 TargetTypeEnum.audiovideo: (True,  True,  True,  True),
                 TargetTypeEnum.thumbnails: (False, False, False, False),
                 TargetTypeEnum.identity:   (None, None,   False, True)}
    
    def __init__(self, context, targetKey):
        tag = "(%s:%s:%s) " % (context.config.customer.name,
                               context.config.profile.label,
                               context.config.targets[targetKey].label)
        reporter = context.reporter.getTargetReporter(targetKey)
        TaskContext.__init__(self, context._logger, reporter, tag)
        self.local = context.local
        self._profile = context.config.profile
        self.config = context.config.targets[targetKey]
        self.key = targetKey
        self._random = "%d-%04d" % (os.getpid(),
                                    int(random.random()*10000))

    def hasLinkConfig(self):
        return self._profile.linkDir and self.config.linkFile        

    def getOutputDir(self):
        return self.config.outputDir or self._profile.outputDir

    def getLinkDir(self):
        return self.config.linkDir or self._profile.linkDir

    def getWorkDir(self):
        return self.config.workDir or self._profile.workDir

    def getOutputFile(self):
        return self.config.outputFile

    def getOutputWorkFile(self):
        return WORK_FILE_TEMPLATE % (self.config.outputFile, self._random)
    
    def getOutputWorkPath(self):
        file = WORK_FILE_TEMPLATE % (self.config.outputFile , self._random)
        return self.getWorkDir().append(file).localize(self.local)
        
    def getOutputPath(self):
        path = self.getOutputDir().append(self.config.outputFile)
        return path.localize(self.local)
        
    def getLinkWorkFile(self):
        if self.config.linkFile:
            return WORK_FILE_TEMPLATE % (self.config.linkFile, self._random)
        return None
    
    def getLinkWorkPath(self):
        linkDir = self.getLinkDir()
        linkFile = self.config.linkFile
        if linkDir and linkFile:
            file = WORK_FILE_TEMPLATE % (linkFile, self._random)
            path = self.getWorkDir().append(file)
            return path.localize(self.local)
        return None
    
    def getLinkFile(self):
        return self.config.linkFile
    
    def getLinkPath(self):
        linkDir = self.getLinkDir()
        linkFile = self.config.linkFile
        if linkDir and linkFile:
            return linkDir.append(linkFile).localize(self.local)
        return None
    
    def _escapeForRegex(self, s):
        s = s.replace("\\", "\\\\")
        s = s.replace(".", "\\.")
        return s
    
    def _getFileFromWork(self, path):
        workDir = self.getWorkDir().localize(self.local)
        #May have more than one separator
        workDir = workDir.replace(os.sep, os.sep + "+")
        workDir = self._escapeForRegex(workDir)
        #to be sure it end by a path separator
        workDir +=  os.sep + "*"
        pattern = "^%s%s" % (workDir, WORK_FILE_PATTERN % self._random)
        regex = re.compile(pattern)
        match = regex.match(os.path.realpath(path))
        if not match:
            raise Exception("'%s' is not a temporary file" % path)
        return match.group(1)
        
    
    def getOutputFromWork(self, workPath):
        outputFile = self._getFileFromWork(workPath)
        path = self.getOutputDir().append(outputFile)
        return path.localize(self.local)

    def getLinkFromWork(self, workPath):
        linkFile = self._getFileFromWork(workPath)
        path = self.getLinkDir().append(linkFile)
        return path.localize(self.local)

    def getLinkURL(self, args):
        return "%s%s.m3u?%s" % (self.config.linkUrlPrefix,
                                urllib.quote(self.config.outputFile),
                                args)

    #Maybe it should go out of this class
    def shouldBeAnalyzed(self):
        return self._typeInfo[self.config.type][2]

    def shouldGenerateLinkFile(self):
        return self._typeInfo[self.config.type][3] and self.hasLinkConfig()

    #Maybe it should go out of this class
    def shouldHaveAudio(self):
        """
        Return True if a target must have audio,
        False if it must NOT have audio and None
        if it may have audio.
        """
        #FIXME: Avoid special casing
        if self.config.type == TargetTypeEnum.audiovideo:
            allow_without_audio = AudioVideoToleranceEnum.allow_without_audio
            tolerance = self.config.config.tolerance
            if tolerance == allow_without_audio:
                return None
            return True
        return self._typeInfo[self.config.type][0]
    
    #Maybe it should go out of this class
    def shouldHaveVideo(self):
        """
        Return True if a target must have video,
        False if it must NOT have video and None
        if it may have video.
        """
        #FIXME: Avoid special casing
        if self.config.type == TargetTypeEnum.audiovideo:
            allow_without_video = AudioVideoToleranceEnum.allow_without_video
            tolerance = self.config.config.tolerance
            if tolerance == allow_without_video:
                return None
            return True
        return self._typeInfo[self.config.type][1]


class Context(TaskContext):
    
    def __init__(self, logger, local, config, report):
        tag = "(%s:%s) " % (config.customer.name, 
                               config.profile.label)
        reporter = Reporter(local, report)
        TaskContext.__init__(self, logger, reporter, tag)
        self.local = local
        self.config = config
        self._sourceCtx = SourceContext(self)
        self._altInputDir = None
        reporter.init(self)
        
    def getTag(self):
        cust = self.config.customer.name
        prof = self.config.profile.label
        return "(%s:%s) " % (cust, prof)
        
    def setAltInputDir(self, altInputDir):
        self._altInputDir = altInputDir
        self._sourceCtx.setAltInputDir(altInputDir)
        
    def getSourceContext(self):
        return self._sourceCtx
    
    def getTargetContext(self, targetKey):
        return TargetContext(self, targetKey)
    
    def getTargetContexts(self):
        return [TargetContext(self, key) 
                for key, config in self.config.targets.items()
                if config != None]

    def getInputDir(self):        
        if self._altInputDir:
            return self._altInputDir
        return self.config.profile.inputDir.localize(self.local)
    
    def getOutputDir(self):
        return self.config.profile.outputDir.localize(self.local)
    
    def getLinkDir(self):
        return self.config.profile.linkDir.localize(self.local)
    
    def getOutputWorkDir(self):
        return self.config.profile.workDir.localize(self.local)
    
    def getLinkWorkDir(self):
        return self.config.profile.workDir.localize(self.local)

    def getDoneDir(self):
        return self.config.profile.doneDir.localize(self.local)
    
    def getFailedDir(self):
        return self.config.profile.failedDir.localize(self.local)