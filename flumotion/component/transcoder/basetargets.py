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
import shutil

from zope.interface import implements
from twisted.python.failure import Failure

from flumotion.common import common
from flumotion.transcoder import log, defer, fileutils
from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.errors import TranscoderConfigError
from flumotion.component.transcoder.transcoder import ITranscoderProducer


class BaseTarget(log.LoggerProxy):
    
    def __init__(self, targetContext):
        log.LoggerProxy.__init__(self, targetContext)
        self._context = targetContext
        self._waiters = []
        self._outcome = None


    ## Public Methods ##

    def wait(self):
        if self._outcome:
            succeed, result = self._outcome
            if succeed:
                return defer.succeed(result)
            else:
                return defer.failed(result)
        d = defer.Deferred()
        self._waiters.append(d)
        return d

    def getContext(self):
        return self._context

    def getLabel(self):
        return self._context.getLabel()

    def getOutputFiles(self):
        return []


    ## Protected Methods ##
    
    def _fireFailed(self, failure):
        self._outcome = (False, failure)
        for d in self._waiters:
            d.errback(failure)
        del self._waiters[:]

    def _fireDone(self, result=None):
        self._outcome = (True, result)
        for d in self._waiters:
            d.callback(result)
        del self._waiters[:]


class TargetProcessing(BaseTarget):

    def __init__(self, targetContext):
        BaseTarget.__init__(self, targetContext)
        self._outputs = []


    ## Public Methods ##

    def getOutputFiles(self):
        return list(self._outputs)

    def process(self):
        try:
            result = self._doProcessing()
            if defer.isDeferred(result):
                result.addCallbacks(self._fireDone, self._fireFailed)
                return result
            else:
                self._fireDone(self)
                return defer.succeed(self)
        except:
            f = Failure()
            self._fireFailed(f)
            return defer.fail(f)
        
    
    ## Protected Methods ##
    
    def _doProcessing(self):
        raise NotImplementedError()
    
        
class TranscodingTarget(BaseTarget):
    
    implements(ITranscoderProducer)
    
    def __init__(self, targetContext):
        BaseTarget.__init__(self, targetContext)
        self._bins = {}
        self._pipelineInfo = {}
        self._config = targetContext.getTranscodingConfig()
        self._outputPath = targetContext.getOutputWorkPath()
        fileutils.ensureDirExists(os.path.dirname(self._outputPath),
                                  "transcoding output")


    ## Public Methods ##

    def getPipelineInfo(self):
        return dict(self._pipelineInfo)

    def getBins(self):
        return self._bins


    ## Public Overriden Methods ##

    def getOutputFiles(self):
        return (self._getOutputPath(),)


    ## ITranscoderProducer Methods ##
    
    def raiseError(self, msg, *args):
        raise TranscoderError(msg % args, data=self.getContext())
    
    def getMonitoredFiles(self):
        return []

    def checkSourceMedia(self, sourcePath, sourceAnalysis):
        pass

    def prepare(self, timeout=None):
        return defer.succeed(self)

    def updatePipeline(self, pipeline, analysis, tees, timeout=None):
        raise NotImplementedError()

    def finalize(self, timeout=None):
        return defer.succeed(self)
    
    def abort(self, timeout=None):
        return defer.succeed(self)

    def onTranscodingFailed(self, failure):
        self._transcoder = None
        self._fireFailed(failure)
    
    def onTranscodingDone(self):
        self._transcoder = None
        self._fireDone(self)
        
    
    ## Protected Methods ##
    
    def _checkConfAttr(self, name, checkValue=False):
        if hasattr(self._config, name):
            if (not checkValue) or getattr(self._config, name):
                return
        raise TranscoderConfigError("Invalid transcoding config for target"
                                    "%s, property %s not found or invalid"
                                    % (self.getLabel(), name))

    def _getTranscodingTag(self):
        return self.getContext().getName()
    
    def _getTranscodingConfig(self):
        return self._config
    
    def _getOutputPath(self):
        return self._outputPath
    


class IdentityTarget(TargetProcessing):
    
    def __init__(self, targetContext):
        """
        This target only copy the source file to the target file.
        """
        TargetProcessing.__init__(self, targetContext)
        
    
    ## Protected Virtual Methods Overriding ##
    
    def _doProcessing(self):
        targCtx = self.getContext()
        context = targCtx.context
        srcCtx = context.getSourceContext()
        sourcePath = srcCtx.getInputPath()
        destPath = targCtx.getOutputWorkPath()
        fileutils.ensureDirExists(os.path.dirname(destPath),
                                  "identity output")
        shutil.copy(sourcePath, destPath)
        self._outputs.append(destPath)
        return self



