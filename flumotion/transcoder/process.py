# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import os
import socket
import signal

from twisted.internet import reactor

from flumotion.common import worker, messages

from flumotion.common.messages import N_
T_ = messages.gettexter('flumotion-transcoder')

from flumotion.transcoder import log, defer, utils

KILL_TIMEOUT = 10


class ProcessError(Exception):
    pass


class Process(worker.ProcessProtocol, log.Loggable):
    
    def __init__(self, type, command, logger=None):
        self._logger = logger or self
        worker.ProcessProtocol.__init__(self, self._logger, type,
                                        type, socket.gethostname())
        self.command = utils.splitCommandFields(command)
        self.logName = self.command[0]
        self.logCategory = type
        self.output = None
        self.terminated = None
        self._aborted = None
        self.timeout = None
        

    def execute(self, params=None, path=None, env=None, timeout=None):
        if self.pid:
            raise ProcessError("A process is already running with PID %d" % self.pid)
        self.output = ''
        self.terminated = defer.Deferred()
        self.timeout = None
        if params:
            argv = []
            for part in self.command:
                argv.append(part % params)
        else:
            argv = self.command
        self._logger.debug('%s command: %s', self.processType,
                          '"' + '" "'.join(argv) + '"')
        childFDs = {0: 0, 1: 'r', 2: 2}
        envVars = dict(os.environ)
        if env:
            envVars.update(env)
        process = reactor.spawnProcess(self, argv[0], env=env, path=path,
                                       args=argv, childFDs=childFDs)
        self.setPid(process.pid)
        self.timeout = utils.createTimeout(timeout, self._timeout, "timeout")
        return self.terminated

    def abort(self):
        self._logger.debug('Aborting %s', self.processType)
        if not self.pid:
            return defer.succeed(self)
        if self._aborted:
            return self._aborted
        self._aborted = defer.Deferred()
        self.timeout = utils.createTimeout(0, self._timeout, "abort")
        return self._aborted

    def _timeout(self, what):
        if not self.pid:
            self._logger.warning("%s %s, but no PID available" 
                                % (self.processType, what))
            return
        self._logger.warning("%s (%d) %s, sending a SIGTERM"
                            % (self.processType, self.pid, what))
        os.kill(self.pid, signal.SIGTERM)
        self.timeout = utils.createTimeout(KILL_TIMEOUT, 
                                           self._killTimeout, what)
        
    def _killTimeout(self, what):
        if not self.pid:
            self._logger.warning("%s %s timeout (again?), but no PID available" 
                                % (self.processType, what))
            return
        self._logger.warning("%s (%d) %s timeout (again?), sending a SIGKILL"
                            % (self.processType, self.pid, what))
        os.kill(self.pid, signal.SIGKILL)
        self.timeout = utils.createTimeout(KILL_TIMEOUT, 
                                           self._killTimeout, what)
    
    def outReceived(self, data):
        self.output += data
        lines = self.output.split('\n')
        for l in lines[:-1]:
            self.info(l)
        self.output = lines[-1]

    def sendMessage(self, message):
        translated = messages.Translator().translate(message)
        lines = translated.split('\n')
        for l in lines:
            if l and len(l) > 0:
                self._logger.warning(l)
        if message.debug:
            self._logger.debug(message.debug)

    def processEnded(self, status):
        utils.cancelTimeout(self.timeout)
        if self.output:
            self.info(self.output)
        self.output = None
        worker.ProcessProtocol.processEnded(self, status)
        if self._aborted:
            self._aborted.callback(self)
        else:
            code = status.value.exitCode
            if code == 0:
                self.terminated.callback(None)
            else:
                self.terminated.errback(status)
