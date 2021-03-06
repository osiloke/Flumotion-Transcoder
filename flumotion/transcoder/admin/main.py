# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007,2008,2009 Fluendo, S.L.
# Copyright (C) 2010,2011 Flumotion Services, S.A.
# All rights reserved.
#
# This file may be distributed and/or modified under the terms of
# the GNU Lesser General Public License version 2.1 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.LGPL" in the source distribution for more information.
#
# Headers in this file shall remain intact.

import sys
import os
import optparse

from twisted.internet import reactor

from flumotion.common import common, process
from flumotion.configure import configure

from flumotion.inhouse import inifile, log, defer, errors as iherrors
from flumotion.inhouse import utils, fileutils

from flumotion.transcoder import constants
from flumotion.transcoder.admin import adminconfig, adminconsts
from flumotion.transcoder.admin import admin, notifier


def parse_options(args):
    usage = 'usage: flumotion-transcoder-admin [options] CONFIG-FILE'
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('', '--version',
                      action="store_true", dest="version",
                      default=False,
                      help="show version information")
    parser.add_option('-D', '--daemonize',
                     action="store_true", dest="daemonize",
                     default=False,
                     help="run in background as a daemon")
    parser.add_option('', '--daemonize-to',
                     action="store", dest="daemonizeTo",
                     help="what directory to run from when daemonizing; "
                          "default: '/'")
    parser.add_option('-d', '--debug',
                     action="store", dest="debug",
                     help="override the configuration debug level")

    parser.add_option('-L', '--logdir',
                      action="store", dest="logdir",
                      help="flumotion log directory (default: %s)" %
                        configure.logdir)
    parser.add_option('-R', '--rundir',
                      action="store", dest="rundir",
                      help="flumotion run directory (default: %s)" %
                        configure.rundir)

    options, args = parser.parse_args(args)

    # Force options down configure's throat
    for d in ['logdir', 'rundir']:
        o = getattr(options, d, None)
        if o:
            log.debug('Setting configure.%s to %s' % (d, o))
            setattr(configure, d, o)

    if options.version:
        print common.version("flumotion-transcoder-admin")
        sys.exit(0)

    if options.daemonizeTo and not options.daemonize:
        raise iherrors.SystemError(
            '--daemonize-to can only be used with -D/--daemonize.')

    if len(args) != 2:
        sys.exit(usage)

    configPath = args[1]
    if not os.path.exists(configPath):
        raise iherrors.SystemError("Configuration file '%s' not found"
                                 % configPath)

    return options, configPath


def possess(daemonizeTo=None):
    fileutils.ensureDirExists(configure.logdir, "log file")
    fileutils.ensureDirExists(configure.rundir, "run file")
    if not daemonizeTo:
        daemonizeTo = '/'

    pid = process.getPid('transcoder-admin')
    if pid:
        if process.checkPidRunning(pid):
            raise iherrors.SystemError(
                'A flumotion-transcoder-admin is already running '
                + 'as pid %d' % pid)
        else:
            log.warning("flumotion-transcoder-admin should have been "
                        "running with pid %s.  Restarting", str(pid))
            process.deletePidFile('transcoder-admin')

    logPath = os.path.join(configure.logdir, 'transcoder-admin.log')

    # here we daemonize; so we also change our pid
    if not daemonizeTo:
        daemonizeTo = '/'
    process.daemonize(stdout=logPath, stderr=logPath,
                      directory=daemonizeTo)

    log.info('Started daemon')

    # from now on I should keep running, whatever happens
    log.debug('writing pid file')
    process.writePidFile('transcoder-admin')

def exorcize():
    log.debug('deleting pid file')
    process.deletePidFile('transcoder-admin')

def main(args):
    log.setDefaultCategory(adminconsts.ADMIN_LOG_CATEGORY)
    log.setDebugNotifier(notifier.notifyDebug)

    options, configPath = parse_options(args)

    loader = inifile.IniFile()
    config = adminconfig.ClusterConfig()
    try:
        loader.loadFromFile(config, configPath)
    except Exception, e:
        sys.stderr.write('Error: %s\n' % e)
        sys.exit(1)

    debug = options.debug or config.debug
    if debug:
        log.setFluDebug(debug)

    if options.daemonize:
        possess(options.daemonizeTo)

    a = admin.TranscoderAdmin(config)
    utils.callNext(a.initialize)
    reactor.run()

    if options.daemonize:
        exorcize()

    log.info('Stopping transcoder-admin')
