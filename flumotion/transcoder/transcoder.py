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
import signal
import shutil
import sys
import ConfigParser
import string

import gobject
import gst

from twisted.internet import reactor

from gst.extend.discoverer import Discoverer

from flumotion.common import log, common

from flumotion.transcoder import trans

from flumotion.transcoder.watcher import DirectoryWatcher

GET_REQUEST_TIMEOUT = 60

# FIXME: this would not work well if we want to save to a separate dir per
# encoding profile
def getOutputFilename(filename, extension):
    """
    Returns the output filename for the given input filename.
    The returned filename is the basename, it does not contain the full
    path.
    """
    prefix = os.path.basename(filename).rsplit('.', 1)[0]
    return string.join([prefix, extension], '.')

class InputHandler(gobject.GObject, log.Loggable):
    """
    I handle one incoming directory, watching it for new files and starting
    transcoding tasks.

    Signals:
    _ done : the given filename has succesfully been transcoded
    _ error: An error happened on the given filename, with the given reason
    _ newfile : A new file has arrived in the incoming directory
    """
    __gsignals__ = {
        "done" : ( gobject.SIGNAL_RUN_LAST,
                   gobject.TYPE_NONE,
                   (gobject.TYPE_STRING, )),
        "error": ( gobject.SIGNAL_RUN_LAST,
                   gobject.TYPE_NONE,
                   (gobject.TYPE_STRING, gobject.TYPE_STRING)),
        "newfile" : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_STRING, ))
        }

    def __init__(self, name, inputdirectory, outputdirectory,
                 workdirectory=None, linkdirectory=None, errordirectory=None,
                 urlprefix=None, getrequest=None,
                 timeout=3):
        gobject.GObject.__init__(self)
        self.name = name
        self.inputdirectory = inputdirectory
        self.outputdirectory = outputdirectory
        self.workdirectory = workdirectory
        self.linkdirectory = linkdirectory
        self.errordirectory = errordirectory
        self.urlprefix = urlprefix
        self.getrequest = getrequest
        self.debug('Preparing get request %s' % self.getrequest)
        self.timeout = timeout

        # dict of profile name -> (profile, extension)
        self._profiles = {}

        self.watcher = None
        # list of queued complete files to encode
        self.queue = []

        # current processing file
        # FIXME: describe lifetime of this variable
        self.processing = None

        # list of processed files
        self.processed = []

        self._validateArguments()

    def _validateArguments(self):
        """ Makes sure given arguments are valid """
        if not self.workdirectory:
            self.workdirectory = os.path.join(self.outputdirectory, "temp")
        for p in [self.inputdirectory, self.outputdirectory,
                  self.linkdirectory, self.workdirectory, self.errordirectory]:
            if p and not os.path.isdir(p):
                self.debug("Creating directory '%s'" % p)
                try:
                    os.makedirs(p)
                except OSError, e:
                    self.warning("Could not create directory '%s'" % p)
                    self.debug(log.getExceptionMessage(e))

    def addProfile(self, name, profile, extension):
        """
        Add a Profile and extension to the InputHandler..
        If a profile with the same name already exists, it will be
        overridden.
        """
        if not isinstance(profile, trans.Profile):
            raise TypeError, "Given configuration is not a trans.Profile"
        self._profiles[profile.name] = (profile, extension)

    def setUp(self):
        """
        Sets up the InputHandler.
        Fills up the queue with existing non-processed files.
        Starts a watcher on the incoming directory.
        """
        # analyze incoming directory
        infiles = os.listdir(self.inputdirectory)
        # check which files from the queue have already been processed
        outputfiles = os.listdir(self.outputdirectory)

        for infile in infiles:
            done = True
            for profile, ext in self._profiles.itervalues():
                if not getOutputFilename(infile, ext) in outputfiles:
                    done = False
                    break
            if done:
                self.processed.append(infile)

        # Create a new watcher to look over the input directory
        watcher = DirectoryWatcher(self.inputdirectory, timeout=self.timeout,
                                   ignorefiles=self.processed)
        watcher.connect('complete-file', self._watcherCompleteFileCb)
        watcher.start()

    def _watcherCompleteFileCb(self, watcher, filename):
        self.queue.append(os.path.join(watcher.path, filename))
        self.emit('newfile', filename)

    def start(self):
        """
        Start a transcoding task.
        Returns a pid if the task could be started, or None.

        This should never return 0, because the child for the task will run
        until it reaches sys.exit()
        """
        self.log("start()")
        if not self.queue:
            self.log("incoming queue empty, returning")
            return None
        if self.processing:
            self.warning("Already processing %s" % self.processing)
            return None

        self.processing = self.queue.pop(0)
        self.debug("Start processing %s" % self.processing)
        self.debug("%d files left in queue after this" % len(self.queue))
        
        pid = os.fork()
        if pid:
            self._parent(pid)
        else:
            self._child()

    def _parent(self, pid):
        # waits for child blockingly
        self.debug("Forked task with pid %d" % pid)
        self.debug('Waiting for task with pid %r to finish' % pid)
        (pid, status) = os.waitpid(pid, 0)

        self.working = False
        self.debug('Task with pid %d finished' % pid)

        success = False

        if os.WIFEXITED(status):
            exitstatus = os.WEXITSTATUS(status)
            if exitstatus == 0:
                self.info('Task %r stopped successfully.' % pid)
                success = True
            else:
                self.warning('Task %r failed.' % pid)
        elif os.WIFSIGNALED(status):
            signum = os.WTERMSIG(status)
            if signum == signal.SIGKILL:
                self.warning('Task %r was killed.' % pid)
            elif signum == signal.SIGSEGV:
                self.warning('Task %r segfaulted.' % pid)
            else:
                self.warning('Task %r signaled with signum %r.' % (
                    pid, signum))
        else:
            self.warning('Unhandled status %r' % status)

        if not success:
            if not self.errordirectory:
                self.warning('Cannot move to error, not specified')
            else:
                try:
                    shutil.move(self.processing, self.errordirectory)
                    self.warning('Moving input file to errors')
                except IOError, e:
                    self.warning('Could not save transcoded file: %s' % (
                        log.getExceptionMessage(e)))

        self._processed(self.processing)


    def _child(self):
        name = os.path.basename(self.processing)
        mt = trans.MultiTranscoder(name, self.processing)
        # add each of our profiles
        for profile, ext in self._profiles.values():
            outputFilename = getOutputFilename(self.processing, ext)
            outputPath = os.path.join(self.workdirectory, outputFilename)
            mt.addOutput(outputPath, profile)

        def _doneCb(mt, inputPath):
            self._handleOutputFiles(inputPath)

        def _errorCb(mt, message, inputPath):
            self.emit('error', inputPath, message)

        mt.connect('done', _doneCb, self.processing)
        mt.connect('error', _errorCb, self.processing)
        mt.start()

        # now make sure we don't return until we sys.exit
        mainloop = gobject.MainLoop()
        mainloop.run()

    # called in parent
    def _processed(self, inputPath):
        # called to mark the file as processed, regardless of error or not
        self.processing = None
        self.processed.append(inputPath)
        self.debug('Processed %s' % inputPath)

    def _handleOutputFiles(self, inputfile):
        """
        Handle the output files created by the task.
        Emits 'done' when all output files are handled.

        @param inputfile: name of the input file
        """
        # "global" list that we can use to see when we can emit 'done'
        outputfiles = []

        for profile, ext in self._profiles.itervalues():
            outputfiles.append(getOutputFilename(inputfile, ext))

        def _discoveredOutputFile(inputfile, profile, ext):
            self._moveOutputFile(inputfile, profile, ext)
            outRelPath = getOutputFilename(inputfile, ext)
            outputfiles.remove(outRelPath)
            if not outputfiles:
                self.debug('All output files discovered, emitting done')
                self.emit('done', inputfile)

        for profile, ext in self._profiles.itervalues():
            self._discoverOutputFile(inputfile, profile, ext,
                _discoveredOutputFile)

    def _discoverOutputFile(self, inputfile, profile, extension, callback):
        """
        Possibly discover the output file if the config contains a
        linkdirectory that we should write cortado links to.
        Calls the callback when done discovering.

        @param callback: callable that will be called with inputfile, profile
                         and extension.
        """
        if not self.linkdirectory:
            # call back immediately
            gobject.timeout_add(0, callback, inputfile, profile, extension)
            return

        # discover the media
        def _discoveredCb(discoverer, ismedia, outputfile):
            if not ismedia:
                self.warning("Discoverer thinks output file '%s' is not a media file" % outputfile)
                gobject.timeout_add(0, callback, inputfile, profile, extension)
                return
            self.debug("Work file '%s' has mime type %s" % (
                workfile, discoverer.mimetype))
            if discoverer.mimetype != 'application/ogg':
                self.debug("File '%s' not an ogg file, not writing link" %
                    workfile)
                gobject.timeout_add(0, callback, inputfile, profile, extension)
                return
            # ogg file, write link
            args = {'cortado': '1'}

            duration = 0.0
            if discoverer.videolength:
                duration = float(discoverer.videolength / gst.SECOND)
            elif discoverer.audiolength:
                duration = float(discoverer.audiolength / gst.SECOND)

            if duration:
                # let buffer time be at least 5 seconds
                bytesPerSecond = os.stat(workfile).st_size / duration
                # specified in Kb
                bufferSize = int(bytesPerSecond * 5 / 1024)
            else:
                bufferSize = 128 # Default if we couldn't figure out duration
            args['buffer'] = str(bufferSize)
            # cortado doesn't handle Theora cropping, so we need to round
            # up width and height for display
            rounder = lambda i: (i + (16 - 1)) / 16 * 16
            if discoverer.videowidth:
                args['width'] = str(rounder(discoverer.videowidth))
            if discoverer.videoheight:
                args['height'] = str(rounder(discoverer.videoheight))
            if duration:
                args['duration'] = str(duration)
            args['audio'] = '0'
            args['video'] = '0'
            if discoverer.audiocaps:
                args['audio'] = '1'
            if discoverer.videocaps:
                args['video'] = '1'
            argString = "&".join("%s=%s" % (k, v) for (k, v) in args.items())
            outRelPath = getOutputFilename(inputfile, extension)
            link = self.urlprefix + outRelPath + ".m3u?" + argString
            # make sure we have width and height for audio too
            if not args.has_key('width'):
                args['width'] = 320
            if not args.has_key('height'):
                args['height'] = 40

            linkPath = os.path.join(self.linkdirectory, outRelPath) + '.link'
            handle = open(linkPath, 'w')
            handle.write(
                '<iframe src="%s" width="%s" height="%s" '
                'frameborder="0" scrolling="no" '
                'marginwidth="0" marginheight="0" />\n' % (
                    link, args['width'], args['height']))
            handle.close()
            self.info("Written link file %s" % linkPath)

            # if we need to post a get request, we should do that before we
            # callback
            if self.getrequest:
                self.debug('Preparing get request')
                args = args.copy()
                # I actually had an incoming file get transcoded to two outgoing
                # files where one was 1.999 secs and the other 2.000 secs
                # so let's round.
                s = int(round(duration))
                m = s / 60
                s -= m * 60
                h = m / 60
                m -= h * 60
                args['hours'] = h
                args['minutes'] = m
                args['seconds'] = s
                args['outputPath'] = outRelPath

                url = self.getrequest % args

                def doGetRequest(url, triesLeft=3):
                    from twisted.web import client
                    self.debug('Doing get request %s' % url)
                    d = client.getPage(url, timeout=GET_REQUEST_TIMEOUT / 2)
                    d.addCallback(getPageCb)
                    d.addErrback(getPageEb, url, triesLeft)
                    return d

                def getPageCb(result):
                    self.info('Done get request to inform server for %s' % outRelPath)
                    self.debug('Got result %s' % result)
                    # finish with the callback
                    gobject.timeout_add(0, callback, inputfile, profile,
                        extension)

                def getPageEb(failure, url, triesLeft):
                    if triesLeft == 0:
                        self.warning('Could not inform server for %s' % outRelPath)
                        # finish with the callback regardless
                        gobject.timeout_add(0, callback, inputfile, profile,
                            extension)
                        return
                    self.debug('failure: %s' % log.getFailureMessage(failure))
                    triesLeft -= 1
                    self.debug('%d tries left' % triesLeft)
                    self.info('Could not do get request for %s, '
                        'trying again in %d seconds' % (
                            outRelPath, GET_REQUEST_TIMEOUT))
                    reactor.callLater(GET_REQUEST_TIMEOUT,
                        doGetRequest, url, triesLeft)

                # start
                doGetRequest(url)
                return

            # done
            gobject.timeout_add(0, callback, inputfile, profile, extension)
            return

        outRelPath = getOutputFilename(inputfile, extension)
        workfile = os.path.join(self.workdirectory, outRelPath)
        self.debug("Analyzing transcoded file '%s'" % workfile)
        discoverer = Discoverer(workfile)

        discoverer.connect('discovered', _discoveredCb, workfile)
        discoverer.discover()
        return True

    def _moveOutputFile(self, inputfile, profile, ext):
        """
        move the output file from the work directory to the output directory.
        """
        outRelPath = getOutputFilename(inputfile, ext)
        workfile = os.path.join(self.workdirectory, outRelPath)
        outfile = os.path.join(self.outputdirectory, outRelPath)
        try:
            shutil.move(workfile, outfile)
        except IOError, e:
            self.warning('Could not save transcoded file: %s' % (
                log.getExceptionMessage(e)))
        self.log('Finished transcoding file to %s' % outfile)

