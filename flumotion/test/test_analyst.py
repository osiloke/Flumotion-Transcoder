# -*- Mode: Python; test-case-name: flumotion.test.test_enum -*-
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

#from twisted.internet import gtk2reactor
#gtk2reactor.install(useGtk=False)

import os
import common
import gsttestutils
import gst
import tempfile
import random

from twisted.trial import unittest
from twisted.internet import defer

from flumotion.component.transcoder.analyst import MediaAnalyst
from flumotion.component.transcoder.analyst import MediaAnalysisTimeoutError
from flumotion.component.transcoder.analyst import MediaAnalysisUnknownTypeError
from flumotion.test import comptest

FLOAT_THRESHOLD = 0.0001
DURATION_THRESHOLD = 0.2

def _checkEqual(v1, v2):
    if not (v1 == v2):
        raise Exception("Value '%s' not equal to '%s'" % (str(v1), str(v2)))

def _toFloat(v):
    if isinstance(v, float):
        return v
    if isinstance(v, (int, long)):
        return float(v)
    if isinstance(v, (tuple, list)) and (len(v) == 2):
        return float(v[0]) / float(v[1])
    if isinstance(v, gst.Fraction):
        return float(v.num) / float(v.denom)
    raise Exception("Cannot convert to float: %s" % str(v))

def _checkFloat(f1, f2, t=FLOAT_THRESHOLD):
    if abs(_toFloat(f1) - _toFloat(f2)) > t:
        raise Exception("Float values not equals: %f != %f (%f)"
                        % (_toFloat(f1), _toFloat(f2),
                           abs(_toFloat(f1) - _toFloat(f2))))


class TestAnalyst(unittest.TestCase, gsttestutils.GstreamerUnitTestMixin):

    def tearDown(self):
        #FIXME: This shouldn't be used
        comptest.cleanup_reactor()

    def cbAnalyse(self, generator, shouldWork, analyst, timeout):
        d = analyst.analyse(generator.path, timeout)
        args = (generator,)
        if shouldWork:
            d.addCallbacks(self.cbExpectedResult, self.ebHasFailed,
                           callbackArgs=args, errbackArgs=args)
        else:
            d.addCallbacks(self.cbShouldHaveFailed, self.ebTimeoutExpected,
                           callbackArgs=args, errbackArgs=args)
        return d

    def bbRemoveTempFile(self, result, generator):
        if os.path.isfile(generator.path):
            os.remove(generator.path)
        return result

    def cbShouldHaveFailed(self, result, generator):
        raise Exception("Should have failed")

    def cbExpectedResult(self, result, generator):
        return generator

    def ebTimeoutExpected(self, failure, generator):
        if failure.check(MediaAnalysisTimeoutError):
            return generator
        return failure

    def ebHasFailed(self, failure, generator):
        raise Exception("Has failed (%s)" % str(failure))


    def testSerializedAnalysisTimeout(self):
        generator = gsttestutils.MediaGenerator(duration=10,
                                                videoCodec="theoraenc",
                                                audioCodec="vorbisenc",
                                                muxer="oggmux")
        analyst = MediaAnalyst()
        d = generator.generate()
        d.addCallback(self.cbAnalyse, True, analyst, None)
        d.addCallback(self.cbAnalyse, False, analyst, 0.0)
        d.addCallback(self.cbAnalyse, False, analyst, 0.01)
        d.addCallback(self.cbAnalyse, True, analyst, 1000.0)
        d.addBoth(self.bbRemoveTempFile, generator)
        return d

    def testParallelizedAnalysisTimeout(self):

        def generated(generator):
            defs = []
            defs.append(self.cbAnalyse(generator, True, analyst, None))
            defs.append(self.cbAnalyse(generator, False, analyst, 0.0))
            defs.append(self.cbAnalyse(generator, False, analyst, 0.01))
            defs.append(self.cbAnalyse(generator, True, analyst, 1000.0))
            d = defer.DeferredList(defs, fireOnOneCallback=False,
                                   fireOnOneErrback=True, consumeErrors=False)
            d.addBoth(self.bbRemoveTempFile, generator)
            d.addErrback(lambda f: f.value.subFailure)
            return d

        generator = gsttestutils.MediaGenerator(duration=10,
                                                videoCodec="theoraenc",
                                                audioCodec="vorbisenc",
                                                muxer="oggmux")
        analyst = MediaAnalyst()
        d = generator.generate()
        d.addCallback(generated)
        return d


