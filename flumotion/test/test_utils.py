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
from flumotion.transcoder import utils


class TestUtils(unittest.TestCase):
    
    def testsplitPath(self):
        
        def check(value, *expected):
            result = utils.splitPath(value)
            self.assertEqual(list(result), list(expected))
            
        check("test.txt", "", "test", ".txt")
        check("test.", "", "test", ".")
        check(".txt", "", "", ".txt")
        check(".", "", "", ".")
        
        check("/test.txt", "/", "test", ".txt")
        check("/test.", "/", "test", ".")
        check("/.txt", "/", "", ".txt")
        check("/.", "/", "", ".")
        
        check("te.st.txt", "", "te.st", ".txt")
        check("te.st.", "", "te.st", ".")
        check("/te.st.txt", "/", "te.st", ".txt")
        check("/te.st.", "/", "te.st", ".")
        
        check("sub/dir/test.txt", "sub/dir/", "test", ".txt")
        check("sub/dir/test.", "sub/dir/", "test", ".")
        check("sub/dir/.txt", "sub/dir/", "", ".txt")
        check("sub/dir/.", "sub/dir/", "", ".")
        
        check("/sub/dir/test.txt", "/sub/dir/", "test", ".txt")
        check("/sub/dir/test.", "/sub/dir/", "test", ".")
        check("/sub/dir/.txt", "/sub/dir/", "", ".txt")
        check("/sub/dir/.", "/sub/dir/", "", ".")
        
        check("sub/dir/te.st.txt", "sub/dir/", "te.st", ".txt")
        check("sub/dir/te.st.", "sub/dir/", "te.st", ".")
        check("/sub/dir/te.st.txt", "/sub/dir/", "te.st", ".txt")
        check("/sub/dir/te.st.", "/sub/dir/", "te.st", ".")
            
        check("sub.dir/test.txt", "sub.dir/", "test", ".txt")
        check("sub.dir/test.", "sub.dir/", "test", ".")
        check("sub.dir/.txt", "sub.dir/", "", ".txt")
        check("sub.dir/.", "sub.dir/", "", ".")
        
        check("/sub.dir/test.txt", "/sub.dir/", "test", ".txt")
        check("/sub.dir/test.", "/sub.dir/", "test", ".")
        check("/sub.dir/.txt", "/sub.dir/", "", ".txt")
        check("/sub.dir/.", "/sub.dir/", "", ".")
        
        check("", "", "", "")
        check("/", "/", "", "")
        check("txt/", "txt/", "", "")
        check("test.txt/", "test.txt/", "", "")
        check("sub.dir/test.txt/", "sub.dir/test.txt/", "", "")
        check("/sub.dir/test.txt/", "/sub.dir/test.txt/", "", "")

    def testCleanupPath(self):
        
        def check(value, expected):
            result = utils.cleanupPath(value)
            self.assertEqual(result, expected)
            
        check("", "")
        check(".", ".")
        check("./", "./")
        check("/./", "/")
        check("/./././", "/")
        check("./././.", ".")
        check("././././", "./")
        check("file.txt", "file.txt")
        check("file.txt/", "file.txt/")
        check("/file.txt", "/file.txt")
        check("spame/file.txt", "spame/file.txt")
        check("test/foo/spame/file.txt", "test/foo/spame/file.txt")
        check("/test/foo/spame/file.txt", "/test/foo/spame/file.txt")
        check("/test/foo/spame/file.txt/", "/test/foo/spame/file.txt/")
        check("te.st/fo.o/spa.me/file.txt", "te.st/fo.o/spa.me/file.txt")
        
        check("//file.txt", "/file.txt")
        check("///file.txt", "/file.txt")
        check("//////////file.txt", "/file.txt")
        check("file.txt//", "file.txt/")
        check("file.txt///", "file.txt/")
        check("file.txt//////////", "file.txt/")
        
        check("spame////file.txt", "spame/file.txt")
        check("/spame////file.txt", "/spame/file.txt")
        check("////spame/file.txt", "/spame/file.txt")
        check("////spame////file.txt", "/spame/file.txt")
        check("////spame////file.txt////", "/spame/file.txt/")
        
        check("./test/foo/spame/file.txt", "test/foo/spame/file.txt")
        check("test/./foo/spame/file.txt", "test/foo/spame/file.txt")
        check("test/foo/spame/./file.txt", "test/foo/spame/file.txt")
        check("./test/./foo/./spame/./file.txt", "test/foo/spame/file.txt")
        check("test/foo/spame/file.txt/.", "test/foo/spame/file.txt/")
        check("./test/foo/spame/file.txt/.", "test/foo/spame/file.txt/")
        check("./././././test/./././foo/././spame/./file.txt", "test/foo/spame/file.txt")
        
        check(".////test///foo//spame/file.txt", "test/foo/spame/file.txt")
        check("test////.///foo//spame/file.txt", "test/foo/spame/file.txt")
        check("test///foo/////spame//file.txt////.", "test/foo/spame/file.txt/")
        check("./././///././////test/////././//./foo//.//.////spame/.//file.txt", "test/foo/spame/file.txt")
        
    def testEnsureDirPath(self):
            
        def check(value, expected):
            result = utils.ensureDirPath(value)
            self.assertEqual(result, expected)
        
        check("", "")
        check("file.txt", "file.txt/")    
        check("/file.txt", "/file.txt/")    
        check("file.txt/", "file.txt/")
        check(".", "./")
        check("file.txt/.", "file.txt/./")    

    def testEnsureAbsPath(self):
            
        def check(value, expected):
            result = utils.ensureAbsPath(value)
            self.assertEqual(result, expected)
        
        check("", "/")
        check("file.txt", "/file.txt")    
        check("/file.txt", "/file.txt")    
        check("file.txt/", "/file.txt/")
        check(".", "/.")
        check("./file.txt", "/./file.txt")
        check("test/spame/file.txt", "/test/spame/file.txt")    
        check("/test/spame/file.txt", "/test/spame/file.txt")    
        
    def testEnsureRelPath(self):
            
        def check(value, expected):
            result = utils.ensureRelPath(value)
            self.assertEqual(result, expected)
        
        check("", "")
        check(".", ".")
        check("./", "./")
        check("/.", ".")
        check("file.txt", "file.txt")    
        check("/file.txt", "file.txt")
        check("file.txt/", "file.txt/")
        check("./file.txt", "./file.txt")
        check("test/spame/file.txt", "test/spame/file.txt")    
        check("/test/spame/file.txt", "test/spame/file.txt")    
        
        check("/////.", ".")
        check("//////file.txt", "file.txt")
        check("///test/spame/file.txt", "test/spame/file.txt")    

    def testEnsureAbsDirPath(self):
            
        def check(value, expected):
            result = utils.ensureAbsDirPath(value)
            self.assertEqual(result, expected)
        
        check("", "/")
        check("file.txt", "/file.txt/")
        check("/file.txt", "/file.txt/")
        check("file.txt/", "/file.txt/")
        check("/file.txt/", "/file.txt/")
        check(".", "/./")
        check("./file.txt", "/./file.txt/")
        check("file.txt/.", "/file.txt/./")
        check("./file.txt/.", "/./file.txt/./")
        
    def testEnsureRelDirPath(self):
            
        def check(value, expected):
            result = utils.ensureRelDirPath(value)
            self.assertEqual(result, expected)
        
        check("", "")
        check(".", "./")
        check("./", "./")
        check("/.", "./")
        check("/./", "./")
        check("file.txt", "file.txt/")
        check("/file.txt", "file.txt/")
        check("file.txt/", "file.txt/")
        check("/file.txt/", "file.txt/")
        check("./file.txt", "./file.txt/")
        check("test/spame/file.txt", "test/spame/file.txt/")
        check("/test/spame/file.txt", "test/spame/file.txt/")
        check("/////.", "./")
        check("/////./", "./")
        check("//////file.txt", "file.txt/")
        check("//////file.txt/", "file.txt/")
        check("///test/spame/file.txt", "test/spame/file.txt/")    
        check("///test/spame/file.txt/", "test/spame/file.txt/")    
        
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
        
        
    def test_joinMailRecipients(self):
        
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

    def test_splitMailRecipients(self):
        
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
        
        