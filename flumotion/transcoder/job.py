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

import gst
import os
import signal
import sys
import optparse
import shutil
import socket
import re
import urllib

from gst.extend.discoverer import Discoverer
from twisted.internet import reactor, defer
from twisted.python import failure
from flumotion.common import common, log, messages, worker
from flumotion.transcoder import config, trans

usage="usage: flumotion-transcoder-job [OPTIONS] CONF-FILE INPUT-FILE PROFILE1 PROFILE2..."

class TranscodingError(Exception):
    pass

class PostProcessProtocol(worker.ProcessProtocol, log.Loggable):
    
    def __init__(self, job, name):
        self.logName = name
        self.job = job
        self.output = ''
        self.terminated = defer.Deferred()
        worker.ProcessProtocol.__init__(self, job, job.processing,
                                        'post-process', socket.gethostname())

    def getTerminatedDeferred(self):
        return self.terminated

    def outReceived(self, data):
        self.output += data
        lines = self.output.split('\n')
        for l in lines[:-1]:
            self.info(l)
        self.output = lines[-1]

    def sendMessage(self, message):
        translated = messages.Translator().translate(message)
        self.job.warning('Message from post-process %s: %r (%s)', message.id,
                      translated, message.debug)

    def processEnded(self, status):
        if self.output:
            self.info(self.output)
        self.terminated.callback(status.value.exitCode==0)
        worker.ProcessProtocol.processEnded(self, status)

