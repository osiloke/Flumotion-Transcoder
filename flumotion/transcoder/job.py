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

import sys
import optparse

from twisted.internet import reactor
from flumotion.common import common, log
from flumotion.transcoder import transcoder, config

usage="usage: flumotion-transcode-job [OPTIONS] CONF-FILE INPUT-FILE PROFILE1 PROFILE2..."

def _createParser():
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-d', '--debug',
        action="store", type="string", dest="debug",
        help="set debug levels")
    parser.add_option('-C', '--customer',
        action="store", type="string", dest="customer",
        help="The name of the customer, as it appears in the conf file")

    return parser

def main(argv):
    parser = _createParser()
    options, args = parser.parse_args(argv[1:])

    if options.debug:
        log.setFluDebug(options.debug)

    if not options.customer:
        raise SystemError, 'Missing required argument: --customer'

    if len(args) < 3:
        sys.stderr.write(usage + '\n')
        sys.exit(1)

    confFile = args[0]
    inputFile = args[1]
    profiles = args[2:]

    log.info('transjob', 'Started')

    conf = config.Config(args[0])
    trans = transcoder.Transcoder(conf)
    reactor.callLater(0, trans.run)
    reactor.run()
