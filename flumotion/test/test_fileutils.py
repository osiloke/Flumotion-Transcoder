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
from flumotion.transcoder import fileutils


class TestFileUtils(unittest.TestCase):
    
    def testsplitPath(self):
        
        def check(value, *expected):
            result = fileutils.splitPath(value)
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
            result = fileutils.cleanupPath(value)
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
            result = fileutils.ensureDirPath(value)
            self.assertEqual(result, expected)
        
        check("", "")
        check("file.txt", "file.txt/")    
        check("/file.txt", "/file.txt/")    
        check("file.txt/", "file.txt/")
        check(".", "./")
        check("file.txt/.", "file.txt/./")    

    def testEnsureAbsPath(self):
            
        def check(value, expected):
            result = fileutils.ensureAbsPath(value)
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
            result = fileutils.ensureRelPath(value)
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
            result = fileutils.ensureAbsDirPath(value)
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
            result = fileutils.ensureRelDirPath(value)
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
