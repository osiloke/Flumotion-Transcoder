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
from twisted.internet import reactor

from flumotion.transcoder.ringbuffer import RingBuffer


class TestJanitor(unittest.TestCase):

    def testCapacityOf1(self):
        b = RingBuffer(1)
        self.assertEqual(len(b), 0)
        self.assertEqual(b.pop(), None)
        self.assertEqual(len(b), 0)
        self.assertEqual(b.push(1), None)
        self.assertEqual(len(b), 1)
        self.assertEqual(1 in b, True)
        self.assertEqual(b.values(), [1])
        self.assertEqual(b.push(2), 1)
        self.assertEqual(len(b), 1)
        self.assertEqual(1 in b, False)
        self.assertEqual(2 in b, True)
        self.assertEqual(b.values(), [2])
        self.assertEqual(b.push(3), 2)
        self.assertEqual(len(b), 1)
        self.assertEqual(1 in b, False)
        self.assertEqual(2 in b, False)
        self.assertEqual(3 in b, True)
        self.assertEqual(b.values(), [3])
        self.assertEqual(b.push(4), 3)
        self.assertEqual(len(b), 1)
        self.assertEqual(1 in b, False)
        self.assertEqual(2 in b, False)
        self.assertEqual(3 in b, False)
        self.assertEqual(4 in b, True)
        self.assertEqual(b.values(), [4])
        self.assertEqual(b.push(None), None)
        self.assertEqual(len(b), 1)
        self.assertEqual(1 in b, False)
        self.assertEqual(2 in b, False)
        self.assertEqual(3 in b, False)
        self.assertEqual(4 in b, True)
        self.assertEqual(b.values(), [4])
        self.assertEqual(b.pop(), 4)
        self.assertEqual(len(b), 0)
        self.assertEqual(1 in b, False)
        self.assertEqual(2 in b, False)
        self.assertEqual(3 in b, False)
        self.assertEqual(4 in b, False)
        self.assertEqual(b.values(), [])
        self.assertEqual(b.pop(), None)
        self.assertEqual(len(b), 0)
        self.assertEqual(1 in b, False)
        self.assertEqual(2 in b, False)
        self.assertEqual(3 in b, False)
        self.assertEqual(4 in b, False)
        self.assertEqual(b.values(), [])
        self.assertEqual(b.push(5), None)
        self.assertEqual(len(b), 1)
        self.assertEqual(5 in b, True)
        self.assertEqual(b.values(), [5])
        self.assertEqual(b.remove(5), 5)
        self.assertEqual(len(b), 0)
        self.assertEqual(5 in b, False)
        self.assertEqual(b.values(), [])

    def testCapacityOf5(self):
        
        def checkContain(buff, i, o):
            for v in i:
                self.assertEqual(v in b, True)
            for v in o:
                self.assertEqual(v in b, False)
        
        b = RingBuffer(5)
        self.assertEqual(len(b), 0)
        self.assertEqual(b.pop(), None)
        self.assertEqual(len(b), 0)
        self.assertEqual(b.push(1), None)
        self.assertEqual(b.push(2), None)
        self.assertEqual(len(b), 2)
        self.assertEqual(b.pop(), 1)
        self.assertEqual(len(b), 1)
        self.assertEqual(b.push(3), None)
        self.assertEqual(b.push(4), None)
        self.assertEqual(len(b), 3)
        self.assertEqual(b.pop(), 2)
        self.assertEqual(len(b), 2)
        
        self.assertEqual(b.values(), [3, 4])
        checkContain(b, b.values(), range(1, 3))
        
        self.assertEqual(b.push(5), None)
        self.assertEqual(len(b), 3)
        self.assertEqual(b.push(6), None)
        self.assertEqual(len(b), 4)
        self.assertEqual(b.pop(), 3)
        self.assertEqual(len(b), 3)
        self.assertEqual(b.push(7), None)
        self.assertEqual(len(b), 4)
        self.assertEqual(b.push(8), None)
        self.assertEqual(len(b), 5)
        self.assertEqual(b.pop(), 4)
        self.assertEqual(len(b), 4)
        
        self.assertEqual(b.values(), [5, 6, 7, 8])
        checkContain(b, b.values(), range(1, 5))
        
        self.assertEqual(b.push(9), None)
        self.assertEqual(len(b), 5)
        self.assertEqual(b.push(10), 5)
        self.assertEqual(len(b), 5)
        self.assertEqual(b.pop(), 6)
        self.assertEqual(len(b), 4)
        self.assertEqual(b.push(11), None)
        self.assertEqual(len(b), 5)
        self.assertEqual(b.push(12), 7)
        self.assertEqual(len(b), 5)
        self.assertEqual(b.pop(), 8)
        self.assertEqual(len(b), 4)

        self.assertEqual(b.values(), [9, 10, 11, 12])
        checkContain(b, b.values(), range(1, 9))
        
        self.assertEqual(b.push(13), None)
        self.assertEqual(len(b), 5)
        self.assertEqual(b.push(14), 9)
        self.assertEqual(len(b), 5)
        self.assertEqual(b.pop(), 10)
        self.assertEqual(len(b), 4)
        self.assertEqual(b.push(15), None)
        self.assertEqual(len(b), 5)
        self.assertEqual(b.push(16), 11)
        self.assertEqual(len(b), 5)
        self.assertEqual(b.pop(), 12)
        self.assertEqual(len(b), 4)
        
        self.assertEqual(b.values(), [13, 14, 15, 16])
        checkContain(b, b.values(), range(1, 13))
        
        self.assertEqual(b.push(17), None)
        self.assertEqual(b.push(18), 13)
        self.assertEqual(b.push(19), 14)
        self.assertEqual(b.push(20), 15)
        self.assertEqual(b.push(21), 16)
        self.assertEqual(b.push(22), 17)
        self.assertEqual(b.push(23), 18)
        self.assertEqual(len(b), 5)

        self.assertEqual(b.values(), [19, 20, 21, 22, 23])
        checkContain(b, b.values(), range(1, 19))
        
        self.assertEqual(b.pop(), 19)
        self.assertEqual(b.pop(), 20)
        self.assertEqual(b.pop(), 21)
        self.assertEqual(b.pop(), 22)
        self.assertEqual(b.pop(), 23)
        self.assertEqual(len(b), 0)
        self.assertEqual(b.pop(), None)
        self.assertEqual(b.pop(), None)
        self.assertEqual(b.pop(), None)
        self.assertEqual(len(b), 0)
        
        self.assertEqual(b.values(), [])
        checkContain(b, b.values(), range(1, 24))
        
        self.assertEqual(b.push(24), None)
        self.assertEqual(b.push(25), None)
        self.assertEqual(b.push(26), None)
        self.assertEqual(b.push(27), None)
        self.assertEqual(b.push(28), None)
        self.assertEqual(b.push(29), 24)
        self.assertEqual(len(b), 5)
        
        self.assertEqual(b.values(), [25, 26, 27, 28, 29])
        checkContain(b, b.values(), range(1, 25))
        
        self.assertEqual(b.remove(26), 26)
        self.assertEqual(len(b), 4)
        self.assertEqual(b.values(), [25, 27, 28, 29])
        checkContain(b, b.values(), range(1, 25) + [26])
        
        self.assertEqual(b.remove(28), 28)
        self.assertEqual(len(b), 3)
        self.assertEqual(b.values(), [25, 27, 29])
        checkContain(b, b.values(), range(1, 25) + [26, 28])
        
        # Removing element do not realy free space,
        # It only make hole
        self.assertEqual(b.push(30), 25)
        self.assertEqual(len(b), 3)
        self.assertEqual(b.push(31), None)
        self.assertEqual(len(b), 4)
        self.assertEqual(b.push(32), 27)
        self.assertEqual(len(b), 4)
        self.assertEqual(b.push(33), None)
        self.assertEqual(len(b), 5)
        self.assertEqual(b.push(34), 29)
        self.assertEqual(len(b), 5)
        self.assertEqual(b.values(), [30, 31, 32, 33, 34])
        checkContain(b, b.values(), range(1, 30))
        
        self.assertEqual(b.remove(31), 31)
        self.assertEqual(len(b), 4)
        self.assertEqual(b.values(), [30, 32, 33, 34])
        checkContain(b, b.values(), range(1, 30) + [31])
        
        self.assertEqual(b.remove(33), 33)
        self.assertEqual(len(b), 3)
        self.assertEqual(b.values(), [30, 32, 34])
        checkContain(b, b.values(), range(1, 30) + [31, 33])
        
        self.assertEqual(b.pop(), 30)
        self.assertEqual(b.pop(), 32)
        self.assertEqual(b.pop(), 34)
        self.assertEqual(len(b), 0)
        self.assertEqual(b.pop(), None)
        self.assertEqual(b.pop(), None)
        self.assertEqual(len(b), 0)
        
        self.assertEqual(b.values(), [])
        checkContain(b, b.values(), range(1, 35))
        
        self.assertEqual(b.push(35), None)
        self.assertEqual(b.push(36), None)
        self.assertEqual(b.push(37), None)
        self.assertEqual(b.push(38), None)
        self.assertEqual(b.push(39), None)
        self.assertEqual(b.push(40), 35)
        self.assertEqual(len(b), 5)
        
        self.assertEqual(b.values(), [36, 37, 38, 39, 40])
        checkContain(b, b.values(), range(1, 36))
        
        self.assertEqual(b.remove(39), 39)
        self.assertEqual(len(b), 4)
        self.assertEqual(b.remove(37), 37)
        self.assertEqual(len(b), 3)
        self.assertEqual(b.remove(40), 40)
        self.assertEqual(len(b), 2)
        self.assertEqual(b.remove(36), 36)
        self.assertEqual(len(b), 1)
        self.assertEqual(b.remove(38), 38)
        self.assertEqual(len(b), 0)
        
        self.assertEqual(b.values(), [])
        checkContain(b, b.values(), range(1, 41))
        
        self.assertEqual(b.pop(), None)
        self.assertEqual(b.pop(), None)
        self.assertEqual(len(b), 0)
        
        
