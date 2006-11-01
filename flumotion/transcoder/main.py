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

usage="usage: flumotion-transcoder [OPTIONS] CONF-FILE"

def daemonizeHelper(processType, daemonizeTo='/', processName=None):
    """
    Daemonize a process, writing log files and PID files to conventional
    locations.

    @param processType: The process type, for example 'worker'. Used
    as part of the log file and PID file names.
    @type  processType: str
    @param daemonizeTo: The directory that the daemon should run in.
    @type  daemonizeTo: str
    @param processName: The service name of the process. Used to
    disambiguate different instances of the same daemon.
    @type  processName: str
    """
    from flumotion.configure import configure
    import os
    common.ensureDir(configure.logdir, "log file")
    common.ensureDir(configure.rundir, "run file")

    if common.getPid(processType, processName):
        raise SystemError(
            "A %s service named '%s' is already running"
            % (processType, processName or processType))

    log.info(processType, "%s service named '%s' daemonizing",
             processType, processName)

    if processName:
        logPath = os.path.join(configure.logdir,
                               '%s.%s.log' % (processType, processName))
    else:
        logPath = os.path.join(configure.logdir,
                               '%s.log' % (processType,))
    log.debug(processType, 'Further logging will be done to %s', logPath)

    # here we daemonize; so we also change our pid
    common.daemonize(stdout=logPath, stderr=logPath, directory=daemonizeTo)

    log.info(processType, 'Started daemon')

    # from now on I should keep running until killed, whatever happens
    path = common.writePidFile(processType, processName)
    log.debug(processType, 'written pid file %s', path)

def _createParser():
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-d', '--debug',
        action="store", type="string", dest="debug",
        help="set debug levels")
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
        sys.stderr.write(usage + '\n')
        sys.exit(1)

    # do this before daemonizing so that we can use relpaths
    conf = config.Config(args[0])

    if options.daemonize:
        # FIXME: remove the above copy whenever we can dep on new
        # flumotion
        # common.daemonizeHelper('transcoder')
        daemonizeHelper('transcoder')

    log.info('transcoder', 'Started')

    trans = transcoder.Transcoder(conf)
    reactor.callLater(0, trans.run)
    reactor.run()

    if options.daemonize:
        common.deletePidFile('transcoder')
