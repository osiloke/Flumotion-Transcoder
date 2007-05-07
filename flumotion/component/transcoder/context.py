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

from flumotion.transcoder.enums import TargetTypeEnum
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
        BaseContext.__init__(self, context.logger, tag)
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
        return self.config.reportTemplate % self._random
        
    def getFailedReportPath(self):
        dir = self._profile.failedReportsDir
        return os.path.join(dir, self.config.reportTemplate % self._random)

    def getDoneReportPath(self):
        dir = self._profile.doneReportsDir
        return os.path.join(dir, self.config.reportTemplate % self._random)
        
    def getInputPath(self):
        dir = self._altInputDir or self._profile.inputDir
        return os.path.join(dir, self.config.inputFile)
        
    def getDoneInputPath(self):
        dir = self._profile.doneDir
        return os.path.join(dir, self.config.inputFile)

    def getFailedInputPath(self):
        dir = self._profile.failedDir
        return os.path.join(dir, self.config.inputFile)
        
        
class TargetContext(TaskContext):
    
    _typeInfo = {TargetTypeEnum.audio:      (True, False),
                 TargetTypeEnum.video:      (False, True),
                 TargetTypeEnum.audiovideo: (True, True),
                 TargetTypeEnum.thumbnails: (False, False)}
    
    def __init__(self, context, targetIndex):
        tag = "(%s:%s:%s) " % (context.config.customer.name,
                               context.config.profile.label,
                               context.config.targets[targetIndex].label)
        reporter = context.reporter.getTargetReporter(targetIndex)
        TaskContext.__init__(self, context.logger, reporter, tag)
        self._profile = context.config.profile
        self.config = context.config.targets[targetIndex]
        self.index = targetIndex
        self._random = "%d-%04d" % (os.getpid(),
                                    int(random.random()*10000))

    def hasLinkConfig(self):
        return self._profile.linkDir and self.config.linkFile        

    def getOutputFile(self):
        return self.config.outputFile

    def getOutputWorkFile(self):
        return WORK_FILE_TEMPLATE % (self.config.outputFile, self._random)
    
    def getOutputWorkPath(self):
        return os.path.join(self._profile.workDir,
                            WORK_FILE_TEMPLATE % (self.config.outputFile , 
                                                  self._random))
        
    def getOutputPath(self):
        return os.path.join(self._profile.outputDir, 
                            self.config.outputFile)
        
    def getLinkWorkFile(self):
        if self.config.linkFile:
            return WORK_FILE_TEMPLATE % (self.config.linkFile, self._random)
        return None
    
    def getLinkWorkPath(self):
        linkDir = self._profile.linkDir
        linkFile = self.config.linkFile
        if linkDir and linkFile:
            return os.path.join(self._profile.workDir,
                                WORK_FILE_TEMPLATE % (linkFile, self._random))
        return None
    
    def getLinkPath(self):
        linkDir = self._profile.linkDir
        linkFile = self.config.linkFile
        if linkDir and linkFile:
            return os.path.join(linkDir, linkFile)
        return None
    
    def _escapeForRegex(self, s):
        s = s.replace("\\", "\\\\")
        s = s.replace(".", "\\.")
        return s
    
    def _getFileFromWork(self, path):
        workDir = self._profile.workDir
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
        outputDir = self._profile.outputDir
        return os.path.join(outputDir, outputFile)

    def getLinkFromWork(self, workPath):
        linkFile = self._getFileFromWork(workPath)
        linkDir = self._profile.linkDir
        return os.path.join(linkDir, linkFile)

    def getLinkURL(self, args):
        return "%s%s.m3u?%s" % (self.config.linkUrlPrefix,
                                urllib.quote(self.config.outputFile),
                                args)

    #Maybe it should go out of this class
    def hasAudio(self):
        return self._typeInfo[self.config.type][0]
    
    #Maybe it should go out of this class
    def hasVideo(self):
        return self._typeInfo[self.config.type][1]


class Context(TaskContext):
    
    def __init__(self, logger, config, report):        
        tag = "(%s:%s) " % (config.customer.name, 
                               config.profile.label)
        reporter = Reporter(report)
        TaskContext.__init__(self, logger, reporter, tag)
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
    
    def getTargetContext(self, targetIndex):
        return TargetContext(self, targetIndex)
    
    def getTargetContexts(self):
        return [TargetContext(self, index) 
                for index, config in enumerate(self.config.targets)
                if config != None]

    def getInputDir(self):        
        return self._altInputDir or self.config.profile.inputDir
    
    def getOutputDir(self):
        return self.config.profile.outputDir
    
    def getWorkDir(self):
        return self.config.profile.workDir