class Transcoder(log.Loggable):
    """
    Transcoder
    """
    logCategory = 'transcoder'

    def __init__(self):
        self._incomings = []
        self.currentidx = 0
        self.working = False
        self._inputHandlers = []

    def run(self):
        """ Start the Transcoder """
        # setup the various inputHandlers
        if len(self._inputHandlers) == 0:
            raise IndexError, "No _inputHandlers available"
        for inputHandler in self._inputHandlers:
            inputHandler.setUp()
        self._nextTask()
        
    def _nextTask(self):
        """ Start the next task """

        # Find the next inputHandler to run
        if self.working:
            self.debug('Already working, returning')
            return

        nb = len(self._inputHandlers)
        idx = self.currentidx % nb
        for i in range(nb):
            inputHandler = self._inputHandlers[(idx + i) % nb]
            if len(inputHandler.queue):
                self.working = True
                self.debug('Task %s has %d files in queue, starting' % (
                    inputHandler.name, len(inputHandler.queue)))
                # this blocks until the task is done
                inputHandler.start()
                self.working = False
                break
            
    def addInputHandler(self, inputHandler):
        """
        Add an InputHandler.
        """
        self.info('Adding inputHandler %s' % inputHandler.name)
        inputHandler.connect('done', self._inputHandlerDoneCb)
        inputHandler.connect('error', self._inputHandlerErrorCb)
        inputHandler.connect('newfile', self._inputHandlerNewFileCb)
        self._inputHandlers.append(inputHandler)

    def _inputHandlerDoneCb(self, inputHandler, filename):
        self.log("DONE in inputHandler %s with filename %s" % (inputHandler.name, filename))
        self.info("Input file '%s' transcoded successfully." % filename)
        os._exit(0)

    def _inputHandlerErrorCb(self, inputHandler, filename, reason):
        # this comes from a child
        self.warning("ERROR in inputHandler %s with filename %s" % (inputHandler.name, filename))
        self.warning("Reason for ERROR : %s" % reason)
        os._exit(1)

    def _inputHandlerNewFileCb(self, inputHandler, filename):
        self.info("New incoming file in inputHandler '%s' : %s" % (inputHandler.name, filename))
        self._nextTask()

