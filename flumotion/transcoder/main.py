# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.
# Flumotion Transcoder

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import os
import sys
import optparse

import gobject

from twisted.internet import reactor
from flumotion.common import common, log
from flumotion.transcoder import transcoder

def _createParser():
    parser = optparse.OptionParser()
    parser.add_option('-d', '--debug',
        action="store", type="string", dest="debug",
        help="set debug levels")
    parser.add_option('-l', '--log',
        action="store", type="string", dest="log",
        help="where to log to when daemonizing")
    parser.add_option('-D', '--daemonize',
        action="store_true", dest="daemonize",
        help="run in background as a daemon")

    return parser

def main(argv):
    parser = _createParser()
    options, args = parser.parse_args(argv[1:])

    if options.debug:
        log.setFluDebug(options.debug)

    if len(args) < 1:
        print "Usage:\n\t%s <configuration file>" % argv[0]
        sys.exit()
    if options.daemonize:
        if common.getPid('transcoder'):
            raise SystemError(
                "A transcoder service is already running")

        logPath = os.path.join(os.getcwd(), "transcoder.log")
        if options.log:
            logPath = options.log
        log.debug('transcoder', 'Daemonizing')
        common.daemonize(stdout=logPath, stderr=logPath)
        log.debug('transcoder', 'Daemonized')
        # from now on I should keep running, whatever happens
        path = common.writePidFile('transcoder')
        log.debug('transcoder', 'written pid file %s' % path)


    log.info('transcoder', 'Started')

    trans = transcoder.Transcoder()
    transcoder.configure_transcoder(trans, args[0])
    reactor.callLater(0, trans.run)
    reactor.run()
