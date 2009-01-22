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
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.context import store

class Dummy(object):
    def __init__(self, items, values):
        self._values = values
        self._items = items
    def __getitem__(self, name):
        return self._items[name]
    def __getattr__(self, attr):
        if attr.startswith("get"):
            name = attr[3].lower() + attr[4:]
            if name not in self._values:
                raise AttributeError(attr)
            return lambda : self._values[name]
        if attr.startswith("set"):
            name = attr[3].lower() + attr[4:]
            if name not in self._values:
                raise AttributeError(attr)
            return lambda val: self._values.__setitem__(name, val)
        if attr not in self._values:
            raise AttributeError(attr)
        return self._values[attr]
    def getCustomerStoreByName(self, name):
        return self._items[name]
    def getProfileStoreByName(self, name):
        return self._items[name]
    def getTargetStoreByName(self, name):
        return self._items[name]

class TestTranscoderContext(unittest.TestCase):

    def getContext(self, custName, custSubdir, profName, profSubdir,
                      targName, targSubdir, targExt):
        target = Dummy({},
                       {"identifier": targName,
                        "label": targName,
                        "name": targName,
                        "subdir": targSubdir,
                        "extension": targExt,
                        "outputDir": None,
                        "linkDir": None,
                        "outputFileTemplate":
                            adminconsts.DEFAULT_OUTPUT_MEDIA_TEMPLATE,
                        "linkFileTemplate":
                             adminconsts.DEFAULT_LINK_FILE_TEMPLATE})
        profile = Dummy({targName: target},
                        {"identifier": profName,
                         "label": profName,
                         "name": profName,
                         "subdir": profSubdir,
                         "inputDir": None,
                         "outputDir": None,
                         "failedDir": None,
                         "doneDir": None,
                         "linkDir": None,
                         "workDir": None,
                         "configDir": None,
                         "tempRepDir": None,
                         "failedRepDir": None,
                         "doneRepDir": None,
                         "configFileTemplate":
                             adminconsts.DEFAULT_CONFIG_FILE_TEMPLATE,
                         "reportFileTemplate":
                             adminconsts.DEFAULT_REPORT_FILE_TEMPLATE})
        customer = Dummy({profName: profile},
                         {"identifier": custName,
                          "label": custName,
                          "name": custName,
                          "subdir": custSubdir,
                          "inputDir": None,
                          "outputDir": None,
                          "failedDir": None,
                          "doneDir": None,
                          "linkDir": None,
                          "workDir": None,
                          "configDir": None,
                          "tempRepDir": None,
                          "failedRepDir": None,
                          "doneRepDir": None})
        return store.StoreContext(None,
                                  Dummy({custName: customer},
                                        {"identifier": "dummy",
                                         "label": "dummy"}))


    def testCustomerContext(self):

        def checkCtx(virtPath, expected):
            self.assertEqual(str(virtPath), expected)

        def checkVal(value, expected):
            self.assertEqual(value, expected)

        # Basic Checks
        storeCtx = self.getContext("Fluendo-BCN (1/2)", None, "OGG/Theora-vorbis",
                                   None, "High Quality", "high", ".ogg")
        custCtx = storeCtx.getCustomerContextByName("Fluendo-BCN (1/2)")
        checkVal(custCtx.subdir, "fluendo-bcn_(1_2)/")
        checkCtx(custCtx.inputBase, "default:/fluendo-bcn_(1_2)/files/incoming/")
        checkCtx(custCtx.failedBase, "default:/fluendo-bcn_(1_2)/files/failed/")
        checkCtx(custCtx.doneBase, "default:/fluendo-bcn_(1_2)/files/done/")
        checkCtx(custCtx.outputBase, "default:/fluendo-bcn_(1_2)/files/outgoing/")
        checkCtx(custCtx.workBase, "temp:/fluendo-bcn_(1_2)/work/")
        checkCtx(custCtx.linkBase, "default:/fluendo-bcn_(1_2)/files/links/")
        checkCtx(custCtx.configBase, "default:/fluendo-bcn_(1_2)/configs/")
        checkCtx(custCtx.tempRepBase, "default:/fluendo-bcn_(1_2)/reports/pending/")
        checkCtx(custCtx.failedRepBase, "default:/fluendo-bcn_(1_2)/reports/failed/")
        checkCtx(custCtx.doneRepBase, "default:/fluendo-bcn_(1_2)/reports/done/")

        # Empty but not None subdir checks
        storeCtx = self.getContext("Big Client Corp.", "", "OGG/Theora-vorbis",
                                   None, "High Quality", "high", ".ogg")
        custCtx = storeCtx.getCustomerContextByName("Big Client Corp.")
        checkVal(custCtx.subdir, "")
        checkCtx(custCtx.inputBase, "default:/files/incoming/")
        checkCtx(custCtx.failedBase, "default:/files/failed/")
        checkCtx(custCtx.doneBase, "default:/files/done/")
        checkCtx(custCtx.outputBase, "default:/files/outgoing/")
        checkCtx(custCtx.workBase, "temp:/work/")
        checkCtx(custCtx.linkBase, "default:/files/links/")
        checkCtx(custCtx.configBase, "default:/configs/")
        checkCtx(custCtx.tempRepBase, "default:/reports/pending/")
        checkCtx(custCtx.failedRepBase, "default:/reports/failed/")
        checkCtx(custCtx.doneRepBase, "default:/reports/done/")

        # Subdir Checks
        storeCtx = self.getContext("Big Client Corp.", "big/client", "OGG/Theora-vorbis",
                                   None, "High Quality", "high", ".ogg")
        custCtx = storeCtx.getCustomerContextByName("Big Client Corp.")
        checkVal(custCtx.subdir, "big/client/")
        checkCtx(custCtx.inputBase, "default:/big/client/files/incoming/")
        checkCtx(custCtx.failedBase, "default:/big/client/files/failed/")
        checkCtx(custCtx.doneBase, "default:/big/client/files/done/")
        checkCtx(custCtx.outputBase, "default:/big/client/files/outgoing/")
        checkCtx(custCtx.workBase, "temp:/big/client/work/")
        checkCtx(custCtx.linkBase, "default:/big/client/files/links/")
        checkCtx(custCtx.configBase, "default:/big/client/configs/")
        checkCtx(custCtx.tempRepBase, "default:/big/client/reports/pending/")
        checkCtx(custCtx.failedRepBase, "default:/big/client/reports/failed/")
        checkCtx(custCtx.doneRepBase, "default:/big/client/reports/done/")

        # More subdir Checks
        storeCtx = self.getContext("Big Client Corp.", "./big/client/.", "OGG/Theora-vorbis",
                                   None, "High Quality", "high", ".ogg")
        custCtx = storeCtx.getCustomerContextByName("Big Client Corp.")
        checkVal(custCtx.subdir, "big/client/")
        checkCtx(custCtx.inputBase, "default:/big/client/files/incoming/")
        checkCtx(custCtx.failedBase, "default:/big/client/files/failed/")
        checkCtx(custCtx.doneBase, "default:/big/client/files/done/")
        checkCtx(custCtx.outputBase, "default:/big/client/files/outgoing/")
        checkCtx(custCtx.workBase, "temp:/big/client/work/")
        checkCtx(custCtx.linkBase, "default:/big/client/files/links/")
        checkCtx(custCtx.configBase, "default:/big/client/configs/")
        checkCtx(custCtx.tempRepBase, "default:/big/client/reports/pending/")
        checkCtx(custCtx.failedRepBase, "default:/big/client/reports/failed/")
        checkCtx(custCtx.doneRepBase, "default:/big/client/reports/done/")

        # Directory override checks
        custCtx.store.setInputDir("/my/input/dir/")
        custCtx.store.setWorkDir("/my/work/dir/")
        custCtx.store.setConfigDir("/my/config/dir/")
        custCtx.store.setDoneRepDir("/my/reports/done/dir/")
        checkVal(custCtx.subdir, "big/client/")
        checkCtx(custCtx.inputBase, "default:/my/input/dir/")
        checkCtx(custCtx.failedBase, "default:/big/client/files/failed/")
        checkCtx(custCtx.doneBase, "default:/big/client/files/done/")
        checkCtx(custCtx.outputBase, "default:/big/client/files/outgoing/")
        checkCtx(custCtx.workBase, "temp:/my/work/dir/")
        checkCtx(custCtx.linkBase, "default:/big/client/files/links/")
        checkCtx(custCtx.configBase, "default:/my/config/dir/")
        checkCtx(custCtx.tempRepBase, "default:/big/client/reports/pending/")
        checkCtx(custCtx.failedRepBase, "default:/big/client/reports/failed/")
        checkCtx(custCtx.doneRepBase, "default:/my/reports/done/dir/")


    def testUnboundProfileContext(self):

        def checkCtx(virtPath, expected):
            self.assertEqual(str(virtPath), expected)

        def checkVal(value, expected):
            self.assertEqual(value, expected)

        # Basic Checks
        storeCtx = self.getContext("Fluendo", None, "OGG/Theora-vorbis",
                                   None, "High Quality", "high", ".ogg")
        custCtx = storeCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getUnboundProfileContextByName("OGG/Theora-vorbis")
        checkVal(profCtx.subdir, "ogg_theora-vorbis/")
        checkCtx(profCtx.inputBase, "default:/fluendo/files/incoming/ogg_theora-vorbis/")
        checkCtx(profCtx.failedBase, "default:/fluendo/files/failed/ogg_theora-vorbis/")
        checkCtx(profCtx.doneBase, "default:/fluendo/files/done/ogg_theora-vorbis/")
        checkCtx(profCtx.outputBase, "default:/fluendo/files/outgoing/ogg_theora-vorbis/")
        checkCtx(profCtx.workBase, "temp:/fluendo/work/ogg_theora-vorbis/")
        checkCtx(profCtx.linkBase, "default:/fluendo/files/links/ogg_theora-vorbis/")
        checkCtx(profCtx.configBase, "default:/fluendo/configs/ogg_theora-vorbis/")
        checkCtx(profCtx.tempRepBase, "default:/fluendo/reports/pending/ogg_theora-vorbis/")
        checkCtx(profCtx.failedRepBase, "default:/fluendo/reports/failed/ogg_theora-vorbis/")
        checkCtx(profCtx.doneRepBase, "default:/fluendo/reports/done/ogg_theora-vorbis/")

        # Subdir Checks
        storeCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis",
                                   "ogg/vorb", "High Quality", "high", ".ogg")
        custCtx = storeCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getUnboundProfileContextByName("OGG/Theora-vorbis")
        checkVal(profCtx.subdir, "ogg/vorb/")
        checkCtx(profCtx.inputBase, "default:/flu/one/files/incoming/ogg/vorb/")
        checkCtx(profCtx.failedBase, "default:/flu/one/files/failed/ogg/vorb/")
        checkCtx(profCtx.doneBase, "default:/flu/one/files/done/ogg/vorb/")
        checkCtx(profCtx.outputBase, "default:/flu/one/files/outgoing/ogg/vorb/")
        checkCtx(profCtx.workBase, "temp:/flu/one/work/ogg/vorb/")
        checkCtx(profCtx.linkBase, "default:/flu/one/files/links/ogg/vorb/")
        checkCtx(profCtx.configBase, "default:/flu/one/configs/ogg/vorb/")
        checkCtx(profCtx.tempRepBase, "default:/flu/one/reports/pending/ogg/vorb/")
        checkCtx(profCtx.failedRepBase, "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.doneRepBase, "default:/flu/one/reports/done/ogg/vorb/")

        # More subdir Checks
        storeCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis",
                                   "/ogg//./vorb/", "High Quality", "high", ".ogg")
        custCtx = storeCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getUnboundProfileContextByName("OGG/Theora-vorbis")
        checkVal(profCtx.subdir, "ogg/vorb/")
        checkCtx(profCtx.inputBase, "default:/flu/one/files/incoming/ogg/vorb/")
        checkCtx(profCtx.failedBase, "default:/flu/one/files/failed/ogg/vorb/")
        checkCtx(profCtx.doneBase, "default:/flu/one/files/done/ogg/vorb/")
        checkCtx(profCtx.outputBase, "default:/flu/one/files/outgoing/ogg/vorb/")
        checkCtx(profCtx.workBase, "temp:/flu/one/work/ogg/vorb/")
        checkCtx(profCtx.linkBase, "default:/flu/one/files/links/ogg/vorb/")
        checkCtx(profCtx.configBase, "default:/flu/one/configs/ogg/vorb/")
        checkCtx(profCtx.tempRepBase, "default:/flu/one/reports/pending/ogg/vorb/")
        checkCtx(profCtx.failedRepBase, "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.doneRepBase, "default:/flu/one/reports/done/ogg/vorb/")

        # Empty Subdir Checks
        storeCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis",
                                   "", "High Quality", "high", ".ogg")
        custCtx = storeCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getUnboundProfileContextByName("OGG/Theora-vorbis")
        checkVal(profCtx.subdir, "")
        checkCtx(profCtx.inputBase, "default:/flu/one/files/incoming/")
        checkCtx(profCtx.failedBase, "default:/flu/one/files/failed/")
        checkCtx(profCtx.doneBase, "default:/flu/one/files/done/")
        checkCtx(profCtx.outputBase, "default:/flu/one/files/outgoing/")
        checkCtx(profCtx.workBase, "temp:/flu/one/work/")
        checkCtx(profCtx.linkBase, "default:/flu/one/files/links/")
        checkCtx(profCtx.configBase, "default:/flu/one/configs/")
        checkCtx(profCtx.tempRepBase, "default:/flu/one/reports/pending/")
        checkCtx(profCtx.failedRepBase, "default:/flu/one/reports/failed/")
        checkCtx(profCtx.doneRepBase, "default:/flu/one/reports/done/")

        # Template Checks
        storeCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis",
                                   "ogg/vorb", "High Quality", "high", ".ogg")
        custCtx = storeCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getUnboundProfileContextByName("OGG/Theora-vorbis")
        profCtx.store.setConfigFileTemplate("%(sourceDir)sfoo/%(sourceBasename)s.conf")
        profCtx.store.setReportFileTemplate("/%(sourceDir)s/spam/%(sourceFile)s.dat")
        checkCtx(profCtx.configBase, "default:/flu/one/configs/ogg/vorb/")
        checkCtx(profCtx.tempRepBase, "default:/flu/one/reports/pending/ogg/vorb/")
        checkCtx(profCtx.failedRepBase, "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.doneRepBase, "default:/flu/one/reports/done/ogg/vorb/")

        profCtx.store.setConfigFileTemplate("%(sourceFile)s.conf")
        profCtx.store.setReportFileTemplate("%(sourceBasename)s/report.txt")
        checkCtx(profCtx.configBase, "default:/flu/one/configs/ogg/vorb/")
        checkCtx(profCtx.tempRepBase, "default:/flu/one/reports/pending/ogg/vorb/")
        checkCtx(profCtx.failedRepBase, "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.doneRepBase, "default:/flu/one/reports/done/ogg/vorb/")

        # Override Checks
        storeCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis",
                                   "ogg/vorb", "High Quality", "high", ".ogg")
        custCtx = storeCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getUnboundProfileContextByName("OGG/Theora-vorbis")
        profCtx.store.setInputDir("/override/input/")
        profCtx.store.setDoneDir("override/done")
        profCtx.store.setLinkDir("override/links/")
        profCtx.store.setConfigDir("/override/configs")
        profCtx.store.setWorkDir("/override/work/")
        checkVal(profCtx.subdir, "ogg/vorb/")
        checkCtx(profCtx.inputBase, "default:/override/input/")
        checkCtx(profCtx.failedBase, "default:/flu/one/files/failed/ogg/vorb/")
        checkCtx(profCtx.doneBase, "default:/override/done/")
        checkCtx(profCtx.outputBase, "default:/flu/one/files/outgoing/ogg/vorb/")
        checkCtx(profCtx.workBase, "temp:/override/work/")
        checkCtx(profCtx.linkBase, "default:/override/links/")
        checkCtx(profCtx.configBase, "default:/override/configs/")
        checkCtx(profCtx.tempRepBase, "default:/flu/one/reports/pending/ogg/vorb/")
        checkCtx(profCtx.failedRepBase, "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.doneRepBase, "default:/flu/one/reports/done/ogg/vorb/")


    def testProfileContext(self):

        def checkCtx(virtPath, expected):
            self.assertEqual(str(virtPath), expected)

        def checkVal(value, expected):
            self.assertEqual(value, expected)

        # Basic Checks
        storeCtx = self.getContext("Fluendo", None, "OGG/Theora-vorbis",
                                   None, "High Quality", "high", ".ogg")
        custCtx = storeCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG/Theora-vorbis", "test.file.avi")
        checkVal(profCtx.subdir, "ogg_theora-vorbis/")

        checkCtx(profCtx.inputBase, "default:/fluendo/files/incoming/ogg_theora-vorbis/")
        checkCtx(profCtx.failedBase, "default:/fluendo/files/failed/ogg_theora-vorbis/")
        checkCtx(profCtx.doneBase, "default:/fluendo/files/done/ogg_theora-vorbis/")
        checkCtx(profCtx.outputBase, "default:/fluendo/files/outgoing/ogg_theora-vorbis/")
        checkCtx(profCtx.workBase, "temp:/fluendo/work/ogg_theora-vorbis/")
        checkCtx(profCtx.linkBase, "default:/fluendo/files/links/ogg_theora-vorbis/")
        checkCtx(profCtx.configBase, "default:/fluendo/configs/ogg_theora-vorbis/")
        checkCtx(profCtx.tempRepBase, "default:/fluendo/reports/pending/ogg_theora-vorbis/")
        checkCtx(profCtx.failedRepBase, "default:/fluendo/reports/failed/ogg_theora-vorbis/")
        checkCtx(profCtx.doneRepBase, "default:/fluendo/reports/done/ogg_theora-vorbis/")

        checkCtx(profCtx.inputDir, "default:/fluendo/files/incoming/ogg_theora-vorbis/")
        checkCtx(profCtx.failedDir, "default:/fluendo/files/failed/ogg_theora-vorbis/")
        checkCtx(profCtx.doneDir, "default:/fluendo/files/done/ogg_theora-vorbis/")
        checkCtx(profCtx.configDir, "default:/fluendo/configs/ogg_theora-vorbis/")
        checkCtx(profCtx.tempRepDir, "default:/fluendo/reports/pending/ogg_theora-vorbis/")
        checkCtx(profCtx.failedRepDir, "default:/fluendo/reports/failed/ogg_theora-vorbis/")
        checkCtx(profCtx.doneRepDir, "default:/fluendo/reports/done/ogg_theora-vorbis/")

        checkVal(profCtx.inputRelPath, "test.file.avi")
        checkVal(profCtx.failedRelPath, "test.file.avi")
        checkVal(profCtx.doneRelPath, "test.file.avi")
        checkVal(profCtx.configRelPath, "test.file.avi.ini")
        checkVal(profCtx.tempRepRelPath, "test.file.avi.%(id)s.rep")
        checkVal(profCtx.failedRepRelPath, "test.file.avi.%(id)s.rep")
        checkVal(profCtx.doneRepRelPath, "test.file.avi.%(id)s.rep")

        checkVal(profCtx.inputFile, "test.file.avi")
        checkVal(profCtx.failedFile, "test.file.avi")
        checkVal(profCtx.doneFile, "test.file.avi")
        checkVal(profCtx.configFile, "test.file.avi.ini")
        checkVal(profCtx.tempRepFile, "test.file.avi.%(id)s.rep")
        checkVal(profCtx.failedRepFile, "test.file.avi.%(id)s.rep")
        checkVal(profCtx.doneRepFile, "test.file.avi.%(id)s.rep")

        checkCtx(profCtx.inputPath, "default:/fluendo/files/incoming/ogg_theora-vorbis/test.file.avi")
        checkCtx(profCtx.failedPath, "default:/fluendo/files/failed/ogg_theora-vorbis/test.file.avi")
        checkCtx(profCtx.donePath, "default:/fluendo/files/done/ogg_theora-vorbis/test.file.avi")
        checkCtx(profCtx.configPath, "default:/fluendo/configs/ogg_theora-vorbis/test.file.avi.ini")
        checkCtx(profCtx.tempRepPath, "default:/fluendo/reports/pending/ogg_theora-vorbis/test.file.avi.%(id)s.rep")
        checkCtx(profCtx.failedRepPath, "default:/fluendo/reports/failed/ogg_theora-vorbis/test.file.avi.%(id)s.rep")
        checkCtx(profCtx.doneRepPath, "default:/fluendo/reports/done/ogg_theora-vorbis/test.file.avi.%(id)s.rep")

        # Subdir Checks
        storeCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis",
                                   "ogg/vorb", "High Quality", "high", ".ogg")
        custCtx = storeCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG/Theora-vorbis", "my/sub.dir/test.file.avi")
        checkVal(profCtx.subdir, "ogg/vorb/")
        checkCtx(profCtx.inputBase, "default:/flu/one/files/incoming/ogg/vorb/")
        checkCtx(profCtx.failedBase, "default:/flu/one/files/failed/ogg/vorb/")
        checkCtx(profCtx.doneBase, "default:/flu/one/files/done/ogg/vorb/")
        checkCtx(profCtx.outputBase, "default:/flu/one/files/outgoing/ogg/vorb/")
        checkCtx(profCtx.workBase, "temp:/flu/one/work/ogg/vorb/")
        checkCtx(profCtx.linkBase, "default:/flu/one/files/links/ogg/vorb/")
        checkCtx(profCtx.configBase, "default:/flu/one/configs/ogg/vorb/")
        checkCtx(profCtx.tempRepBase, "default:/flu/one/reports/pending/ogg/vorb/")
        checkCtx(profCtx.failedRepBase, "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.doneRepBase, "default:/flu/one/reports/done/ogg/vorb/")

        checkCtx(profCtx.inputDir, "default:/flu/one/files/incoming/ogg/vorb/my/sub.dir/")
        checkCtx(profCtx.failedDir, "default:/flu/one/files/failed/ogg/vorb/my/sub.dir/")
        checkCtx(profCtx.doneDir, "default:/flu/one/files/done/ogg/vorb/my/sub.dir/")
        checkCtx(profCtx.configDir, "default:/flu/one/configs/ogg/vorb/my/sub.dir/")
        checkCtx(profCtx.tempRepDir, "default:/flu/one/reports/pending/ogg/vorb/my/sub.dir/")
        checkCtx(profCtx.failedRepDir, "default:/flu/one/reports/failed/ogg/vorb/my/sub.dir/")
        checkCtx(profCtx.doneRepDir, "default:/flu/one/reports/done/ogg/vorb/my/sub.dir/")

        checkVal(profCtx.inputRelPath, "my/sub.dir/test.file.avi")
        checkVal(profCtx.failedRelPath, "my/sub.dir/test.file.avi")
        checkVal(profCtx.doneRelPath, "my/sub.dir/test.file.avi")
        checkVal(profCtx.configRelPath, "my/sub.dir/test.file.avi.ini")
        checkVal(profCtx.tempRepRelPath, "my/sub.dir/test.file.avi.%(id)s.rep")
        checkVal(profCtx.failedRepRelPath, "my/sub.dir/test.file.avi.%(id)s.rep")
        checkVal(profCtx.doneRepRelPath, "my/sub.dir/test.file.avi.%(id)s.rep")

        checkVal(profCtx.inputFile, "test.file.avi")
        checkVal(profCtx.failedFile, "test.file.avi")
        checkVal(profCtx.doneFile, "test.file.avi")
        checkVal(profCtx.configFile, "test.file.avi.ini")
        checkVal(profCtx.tempRepFile, "test.file.avi.%(id)s.rep")
        checkVal(profCtx.failedRepFile, "test.file.avi.%(id)s.rep")
        checkVal(profCtx.doneRepFile, "test.file.avi.%(id)s.rep")

        checkCtx(profCtx.inputPath, "default:/flu/one/files/incoming/ogg/vorb/my/sub.dir/test.file.avi")
        checkCtx(profCtx.failedPath, "default:/flu/one/files/failed/ogg/vorb/my/sub.dir/test.file.avi")
        checkCtx(profCtx.donePath, "default:/flu/one/files/done/ogg/vorb/my/sub.dir/test.file.avi")
        checkCtx(profCtx.configPath, "default:/flu/one/configs/ogg/vorb/my/sub.dir/test.file.avi.ini")
        checkCtx(profCtx.tempRepPath, "default:/flu/one/reports/pending/ogg/vorb/my/sub.dir/test.file.avi.%(id)s.rep")
        checkCtx(profCtx.failedRepPath, "default:/flu/one/reports/failed/ogg/vorb/my/sub.dir/test.file.avi.%(id)s.rep")
        checkCtx(profCtx.doneRepPath, "default:/flu/one/reports/done/ogg/vorb/my/sub.dir/test.file.avi.%(id)s.rep")

        # More subdir Checks
        storeCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis",
                                   "/ogg//./vorb/", "High Quality", "high", ".ogg")
        custCtx = storeCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG/Theora-vorbis", "my/sub.dir/test.file.avi")
        checkVal(profCtx.subdir, "ogg/vorb/")
        checkCtx(profCtx.inputBase, "default:/flu/one/files/incoming/ogg/vorb/")
        checkCtx(profCtx.failedBase, "default:/flu/one/files/failed/ogg/vorb/")
        checkCtx(profCtx.doneBase, "default:/flu/one/files/done/ogg/vorb/")
        checkCtx(profCtx.outputBase, "default:/flu/one/files/outgoing/ogg/vorb/")
        checkCtx(profCtx.workBase, "temp:/flu/one/work/ogg/vorb/")
        checkCtx(profCtx.linkBase, "default:/flu/one/files/links/ogg/vorb/")
        checkCtx(profCtx.configBase, "default:/flu/one/configs/ogg/vorb/")
        checkCtx(profCtx.tempRepBase, "default:/flu/one/reports/pending/ogg/vorb/")
        checkCtx(profCtx.failedRepBase, "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.doneRepBase, "default:/flu/one/reports/done/ogg/vorb/")

        # Empty Subdir Checks
        storeCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis",
                                   "", "High Quality", "high", ".ogg")
        custCtx = storeCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG/Theora-vorbis", "my/sub.dir/test.file.avi")
        checkVal(profCtx.subdir, "")
        checkCtx(profCtx.inputBase, "default:/flu/one/files/incoming/")
        checkCtx(profCtx.failedBase, "default:/flu/one/files/failed/")
        checkCtx(profCtx.doneBase, "default:/flu/one/files/done/")
        checkCtx(profCtx.outputBase, "default:/flu/one/files/outgoing/")
        checkCtx(profCtx.workBase, "temp:/flu/one/work/")
        checkCtx(profCtx.linkBase, "default:/flu/one/files/links/")
        checkCtx(profCtx.configBase, "default:/flu/one/configs/")
        checkCtx(profCtx.tempRepBase, "default:/flu/one/reports/pending/")
        checkCtx(profCtx.failedRepBase, "default:/flu/one/reports/failed/")
        checkCtx(profCtx.doneRepBase, "default:/flu/one/reports/done/")

        checkCtx(profCtx.inputDir, "default:/flu/one/files/incoming/my/sub.dir/")
        checkCtx(profCtx.failedDir, "default:/flu/one/files/failed/my/sub.dir/")
        checkCtx(profCtx.doneDir, "default:/flu/one/files/done/my/sub.dir/")
        checkCtx(profCtx.configDir, "default:/flu/one/configs/my/sub.dir/")
        checkCtx(profCtx.tempRepDir, "default:/flu/one/reports/pending/my/sub.dir/")
        checkCtx(profCtx.failedRepDir, "default:/flu/one/reports/failed/my/sub.dir/")
        checkCtx(profCtx.doneRepDir, "default:/flu/one/reports/done/my/sub.dir/")

        checkCtx(profCtx.inputPath, "default:/flu/one/files/incoming/my/sub.dir/test.file.avi")
        checkCtx(profCtx.failedPath, "default:/flu/one/files/failed/my/sub.dir/test.file.avi")
        checkCtx(profCtx.donePath, "default:/flu/one/files/done/my/sub.dir/test.file.avi")
        checkCtx(profCtx.configPath, "default:/flu/one/configs/my/sub.dir/test.file.avi.ini")
        checkCtx(profCtx.tempRepPath, "default:/flu/one/reports/pending/my/sub.dir/test.file.avi.%(id)s.rep")
        checkCtx(profCtx.failedRepPath, "default:/flu/one/reports/failed/my/sub.dir/test.file.avi.%(id)s.rep")
        checkCtx(profCtx.doneRepPath, "default:/flu/one/reports/done/my/sub.dir/test.file.avi.%(id)s.rep")

        # Template Checks
        storeCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis",
                                   "ogg/vorb", "High Quality", "high", ".ogg")
        custCtx = storeCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG/Theora-vorbis", "my/sub.dir/test.file.avi")
        profCtx.store.setConfigFileTemplate("%(sourceDir)sfoo/%(sourceBasename)s.conf")
        profCtx.store.setReportFileTemplate("/%(sourceDir)s/spam/%(sourceFile)s.dat")
        checkCtx(profCtx.configBase, "default:/flu/one/configs/ogg/vorb/")
        checkCtx(profCtx.tempRepBase, "default:/flu/one/reports/pending/ogg/vorb/")
        checkCtx(profCtx.failedRepBase, "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.doneRepBase, "default:/flu/one/reports/done/ogg/vorb/")
        checkCtx(profCtx.configDir, "default:/flu/one/configs/ogg/vorb/my/sub.dir/foo/")
        checkCtx(profCtx.tempRepDir, "default:/flu/one/reports/pending/ogg/vorb/my/sub.dir/spam/")
        checkCtx(profCtx.failedRepDir, "default:/flu/one/reports/failed/ogg/vorb/my/sub.dir/spam/")
        checkCtx(profCtx.doneRepDir, "default:/flu/one/reports/done/ogg/vorb/my/sub.dir/spam/")
        checkVal(profCtx.configRelPath, "my/sub.dir/foo/test.file.conf")
        checkVal(profCtx.tempRepRelPath, "my/sub.dir/spam/test.file.avi.dat")
        checkVal(profCtx.failedRepRelPath, "my/sub.dir/spam/test.file.avi.dat")
        checkVal(profCtx.doneRepRelPath, "my/sub.dir/spam/test.file.avi.dat")
        checkVal(profCtx.configFile, "test.file.conf")
        checkVal(profCtx.tempRepFile, "test.file.avi.dat")
        checkVal(profCtx.failedRepFile, "test.file.avi.dat")
        checkVal(profCtx.doneRepFile, "test.file.avi.dat")
        checkCtx(profCtx.configPath, "default:/flu/one/configs/ogg/vorb/my/sub.dir/foo/test.file.conf")
        checkCtx(profCtx.tempRepPath, "default:/flu/one/reports/pending/ogg/vorb/my/sub.dir/spam/test.file.avi.dat")
        checkCtx(profCtx.failedRepPath, "default:/flu/one/reports/failed/ogg/vorb/my/sub.dir/spam/test.file.avi.dat")
        checkCtx(profCtx.doneRepPath, "default:/flu/one/reports/done/ogg/vorb/my/sub.dir/spam/test.file.avi.dat")

        profCtx.store.setConfigFileTemplate("%(sourceFile)s.conf")
        profCtx.store.setReportFileTemplate("%(sourceBasename)s/report.txt")
        checkCtx(profCtx.configBase, "default:/flu/one/configs/ogg/vorb/")
        checkCtx(profCtx.tempRepBase, "default:/flu/one/reports/pending/ogg/vorb/")
        checkCtx(profCtx.failedRepBase, "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.doneRepBase, "default:/flu/one/reports/done/ogg/vorb/")
        checkCtx(profCtx.configDir, "default:/flu/one/configs/ogg/vorb/")
        checkCtx(profCtx.tempRepDir, "default:/flu/one/reports/pending/ogg/vorb/test.file/")
        checkCtx(profCtx.failedRepDir, "default:/flu/one/reports/failed/ogg/vorb/test.file/")
        checkCtx(profCtx.doneRepDir, "default:/flu/one/reports/done/ogg/vorb/test.file/")
        checkVal(profCtx.configRelPath, "test.file.avi.conf")
        checkVal(profCtx.tempRepRelPath, "test.file/report.txt")
        checkVal(profCtx.failedRepRelPath, "test.file/report.txt")
        checkVal(profCtx.doneRepRelPath, "test.file/report.txt")
        checkVal(profCtx.configFile, "test.file.avi.conf")
        checkVal(profCtx.tempRepFile, "report.txt")
        checkVal(profCtx.failedRepFile, "report.txt")
        checkVal(profCtx.doneRepFile, "report.txt")
        checkCtx(profCtx.configPath, "default:/flu/one/configs/ogg/vorb/test.file.avi.conf")
        checkCtx(profCtx.tempRepPath, "default:/flu/one/reports/pending/ogg/vorb/test.file/report.txt")
        checkCtx(profCtx.failedRepPath, "default:/flu/one/reports/failed/ogg/vorb/test.file/report.txt")
        checkCtx(profCtx.doneRepPath, "default:/flu/one/reports/done/ogg/vorb/test.file/report.txt")


        # Override Checks
        storeCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis",
                                   "ogg/vorb", "High Quality", "high", ".ogg")
        custCtx = storeCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG/Theora-vorbis", "my/sub.dir/test.file.avi")
        profCtx.store.setInputDir("/override/input/")
        profCtx.store.setDoneDir("override/done")
        profCtx.store.setLinkDir("override/links/")
        profCtx.store.setConfigDir("/override/configs")
        profCtx.store.setWorkDir("/override/work/")
        checkVal(profCtx.subdir, "ogg/vorb/")
        checkCtx(profCtx.inputBase, "default:/override/input/")
        checkCtx(profCtx.failedBase, "default:/flu/one/files/failed/ogg/vorb/")
        checkCtx(profCtx.doneBase, "default:/override/done/")
        checkCtx(profCtx.outputBase, "default:/flu/one/files/outgoing/ogg/vorb/")
        checkCtx(profCtx.workBase, "temp:/override/work/")
        checkCtx(profCtx.linkBase, "default:/override/links/")
        checkCtx(profCtx.configBase, "default:/override/configs/")
        checkCtx(profCtx.tempRepBase, "default:/flu/one/reports/pending/ogg/vorb/")
        checkCtx(profCtx.failedRepBase, "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.doneRepBase, "default:/flu/one/reports/done/ogg/vorb/")

        checkCtx(profCtx.inputDir, "default:/override/input/my/sub.dir/")
        checkCtx(profCtx.failedDir, "default:/flu/one/files/failed/ogg/vorb/my/sub.dir/")
        checkCtx(profCtx.doneDir, "default:/override/done/my/sub.dir/")
        checkCtx(profCtx.configDir, "default:/override/configs/my/sub.dir/")
        checkCtx(profCtx.tempRepDir, "default:/flu/one/reports/pending/ogg/vorb/my/sub.dir/")
        checkCtx(profCtx.failedRepDir, "default:/flu/one/reports/failed/ogg/vorb/my/sub.dir/")
        checkCtx(profCtx.doneRepDir, "default:/flu/one/reports/done/ogg/vorb/my/sub.dir/")

        checkVal(profCtx.inputRelPath, "my/sub.dir/test.file.avi")
        checkVal(profCtx.failedRelPath, "my/sub.dir/test.file.avi")
        checkVal(profCtx.doneRelPath, "my/sub.dir/test.file.avi")
        checkVal(profCtx.configRelPath, "my/sub.dir/test.file.avi.ini")
        checkVal(profCtx.tempRepRelPath, "my/sub.dir/test.file.avi.%(id)s.rep")
        checkVal(profCtx.failedRepRelPath, "my/sub.dir/test.file.avi.%(id)s.rep")
        checkVal(profCtx.doneRepRelPath, "my/sub.dir/test.file.avi.%(id)s.rep")

        checkVal(profCtx.inputFile, "test.file.avi")
        checkVal(profCtx.failedFile, "test.file.avi")
        checkVal(profCtx.doneFile, "test.file.avi")
        checkVal(profCtx.configFile, "test.file.avi.ini")
        checkVal(profCtx.tempRepFile, "test.file.avi.%(id)s.rep")
        checkVal(profCtx.failedRepFile, "test.file.avi.%(id)s.rep")
        checkVal(profCtx.doneRepFile, "test.file.avi.%(id)s.rep")

        checkCtx(profCtx.inputPath, "default:/override/input/my/sub.dir/test.file.avi")
        checkCtx(profCtx.failedPath, "default:/flu/one/files/failed/ogg/vorb/my/sub.dir/test.file.avi")
        checkCtx(profCtx.donePath, "default:/override/done/my/sub.dir/test.file.avi")
        checkCtx(profCtx.configPath, "default:/override/configs/my/sub.dir/test.file.avi.ini")
        checkCtx(profCtx.tempRepPath, "default:/flu/one/reports/pending/ogg/vorb/my/sub.dir/test.file.avi.%(id)s.rep")
        checkCtx(profCtx.failedRepPath, "default:/flu/one/reports/failed/ogg/vorb/my/sub.dir/test.file.avi.%(id)s.rep")
        checkCtx(profCtx.doneRepPath, "default:/flu/one/reports/done/ogg/vorb/my/sub.dir/test.file.avi.%(id)s.rep")



    def testTargetContext(self):

        def checkCtx(virtPath, expected):
            self.assertEqual(str(virtPath), expected)

        def checkVal(value, expected):
            self.assertEqual(value, expected)

        storeCtx = self.getContext("Fluendo", None, "OGG",
                                   None, "High Quality", None, "ogg")
        custCtx = storeCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG", "test.file.avi")
        targCtx = profCtx.getTargetContextByName("High Quality")
        checkVal(targCtx.subdir, '')
        checkCtx(targCtx.outputDir, "default:/fluendo/files/outgoing/ogg/")
        checkCtx(targCtx.linkDir, "default:/fluendo/files/links/ogg/")
        checkVal(targCtx.outputRelPath, "test.file.avi.ogg")
        checkVal(targCtx.linkRelPath, "test.file.avi.ogg.link")
        checkVal(targCtx.outputFile, "test.file.avi.ogg")
        checkVal(targCtx.linkFile, "test.file.avi.ogg.link")
        checkCtx(targCtx.outputPath, "default:/fluendo/files/outgoing/ogg/test.file.avi.ogg")
        checkCtx(targCtx.linkPath, "default:/fluendo/files/links/ogg/test.file.avi.ogg.link")

        # Subdir checks
        storeCtx = self.getContext("Fluendo", None, "OGG",
                                   None, "High Quality", "very/high", "ogg")
        custCtx = storeCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG", "test.file.avi")
        targCtx = profCtx.getTargetContextByName("High Quality")
        checkVal(targCtx.subdir, "very/high/")
        checkCtx(targCtx.outputDir, "default:/fluendo/files/outgoing/ogg/very/high/")
        checkCtx(targCtx.linkDir, "default:/fluendo/files/links/ogg/very/high/")
        checkVal(targCtx.outputRelPath, "very/high/test.file.avi.ogg")
        checkVal(targCtx.linkRelPath, "very/high/test.file.avi.ogg.link")
        checkVal(targCtx.outputFile, "test.file.avi.ogg")
        checkVal(targCtx.linkFile, "test.file.avi.ogg.link")
        checkCtx(targCtx.outputPath, "default:/fluendo/files/outgoing/ogg/very/high/test.file.avi.ogg")
        checkCtx(targCtx.linkPath, "default:/fluendo/files/links/ogg/very/high/test.file.avi.ogg.link")

        # More subdir checks
        storeCtx = self.getContext("Fluendo", None, "OGG",
                                   None, "High Quality", "/very/./high", "ogg")
        custCtx = storeCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG", "test.file.avi")
        targCtx = profCtx.getTargetContextByName("High Quality")
        checkVal(targCtx.subdir, "very/high/")
        checkCtx(targCtx.outputDir, "default:/fluendo/files/outgoing/ogg/very/high/")
        checkCtx(targCtx.linkDir, "default:/fluendo/files/links/ogg/very/high/")
        checkVal(targCtx.outputRelPath, "very/high/test.file.avi.ogg")
        checkVal(targCtx.linkRelPath, "very/high/test.file.avi.ogg.link")
        checkVal(targCtx.outputFile, "test.file.avi.ogg")
        checkVal(targCtx.linkFile, "test.file.avi.ogg.link")
        checkCtx(targCtx.outputPath, "default:/fluendo/files/outgoing/ogg/very/high/test.file.avi.ogg")
        checkCtx(targCtx.linkPath, "default:/fluendo/files/links/ogg/very/high/test.file.avi.ogg.link")

        # Empty subdir checks
        storeCtx = self.getContext("Fluendo", None, "OGG",
                                   None, "High Quality", "", "ogg")
        custCtx = storeCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG", "test.file.avi")
        targCtx = profCtx.getTargetContextByName("High Quality")
        checkVal(targCtx.subdir, '')
        checkCtx(targCtx.outputDir, "default:/fluendo/files/outgoing/ogg/")
        checkCtx(targCtx.linkDir, "default:/fluendo/files/links/ogg/")
        checkVal(targCtx.outputRelPath, "test.file.avi.ogg")
        checkVal(targCtx.linkRelPath, "test.file.avi.ogg.link")
        checkVal(targCtx.outputFile, "test.file.avi.ogg")
        checkVal(targCtx.linkFile, "test.file.avi.ogg.link")
        checkCtx(targCtx.outputPath, "default:/fluendo/files/outgoing/ogg/test.file.avi.ogg")
        checkCtx(targCtx.linkPath, "default:/fluendo/files/links/ogg/test.file.avi.ogg.link")

        # Templates checks
        storeCtx = self.getContext("Fluendo", None, "OGG",
                                   None, "High Quality", "very/high", "ogg")
        custCtx = storeCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG", "test.file.avi")
        targCtx = profCtx.getTargetContextByName("High Quality")
        targCtx.store.setOutputFileTemplate("/%(targetDir)s/%(sourceFile)s.hq%(targetExtension)s")
        targCtx.store.setLinkFileTemplate("%(sourceBasename)s///./%(targetSubdir)sthe.link")
        checkVal(targCtx.subdir, "very/high/")
        checkCtx(targCtx.outputDir, "default:/fluendo/files/outgoing/ogg/very/high/")
        checkCtx(targCtx.linkDir, "default:/fluendo/files/links/ogg/test.file/very/high/")
        checkVal(targCtx.outputRelPath, "very/high/test.file.avi.hq.ogg")
        checkVal(targCtx.linkRelPath, "test.file/very/high/the.link")
        checkVal(targCtx.outputFile, "test.file.avi.hq.ogg")
        checkVal(targCtx.linkFile, "the.link")
        checkCtx(targCtx.outputPath, "default:/fluendo/files/outgoing/ogg/very/high/test.file.avi.hq.ogg")
        checkCtx(targCtx.linkPath, "default:/fluendo/files/links/ogg/test.file/very/high/the.link")

