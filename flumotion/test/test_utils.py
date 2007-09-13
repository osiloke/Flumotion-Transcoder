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
from flumotion.transcoder import utils


class TestUtils(unittest.TestCase):
    
    def testStripEscaped(self):
        
        def check(value, expected):
            result = utils.stripEscaped(value)
            self.assertEqual(result, expected)
        
        check('AAA', 'AAA')
        check(' AAA ', 'AAA')
        check('  AAA    ', 'AAA')
        check('\\ AAA', '\\ AAA')
        check('AAA\\ ', 'AAA\\ ')
        check('\\   AAA', '\\   AAA')
        check('AAA  \\ ', 'AAA  \\ ')
        check('  \\ AAA', '\\ AAA')
        
    def testSplitEscaped(self):
        
        def check(value, expected):
            result = utils.splitEscaped('X', value)
            self.assertEqual(result, expected)
    
        check('', [''])
        check('XX', ['', '', ''])
        check('XBX', ['', 'B', ''])
        check('\\XBX', ['\\XB', ''])
        check('\\\\XBX', ['\\\\', 'B', ''])
        check('AXBXC', ['A', 'B', 'C'])
        check('A\\XBXC', ['A\\XB', 'C'])
        check('AXB\\XC', ['A', 'B\\XC'])
        check('\\\\AXBXC', ['\\\\A', 'B', 'C'])
        check('A\\\\XBXC', ['A\\\\', 'B', 'C'])
        check('AX\\\\BXC', ['A', '\\\\B', 'C'])
        check('AXB\\\\XC', ['A', 'B\\\\', 'C'])
        check('AXBX\\\\C', ['A', 'B', '\\\\C'])
        check('AXBXC\\\\', ['A', 'B', 'C\\\\'])
        check('\\\\XBX', ['\\\\', 'B', ''])
        check('X\\\\BX', ['', '\\\\B', ''])
        check('XB\\\\X', ['', 'B\\\\', ''])
        check('XBX\\\\', ['', 'B', '\\\\'])        
        check('A\\\\\\XBXC', ['A\\\\\\XB', 'C'])
        check('AXB\\\\\\XC', ['A', 'B\\\\\\XC'])
        
        
    def testSplitCommandFields(self):
        
        def check(value, expected):
            result = utils.splitCommandFields(value)
            self.assertEqual(result, expected)
            
        check('', [])
        check(' ', [])
        check('         ', [])
        
        check('""', [''])
        check('   ""    ', [''])
        check('   ""    ""', ['',''])
        
        check('1', ['1'])
        check('    1', ['1'])
        check('1    ', ['1'])
        check('    1    ', ['1'])
        check('1 2', ['1', '2'])
        check('1 2   3', ['1', '2', '3'])
        check('1   2   3', ['1', '2', '3'])
        
        check('"1"', ['1'])
        check('1 "2"', ['1', '2'])
        check('1 "2"   3', ['1', '2', '3'])
        check('1 2   "3"', ['1', '2', '3'])
        check('1 2 "  3"', ['1', '2', '  3'])
        check('1 2 "  3"  ', ['1', '2', '  3'])
        
        check('123 1\\\\23 123', ['123', '1\\23', '123'])
        check('123 "1\\\\23" 123', ['123', '1\\23', '123'])
        check('123 "1\\"23" 123', ['123', '1"23', '123'])
        check('123 1\\\\23 "123"', ['123', '1\\23', '123'])
        check('123 1\\"23 "123"', ['123', '1"23', '123'])
        check('\\\\123 \\\\123\\\\ 123\\\\', ['\\123', '\\123\\', '123\\'])
        check('\\"123 \\"123\\" 123\\"', ['"123', '"123"', '123"'])
        
        check('12\\ 3 123 123', ['12 3', '123', '123'])
        check('12\\ 3 "12 3" 123', ['12 3', '12 3', '123'])
        check('\\ 123 12\\ 3 1\\ 23', [' 123', '12 3', '1 23'])
        check('\\ 123 "12\\ 3" 1\\ 23', [' 123', '12\\ 3', '1 23'])
        check('\\ 123 \\ 123\\  123\\ ', [' 123', ' 123 ', '123 '])
        
        
    def testJoinCommandFields(self):
        
        def check(value, expected):
            result = utils.joinCommandFields(value)
            self.assertEqual(result, expected)
            
        check([], '')
        
        check([''], '""')
        check(['','',''], '"" "" ""')
        
        check(['AAA'], 'AAA')
        check(['AAA', 'BBB', 'CCC'], 'AAA BBB CCC')
        check(['AAA ', 'BBB', 'CCC'], '"AAA " BBB CCC')
        check(['AAA', 'BB B', 'CCC'], 'AAA "BB B" CCC')
        
        check(['A\\AA', 'BBB', 'CCC'], 'A\\\\AA BBB CCC')
        check(['AAA', 'BBB', 'CCC\\'], 'AAA BBB CCC\\\\')

        check(['"AAA"', 'BBB', 'CCC'], '"\\"AAA\\"" BBB CCC')
        check(['"AAA"', 'BB"B', '"CCC'], '"\\"AAA\\"" "BB\\"B" "\\"CCC"')
        
        
    def testJoinSplitCommandFields(self):
        
        def check(value):
            temp = utils.joinCommandFields(value)
            result = utils.splitCommandFields(temp)
            self.assertEqual(result, value)
            
        check([])
        check([''])
        check(['','',''])
        
        check(['AAA','','CCC'])
        check(['AAA','BBB','CCC'])
        
        check(['AA\\A','\\BBB','CCC\\'])
        check(['AAA','\\BBB\\','CCC'])
        
        check(['AA"A','"BBB','CCC"'])
        check(['AAA','"BBB"','CCC'])
        
        check(['  AAA','B  BB','CCC  '])
        check(['  AAA  ','BBB','  CCC  '])
        check(['AAA  ','  BBB  ','  CCC'])
        
        
    def testJoinMailRecipients(self):
        
        def check(value, expected):
            result = utils.joinMailRecipients(value)
            self.assertEqual(result, expected)
        
        check([], "")
        
        check([(None, "test@mail.com")], "test@mail.com")
        check([(None, "test@mail.com"), (None, "test2@mail.com")], 
              "test@mail.com, test2@mail.com")
        check([(None, "test@mail.com"), (None, "test2@mail.com"), (None, "test3@mail.com")], 
              "test@mail.com, test2@mail.com, test3@mail.com")
        
        check([("", "test@mail.com")], "test@mail.com")
        check([("", "test@mail.com"), ("", "test2@mail.com")], 
              "test@mail.com, test2@mail.com")
        check([("", "test@mail.com"), ("", "test2@mail.com"), ("", "test3@mail.com")], 
              "test@mail.com, test2@mail.com, test3@mail.com")
        
        check([("Name", "test@mail.com")], "Name <test@mail.com>")
        check([("Name", "test@mail.com"), ("With Space", "test2@mail.com")], 
              "Name <test@mail.com>, With Space <test2@mail.com>")
        check([("Name", "test@mail.com"), ("With Space", "test2@mail.com"), ("And More", "test3@mail.com")], 
              "Name <test@mail.com>, With Space <test2@mail.com>, And More <test3@mail.com>")
        
        check([(None, "test@mail.com"), ("With Space", "test2@mail.com"), ("", "test3@mail.com")], 
              "test@mail.com, With Space <test2@mail.com>, test3@mail.com")

    def testSplitMailRecipients(self):
        
        def check(value, expected):
            result = utils.splitMailRecipients(value)
            self.assertEqual(result, expected)
        
        check("", [])
        
        check("test@mail.com", [("", "test@mail.com")])
        check("test@mail.com, test2@mail.com", 
              [("", "test@mail.com"), ("", "test2@mail.com")])
        check("test@mail.com, test2@mail.com, test3@mail.com",
              [("", "test@mail.com"), ("", "test2@mail.com"), ("", "test3@mail.com")])
        
        check("Name <test@mail.com>", [("Name", "test@mail.com")])
        check("Name <test@mail.com>, With Space <test2@mail.com>", 
              [("Name", "test@mail.com"), ("With Space", "test2@mail.com")])
        check("Name <test@mail.com>, With Space <test2@mail.com>, And More <test3@mail.com>",
              [("Name", "test@mail.com"), ("With Space", "test2@mail.com"), ("And More", "test3@mail.com")])
        
        check("test@mail.com, With Space <test2@mail.com>, test3@mail.com",
              [("", "test@mail.com"), ("With Space", "test2@mail.com"), ("", "test3@mail.com")])

        
    def testFilterFormat(self):
        
        def check(value, expectedFormat, expectedResult, vars):
            format = utils.filterFormat(value, vars)
            self.assertEqual(format, expectedFormat)
            result = None
            try:
                result = format % vars                
            except Exception, e:
                self.fail("'%s' %% %r Sould work: %s" % (value, vars, e))
            self.assertEqual(result, expectedResult)
        
        vars = {"toto": "AAA", "tata": "BBB", "titi": "CCC"}
        check("", "", "", {})
        check("", "", "", vars)
        check("pimpampoum", "pimpampoum", "pimpampoum", vars)
        check("%(toto)s", "%(toto)s", "AAA", vars)
        check("%(titi)s", "%(titi)s", "CCC", vars)
        check("1111 555 333 %(toto)s 4444",
              "1111 555 333 %(toto)s 4444",
              "1111 555 333 AAA 4444", vars)
        check("%pim%pam%poum%", "%%pim%%pam%%poum%%", "%pim%pam%poum%", vars)
        check("%pim%%pam%%poum%", "%%pim%%%%pam%%%%poum%%", "%pim%%pam%%poum%", vars)
        check("%%pim%%%pam%%%poum%%", "%%%%pim%%%%%%pam%%%%%%poum%%%%", "%%pim%%%pam%%%poum%%", vars)
        check("%(pim)%(pam)%(poum)%", "%%(pim)%%(pam)%%(poum)%%", "%(pim)%(pam)%(poum)%", vars)
        check("%(pim%(pam)%(poum%", "%%(pim%%(pam)%%(poum%%", "%(pim%(pam)%(poum%", vars)
        check("%(pim)%(pam%(poum)%", "%%(pim)%%(pam%%(poum)%%", "%(pim)%(pam%(poum)%", vars)
        check("%(pim)s%(pam)s%(poum)s", "%%(pim)s%%(pam)s%%(poum)s", "%(pim)s%(pam)s%(poum)s", vars)
        check("%(pim%(pam)s%(poum", "%%(pim%%(pam)s%%(poum", "%(pim%(pam)s%(poum", vars)
        check("%(pim)s%(pam%(poum)s", "%%(pim)s%%(pam%%(poum)s", "%(pim)s%(pam%(poum)s", vars)
        check("%(pim)s%(toto)s%(poum)s", "%%(pim)s%(toto)s%%(poum)s", "%(pim)sAAA%(poum)s", vars)
        check("%(pims%(toto)s%(poums", "%%(pims%(toto)s%%(poums", "%(pimsAAA%(poums", vars)
        check("%%(pim)s%%(toto)s%(poum)s%", "%%%%(pim)s%%%(toto)s%%(poum)s%%", "%%(pim)s%AAA%(poum)s%", vars)
        check("%(toto)s%(tata)s%(titi)s", "%(toto)s%(tata)s%(titi)s", "AAABBBCCC", vars)
        check("%(totos%(tata)s%(titis", "%%(totos%(tata)s%%(titis", "%(totosBBB%(titis", vars)
        check("%%(toto)s111%%222%(tata)s444%555%(titi666%(pam)s777%(titi)s%(pam)s%%",
              "%%%(toto)s111%%%%222%(tata)s444%%555%%(titi666%%(pam)s777%(titi)s%%(pam)s%%%%",
              "%AAA111%%222BBB444%555%(titi666%(pam)s777CCC%(pam)s%%", vars)
        check("%(toto)satest%(tata)sta%%ta%(pim)tutu%d%(titi)spam%%%spam%",
              "%(toto)satest%(tata)sta%%%%ta%%(pim)tutu%%d%(titi)spam%%%%%%spam%%",
              "AAAatestBBBta%%ta%(pim)tutu%dCCCpam%%%spam%", vars)
        