class TestAnalystWithGoodFiles(unittest.TestCase, gsttestutils.GstreamerUnitTestMixin):

    def tearDown(self):
        #FIXME: This shouldn't be used
        comptest.cleanup_reactor()

    def checkMedia(self, result=None, analyst=None, timeout=None, *args, **kwargs):
        generator = gsttestutils.MediaGenerator(*args, **kwargs)
        d = generator.generate()
        d.addCallback(self.cbAnalyse, analyst, timeout, result)
        d.addBoth(self.bbRemoveTempFile, generator)
        return d

    def cbAnalyse(self, generator, analyst, timeout=None, oldResult=None):
        if not analyst:
            analyst = MediaAnalyst()
        d = analyst.analyse(generator.path, timeout)
        d.addCallback(self.cbCheckValid, generator, oldResult)
        return d

    def cbCheckValid(self, analysis, generator, oldResult):
        _checkFloat(generator.duration, analysis.getMediaDuration(),
                        DURATION_THRESHOLD)
        if generator.videoCodec:
            if not analysis.hasVideo:
                raise Exception("Video not detected")
            _checkEqual(generator.videoWidth, analysis.videoWidth)
            _checkEqual(generator.videoHeight, analysis.videoHeight)
            _checkFloat(generator.videoRate, analysis.videoRate)
        if generator.audioCodec:
            if not analysis.hasAudio:
                raise Exception("Audio not detected")
            _checkEqual(generator.audioRate, analysis.audioRate)
            _checkEqual(generator.audioChannels, analysis.audioChannels)
        return oldResult

    def bbRemoveTempFile(self, result, generator):
        if os.path.isfile(generator.path):
            os.remove(generator.path)
        return result

    def bbRemoveTempFiles(self, result, generators):
        for generator in generators:
            if os.path.isfile(generator.path):
                os.remove(generator.path)
        return result

    def multipleSerialTests(self, times, analyst, vcodec, acodec, muxer, duration,
                            width, height, par, vrate, arate, channels):
        generator = gsttestutils.MediaGenerator(duration=duration,
                                                videoCodec=vcodec,
                                                audioCodec=acodec,
                                                muxer=muxer,
                                                videoWidth=width,
                                                videoHeight=height,
                                                videoPAR=par,
                                                videoRate=vrate,
                                                audioRate=arate,
                                                audioChannels=channels)
        d = generator.generate()
        for i in range(times):
            d.addCallback(self.cbAnalyse, analyst, None, generator)
        d.addBoth(self.bbRemoveTempFile, generator)
        return d

    def multipleParallelTests(self, times, analyst, vcodec, acodec, muxer, duration,
                              width, height, par, vrate, arate, channels):

        def generated(generator, times, analyst):
            deferreds = []
            for i in range(times):
                deferreds.append(self.cbAnalyse(generator, analyst, None, generator))
            d = defer.DeferredList(deferreds, fireOnOneCallback=False,
                                   fireOnOneErrback=True, consumeErrors=False)
            d.addErrback(lambda f: f.value.subFailure)
            return d

        generator = gsttestutils.MediaGenerator(duration=duration,
                                                videoCodec=vcodec,
                                                audioCodec=acodec,
                                                muxer=muxer,
                                                videoWidth=width,
                                                videoHeight=height,
                                                videoPAR=par,
                                                videoRate=vrate,
                                                audioRate=arate,
                                                audioChannels=channels)
        d = generator.generate()
        d.addCallback(generated, times, analyst)
        d.addBoth(self.bbRemoveTempFile, generator)
        return d

    def genTestFiles(self, codecs, durations, widths, heights,
                     pars, vrates, arates, channels):
        generators = []
        for vc, ac, mux in codecs:
            for d in durations:
                for w in widths:
                    for h in heights:
                        for par in pars:
                            for vr in vrates:
                                for ar in arates:
                                    for ch in channels:
                                        gen = gsttestutils.MediaGenerator(
                                                            duration=d,
                                                            videoCodec=vc,
                                                            audioCodec=ac,
                                                            muxer=mux,
                                                            videoWidth=w,
                                                            videoHeight=h,
                                                            videoPAR=par,
                                                            videoRate=vr,
                                                            audioRate=ar,
                                                            audioChannels=ch)
                                        generators.append(gen)
        d = defer.Deferred()
        for gen in generators:
            d.addCallback(lambda r, g: g.generate(), gen)
        d.addCallback(lambda r: generators)
        d.addErrback(self.bbRemoveTempFiles, generators)
        d.callback(None)
        return d

    def serialTests(self, analyst, codecs, durations, widths, heights,
                    pars, vrates, arates, channels):

        def generated(generators, analyst):
            d = defer.Deferred()
            for gen in generators:
                d.addCallback(lambda r, g, a: self.cbAnalyse(g, a), gen, analyst)
            d.addBoth(self.bbRemoveTempFiles, generators)
            d.callback(None)
            return d

        d = self.genTestFiles(codecs, durations, widths, heights, pars,
                              vrates, arates, channels)
        d.addCallback(generated, analyst)
        return d

    def parallelTests(self, analyst, codecs, durations, widths, heights,
                      pars, vrates, arates, channels):

        def generated(generators, analyst):
            defs = []
            for gen in generators:
                defs.append(self.cbAnalyse(gen, analyst))
            d = defer.DeferredList(defs, fireOnOneCallback=False,
                                   fireOnOneErrback=True, consumeErrors=False)
            d.addBoth(self.bbRemoveTempFiles, generators)
            d.addErrback(lambda f: f.value.subFailure)
            return d

        d = self.genTestFiles(codecs, durations, widths, heights, pars,
                              vrates, arates, channels)
        d.addCallback(generated, analyst)
        return d

    def testSerializedWithDifferentAnalyst(self):
        return self.serialTests(None,
                                (("theoraenc", "vorbisenc", "oggmux"),),
                                (1, 7),
                                (104, 296),
                                (104, 296),
                                ((1, 1),),
                                (20, (25, 2)),
                                (44100,),
                                (2,))

    def testSerializedWithSameAnalyst(self):
        return self.serialTests(MediaAnalyst(),
                                (("theoraenc", "vorbisenc", "oggmux"),),
                                (1, 7),
                                (104, 296),
                                (104, 296),
                                ((1, 1),),
                                (20, (25, 2)),
                                (44100,),
                                (2,))

    def testParallelizedWithDifferentAnalyst(self):
        return self.parallelTests(None,
                                  (("theoraenc", "vorbisenc", "oggmux"),),
                                  (3, 7),
                                  (104, 296),
                                  (104, 296),
                                  ((1, 1),),
                                  ((25, 2),),
                                  (44100,),
                                  (1,))

    def testParallelizedWithSameAnalyst(self):
        return self.parallelTests(MediaAnalyst(),
                                  (("theoraenc", "vorbisenc", "oggmux"),),
                                  (3, 7),
                                  (104, 296),
                                  (104, 296),
                                  ((1, 1),),
                                  ((25, 2),),
                                  (44100,),
                                  (1,))

    def testMultipleSerialAnalysisOfTheSameFile(self):
        return self.multipleSerialTests(5, None,
                                        "theoraenc", "vorbisenc", "oggmux",
                                        4, 320, 240, (1,1), 25, 22050, 2)

    def testMultipleParallelAnalysisOfTheSameFile(self):
        return self.multipleParallelTests(5, None,
                                          "theoraenc", "vorbisenc", "oggmux",
                                          4, 320, 240, (1,1), 25, 22050, 2)

    def testMultipleSerialAnalysisOfTheSameFileOneAnlyst(self):
        return self.multipleSerialTests(5, MediaAnalyst(),
                                        "theoraenc", "vorbisenc", "oggmux",
                                        4, 320, 240, (1,1), 25, 22050, 2)

    def testMultipleParallelAnalysisOfTheSameFileOneAnlyst(self):
        return self.multipleParallelTests(5, MediaAnalyst(),
                                          "theoraenc", "vorbisenc", "oggmux",
                                          4, 320, 240, (1,1), 25, 22050, 2)


