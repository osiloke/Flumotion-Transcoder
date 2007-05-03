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

import os
import popen2
import commands
import shutil
import socket
import sys
import string

from twisted.internet import reactor
from flumotion.common import log, common, worker, messages
from flumotion.transcoder.watcher import DirectoryWatcher

SENDMAIL = "/usr/sbin/sendmail"

class JobProcessProtocol(worker.ProcessProtocol):
    def __init__(self, trans, customer, relpath):
        self.relpath = relpath
        self.customer = customer
        self.output = ''
        worker.ProcessProtocol.__init__(self, trans, relpath,
                                        'job', socket.gethostname())

    def outReceived(self, data):
        self.output += data

    def sendMessage(self, message):
        trans = self.loggable
        translated = messages.Translator().translate(message)
        trans.warning('Message from job: %s: %r (%s)', message.id,
                      translated, message.debug)

    def processEnded(self, status):
        trans = self.loggable
        trans.jobFinished(self.customer, self.relpath, self.output,
                          status.value.exitCode==0)
        # chain up
        worker.ProcessProtocol.processEnded(self, status)

class Transcoder(log.Loggable):
    """
    Transcoder
    """
    logCategory = 'transcoder'

    def __init__(self, config):
        """
        @param config: Transcoder configuration
        @type  config: L{flumotion.transcoder.config.Config}
        """
        self.config = config
        self.currentidx = 0
        self.working = False
        self.watchers = {}
        self.queue = []
        self.processing = {}

        for name, customer in config.customers.items():
            self.info('Adding customer %s', name)
            customer.ensureDirs()
            ignorefiles = customer.alreadyProcessedFiles()
            watcher = DirectoryWatcher(customer.inputDir,
                                       timeout=customer.timeout,
                                       ignorefiles=ignorefiles)
            watcher.connect('complete-file', self.newFile, customer)
            watcher.start()
            self.watchers[customer] = watcher

    def newFile(self, watcher, filename, customer):
        self.info('queueing file %s for customer %s (priority %d)',
                  filename, customer.name, customer.priority)
        self.queue.append((-customer.priority, customer, filename))
        self.schedule()

    def schedule(self):
        self.debug('schedule requested: %d jobs queued, %d jobs running',
                   len(self.queue), len(self.processing))

        if not self.queue:
            self.debug('schedule: nothing to do')
            return

        while self.queue and len(self.processing) < self.config.maxJobs:
            self.debug('schedule: requesting job start')
            self.startJob()
        
        self.debug('schedule finished: %d jobs queued, %d jobs running',
                   len(self.queue), len(self.processing))

    def startJob(self):
        self.queue.sort(key=lambda tup: tup[0])
        # because python's sort is stable this should offer FIFO
        # scheduling within the same priority
        negpriority, customer, relpath = self.queue.pop(0)
        self.info('starting transcode of %s for %s', relpath,
                  customer.name)
        p = JobProcessProtocol(self, customer, relpath)
        executable = os.path.join(os.path.dirname(sys.argv[0]),
                                  'flumotion-transcoder-job')
        argv = [executable, '-C', customer.name, self.config.confFile,
                os.path.join(customer.inputDir, relpath)]
        argv.extend(customer.profiles.keys())
        self.log('Job arguments: %r', argv)
        self.debug('Job command line: %s', string.join(argv, ' '))
        # stdin/stderr from parent, but capture stdout
        childFDs = {0: 0, 1: 'r', 2: 2}
        env = dict(os.environ)
        env['FLU_DEBUG'] = log._FLU_DEBUG
        if self.config.gstDebug:
            env['GST_DEBUG'] = self.config.gstDebug
        process = reactor.spawnProcess(p, argv[0], env=env,
                                       args=argv, childFDs=childFDs)
        p.setPid(process.pid)
        self.processing[(customer, relpath)] = p

    def jobFinished(self, customer, relpath, output, success):
        self.info('Job %s/%s finished %s', customer.name, relpath,
                  success and 'successfully' or 'with failure')
        self.debug('Job stdout: %r', output)
        if not success:
            self._sendErrorMail(customer, relpath)
            self._moveInputToErrors(customer, relpath)
        self.processing.pop((customer, relpath))
        self.schedule()

    def _writeInfo(self, out, filepath):
        if not os.path.isfile(filepath):
            out.write("    File '%s' not found\n" % filepath)
            return
        escapedpath = filepath.replace(" ", "\\ ")
        out.write("    File Type: %s\n" % commands.getoutput("file -b %s" % escapedpath))
        out.write("    File Size: %d KB\n" % (os.stat(filepath).st_size / 1024))
        out.write("    Discoverer:\n")
        gstfile = commands.getoutput("GST_DEBUG_NO_COLOR=1 GST_DEBUG=2 python "
                                     "/usr/share/gst-python/0.10/examples/gstfile.py %s" 
                                     % escapedpath).split('\n')
        for l in gstfile:
            out.write("> %s\n" % l)

    def _sendErrorMail(self, customer, relpath):
      if customer.errMail:
          if not os.path.exists(SENDMAIL):
              self.warning("Cannot send error notification mail, sendmail not found at %s"
                           % SENDMAIL)
              return
          p = popen2.Popen4("%s -t" % SENDMAIL)
          p.tochild.write("To: %s\n" % customer.errMail)
          p.tochild.write("Subject: Transcoding Error (%s)\n" % customer.name)
          p.tochild.write("\n")
          p.tochild.write("Transcoding Error Report:\n")
          p.tochild.write("=========================\n")
          p.tochild.write('\n\n')
          incomingpath = os.path.join(customer.inputDir, relpath)
          errorpath = os.path.join(customer.errorDir, relpath)
          p.tochild.write("  Customer Name: %s\n" % customer.name)
          p.tochild.write("  --------------\n")
          p.tochild.write('\n')
          p.tochild.write("  Incoming File: '%s'\n" % incomingpath)
          p.tochild.write("  --------------\n")
          p.tochild.write('\n')
          p.tochild.write("  Error File: '%s'\n" % errorpath)
          p.tochild.write("  -----------\n")
          p.tochild.write('\n')
          p.tochild.write("  Source File Information:\n")
          p.tochild.write("  ------------------------\n")
          self._writeInfo(p.tochild, incomingpath)
          for name, profile in customer.profiles.iteritems():
              p.tochild.write('\n')
              p.tochild.write("  Profile '%s' File Information:\n" % name)
              p.tochild.write("  ----------------------------------------\n")
              outname = profile.getOutputBasename(relpath)
              filepath = os.path.join(customer.workDir, outname)
              self._writeInfo(p.tochild, filepath)
          p.tochild.write('\n')
          p.tochild.write("  Last 20 log lines:\n")
          p.tochild.write("  ------------------\n")
          loglines = commands.getoutput("tail -n 20 /var/log/flumotion/transcoder.log"
                                        " | perl -e 'while (<STDIN>) "
                                        "{s/\\033\\[(?:\\d+(?:;\\d+)*)*m//go; print $_}'").split('\n')
          for l in loglines:
              p.tochild.write("> %s\n" % l)
          p.tochild.close()
          while True:
              try:
                exitCode = p.wait()
                break
              except OSError, e:
                if e.errno == errno.EINTR:
                    continue
                else:
                    raise
          if exitCode != 0:
              self.warning("Failed to send error notification mail to %s (Exit code %s)"
                           % (customer.errMail, str(exitCode)))
          else:
              self.info("Error notification send to %s" % customer.errMail)

    def _moveInputToErrors(self, customer, relpath):
        self.watchers[customer].remove(relpath)
        infile = os.path.join(customer.inputDir, relpath)        
        if os.path.exists(infile):
            if not customer.errorDir:
                self.warning('Cannot move %s to to errordir: customer '
                             '%s does not have an errordir', relpath,
                             customer.name)
            else:
                try:
                    self.warning('Moving %s to errordir', relpath)
                    shutil.move(infile, customer.errorDir)
                except IOError, e:
                    self.warning('Could move input to errordir: %s',
                                 log.getExceptionMessage(e))
