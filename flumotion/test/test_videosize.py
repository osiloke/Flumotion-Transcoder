# -*- Mode: Python; test-case-name: flumotion.test.test_enum -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# This file may be distributed and/or modified under the terms of
# the GNU General Public License version 2 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.GPL" in the source distribution for more information.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import common

from twisted.trial import unittest

from flumotion.transcoder.enums import VideoScaleMethodEnum
from flumotion.component.transcoder import videosize

class TestVideoSize(unittest.TestCase):

    def _format(self, w, h, par):
        if w:
            sw = "%3d" % w
        else:
            sw = "???"
        if h:
            sh = "%3d" % h
        else:
            sh = "???"
        if par:
            spar = "%d/%d" % (par[0], par[1])
        else:
            spar = "?/?"

        result = "%sx%s par=%s" % (sw, sh, spar)
        if  w != None and h != None and par != None:
            dar = videosize.getVideoDAR(w, h, par)
            result += " dar=%.4f ~ %03d/%03d" % (float(dar[0]) / float(dar[1]),
                                                 dar[0], dar[1])
        else:
            result += "                     "
        return result

    def _expect(self, iw, ih, ipar, ow, oh, opar, mw, mh, pref, ew, eh, epar):
        rw, rh, rpar = videosize.getVideoSize(iw, ih, ipar,
                                              ow, oh, opar,
                                              mw, mh, pref)
        #print "IN: %s - PREF: %s - OUT: %s" % (self._format(iw, ih, ipar),
        #                                       self._format(ow, oh, opar),
        #                                       self._format(rw, rh, rpar))
        idar = (float(iw) * ipar[0]) / (float(ih) * ipar[1])
        rdar = (float(rw) * rpar[0]) / (float(rh) * rpar[1])
        self.assertTrue(abs(idar - rdar) < 0.03, "Display Aspect Ratio Changed")
        self.assertEquals((rw, rh, rpar), (ew, eh, epar))

    def testMaxSizeWithPreferredSize(self):
        self._expect(320, 240, (1, 1),
                     200, None, (1, 1),
                     300, 200, None,
                     200, 150, (1, 1))
        self._expect(320, 240, (1, 1),
                     200, None, (1, 1),
                     150, 100, None,
                     133, 100, (1, 1))
        self._expect(320, 240, (1, 1),
                     200, None, (1, 1),
                     100, 50, None,
                     67, 50, (1, 1))

        self._expect(320, 240, (1, 1),
                     None, 180, (1, 1),
                     300, 200, None,
                     240, 180, (1, 1))
        self._expect(320, 240, (1, 1),
                     None, 180, (1, 1),
                     150, 100, None,
                     133, 100, (1, 1))
        self._expect(320, 240, (1, 1),
                     None, 180, (1, 1),
                     100, 50, None,
                     67, 50, (1, 1))

        self._expect(320, 240, (1, 1),
                     180, 180, (1, 1),
                     300, 200, None,
                     180, 135, (1, 1))
        self._expect(320, 240, (1, 1),
                     180, 180, (1, 1),
                     150, 100, None,
                     133, 100, (1, 1))
        self._expect(320, 240, (1, 1),
                     180, 180, (1, 1),
                     100, 50, None,
                     67, 50, (1, 1))


    def testMaxSizeWithoutPreferredSize(self):
        self._expect(320, 240, (1, 1),
                     None, None, (1, 1),
                     200, 300, VideoScaleMethodEnum.upscale,
                     200, 150, (1, 1))
        self._expect(320, 240, (1, 1),
                     None, None, (1, 2),
                     200, 300, VideoScaleMethodEnum.upscale,
                     200, 75, (1, 2))
        self._expect(320, 240, (1, 1),
                     None, None, (1, 3),
                     200, 300, VideoScaleMethodEnum.upscale,
                     200, 50, (1, 3))
        self._expect(320, 240, (1, 1),
                     None, None, (2, 1),
                     200, 300, VideoScaleMethodEnum.upscale,
                     200, 300, (2, 1))
        self._expect(320, 240, (1, 1),
                     None, None, (3, 1),
                     200, 300, VideoScaleMethodEnum.upscale,
                     133, 300, (3, 1))

        self._expect(320, 240, (1, 1),
                     None, None, (1, 1),
                     400, 500, VideoScaleMethodEnum.upscale,
                     320, 240, (1, 1))
        self._expect(320, 240, (1, 1),
                     None, None, (1, 2),
                     400, 500, VideoScaleMethodEnum.upscale,
                     400, 150, (1, 2))
        self._expect(320, 240, (1, 1),
                     None, None, (1, 3),
                     400, 500, VideoScaleMethodEnum.upscale,
                     400, 100, (1, 3))
        self._expect(320, 240, (1, 1),
                     None, None, (2, 1),
                     400, 500, VideoScaleMethodEnum.upscale,
                     320, 480, (2, 1))
        self._expect(320, 240, (1, 1),
                     None, None, (3, 1),
                     400, 500, VideoScaleMethodEnum.upscale,
                     222, 500, (3, 1))


    def testPreferredSize(self):
        self._expect(320, 240, (1, 1),
                     200, 200, (1, 1),
                     None, None, None,
                     200, 150, (1, 1))
        self._expect(240, 320, (1, 1),
                     200, 200, (1, 1),
                     None, None, None,
                     150, 200, (1, 1))

        self._expect(320, 240, (3, 4),
                     200, 300, (1, 2),
                     None, None, None,
                     200, 100, (1, 2))
        self._expect(320, 240, (3, 4),
                     200, 300, (1, 3),
                     None, None, None,
                     200, 67, (1, 3))
        self._expect(320, 240, (3, 4),
                     200, 300, (2, 1),
                     None, None, None,
                     150, 300, (2, 1))
        self._expect(320, 240, (3, 4),
                     200, 300, (3, 1),
                     None, None, None,
                     100, 300, (3, 1))

        self._expect(240, 320, (3, 4),
                     200, 300, (1, 2),
                     None, None, None,
                     200, 178, (1, 2))
        self._expect(240, 320, (3, 4),
                     200, 300, (1, 3),
                     None, None, None,
                     200, 119, (1, 3))
        self._expect(240, 320, (3, 4),
                     200, 300, (2, 1),
                     None, None, None,
                     84, 300, (2, 1))
        self._expect(240, 320, (3, 4),
                     200, 300, (3, 1),
                     None, None, None,
                     56, 300, (3, 1))

        self._expect(900, 900, (7, 8),
                     800, 200, (1, 1),
                     None, None, None,
                     175, 200, (1, 1))
        self._expect(900, 900, (7, 8),
                     200, 800, (1, 1),
                     None, None, None,
                     200, 229, (1, 1))

    def testPreferredHeight(self):
        self._expect(320, 240, (1, 1),
                     None, 200, (1, 1),
                     None, None, None,
                     267, 200, (1, 1))
        self._expect(240, 320, (1, 1),
                     None, 200, (1, 1),
                     None, None, None,
                     150, 200, (1, 1))

        self._expect(320, 240, (8, 7),
                     None, 200, None,
                     None, None, None,
                     267, 200, (8, 7))
        self._expect(240, 320, (8, 7),
                     None, 200, None,
                     None, None, None,
                     150, 200, (8, 7))

        self._expect(320, 240, (3, 4),
                     None, 200, (1, 1),
                     None, None, None,
                     200, 200, (1, 1))
        self._expect(320, 240, (3, 4),
                     None, 200, (1, 2),
                     None, None, None,
                     400, 200, (1, 2))
        self._expect(320, 240, (3, 4),
                     None, 200, (1, 3),
                     None, None, None,
                     600, 200, (1, 3))
        self._expect(320, 240, (3, 4),
                     None, 200, (2, 1),
                     None, None, None,
                     100, 200, (2, 1))
        self._expect(320, 240, (3, 4),
                     None, 200, (3, 1),
                     None, None, None,
                     67, 200, (3, 1))

        self._expect(240, 320, (3, 4),
                     None, 200, (1, 1),
                     None, None, None,
                     113, 200, (1, 1))
        self._expect(240, 320, (3, 4),
                     None, 200, (1, 2),
                     None, None, None,
                     225, 200, (1, 2))
        self._expect(240, 320, (3, 4),
                     None, 200, (1, 3),
                     None, None, None,
                     338, 200, (1, 3))
        self._expect(240, 320, (3, 4),
                     None, 200, (2, 1),
                     None, None, None,
                     56, 200, (2, 1))
        self._expect(240, 320, (3, 4),
                     None, 200, (3, 1),
                     None, None, None,
                     38, 200, (3, 1))

    def testPreferredWidth(self):
        self._expect(320, 240, (1, 1),
                     200, None, (1, 1),
                     None, None, None,
                     200, 150, (1, 1))
        self._expect(240, 320, (1, 1),
                     200, None, (1, 1),
                     None, None, None,
                     200, 267, (1, 1))

        self._expect(320, 240, (8, 7),
                     200, None, None,
                     None, None, None,
                     200, 150, (8, 7))
        self._expect(240, 320, (8, 7),
                     200, None, None,
                     None, None, None,
                     200, 267, (8, 7))

        self._expect(320, 240, (4, 3),
                     200, None, (1, 1),
                     None, None, None,
                     200, 113, (1, 1))
        self._expect(320, 240, (4, 3),
                     200, None, (1, 2),
                     None, None, None,
                     200, 56, (1, 2))
        self._expect(320, 240, (4, 3),
                     200, None, (1, 3),
                     None, None, None,
                     200, 38, (1, 3))
        self._expect(320, 240, (4, 3),
                     200, None, (2, 1),
                     None, None, None,
                     200, 225, (2, 1))
        self._expect(320, 240, (4, 3),
                     200, None, (3, 1),
                     None, None, None,
                     200, 338, (3, 1))

        self._expect(240, 320, (4, 3),
                     200, None, (1, 1),
                     None, None, None,
                     200, 200, (1, 1))
        self._expect(240, 320, (4, 3),
                     200, None, (1, 2),
                     None, None, None,
                     200, 100, (1, 2))
        self._expect(240, 320, (4, 3),
                     200, None, (1, 3),
                     None, None, None,
                     200, 67, (1, 3))
        self._expect(240, 320, (4, 3),
                     200, None, (2, 1),
                     None, None, None,
                     200, 400, (2, 1))
        self._expect(240, 320, (4, 3),
                     200, None, (3, 1),
                     None, None, None,
                     200, 600, (3, 1))

    def testDefaultPreferredMethod(self):
        #The default preferred method is "height"
        self._expect(320, 240, (1, 1),
                     None, None, (1, 2),
                     None, None, None,
                     640, 240, (1, 2))
        self._expect(240, 320, (1, 1),
                     None, None, (1, 2),
                     None, None, None,
                     480, 320, (1, 2))
        self._expect(320, 240, (1, 1),
                     None, None, (2, 1),
                     None, None, None,
                     160, 240, (2, 1))
        self._expect(240, 320, (1, 1),
                     None, None, (2, 1),
                     None, None, None,
                     120, 320, (2, 1))

    def testPreserveHeightMethod(self):
        self._expect(320, 240, (1, 1),
                     None, None, (1, 2),
                     None, None, VideoScaleMethodEnum.height,
                     640, 240, (1, 2))
        self._expect(320, 240, (1, 1),
                     None, None, (1, 3),
                     None, None, VideoScaleMethodEnum.height,
                     960, 240, (1, 3))
        self._expect(320, 240, (1, 1),
                     None, None, (2, 1),
                     None, None, VideoScaleMethodEnum.height,
                     160, 240, (2, 1))
        self._expect(320, 240, (1, 1),
                     None, None, (3, 1),
                     None, None, VideoScaleMethodEnum.height,
                     107, 240, (3, 1))

        self._expect(240, 320, (1, 1),
                     None, None, (1, 2),
                     None, None, VideoScaleMethodEnum.height,
                     480, 320, (1, 2))
        self._expect(240, 320, (1, 1),
                     None, None, (1, 3),
                     None, None, VideoScaleMethodEnum.height,
                     720, 320, (1, 3))
        self._expect(240, 320, (1, 1),
                     None, None, (2, 1),
                     None, None, VideoScaleMethodEnum.height,
                     120, 320, (2, 1))
        self._expect(240, 320, (1, 1),
                     None, None, (3, 1),
                     None, None, VideoScaleMethodEnum.height,
                     80, 320, (3, 1))

        self._expect(320, 240, (5, 4),
                     None, None, (1, 2),
                     None, None, VideoScaleMethodEnum.height,
                     800, 240, (1, 2))
        self._expect(320, 240, (5, 4),
                     None, None, (1, 3),
                     None, None, VideoScaleMethodEnum.height,
                     1200, 240, (1, 3))
        self._expect(320, 240, (5, 4),
                     None, None, (2, 1),
                     None, None, VideoScaleMethodEnum.height,
                     200, 240, (2, 1))
        self._expect(320, 240, (5, 4),
                     None, None, (3, 1),
                     None, None, VideoScaleMethodEnum.height,
                     133, 240, (3, 1))

        self._expect(240, 320, (5, 4),
                     None, None, (1, 2),
                     None, None, VideoScaleMethodEnum.height,
                     600, 320, (1, 2))
        self._expect(240, 320, (5, 4),
                     None, None, (1, 3),
                     None, None, VideoScaleMethodEnum.height,
                     900, 320, (1, 3))
        self._expect(240, 320, (5, 4),
                     None, None, (2, 1),
                     None, None, VideoScaleMethodEnum.height,
                     150, 320, (2, 1))
        self._expect(240, 320, (5, 4),
                     None, None, (3, 1),
                     None, None, VideoScaleMethodEnum.height,
                     100, 320, (3, 1))


    def testPreserveWidthMethod(self):
        self._expect(320, 240, (1, 1),
                     None, None, (1, 2),
                     None, None, VideoScaleMethodEnum.width,
                     320, 120, (1, 2))
        self._expect(320, 240, (1, 1),
                     None, None, (1, 3),
                     None, None, VideoScaleMethodEnum.width,
                     320, 80, (1, 3))
        self._expect(320, 240, (1, 1),
                     None, None, (2, 1),
                     None, None, VideoScaleMethodEnum.width,
                     320, 480, (2, 1))
        self._expect(320, 240, (1, 1),
                     None, None, (3, 1),
                     None, None, VideoScaleMethodEnum.width,
                     320, 720, (3, 1))

        self._expect(240, 320, (1, 1),
                     None, None, (1, 2),
                     None, None, VideoScaleMethodEnum.width,
                     240, 160, (1, 2))
        self._expect(240, 320, (1, 1),
                     None, None, (1, 3),
                     None, None, VideoScaleMethodEnum.width,
                     240, 107, (1, 3))
        self._expect(240, 320, (1, 1),
                     None, None, (2, 1),
                     None, None, VideoScaleMethodEnum.width,
                     240, 640, (2, 1))
        self._expect(240, 320, (1, 1),
                     None, None, (3, 1),
                     None, None, VideoScaleMethodEnum.width,
                     240, 960, (3, 1))

        self._expect(320, 240, (7, 8),
                     None, None, (1, 2),
                     None, None, VideoScaleMethodEnum.width,
                     320, 137, (1, 2))
        self._expect(320, 240, (7, 8),
                     None, None, (1, 3),
                     None, None, VideoScaleMethodEnum.width,
                     320, 91, (1, 3))
        self._expect(320, 240, (7, 8),
                     None, None, (2, 1),
                     None, None, VideoScaleMethodEnum.width,
                     320, 549, (2, 1))
        self._expect(320, 240, (7, 8),
                     None, None, (3, 1),
                     None, None, VideoScaleMethodEnum.width,
                     320, 823, (3, 1))

        self._expect(240, 320, (7, 8),
                     None, None, (1, 2),
                     None, None, VideoScaleMethodEnum.width,
                     240, 183, (1, 2))
        self._expect(240, 320, (7, 8),
                     None, None, (1, 3),
                     None, None, VideoScaleMethodEnum.width,
                     240, 122, (1, 3))
        self._expect(240, 320, (7, 8),
                     None, None, (2, 1),
                     None, None, VideoScaleMethodEnum.width,
                     240, 731, (2, 1))
        self._expect(240, 320, (7, 8),
                     None, None, (3, 1),
                     None, None, VideoScaleMethodEnum.width,
                     240, 1097, (3, 1))

    def testUpscaleMethod(self):
        self._expect(320, 240, (1, 1),
                     None, None, (1, 2),
                     None, None, VideoScaleMethodEnum.upscale,
                     640, 240, (1, 2))
        self._expect(320, 240, (1, 1),
                     None, None, (1, 3),
                     None, None, VideoScaleMethodEnum.upscale,
                     960, 240, (1, 3))
        self._expect(320, 240, (1, 1),
                     None, None, (2, 1),
                     None, None, VideoScaleMethodEnum.upscale,
                     320, 480, (2, 1))
        self._expect(320, 240, (1, 1),
                     None, None, (3, 1),
                     None, None, VideoScaleMethodEnum.upscale,
                     320, 720, (3, 1))

        self._expect(240, 320, (1, 1),
                     None, None, (1, 2),
                     None, None, VideoScaleMethodEnum.upscale,
                     480, 320, (1, 2))
        self._expect(240, 320, (1, 1),
                     None, None, (1, 3),
                     None, None, VideoScaleMethodEnum.upscale,
                     720, 320, (1, 3))
        self._expect(240, 320, (1, 1),
                     None, None, (2, 1),
                     None, None, VideoScaleMethodEnum.upscale,
                     240, 640, (2, 1))
        self._expect(240, 320, (1, 1),
                     None, None, (3, 1),
                     None, None, VideoScaleMethodEnum.upscale,
                     240, 960, (3, 1))

        self._expect(320, 240, (2, 3),
                     None, None, (1, 2),
                     None, None, VideoScaleMethodEnum.upscale,
                     427, 240, (1, 2))
        self._expect(320, 240, (2, 3),
                     None, None, (1, 3),
                     None, None, VideoScaleMethodEnum.upscale,
                     640, 240, (1, 3))
        self._expect(320, 240, (2, 3),
                     None, None, (2, 1),
                     None, None, VideoScaleMethodEnum.upscale,
                     320, 720, (2, 1))
        self._expect(320, 240, (2, 3),
                     None, None, (3, 1),
                     None, None, VideoScaleMethodEnum.upscale,
                     320, 1080, (3, 1))

        self._expect(240, 320, (2, 3),
                     None, None, (1, 2),
                     None, None, VideoScaleMethodEnum.upscale,
                     320, 320, (1, 2))
        self._expect(240, 320, (2, 3),
                     None, None, (1, 3),
                     None, None, VideoScaleMethodEnum.upscale,
                     480, 320, (1, 3))
        self._expect(240, 320, (2, 3),
                     None, None, (2, 1),
                     None, None, VideoScaleMethodEnum.upscale,
                     240, 960, (2, 1))
        self._expect(240, 320, (2, 3),
                     None, None, (3, 1),
                     None, None, VideoScaleMethodEnum.upscale,
                     240, 1440, (3, 1))

    def testDownscaleMethod(self):
        self._expect(320, 240, (1, 1),
                     None, None, (1, 2),
                     None, None, VideoScaleMethodEnum.downscale,
                     320, 120, (1, 2))
        self._expect(320, 240, (1, 1),
                     None, None, (1, 3),
                     None, None, VideoScaleMethodEnum.downscale,
                     320, 80, (1, 3))
        self._expect(320, 240, (1, 1),
                     None, None, (2, 1),
                     None, None, VideoScaleMethodEnum.downscale,
                     160, 240, (2, 1))
        self._expect(320, 240, (1, 1),
                     None, None, (3, 1),
                     None, None, VideoScaleMethodEnum.downscale,
                     107, 240, (3, 1))

        self._expect(240, 320, (1, 1),
                     None, None, (1, 2),
                     None, None, VideoScaleMethodEnum.downscale,
                     240, 160, (1, 2))
        self._expect(240, 320, (1, 1),
                     None, None, (1, 3),
                     None, None, VideoScaleMethodEnum.downscale,
                     240, 107, (1, 3))
        self._expect(240, 320, (1, 1),
                     None, None, (2, 1),
                     None, None, VideoScaleMethodEnum.downscale,
                     120, 320, (2, 1))
        self._expect(240, 320, (1, 1),
                     None, None, (3, 1),
                     None, None, VideoScaleMethodEnum.downscale,
                     80, 320, (3, 1))

        self._expect(320, 240, (1, 4),
                     None, None, (1, 2),
                     None, None, VideoScaleMethodEnum.downscale,
                     160, 240, (1, 2))
        self._expect(320, 240, (1, 4),
                     None, None, (1, 3),
                     None, None, VideoScaleMethodEnum.downscale,
                     240, 240, (1, 3))
        self._expect(320, 240, (1, 4),
                     None, None, (2, 1),
                     None, None, VideoScaleMethodEnum.downscale,
                     40, 240, (2, 1))
        self._expect(320, 240, (1, 4),
                     None, None, (3, 1),
                     None, None, VideoScaleMethodEnum.downscale,
                     27, 240, (3, 1))

        self._expect(240, 320, (1, 4),
                     None, None, (1, 2),
                     None, None, VideoScaleMethodEnum.downscale,
                     120, 320, (1, 2))
        self._expect(240, 320, (1, 4),
                     None, None, (1, 3),
                     None, None, VideoScaleMethodEnum.downscale,
                     180, 320, (1, 3))
        self._expect(240, 320, (1, 4),
                     None, None, (2, 1),
                     None, None, VideoScaleMethodEnum.downscale,
                     30, 320, (2, 1))
        self._expect(240, 320, (1, 4),
                     None, None, (3, 1),
                     None, None, VideoScaleMethodEnum.downscale,
                     20, 320, (3, 1))

    def testWithoutPreferredSizeAndPAR(self):
        self._expect(320, 240, (1, 1),
                     None, None, None,
                     None, None, None,
                     320, 240, (1, 1))
        self._expect(320, 240, (2, 1),
                     None, None, None,
                     None, None, None,
                     320, 240, (2, 1))
        self._expect(320, 240, (3, 1),
                     None, None, None,
                     None, None, None,
                     320, 240, (3, 1))
        self._expect(320, 240, (1, 2),
                     None, None, None,
                     None, None, None,
                     320, 240, (1, 2))
        self._expect(320, 240, (1, 3),
                     None, None, None,
                     None, None, None,
                     320, 240, (1, 3))
        self._expect(320, 100, (1, 1),
                     None, None, None,
                     None, None, None,
                     320, 100, (1, 1))
        self._expect(100, 240, (1, 1),
                     None, None, None,
                     None, None, None,
                     100, 240, (1, 1))