class Job(log.Loggable):
    def __init__(self, infile, customer, profiles):
        self.processing = infile
        self.config = customer
        self.profiles = profiles
        self.unrecognized_outputs = []
        self.failed_post_processes = []
        self.post_processes = {}

    def get_output_filename(self, profile):
        """
        Returns the output filename for the given profile.
        The returned filename is the basename, it does not contain the full
        path.
        """
        return profile.getOutputBasename(self.processing)

    def failed(self, message, code=1):
        try:
            if isinstance(message, failure.Failure):
                self.debug(log.getFailureMessage(message))
                message = message.getErrorMessage()
            self.warning('Error processing %s: %s', self.processing,
                         message)
            if len(self.unrecognized_outputs) > 0:
                profNames = [p.name for p in self.unrecognized_outputs]
                self.warning("Profile(s) %s output file(s) not recognized"
                             % ", ".join(profNames))
            if len(self.failed_post_processes) > 0:
                profNames = [p.name for p in self.failed_post_processes]
                self.warning("Profile(s) %s post-process(es) failed"
                             % ", ".join(profNames))
            os._exit(code)
        except Exception, e:
            self.warning("Unexpected exception: %s" % str(e))
            os._exit(11)

    def succeed(self, results):
        self.info('Success processing %s, %d output files created', 
                  self.processing, len(results))
        os._exit(0)

    def start(self):
        try:
            name = os.path.basename(self.processing)
            mt = trans.MultiTranscoder(name, self.processing, self.config.transTimeout)
            for profile in self.profiles:
                outputFilename = self.get_output_filename(profile)
                outputPath = os.path.join(self.config.workDir, outputFilename)
                mt.addOutput(outputPath, profile)
    
            mt.connect('done', self.transcode_done)
            mt.connect('error', self.transcode_error)
            mt.start()
        except:
            self.failed(failure.Failure(), code=11)

    def transcode_error(self, mt, message):
        if self.config.errGetRequest:
            try:
                f = failure.Failure(TranscodingError(message))
                d = defer.Deferred()
                d.addErrback(self.performGetRequest, 
                             self.config.errGetRequest, 
                             "failure")
                #recover GET request failures to keep the correct message
                def recoverGETFailure(newFailure):
                    self.warning(log.getExceptionMessage(newFailure.value))
                    return f
                d.addErrback(recoverGETFailure)
                d.addBoth(self.failed, code=2)
                d.errback(f)
                return
            except:
                self.failed(failure.Failure(), code=11)
        else:
            self.failed(message, code=2)

    def transcode_done(self, mt):
        try:
            defs = []
            for profile in self.profiles:
                workfile = os.path.join(self.config.workDir,
                                        self.get_output_filename(profile))
                self.debug("Analyzing transcoded file '%s'", workfile)
                
                d = defer.Deferred()
                #Is the discover patch from #603 applied ? 
                discovererArgs = Discoverer.__init__.im_func.func_code.co_varnames
                if "max_interleave" in discovererArgs:
                    discoverer = Discoverer(workfile, max_interleave=10)
                else:
                    self.warning("Cannot change the maximum frame interleave "
                                 + "of the discoverer, update gst-python")
                    discoverer = Discoverer(workfile)
                discoverer.connect('discovered', lambda a, b, d: d.callback((a, b)), d)
                d.addCallback(self.outputDiscovered,
                              profile,
                              mt._discoverer.is_audio,
                              mt._discoverer.is_video)
                d.addBoth(self.profileFinished, profile)
                defs.append(d)
                discoverer.discover()
            dl = defer.DeferredList(defs,
                                    fireOnOneCallback=False,
                                    fireOnOneErrback=False,
                                    consumeErrors=True)
            targetFiles = []
            dl.addCallback(self.targetsDone, targetFiles)
            dl.addCallback(self.moveOutputFiles)
            if self.config.errGetRequest:
                def performRequestAndKeep(previousFailure):
                    def keepFailure(f):
                        self.warning(log.getExceptionMessage(f.value))
                        return previousFailure
                    try:
                        d = self.performGetRequest(previousFailure,
                                                   self.config.errGetRequest, 
                                                   "failure")
                        d.addErrback(keepFailure)
                        return d
                    except:
                        return keepFailure(failure.Failure())
                dl.addErrback(performRequestAndKeep)
            dl.addErrback(self.failed)
            if self.config.getRequest:
                dl.addCallback(self.performGetRequest, 
                               self.config.getRequest,
                               "success")
                #recover GET request failures
                def recoverGETFailure(f):
                    self.warning(log.getExceptionMessage(f.value))
                    return targetFiles
                dl.addErrback(recoverGETFailure)
            #Proxy the call to performTargetsGetRequest
            #to be able to recover on GET failure without
            #recovering previous failures
            def performTargetsGetRequestAndRecover(result):
                def recover(f):
                    self.warning(log.getExceptionMessage(f.value))
                    return result
                try:
                    d = self.performTargetsGetRequest(result)
                    d.addErrback(recover)
                    return d
                except:
                    return recover(failure.Failure())
            dl.addCallback(performTargetsGetRequestAndRecover)
            dl.addCallbacks(self.succeed, self.failed)
        except:
            self.failed(failure.Failure(), code=11)

    def targetsDone(self, results, targetFiles):
        self.info("All Profiles Done")
        errors = 0
        errors = 0
        for s, r in results:
            if s != defer.SUCCESS:                
                errors += 1
                self.debug(log.getFailureMessage(r))
            else:
                targetFiles.append(r)
        if errors > 0:
            raise TranscodingError("%s profile(s) fail to transcode" % errors)
        return targetFiles

    def outputDiscovered(self, result, profile, is_audio,
                          is_video):
        discoverer, ismedia = result
        if ismedia and (discoverer.is_audio == is_audio 
                        and discoverer.is_video == is_video):
            args = self.buildArgs(profile, discoverer)
            d = defer.Deferred()
            if self.config.linkDir and self.config.urlPrefix:
                d.addCallback(self.writeLinkFile, profile)
                d.addErrback(self.recoverFailure, profile, 
                             args, "link writing")
            if profile.postprocess:
                d.addCallback(self.applyPostProcess, profile)
                d.addErrback(self.fatalFailure, profile, 
                             args, "post-processing")
            d.callback(args)
            return d
        else:
            self.warning("Couldn't recognize the output for profile %s", 
                         profile.name)
            if ismedia:
                gota, gotv = discoverer.is_audio, discoverer.is_video
                self.warning("Expected %saudio and %svideo, but got "
                             "%saudio and %svideo", is_audio or 'no ',
                             is_video or 'no ', gota or 'no ', gotv or
                             'no ')
            else:
                self.warning("Discoverer does not think "
                             + "the output is a media file")
            self.unrecognized_outputs.append(profile)
            raise TranscodingError("Couldn't recognize the output for profile %s", 
                                   profile.name)
            
    def fatalFailure(self, failure, profile, args, task):
        if args.get('fatalError', None):
            self.warning("Skipping %s because of fatal error during %s"
                         % (task, args['fatalError']))
            return failure
        args['fatalError'] = task
        self.warning("Fatal error during %s: %s", task, 
                     log.getExceptionMessage(failure.value))
        return failure

    def recoverFailure(self, failure, profile, args, task):
        if args.get('fatalError', None):
            self.warning("Skipping %s because of fatal error during %s"
                         % (task, args['fatalError']))
            return failure
        self.warning("Recoverable error during %s: %s", task, 
                     log.getExceptionMessage(failure.value))
        return args

    def buildArgs(self, profile, discoverer):
        relpath = self.get_output_filename(profile)
        workfile = os.path.join(self.config.workDir, relpath)
        self.debug("Work file '%s' has mime type %s", workfile,
                   discoverer.mimetype)
        args = {'cortado': '1', 'mimetype': discoverer.mimetype}           
        duration = 0.0
        if discoverer.videolength:
            duration = float(discoverer.videolength / gst.SECOND)
        elif discoverer.audiolength:
            duration = float(discoverer.audiolength / gst.SECOND)
        args['duration'] = duration
        if duration:
            # let buffer time be at least 5 seconds
            bytesPerSecond = os.stat(workfile).st_size / duration
            # specified in Kb
            bufferSize = int(bytesPerSecond * 5 / 1024)
        else:
            bufferSize = 128 # Default if we couldn't figure out duration
        args['c-bufferSize'] = str(bufferSize)
        # cortado doesn't handle Theora cropping, so we need to round
        # up width and height for display
        rounder = lambda i: (i + (16 - 1)) / 16 * 16
        if discoverer.videowidth:
            args['c-width'] = str(rounder(discoverer.videowidth))
        if discoverer.videoheight:
            args['c-height'] = str(rounder(discoverer.videoheight))
        if duration:
            args['c-duration'] = str(duration)
            args['c-seekable'] = 'true'
        args['c-audio'] = 'false'
        args['c-video'] = 'false'
        if discoverer.audiocaps:
            args['c-audio'] = 'true'
        if discoverer.videocaps:
            args['c-video'] = 'true'        
        # make sure we have width and height for audio too
        if not args.has_key('c-width'):
            args['c-width'] = 320
        if not args.has_key('c-height'):
            args['c-height'] = 40
        return args

    def writeLinkFile(self, args, profile):
        relpath = self.get_output_filename(profile)
        workfile = os.path.join(self.config.workDir, relpath)
        if args['mimetype'] != 'application/ogg':
            self.debug("File '%s' not an ogg file, not writing link" %
                       workfile)
            return args
        argString = "&".join("%s=%s" % (k, v) for (k, v) in args.items())
        link = self.config.urlPrefix + urllib.quote(relpath) + ".m3u?" + argString
        linkPath = os.path.join(self.config.linkDir, relpath) + '.link'
        handle = open(linkPath, 'w')
        handle.write(
            '<iframe src="%s" width="%s" height="%s" '
            'frameborder="0" scrolling="no" '
            'marginwidth="0" marginheight="0" />\n' % (
                link, args['c-width'], args['c-height']))
        handle.close()
        self.info("Written link file %s" % linkPath)
        return args

    def applyPostProcess(self, args, profile):
        
        def processTerminated(success):
            p, to = self.post_processes.pop((profile, self.processing))
            to.cancel()
            self.debug("Profile %s post-process with PID %s terminated", 
                       profile.name, str(p.pid))
            if not success:
                self.failed_post_processes.append(profile)
                raise TranscodingError("Post-processing failed for profile %s" 
                                     % profile.name)
            return args
                
        def processFailure(failure):
            p, to = self.post_processes.pop((profile, self.processing))
            to.cancel()
            self.debug("Profile %s post-process with PID %s failed", 
                       profile.name, str(p.pid))
            self.failed_post_processes.append(profile)
            return failure
            
        def killProcessTimeout(process):
            self.warning("Profile %s post-process with PID %d didn't stop, "
                         + "trying to kill it", profile.name, process.pid)
            os.kill(process.pid, signal.SIGKILL)
            to = reactor.callLater(20, killProcessTimeout, process)
            self.post_processes[(profile, self.processing)] = (process, to)
            
        def processTimeout(process):
            self.warning("Profile %s post-process with PID %d timeout", 
                         profile.name, process.pid)
            os.kill(process.pid, signal.SIGTERM)
            to = reactor.callLater(20, killProcessTimeout, process)
            self.post_processes[(profile, self.processing)] = (process, to)
            
        outputFile = self.get_output_filename(profile)
        outputPath = os.path.join(self.config.outputDir, outputFile)
        workfile = os.path.join(self.config.workDir, outputFile)
        self.info('starting post-processing of %s', workfile);
        inputPath = self.processing
        inputFile = os.path.basename(inputPath)
        params = {"workPath": workfile,
                  "workFile": outputFile,
                  "outputFile": outputFile,
                  "outputPath": outputPath,
                  "inputPath": inputPath,
                  "inputFile": inputFile,
                  "workRoot": self.config.workDir,
                  "inputRoot": self.config.inputDir,
                  "outputRoot": self.config.outputDir,
                  "errorRoot": self.config.errorDir,
                  "linkRoot": self.config.linkDir}
        for k, v in params.iteritems():
            params[k] = v.replace(' ', '\ ')
        command = profile.postprocess % params
        argv = re.split('(?<!\\\\) ', command)
        for i, a in enumerate(argv):
            argv[i] = a.replace('\ ', ' ')
        self.debug('Post-process line: %s', '"' + '" "'.join(argv) + '"')
        childFDs = {0: 0, 1: 'r', 2: 'r'}
        env = dict(os.environ)
        env['FLU_DEBUG'] = log._FLU_DEBUG
        
        p = PostProcessProtocol(self, argv[0])
        d = p.getTerminatedDeferred()
        d.addCallbacks(processTerminated, processFailure)
        process = reactor.spawnProcess(p, argv[0], env=env,
                                       args=argv, childFDs=childFDs)
        p.setPid(process.pid)
        to = reactor.callLater(self.config.ppTimeout, processTimeout, p)
        self.post_processes[(profile, self.processing)] = (p, to)
        return d

    def profileFinished(self, result, profile):
        if isinstance(result, failure.Failure):
            result.raiseException()
        return (profile, result)

    def moveOutputFiles(self, targets):
        for profile, args in targets:
            outRelPath = self.get_output_filename(profile)
            workfile = os.path.join(self.config.workDir, outRelPath)
            outfile = os.path.join(self.config.outputDir, outRelPath)
            shutil.move(workfile, outfile)
            self.info("Output file for profile %s moved to %s", 
                      profile.name, outfile)
        return targets

    def performGetRequest(self, result, template, identifier):
        self.debug('Preparing GET request for %s' % identifier)
        inputPath = self.processing
        inputFile = os.path.basename(inputPath)
        vars = {"inputPath": urllib.quote(inputPath),
                "inputFile": urllib.quote(inputFile),
                "workRoot": urllib.quote(self.config.workDir),
                "inputRoot": urllib.quote(self.config.inputDir),
                "outputRoot": urllib.quote(self.config.outputDir),
                "errorRoot": urllib.quote(self.config.errorDir),
                "linkRoot": urllib.quote(self.config.linkDir),
                "message": ""}
        if isinstance(result, failure.Failure):
            vars["message"] = urllib.quote(result.getErrorMessage())
        return self.startGetRequest(result, template % vars, identifier)
    
    def performTargetsGetRequest(self, targets):
        defs = []
        for profile, args in targets:
            if profile.getRequest:
                self.debug('Preparing GET request for profile %s'
                           % profile.name)
                largs = args.copy()
                outputFile = self.get_output_filename(profile)
                outputPath = os.path.join(self.config.outputDir, outputFile)
                inputPath = self.processing
                inputFile = os.path.basename(inputPath)
                # I actually had an incoming file get transcoded to two outgoing
                # files where one was 1.999 secs and the other 2.000 secs
                # so let's round.
                s = int(round(largs['duration']))
                m = s / 60
                s -= m * 60
                h = m / 60
                m -= h * 60
                largs['hours'] = h
                largs['minutes'] = m
                largs['seconds'] = s
                largs['outputFile'] = urllib.quote(outputFile)
                largs["outputPath"] = urllib.quote(outputPath)
                largs["inputPath"] = urllib.quote(inputPath)
                largs["inputFile"] = urllib.quote(inputFile)
                largs["workRoot"] = urllib.quote(self.config.workDir)
                largs["inputRoot"] = urllib.quote(self.config.inputDir)
                largs["outputRoot"] = urllib.quote(self.config.outputDir)
                largs["errorRoot"] = urllib.quote(self.config.errorDir)
                largs["linkRoot"] = urllib.quote(self.config.linkDir)
                url = profile.getRequest % largs
                d = self.startGetRequest(None, url, profile.name)
                def showFailure(f):
                    self.warning(log.getExceptionMessage(f.value))
                    return f
                d.addErrback(showFailure)
                defs.append(d)
        if len(defs) == 0:
            return defer.succeed(targets)
        return defer.DeferredList(defs,
                                  fireOnOneCallback=False,
                                  fireOnOneErrback=False,
                                  consumeErrors=True)

    def startGetRequest(self, result, url, identifier):

        def doGetRequest(url, triesLeft=3):
            from twisted.web import client
            self.debug('Doing get request %s' % url)
            d = client.getPage(url, timeout=self.config.getTimeout / 2)            
            d.addCallbacks(getPageCb,
                           getPageEb,
                           errbackArgs=[url, triesLeft])
            return d

        def getPageCb(page):
            self.info('GET request done for %s' % identifier)
            self.log('Got result %s', page)
            if isinstance(result, failure.Failure):
                result.raiseException()
            return result

        def getPageEb(failure, url, triesLeft):
            if triesLeft == 0:
                raise TranscodingError('Fail to perform GET request for %s'
                                       % identifier)
            self.debug('failure: %s' % log.getFailureMessage(failure))
            triesLeft -= 1
            self.debug('%d tries left' % triesLeft)
            self.info(('Could not do GET request for %s, '
                      + 'trying again in %d seconds')
                      % (identifier, self.config.getTimeout))
            d = defer.Deferred()
            d.addCallback(lambda _: doGetRequest(url, triesLeft))
            reactor.callLater(self.config.getTimeout, d.callback, None)
            return d

        return doGetRequest(url)


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
    profileNames = args[2:]

    log.info('transjob', 'Started')

    conf = config.Config(confFile)
    try:
        customer = conf.customers[options.customer]
    except KeyError:
        raise SystemError, 'Unknown customer: %s' % options.customer
    try:
        profiles = []
        for profileName in profileNames:
            profiles.append(customer.profiles[profileName])
    except KeyError:
        raise SystemError, 'Unknown profile: %s' % profileName

    job = Job(inputFile, customer, profiles)
    job.start()
    reactor.run()
