# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007,2008,2009 Fluendo, S.L.
# Copyright (C) 2010,2011 Flumotion Services, S.A.
# All rights reserved.
#
# This file may be distributed and/or modified under the terms of
# the GNU Lesser General Public License version 2.1 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.LGPL" in the source distribution for more information.
#
# Headers in this file shall remain intact.


import os
import shutil

from zope.interface import implements
from twisted.python.failure import Failure
from twisted.internet import threads

from flumotion.common import common
from flumotion.inhouse import log, defer, fileutils

from flumotion.transcoder.errors import TranscoderError
from flumotion.transcoder.errors import TranscoderConfigError
from flumotion.component.transcoder.transcoder import ITranscoderProducer


class BaseTarget(log.LoggerProxy):

    def __init__(self, targetContext):
        log.LoggerProxy.__init__(self, targetContext)
        self._context = targetContext
        self._outcome = None


    ## Public Methods ##

    def getContext(self):
        return self._context

    def getLabel(self):
        return self._context.getLabel()

    def getOutputFiles(self):
        return []


    ## Protected Methods ##

    def _targetFailed(self, failure):
        pass

    def _targetDone(self):
        pass


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
                result.addCallbacks(defer.dropResult, self._targetFailed,
                                    callbackArgs=(self._targetDone,))
                return result
            else:
                self._targetDone()
                return defer.succeed(self)
        except:
            f = Failure()
            self._targetFailed(f)
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
        self._targetFailed(failure)

    def onTranscodingDone(self):
        self._transcoder = None
        self._targetDone()


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
        self._outputs.append(destPath)
        d = threads.deferToThread(shutil.copy, sourcePath, destPath)
        d.addCallback(defer.overrideResult, self)
        return d