def configure_transcoder(transcoder, configurationfile):
    """ Configure the transcoder with the given configuration file """
    # create a config parser and give the configuration file to it
    parser = ConfigParser.ConfigParser()
    parser.read(configurationfile)
    sections = parser.sections()
    sections.sort()

    inputHandlers = {}

    for section in sections:
        # set raw True so we can have getrequest contain %
        contents = dict(parser.items(section, raw=True))

        # each section has a name
        # the inputHandlers are named without :
        # each profile in a inputHandler has : in the name
        if ':' not in section:
            # a inputHandler section
            inputHandler = InputHandler(section,
                                  contents['inputdirectory'],
                                  contents['outputdirectory'],
                                  contents.get('workdirectory', None),
                                  linkdirectory=contents.get('linkdirectory', None),
                                  errordirectory=contents.get('errordirectory', None),
                                  urlprefix=contents.get('urlprefix', None),
                                  getrequest=contents.get('getrequest', None),
                                  timeout=int(contents.get('timeout', 30)))
            inputHandlers[section] = inputHandler

        else:
            # a profile section
            inputHandlerName = section.split(':')[0]
            profilename = section.split(':')[1]
            try:
                inputHandler = inputHandlers[inputHandlerName]
            except:
                continue
            videowidth = contents.get('videowidth', None) and int(contents['videowidth'])
            videoheight = contents.get('videoheight', None) and int(contents['videoheight'])
            videopar = contents.get('videopar', None)
            maxwidth = contents.get('maxwidth', None) and int(contents['maxwidth'])
            maxheight = contents.get('maxheight', None) and int(contents['maxheight'])
            if videopar:
                videopar = gst.Fraction(*[int(x.strip()) for x in videopar.split('/')])
            videoframerate = contents.get('videoframerate', None)
            if videoframerate:
                videoframerate = gst.Fraction(*[int(x.strip()) for x in videoframerate.split('/')])
            audiorate = contents.get('audiorate', None) and int(contents['audiorate'])
            audiochannels = contents.get('audiochannels', None) and int(contents['audiochannels'])
            profile = trans.Profile(profilename,
                                  contents['audioencoder'],
                                  contents['videoencoder'],
                                  contents['muxer'],
                                  videowidth, videoheight, videopar, videoframerate,
                                  audiorate, audiochannels, maxwidth, maxheight)

            inputHandler.addProfile(profilename, profile, contents['extension'])

    for inputHandler in inputHandlers.keys():
        transcoder.addInputHandler(inputHandlers[inputHandler])
