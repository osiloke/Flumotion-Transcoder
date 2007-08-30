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

from flumotion.transcoder import utils, defer
from flumotion.transcoder.errors import OperationTimedOutError


class TestException(Exception):
    pass

class TestTimeouts(unittest.TestCase):

    def testCallWithTimeout(self):

        delays = []

        def dummySuccessFunc(delay):
            d = defer.Deferred()
            to = reactor.callLater(delay, d.callback, None)
            delays.append(to)
            d.addBoth(defer.bridgeResult, delays.remove, to)
            return d
        
        def dummyFailureFunc(delay):
            d = defer.Deferred()
            to = reactor.callLater(delay, d.errback, TestException())
            delays.append(to)
            d.addBoth(defer.bridgeResult, delays.remove, to)
            return d
        
        def failed(failure, msg):
            self.fail(msg)
        
        def step1():
            d = utils.callWithTimeout(4, dummySuccessFunc, 1)
            d.addCallbacks(step2, failed, errbackArgs=("Step1 should succeed",))
            return d
            
        def step2(result):
            d = utils.callWithTimeout(1, dummySuccessFunc, 4)
            d.addCallbacks(failed, step3, callbackArgs=("Step2 should failed",))
            return d
        
        def step3(failure):
            if not (isinstance(failure.value,
                               OperationTimedOutError)):
                self.fail("Step2 should fail with timout exception, "
                          "not " + failure.value.__class__.__name__)
            d = utils.callWithTimeout(4, dummyFailureFunc, 1)
            d.addCallbacks(failed, step4, callbackArgs=("Step3 should failed",))
            return d
            
        def step4(failure):
            if not (failure.value 
                    and isinstance(failure.value,
                                   TestException)):
                self.fail("Step2 should fail with test exception, "
                          "not " + failure.value.__class__.__name__)
            d = utils.callWithTimeout(1, dummyFailureFunc, 4)
            d.addCallbacks(failed, step5, callbackArgs=("Step4 should failed",))
            return d

        def step5(failure):
            if not (isinstance(failure.value,
                               OperationTimedOutError)):
                self.fail("Step4 should fail with timout exception, "
                          "not " + failure.value.__class__.__name__)
            return

        def cleanup(result):
            for to in delays:
                to.cancel()
            return result

        d = step1()
        d.addBoth(cleanup)
        return d
        
        