class TestAnalystWithBadFiles(unittest.TestCase, gsttestutils.GstreamerUnitTestMixin):

    def tearDown(self):
        #FIXME: This shouldn't be used
        comptest.cleanup_reactor()

    def analyse(self, path, analyst=None):

        def cbShouldFail(result):
            raise Exception("Should have failed")

        def ebExpectedFailure(failure, result):
            if failure.check(MediaAnalysisUnknownTypeError):
                return result
            return failure

        if not analyst:
            analyst = MediaAnalyst()
        d = analyst.analyse(path)
        d.addCallbacks(cbShouldFail, ebExpectedFailure,
                       errbackArgs=(path,))
        return d

    def serialTests(self, times, path, analyst=None):
        d = defer.Deferred()
        for t in range(times):
            d.addCallback(self.analyse, analyst)
        d.callback(path)
        return d

    def parallelTests(self, times, path, analyst=None):
        defs = []
        for t in range(times):
            defs.append(self.analyse(path, analyst))
        d = defer.DeferredList(defs, fireOnOneCallback=False,
                               fireOnOneErrback=True, consumeErrors=False)
        d.addErrback(lambda f: f.value.subFailure)
        return d

    def bbRemoveFile(self, result, path):
        if os.path.isfile(path):
            os.remove(path)
        return result

    def makeEmptyFile(self):
        handle, path = tempfile.mkstemp()
        os.close(handle)
        return path

    def makeGarbageFile(self, size=256*1024):
        handle, path = tempfile.mkstemp()
        try:
            r = open("/dev/urandom", "rb")
            try:
                curr = 0
                while curr < size:
                    data = r.read(min(16*1024, size - curr))
                    os.write(handle, data)
                    curr += len(data)
            finally:
                r.close()
        finally:
            os.close(handle)
        return path

    def testOneEmptyFile(self):
        path = self.makeEmptyFile()
        d = self.serialTests(1, path)
        d.addBoth(self.bbRemoveFile, path)
        return d

    def testSerialMultipleEmptyFiles(self):
        path = self.makeEmptyFile()
        d = self.serialTests(8, path)
        d.addBoth(self.bbRemoveFile, path)
        return d

    def testParallelMultipleEmptyFiles(self):
        path = self.makeEmptyFile()
        d = self.parallelTests(8, path)
        d.addBoth(self.bbRemoveFile, path)
        return d

    def testSerialMultipleEmptyFilesOneAnalyst(self):
        analyst = MediaAnalyst()
        path = self.makeEmptyFile()
        d = self.serialTests(8, path, analyst)
        d.addBoth(self.bbRemoveFile, path)
        return d

    def testParallelMultipleEmptyFilesOneAnalyst(self):
        analyst = MediaAnalyst()
        path = self.makeEmptyFile()
        d = self.parallelTests(8, path, analyst)
        d.addBoth(self.bbRemoveFile, path)
        return d

    def testOneGarbageFile(self):
        path = self.makeGarbageFile()
        d = self.serialTests(1, path)
        d.addBoth(self.bbRemoveFile, path)
        return d

    def testSerialMultipleGarbageFiles(self):
        path = self.makeGarbageFile()
        d = self.serialTests(8, path)
        d.addBoth(self.bbRemoveFile, path)
        return d

    def testParallelMultipleGarbageFiles(self):
        path = self.makeGarbageFile()
        d = self.parallelTests(8, path)
        d.addBoth(self.bbRemoveFile, path)
        return d

    def testSerialMultipleGarbageFilesOneAnalyst(self):
        analyst = MediaAnalyst()
        path = self.makeGarbageFile()
        d = self.serialTests(8, path, analyst)
        d.addBoth(self.bbRemoveFile, path)
        return d

    def testParallelMultipleGarbageFilesOneAnalyst(self):
        analyst = MediaAnalyst()
        path = self.makeGarbageFile()
        d = self.parallelTests(8, path, analyst)
        d.addBoth(self.bbRemoveFile, path)



