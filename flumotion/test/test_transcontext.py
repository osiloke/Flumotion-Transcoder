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

from twisted.trial import unittest
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.context.transcontext import TranscodingContext

class Dummy(object):
    def __init__(self, items, values):
        self._values = values
        self._items = items
    def __getitem__(self, name):
        return self._items[name]
    def __getattr__(self, attr):
        if not  (attr.startswith("get") or  attr.startswith("set")):
            raise AttributeError(attr)
        name = attr[3:]
        if not  name in self._values:
            raise AttributeError(attr)
        if attr[:3] == "get":
            return lambda : self._values[name]
        return lambda val: self._values.__setitem__(name, val)
        

class TestTranscoderContext(unittest.TestCase):

    def getContext(self, custName, custSubdir, profName, profSubdir, 
                      targName, targSubdir, targExt):
        target = Dummy({}, 
                       {"Subdir": targSubdir,
                        "Extension": targExt,
                        "OutputFileTemplate": 
                            adminconsts.DEFAULT_OUTPUT_FILE_TEMPLATE,
                        "LinkFileTemplate": 
                             adminconsts.DEFAULT_LINK_FILE_TEMPLATE})
        profile = Dummy({targName: target},
                        {"Name": profName,
                         "Subdir": profSubdir,
                         "InputDir": None,
                         "OutputDir": None,
                         "FailedDir": None,
                         "DoneDir": None,
                         "LinkDir": None,
                         "WorkDir": None,
                         "ConfigDir": None,
                         "FailedRepDir": None,
                         "DoneRepDir": None,
                         "ConfigFileTemplate": 
                             adminconsts.DEFAULT_CONFIG_FILE_TEMPLATE,
                         "ReportFileTemplate": 
                             adminconsts.DEFAULT_REPORT_FILE_TEMPLATE})
        customer = Dummy({profName: profile},
                         {"Name": custName,
                          "Subdir": custSubdir,
                          "InputDir": None,
                          "OutputDir": None,
                          "FailedDir": None,
                          "DoneDir": None,
                          "LinkDir": None,
                          "WorkDir": None,
                          "ConfigDir": None,
                          "FailedRepDir": None,
                          "DoneRepDir": None})
        return TranscodingContext(Dummy({custName: customer}, {}))


    def testCustomerContext(self):

        def checkCtx(virtPath, expected):
            self.assertEqual(str(virtPath), expected)
    
        def checkVal(value, expected):
            self.assertEqual(value, expected)
        
        # Basic Checks
        transCtx = self.getContext("Fluendo-BCN (1/2)", None, "OGG/Theora-vorbis", 
                                   None, "High Quality", "high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Fluendo-BCN (1/2)")
        checkVal(custCtx.getSubdir(), "fluendo-bcn_(1_2)/")
        checkCtx(custCtx.getInputBase(), "default:/fluendo-bcn_(1_2)/files/incoming/")
        checkCtx(custCtx.getFailedBase(), "default:/fluendo-bcn_(1_2)/files/failed/")
        checkCtx(custCtx.getDoneBase(), "default:/fluendo-bcn_(1_2)/files/done/")
        checkCtx(custCtx.getOutputBase(), "default:/fluendo-bcn_(1_2)/files/outgoing/")
        checkCtx(custCtx.getWorkBase(), "temp:/fluendo-bcn_(1_2)/work/")
        checkCtx(custCtx.getLinkBase(), "default:/fluendo-bcn_(1_2)/files/links/")
        checkCtx(custCtx.getConfigBase(), "default:/fluendo-bcn_(1_2)/configs/")
        checkCtx(custCtx.getFailedRepBase(), "default:/fluendo-bcn_(1_2)/reports/failed/")
        checkCtx(custCtx.getDoneRepBase(), "default:/fluendo-bcn_(1_2)/reports/done/")

        # Empty but not None subdir checks
        transCtx = self.getContext("Big Client Corp.", "", "OGG/Theora-vorbis", 
                                   None, "High Quality", "high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Big Client Corp.")
        checkVal(custCtx.getSubdir(), "")
        checkCtx(custCtx.getInputBase(), "default:/files/incoming/")
        checkCtx(custCtx.getFailedBase(), "default:/files/failed/")
        checkCtx(custCtx.getDoneBase(), "default:/files/done/")
        checkCtx(custCtx.getOutputBase(), "default:/files/outgoing/")
        checkCtx(custCtx.getWorkBase(), "temp:/work/")
        checkCtx(custCtx.getLinkBase(), "default:/files/links/")
        checkCtx(custCtx.getConfigBase(), "default:/configs/")
        checkCtx(custCtx.getFailedRepBase(), "default:/reports/failed/")
        checkCtx(custCtx.getDoneRepBase(), "default:/reports/done/")

        # Subdir Checks
        transCtx = self.getContext("Big Client Corp.", "big/client", "OGG/Theora-vorbis", 
                                   None, "High Quality", "high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Big Client Corp.")
        checkVal(custCtx.getSubdir(), "big/client/")
        checkCtx(custCtx.getInputBase(), "default:/big/client/files/incoming/")
        checkCtx(custCtx.getFailedBase(), "default:/big/client/files/failed/")
        checkCtx(custCtx.getDoneBase(), "default:/big/client/files/done/")
        checkCtx(custCtx.getOutputBase(), "default:/big/client/files/outgoing/")
        checkCtx(custCtx.getWorkBase(), "temp:/big/client/work/")
        checkCtx(custCtx.getLinkBase(), "default:/big/client/files/links/")
        checkCtx(custCtx.getConfigBase(), "default:/big/client/configs/")
        checkCtx(custCtx.getFailedRepBase(), "default:/big/client/reports/failed/")
        checkCtx(custCtx.getDoneRepBase(), "default:/big/client/reports/done/")
        
        # More subdir Checks
        transCtx = self.getContext("Big Client Corp.", "./big/client/.", "OGG/Theora-vorbis", 
                                   None, "High Quality", "high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Big Client Corp.")
        checkVal(custCtx.getSubdir(), "big/client/")
        checkCtx(custCtx.getInputBase(), "default:/big/client/files/incoming/")
        checkCtx(custCtx.getFailedBase(), "default:/big/client/files/failed/")
        checkCtx(custCtx.getDoneBase(), "default:/big/client/files/done/")
        checkCtx(custCtx.getOutputBase(), "default:/big/client/files/outgoing/")
        checkCtx(custCtx.getWorkBase(), "temp:/big/client/work/")
        checkCtx(custCtx.getLinkBase(), "default:/big/client/files/links/")
        checkCtx(custCtx.getConfigBase(), "default:/big/client/configs/")
        checkCtx(custCtx.getFailedRepBase(), "default:/big/client/reports/failed/")
        checkCtx(custCtx.getDoneRepBase(), "default:/big/client/reports/done/")
        
        # Directory override checks
        custCtx.store.setInputDir("/my/input/dir/")
        custCtx.store.setWorkDir("/my/work/dir/")
        custCtx.store.setConfigDir("/my/config/dir/")
        custCtx.store.setDoneRepDir("/my/reports/done/dir/")
        checkVal(custCtx.getSubdir(), "big/client/")
        checkCtx(custCtx.getInputBase(), "default:/my/input/dir/")
        checkCtx(custCtx.getFailedBase(), "default:/big/client/files/failed/")
        checkCtx(custCtx.getDoneBase(), "default:/big/client/files/done/")
        checkCtx(custCtx.getOutputBase(), "default:/big/client/files/outgoing/")
        checkCtx(custCtx.getWorkBase(), "temp:/my/work/dir/")
        checkCtx(custCtx.getLinkBase(), "default:/big/client/files/links/")
        checkCtx(custCtx.getConfigBase(), "default:/my/config/dir/")
        checkCtx(custCtx.getFailedRepBase(), "default:/big/client/reports/failed/")
        checkCtx(custCtx.getDoneRepBase(), "default:/my/reports/done/dir/")


    def testUnboundProfileContext(self):

        def checkCtx(virtPath, expected):
            self.assertEqual(str(virtPath), expected)
    
        def checkVal(value, expected):
            self.assertEqual(value, expected)
        
        # Basic Checks
        transCtx = self.getContext("Fluendo", None, "OGG/Theora-vorbis", 
                                   None, "High Quality", "high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getUnboundProfileContextByName("OGG/Theora-vorbis")
        checkVal(profCtx.getSubdir(), "ogg_theora-vorbis/")
        checkCtx(profCtx.getInputBase(), "default:/fluendo/files/incoming/ogg_theora-vorbis/")
        checkCtx(profCtx.getFailedBase(), "default:/fluendo/files/failed/ogg_theora-vorbis/")
        checkCtx(profCtx.getDoneBase(), "default:/fluendo/files/done/ogg_theora-vorbis/")
        checkCtx(profCtx.getOutputBase(), "default:/fluendo/files/outgoing/ogg_theora-vorbis/")
        checkCtx(profCtx.getWorkBase(), "temp:/fluendo/work/ogg_theora-vorbis/")
        checkCtx(profCtx.getLinkBase(), "default:/fluendo/files/links/ogg_theora-vorbis/")
        checkCtx(profCtx.getConfigBase(), "default:/fluendo/configs/ogg_theora-vorbis/")
        checkCtx(profCtx.getFailedRepBase(), "default:/fluendo/reports/failed/ogg_theora-vorbis/")
        checkCtx(profCtx.getDoneRepBase(), "default:/fluendo/reports/done/ogg_theora-vorbis/")
        
        # Subdir Checks
        transCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis", 
                                   "ogg/vorb", "High Quality", "high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getUnboundProfileContextByName("OGG/Theora-vorbis")
        checkVal(profCtx.getSubdir(), "ogg/vorb/")
        checkCtx(profCtx.getInputBase(), "default:/flu/one/files/incoming/ogg/vorb/")
        checkCtx(profCtx.getFailedBase(), "default:/flu/one/files/failed/ogg/vorb/")
        checkCtx(profCtx.getDoneBase(), "default:/flu/one/files/done/ogg/vorb/")
        checkCtx(profCtx.getOutputBase(), "default:/flu/one/files/outgoing/ogg/vorb/")
        checkCtx(profCtx.getWorkBase(), "temp:/flu/one/work/ogg/vorb/")
        checkCtx(profCtx.getLinkBase(), "default:/flu/one/files/links/ogg/vorb/")
        checkCtx(profCtx.getConfigBase(), "default:/flu/one/configs/ogg/vorb/")
        checkCtx(profCtx.getFailedRepBase(), "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.getDoneRepBase(), "default:/flu/one/reports/done/ogg/vorb/")

        # More subdir Checks
        transCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis", 
                                   "/ogg//./vorb/", "High Quality", "high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getUnboundProfileContextByName("OGG/Theora-vorbis")
        checkVal(profCtx.getSubdir(), "ogg/vorb/")
        checkCtx(profCtx.getInputBase(), "default:/flu/one/files/incoming/ogg/vorb/")
        checkCtx(profCtx.getFailedBase(), "default:/flu/one/files/failed/ogg/vorb/")
        checkCtx(profCtx.getDoneBase(), "default:/flu/one/files/done/ogg/vorb/")
        checkCtx(profCtx.getOutputBase(), "default:/flu/one/files/outgoing/ogg/vorb/")
        checkCtx(profCtx.getWorkBase(), "temp:/flu/one/work/ogg/vorb/")
        checkCtx(profCtx.getLinkBase(), "default:/flu/one/files/links/ogg/vorb/")
        checkCtx(profCtx.getConfigBase(), "default:/flu/one/configs/ogg/vorb/")
        checkCtx(profCtx.getFailedRepBase(), "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.getDoneRepBase(), "default:/flu/one/reports/done/ogg/vorb/")

        # Empty Subdir Checks
        transCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis", 
                                   "", "High Quality", "high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getUnboundProfileContextByName("OGG/Theora-vorbis")
        checkVal(profCtx.getSubdir(), "")
        checkCtx(profCtx.getInputBase(), "default:/flu/one/files/incoming/")
        checkCtx(profCtx.getFailedBase(), "default:/flu/one/files/failed/")
        checkCtx(profCtx.getDoneBase(), "default:/flu/one/files/done/")
        checkCtx(profCtx.getOutputBase(), "default:/flu/one/files/outgoing/")
        checkCtx(profCtx.getWorkBase(), "temp:/flu/one/work/")
        checkCtx(profCtx.getLinkBase(), "default:/flu/one/files/links/")
        checkCtx(profCtx.getConfigBase(), "default:/flu/one/configs/")
        checkCtx(profCtx.getFailedRepBase(), "default:/flu/one/reports/failed/")
        checkCtx(profCtx.getDoneRepBase(), "default:/flu/one/reports/done/")
        
        # Template Checks
        transCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis", 
                                   "ogg/vorb", "High Quality", "high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getUnboundProfileContextByName("OGG/Theora-vorbis")
        profCtx.store.setConfigFileTemplate("%(sourceDir)sfoo/%(sourceBasename)s.conf")
        profCtx.store.setReportFileTemplate("/%(sourceDir)s/spam/%(sourceFile)s.dat")
        checkCtx(profCtx.getConfigBase(), "default:/flu/one/configs/ogg/vorb/")
        checkCtx(profCtx.getFailedRepBase(), "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.getDoneRepBase(), "default:/flu/one/reports/done/ogg/vorb/")
        
        profCtx.store.setConfigFileTemplate("%(sourceFile)s.conf")
        profCtx.store.setReportFileTemplate("%(sourceBasename)s/report.txt")
        checkCtx(profCtx.getConfigBase(), "default:/flu/one/configs/ogg/vorb/")
        checkCtx(profCtx.getFailedRepBase(), "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.getDoneRepBase(), "default:/flu/one/reports/done/ogg/vorb/")
        
        # Override Checks
        transCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis", 
                                   "ogg/vorb", "High Quality", "high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getUnboundProfileContextByName("OGG/Theora-vorbis")
        profCtx.store.setInputDir("/override/input/")
        profCtx.store.setDoneDir("override/done")
        profCtx.store.setLinkDir("override/links/")
        profCtx.store.setConfigDir("/override/configs")
        profCtx.store.setWorkDir("/override/work/")
        checkVal(profCtx.getSubdir(), "ogg/vorb/")
        checkCtx(profCtx.getInputBase(), "default:/override/input/")
        checkCtx(profCtx.getFailedBase(), "default:/flu/one/files/failed/ogg/vorb/")
        checkCtx(profCtx.getDoneBase(), "default:/override/done/")
        checkCtx(profCtx.getOutputBase(), "default:/flu/one/files/outgoing/ogg/vorb/")
        checkCtx(profCtx.getWorkBase(), "temp:/override/work/")
        checkCtx(profCtx.getLinkBase(), "default:/override/links/")
        checkCtx(profCtx.getConfigBase(), "default:/override/configs/")
        checkCtx(profCtx.getFailedRepBase(), "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.getDoneRepBase(), "default:/flu/one/reports/done/ogg/vorb/")


    def testProfileContext(self):

        def checkCtx(virtPath, expected):
            self.assertEqual(str(virtPath), expected)
    
        def checkVal(value, expected):
            self.assertEqual(value, expected)
        
        # Basic Checks
        transCtx = self.getContext("Fluendo", None, "OGG/Theora-vorbis", 
                                   None, "High Quality", "high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG/Theora-vorbis", "test.file.avi")
        checkVal(profCtx.getSubdir(), "ogg_theora-vorbis/")
        
        checkCtx(profCtx.getInputBase(), "default:/fluendo/files/incoming/ogg_theora-vorbis/")
        checkCtx(profCtx.getFailedBase(), "default:/fluendo/files/failed/ogg_theora-vorbis/")
        checkCtx(profCtx.getDoneBase(), "default:/fluendo/files/done/ogg_theora-vorbis/")
        checkCtx(profCtx.getOutputBase(), "default:/fluendo/files/outgoing/ogg_theora-vorbis/")
        checkCtx(profCtx.getWorkBase(), "temp:/fluendo/work/ogg_theora-vorbis/")
        checkCtx(profCtx.getLinkBase(), "default:/fluendo/files/links/ogg_theora-vorbis/")
        checkCtx(profCtx.getConfigBase(), "default:/fluendo/configs/ogg_theora-vorbis/")
        checkCtx(profCtx.getFailedRepBase(), "default:/fluendo/reports/failed/ogg_theora-vorbis/")
        checkCtx(profCtx.getDoneRepBase(), "default:/fluendo/reports/done/ogg_theora-vorbis/")
        
        checkCtx(profCtx.getInputDir(), "default:/fluendo/files/incoming/ogg_theora-vorbis/")
        checkCtx(profCtx.getFailedDir(), "default:/fluendo/files/failed/ogg_theora-vorbis/")
        checkCtx(profCtx.getDoneDir(), "default:/fluendo/files/done/ogg_theora-vorbis/")
        checkCtx(profCtx.getConfigDir(), "default:/fluendo/configs/ogg_theora-vorbis/")
        checkCtx(profCtx.getFailedRepDir(), "default:/fluendo/reports/failed/ogg_theora-vorbis/")
        checkCtx(profCtx.getDoneRepDir(), "default:/fluendo/reports/done/ogg_theora-vorbis/")
        
        checkVal(profCtx.getInputRelPath(), "test.file.avi")
        checkVal(profCtx.getFailedRelPath(), "test.file.avi")
        checkVal(profCtx.getDoneRelPath(), "test.file.avi")
        checkVal(profCtx.getConfigRelPath(), "test.file.avi.ini")
        checkVal(profCtx.getFailedRepRelPath(), "test.file.avi.rep")
        checkVal(profCtx.getDoneRepRelPath(), "test.file.avi.rep")
        
        checkVal(profCtx.getInputFile(), "test.file.avi")
        checkVal(profCtx.getFailedFile(), "test.file.avi")
        checkVal(profCtx.getDoneFile(), "test.file.avi")
        checkVal(profCtx.getConfigFile(), "test.file.avi.ini")
        checkVal(profCtx.getFailedRepFile(), "test.file.avi.rep")
        checkVal(profCtx.getDoneRepFile(), "test.file.avi.rep")
        
        checkCtx(profCtx.getInputPath(), "default:/fluendo/files/incoming/ogg_theora-vorbis/test.file.avi")
        checkCtx(profCtx.getFailedPath(), "default:/fluendo/files/failed/ogg_theora-vorbis/test.file.avi")
        checkCtx(profCtx.getDonePath(), "default:/fluendo/files/done/ogg_theora-vorbis/test.file.avi")
        checkCtx(profCtx.getConfigPath(), "default:/fluendo/configs/ogg_theora-vorbis/test.file.avi.ini")
        checkCtx(profCtx.getFailedRepPath(), "default:/fluendo/reports/failed/ogg_theora-vorbis/test.file.avi.rep")
        checkCtx(profCtx.getDoneRepPath(), "default:/fluendo/reports/done/ogg_theora-vorbis/test.file.avi.rep")
        
        # Subdir Checks
        transCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis", 
                                   "ogg/vorb", "High Quality", "high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG/Theora-vorbis", "my/sub.dir/test.file.avi")
        checkVal(profCtx.getSubdir(), "ogg/vorb/")
        checkCtx(profCtx.getInputBase(), "default:/flu/one/files/incoming/ogg/vorb/")
        checkCtx(profCtx.getFailedBase(), "default:/flu/one/files/failed/ogg/vorb/")
        checkCtx(profCtx.getDoneBase(), "default:/flu/one/files/done/ogg/vorb/")
        checkCtx(profCtx.getOutputBase(), "default:/flu/one/files/outgoing/ogg/vorb/")
        checkCtx(profCtx.getWorkBase(), "temp:/flu/one/work/ogg/vorb/")
        checkCtx(profCtx.getLinkBase(), "default:/flu/one/files/links/ogg/vorb/")
        checkCtx(profCtx.getConfigBase(), "default:/flu/one/configs/ogg/vorb/")
        checkCtx(profCtx.getFailedRepBase(), "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.getDoneRepBase(), "default:/flu/one/reports/done/ogg/vorb/")
        
        checkCtx(profCtx.getInputDir(), "default:/flu/one/files/incoming/ogg/vorb/my/sub.dir/")
        checkCtx(profCtx.getFailedDir(), "default:/flu/one/files/failed/ogg/vorb/my/sub.dir/")
        checkCtx(profCtx.getDoneDir(), "default:/flu/one/files/done/ogg/vorb/my/sub.dir/")
        checkCtx(profCtx.getConfigDir(), "default:/flu/one/configs/ogg/vorb/my/sub.dir/")
        checkCtx(profCtx.getFailedRepDir(), "default:/flu/one/reports/failed/ogg/vorb/my/sub.dir/")
        checkCtx(profCtx.getDoneRepDir(), "default:/flu/one/reports/done/ogg/vorb/my/sub.dir/")
        
        checkVal(profCtx.getInputRelPath(), "my/sub.dir/test.file.avi")
        checkVal(profCtx.getFailedRelPath(), "my/sub.dir/test.file.avi")
        checkVal(profCtx.getDoneRelPath(), "my/sub.dir/test.file.avi")
        checkVal(profCtx.getConfigRelPath(), "my/sub.dir/test.file.avi.ini")
        checkVal(profCtx.getFailedRepRelPath(), "my/sub.dir/test.file.avi.rep")
        checkVal(profCtx.getDoneRepRelPath(), "my/sub.dir/test.file.avi.rep")
        
        checkVal(profCtx.getInputFile(), "test.file.avi")
        checkVal(profCtx.getFailedFile(), "test.file.avi")
        checkVal(profCtx.getDoneFile(), "test.file.avi")
        checkVal(profCtx.getConfigFile(), "test.file.avi.ini")
        checkVal(profCtx.getFailedRepFile(), "test.file.avi.rep")
        checkVal(profCtx.getDoneRepFile(), "test.file.avi.rep")
        
        checkCtx(profCtx.getInputPath(), "default:/flu/one/files/incoming/ogg/vorb/my/sub.dir/test.file.avi")
        checkCtx(profCtx.getFailedPath(), "default:/flu/one/files/failed/ogg/vorb/my/sub.dir/test.file.avi")
        checkCtx(profCtx.getDonePath(), "default:/flu/one/files/done/ogg/vorb/my/sub.dir/test.file.avi")
        checkCtx(profCtx.getConfigPath(), "default:/flu/one/configs/ogg/vorb/my/sub.dir/test.file.avi.ini")
        checkCtx(profCtx.getFailedRepPath(), "default:/flu/one/reports/failed/ogg/vorb/my/sub.dir/test.file.avi.rep")
        checkCtx(profCtx.getDoneRepPath(), "default:/flu/one/reports/done/ogg/vorb/my/sub.dir/test.file.avi.rep")

        # More subdir Checks
        transCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis", 
                                   "/ogg//./vorb/", "High Quality", "high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG/Theora-vorbis", "my/sub.dir/test.file.avi")
        checkVal(profCtx.getSubdir(), "ogg/vorb/")
        checkCtx(profCtx.getInputBase(), "default:/flu/one/files/incoming/ogg/vorb/")
        checkCtx(profCtx.getFailedBase(), "default:/flu/one/files/failed/ogg/vorb/")
        checkCtx(profCtx.getDoneBase(), "default:/flu/one/files/done/ogg/vorb/")
        checkCtx(profCtx.getOutputBase(), "default:/flu/one/files/outgoing/ogg/vorb/")
        checkCtx(profCtx.getWorkBase(), "temp:/flu/one/work/ogg/vorb/")
        checkCtx(profCtx.getLinkBase(), "default:/flu/one/files/links/ogg/vorb/")
        checkCtx(profCtx.getConfigBase(), "default:/flu/one/configs/ogg/vorb/")
        checkCtx(profCtx.getFailedRepBase(), "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.getDoneRepBase(), "default:/flu/one/reports/done/ogg/vorb/")

        # Empty Subdir Checks
        transCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis", 
                                   "", "High Quality", "high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG/Theora-vorbis", "my/sub.dir/test.file.avi")
        checkVal(profCtx.getSubdir(), "")
        checkCtx(profCtx.getInputBase(), "default:/flu/one/files/incoming/")
        checkCtx(profCtx.getFailedBase(), "default:/flu/one/files/failed/")
        checkCtx(profCtx.getDoneBase(), "default:/flu/one/files/done/")
        checkCtx(profCtx.getOutputBase(), "default:/flu/one/files/outgoing/")
        checkCtx(profCtx.getWorkBase(), "temp:/flu/one/work/")
        checkCtx(profCtx.getLinkBase(), "default:/flu/one/files/links/")
        checkCtx(profCtx.getConfigBase(), "default:/flu/one/configs/")
        checkCtx(profCtx.getFailedRepBase(), "default:/flu/one/reports/failed/")
        checkCtx(profCtx.getDoneRepBase(), "default:/flu/one/reports/done/")
        
        checkCtx(profCtx.getInputDir(), "default:/flu/one/files/incoming/my/sub.dir/")
        checkCtx(profCtx.getFailedDir(), "default:/flu/one/files/failed/my/sub.dir/")
        checkCtx(profCtx.getDoneDir(), "default:/flu/one/files/done/my/sub.dir/")
        checkCtx(profCtx.getConfigDir(), "default:/flu/one/configs/my/sub.dir/")
        checkCtx(profCtx.getFailedRepDir(), "default:/flu/one/reports/failed/my/sub.dir/")
        checkCtx(profCtx.getDoneRepDir(), "default:/flu/one/reports/done/my/sub.dir/")
        
        checkCtx(profCtx.getInputPath(), "default:/flu/one/files/incoming/my/sub.dir/test.file.avi")
        checkCtx(profCtx.getFailedPath(), "default:/flu/one/files/failed/my/sub.dir/test.file.avi")
        checkCtx(profCtx.getDonePath(), "default:/flu/one/files/done/my/sub.dir/test.file.avi")
        checkCtx(profCtx.getConfigPath(), "default:/flu/one/configs/my/sub.dir/test.file.avi.ini")
        checkCtx(profCtx.getFailedRepPath(), "default:/flu/one/reports/failed/my/sub.dir/test.file.avi.rep")
        checkCtx(profCtx.getDoneRepPath(), "default:/flu/one/reports/done/my/sub.dir/test.file.avi.rep")

        # Template Checks
        transCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis", 
                                   "ogg/vorb", "High Quality", "high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG/Theora-vorbis", "my/sub.dir/test.file.avi")
        profCtx.store.setConfigFileTemplate("%(sourceDir)sfoo/%(sourceBasename)s.conf")
        profCtx.store.setReportFileTemplate("/%(sourceDir)s/spam/%(sourceFile)s.dat")
        checkCtx(profCtx.getConfigBase(), "default:/flu/one/configs/ogg/vorb/")
        checkCtx(profCtx.getFailedRepBase(), "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.getDoneRepBase(), "default:/flu/one/reports/done/ogg/vorb/")
        checkCtx(profCtx.getConfigDir(), "default:/flu/one/configs/ogg/vorb/my/sub.dir/foo/")
        checkCtx(profCtx.getFailedRepDir(), "default:/flu/one/reports/failed/ogg/vorb/my/sub.dir/spam/")
        checkCtx(profCtx.getDoneRepDir(), "default:/flu/one/reports/done/ogg/vorb/my/sub.dir/spam/")
        checkVal(profCtx.getConfigRelPath(), "my/sub.dir/foo/test.file.conf")
        checkVal(profCtx.getFailedRepRelPath(), "my/sub.dir/spam/test.file.avi.dat")
        checkVal(profCtx.getDoneRepRelPath(), "my/sub.dir/spam/test.file.avi.dat")
        checkVal(profCtx.getConfigFile(), "test.file.conf")
        checkVal(profCtx.getFailedRepFile(), "test.file.avi.dat")
        checkVal(profCtx.getDoneRepFile(), "test.file.avi.dat")
        checkCtx(profCtx.getConfigPath(), "default:/flu/one/configs/ogg/vorb/my/sub.dir/foo/test.file.conf")
        checkCtx(profCtx.getFailedRepPath(), "default:/flu/one/reports/failed/ogg/vorb/my/sub.dir/spam/test.file.avi.dat")
        checkCtx(profCtx.getDoneRepPath(), "default:/flu/one/reports/done/ogg/vorb/my/sub.dir/spam/test.file.avi.dat")
        
        profCtx.store.setConfigFileTemplate("%(sourceFile)s.conf")
        profCtx.store.setReportFileTemplate("%(sourceBasename)s/report.txt")
        checkCtx(profCtx.getConfigBase(), "default:/flu/one/configs/ogg/vorb/")
        checkCtx(profCtx.getFailedRepBase(), "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.getDoneRepBase(), "default:/flu/one/reports/done/ogg/vorb/")
        checkCtx(profCtx.getConfigDir(), "default:/flu/one/configs/ogg/vorb/")
        checkCtx(profCtx.getFailedRepDir(), "default:/flu/one/reports/failed/ogg/vorb/test.file/")
        checkCtx(profCtx.getDoneRepDir(), "default:/flu/one/reports/done/ogg/vorb/test.file/")
        checkVal(profCtx.getConfigRelPath(), "test.file.avi.conf")
        checkVal(profCtx.getFailedRepRelPath(), "test.file/report.txt")
        checkVal(profCtx.getDoneRepRelPath(), "test.file/report.txt")
        checkVal(profCtx.getConfigFile(), "test.file.avi.conf")
        checkVal(profCtx.getFailedRepFile(), "report.txt")
        checkVal(profCtx.getDoneRepFile(), "report.txt")
        checkCtx(profCtx.getConfigPath(), "default:/flu/one/configs/ogg/vorb/test.file.avi.conf")
        checkCtx(profCtx.getFailedRepPath(), "default:/flu/one/reports/failed/ogg/vorb/test.file/report.txt")
        checkCtx(profCtx.getDoneRepPath(), "default:/flu/one/reports/done/ogg/vorb/test.file/report.txt")
        
        
        # Override Checks
        transCtx = self.getContext("Fluendo", "flu/one", "OGG/Theora-vorbis", 
                                   "ogg/vorb", "High Quality", "high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG/Theora-vorbis", "my/sub.dir/test.file.avi")
        profCtx.store.setInputDir("/override/input/")
        profCtx.store.setDoneDir("override/done")
        profCtx.store.setLinkDir("override/links/")
        profCtx.store.setConfigDir("/override/configs")
        profCtx.store.setWorkDir("/override/work/")
        checkVal(profCtx.getSubdir(), "ogg/vorb/")
        checkCtx(profCtx.getInputBase(), "default:/override/input/")
        checkCtx(profCtx.getFailedBase(), "default:/flu/one/files/failed/ogg/vorb/")
        checkCtx(profCtx.getDoneBase(), "default:/override/done/")
        checkCtx(profCtx.getOutputBase(), "default:/flu/one/files/outgoing/ogg/vorb/")
        checkCtx(profCtx.getWorkBase(), "temp:/override/work/")
        checkCtx(profCtx.getLinkBase(), "default:/override/links/")
        checkCtx(profCtx.getConfigBase(), "default:/override/configs/")
        checkCtx(profCtx.getFailedRepBase(), "default:/flu/one/reports/failed/ogg/vorb/")
        checkCtx(profCtx.getDoneRepBase(), "default:/flu/one/reports/done/ogg/vorb/")
        
        checkCtx(profCtx.getInputDir(), "default:/override/input/my/sub.dir/")
        checkCtx(profCtx.getFailedDir(), "default:/flu/one/files/failed/ogg/vorb/my/sub.dir/")
        checkCtx(profCtx.getDoneDir(), "default:/override/done/my/sub.dir/")
        checkCtx(profCtx.getConfigDir(), "default:/override/configs/my/sub.dir/")
        checkCtx(profCtx.getFailedRepDir(), "default:/flu/one/reports/failed/ogg/vorb/my/sub.dir/")
        checkCtx(profCtx.getDoneRepDir(), "default:/flu/one/reports/done/ogg/vorb/my/sub.dir/")
        
        checkVal(profCtx.getInputRelPath(), "my/sub.dir/test.file.avi")
        checkVal(profCtx.getFailedRelPath(), "my/sub.dir/test.file.avi")
        checkVal(profCtx.getDoneRelPath(), "my/sub.dir/test.file.avi")
        checkVal(profCtx.getConfigRelPath(), "my/sub.dir/test.file.avi.ini")
        checkVal(profCtx.getFailedRepRelPath(), "my/sub.dir/test.file.avi.rep")
        checkVal(profCtx.getDoneRepRelPath(), "my/sub.dir/test.file.avi.rep")
        
        checkVal(profCtx.getInputFile(), "test.file.avi")
        checkVal(profCtx.getFailedFile(), "test.file.avi")
        checkVal(profCtx.getDoneFile(), "test.file.avi")
        checkVal(profCtx.getConfigFile(), "test.file.avi.ini")
        checkVal(profCtx.getFailedRepFile(), "test.file.avi.rep")
        checkVal(profCtx.getDoneRepFile(), "test.file.avi.rep")
        
        checkCtx(profCtx.getInputPath(), "default:/override/input/my/sub.dir/test.file.avi")
        checkCtx(profCtx.getFailedPath(), "default:/flu/one/files/failed/ogg/vorb/my/sub.dir/test.file.avi")
        checkCtx(profCtx.getDonePath(), "default:/override/done/my/sub.dir/test.file.avi")
        checkCtx(profCtx.getConfigPath(), "default:/override/configs/my/sub.dir/test.file.avi.ini")
        checkCtx(profCtx.getFailedRepPath(), "default:/flu/one/reports/failed/ogg/vorb/my/sub.dir/test.file.avi.rep")
        

    def testTargetContext(self):
    
        def checkCtx(virtPath, expected):
            self.assertEqual(str(virtPath), expected)
    
        def checkVal(value, expected):
            self.assertEqual(value, expected)
        
        transCtx = self.getContext("Fluendo", None, "OGG", 
                                   None, "High Quality", None, ".ogg")
        custCtx = transCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG", "test.file.avi")
        targCtx = profCtx.getTargetContextByName("High Quality")
        checkVal(targCtx.getSubdir(), '')
        checkCtx(targCtx.getOutputDir(), "default:/fluendo/files/outgoing/ogg/")
        checkCtx(targCtx.getLinkDir(), "default:/fluendo/files/links/ogg/")
        checkVal(targCtx.getOutputRelPath(), "test.file.avi.ogg")
        checkVal(targCtx.getLinkRelPath(), "test.file.avi.link")
        checkVal(targCtx.getOutputFile(), "test.file.avi.ogg")
        checkVal(targCtx.getLinkFile(), "test.file.avi.link")
        checkCtx(targCtx.getOutputPath(), "default:/fluendo/files/outgoing/ogg/test.file.avi.ogg")
        checkCtx(targCtx.getLinkPath(), "default:/fluendo/files/links/ogg/test.file.avi.link")
        
        # Subdir checks
        transCtx = self.getContext("Fluendo", None, "OGG", 
                                   None, "High Quality", "very/high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG", "test.file.avi")
        targCtx = profCtx.getTargetContextByName("High Quality")
        checkVal(targCtx.getSubdir(), "very/high/")
        checkCtx(targCtx.getOutputDir(), "default:/fluendo/files/outgoing/ogg/very/high/")
        checkCtx(targCtx.getLinkDir(), "default:/fluendo/files/links/ogg/very/high/")
        checkVal(targCtx.getOutputRelPath(), "very/high/test.file.avi.ogg")
        checkVal(targCtx.getLinkRelPath(), "very/high/test.file.avi.link")
        checkVal(targCtx.getOutputFile(), "test.file.avi.ogg")
        checkVal(targCtx.getLinkFile(), "test.file.avi.link")
        checkCtx(targCtx.getOutputPath(), "default:/fluendo/files/outgoing/ogg/very/high/test.file.avi.ogg")
        checkCtx(targCtx.getLinkPath(), "default:/fluendo/files/links/ogg/very/high/test.file.avi.link")
        
        # More subdir checks
        transCtx = self.getContext("Fluendo", None, "OGG", 
                                   None, "High Quality", "/very/./high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG", "test.file.avi")
        targCtx = profCtx.getTargetContextByName("High Quality")
        checkVal(targCtx.getSubdir(), "very/high/")
        checkCtx(targCtx.getOutputDir(), "default:/fluendo/files/outgoing/ogg/very/high/")
        checkCtx(targCtx.getLinkDir(), "default:/fluendo/files/links/ogg/very/high/")
        checkVal(targCtx.getOutputRelPath(), "very/high/test.file.avi.ogg")
        checkVal(targCtx.getLinkRelPath(), "very/high/test.file.avi.link")
        checkVal(targCtx.getOutputFile(), "test.file.avi.ogg")
        checkVal(targCtx.getLinkFile(), "test.file.avi.link")
        checkCtx(targCtx.getOutputPath(), "default:/fluendo/files/outgoing/ogg/very/high/test.file.avi.ogg")
        checkCtx(targCtx.getLinkPath(), "default:/fluendo/files/links/ogg/very/high/test.file.avi.link")
        
        # Empty subdir checks
        transCtx = self.getContext("Fluendo", None, "OGG", 
                                   None, "High Quality", "", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG", "test.file.avi")
        targCtx = profCtx.getTargetContextByName("High Quality")
        checkVal(targCtx.getSubdir(), '')
        checkCtx(targCtx.getOutputDir(), "default:/fluendo/files/outgoing/ogg/")
        checkCtx(targCtx.getLinkDir(), "default:/fluendo/files/links/ogg/")
        checkVal(targCtx.getOutputRelPath(), "test.file.avi.ogg")
        checkVal(targCtx.getLinkRelPath(), "test.file.avi.link")
        checkVal(targCtx.getOutputFile(), "test.file.avi.ogg")
        checkVal(targCtx.getLinkFile(), "test.file.avi.link")
        checkCtx(targCtx.getOutputPath(), "default:/fluendo/files/outgoing/ogg/test.file.avi.ogg")
        checkCtx(targCtx.getLinkPath(), "default:/fluendo/files/links/ogg/test.file.avi.link")
        
        # Templates checks
        transCtx = self.getContext("Fluendo", None, "OGG", 
                                   None, "High Quality", "very/high", ".ogg")
        custCtx = transCtx.getCustomerContextByName("Fluendo")
        profCtx = custCtx.getProfileContextByName("OGG", "test.file.avi")
        targCtx = profCtx.getTargetContextByName("High Quality")
        targCtx.store.setOutputFileTemplate("/%(targetPath)s/%(sourceFile)s.hq%(targetExtension)s")
        targCtx.store.setLinkFileTemplate("%(sourceBasename)s///./%(targetSubdir)sthe.link")
        checkVal(targCtx.getSubdir(), "very/high/")
        checkCtx(targCtx.getOutputDir(), "default:/fluendo/files/outgoing/ogg/very/high/")
        checkCtx(targCtx.getLinkDir(), "default:/fluendo/files/links/ogg/test.file/very/high/")
        checkVal(targCtx.getOutputRelPath(), "very/high/test.file.avi.hq.ogg")
        checkVal(targCtx.getLinkRelPath(), "test.file/very/high/the.link")
        checkVal(targCtx.getOutputFile(), "test.file.avi.hq.ogg")
        checkVal(targCtx.getLinkFile(), "the.link")
        checkCtx(targCtx.getOutputPath(), "default:/fluendo/files/outgoing/ogg/very/high/test.file.avi.hq.ogg")
        checkCtx(targCtx.getLinkPath(), "default:/fluendo/files/links/ogg/test.file/very/high/the.link")
        
