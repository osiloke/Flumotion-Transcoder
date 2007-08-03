# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.
# flumotion-platform - Flumotion Streaming Platform

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import sys
import os
import optparse

from twisted.internet import reactor

from flumotion.common import common, errors
from flumotion.configure import configure

from flumotion.transcoder import inifile, log, defer, constants
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
        raise errors.SystemError(
            '--daemonize-to can only be used with -D/--daemonize.')

    if len(args) != 2:
        sys.exit(usage)

    configPath = args[1]
    if not os.path.exists(configPath):
        raise errors.SystemError("Configuration file '%s' not found" 
                                 % configPath)

    return options, configPath

    
def possess(daemonizeTo=None):
    common.ensureDir(configure.logdir, "log file")
    common.ensureDir(configure.rundir, "run file")
    if not daemonizeTo:
        daemonizeTo = '/'

    pid = common.getPid('transcoder-admin')
    if pid:
        if common.checkPidRunning(pid):
            raise errors.SystemError(
                'A flumotion-transcoder-admin is already running '
                + 'as pid %d' % pid)
        else:
            log.warning("flumotion-transcoder-admin should have been "
                        "running with pid %s.  Restarting", str(pid))
            common.deletePidFile('transcoder-admin')

    logPath = os.path.join(configure.logdir, 'transcoder-admin.log')

    # here we daemonize; so we also change our pid
    if not daemonizeTo:
        daemonizeTo = '/'
    common.daemonize(stdout=logPath, stderr=logPath, 
                     directory=daemonizeTo)

    log.info('Started daemon')

    # from now on I should keep running, whatever happens
    log.debug('writing pid file')
    common.writePidFile('transcoder-admin')

def exorcize():
    log.debug('deleting pid file')
    common.deletePidFile('transcoder-admin')

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
    reactor.callLater(0, a.initialize)
    reactor.run()

    if options.daemonize:
        exorcize()

    log.info('Stopping transcoder-admin')
