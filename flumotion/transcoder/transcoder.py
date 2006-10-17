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
import shutil
import sys
import ConfigParser
import string
import time

import gobject
import gst

from gst.extend.discoverer import Discoverer

from flumotion.common import log, common

from flumotion.transcoder import trans

from flumotion.transcoder.watcher import DirectoryWatcher

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

# FIXME: rename, a task is something that runs once for one operation
class TranscoderTask(gobject.GObject, log.Loggable):
    """
    Task for the transcoder

    Handles the work directories and the output settings

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
                 workdirectory=None, linkdirectory=None, urlprefix=None,
                 timeout=3):
        gobject.GObject.__init__(self)
        self.name = name
        self.inputdirectory = inputdirectory
        self.outputdirectory = outputdirectory
        self.workdirectory = workdirectory
        self.linkdirectory = linkdirectory
        self.urlprefix = urlprefix
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
                  self.linkdirectory, self.workdirectory]:
            if p and not os.path.isdir(p):
                self.debug("Creating directory '%s'" % p)
                os.makedirs(p)

    def addProfile(self, name, profile, extension):
        """
        Add a Profile and extension to the task.
        If a profile with the same name already exists, it will be
        overridden.
        """
        if not isinstance(profile, trans.Profile):
            raise TypeError, "Given configuration is not a trans.Profile"
        self._profiles[profile.name] = (profile, extension)

    def setUp(self):
        """
        Sets up the Task.
        Fills up the queue with existing non-processed files.
        Starts a watcher on the incoming directory.
        """
        self.debug("setUp()")
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
        Returns True if the task could be started, else False.
        """
        self.log("start()")
        if not self.queue:
            self.log("task queue empty, returning")
            return False
        if self.processing:
            self.warning("Already processing %s" % self.processing)
            return False
        self.processing = self.queue.pop(0)
        self.debug("Start processing %s" % self.processing)
        self.debug("%d files left in queue after this" % len(self.queue))

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
            self._processed(inputPath)
            self.emit('error', inputPath, message)

        mt.connect('done', _doneCb, self.processing)
        mt.connect('error', _errorCb, self.processing)
        mt.start()
        return True

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
                self._processed(inputfile)
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
        def _discoveredCb(discoverer, ismedia):
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
            # cortado doesn't handle Theora cropping, so we need to round
            # up width and height for display
            rounder = lambda i: (i + (16 - 1)) / 16 * 16
            if discoverer.videowidth:
                args['width'] = str(rounder(discoverer.videowidth))
            if discoverer.videoheight:
                args['height'] = str(rounder(discoverer.videoheight))
            if discoverer.videorate:
                f = discoverer.videorate
                args['framerate'] = str(float(f.num) / f.denom)
            if discoverer.videolength:
                args['duration'] = str(float(discoverer.videolength / gst.SECOND))
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
            handle.write('<iframe src="%s" width="%s" height="%s" frameborder="0" scrolling="no" />\n' % (link, args['width'], args['height']))
            handle.close()
            self.info("Written link file %s" % linkPath)

            # done
            gobject.timeout_add(0, callback, inputfile, profile, extension)
            return

        outRelPath = getOutputFilename(inputfile, extension)
        workfile = os.path.join(self.workdirectory, outRelPath)
        self.debug("Analyzing transcoded file '%s'" % workfile)
        discoverer = Discoverer(workfile)

        discoverer.connect('discovered', _discoveredCb)
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
        self.tasks = []
        self.currentidx = 0
        self.working = False

    def run(self):
        """ Start the Transcoder """
        # setup the various tasks
        if len(self.tasks) == 0:
            raise IndexError, "No tasks available"
        for task in self.tasks:
            task.setUp()
        self._nextTask()
        
    def _nextTask(self):
        """ Start the next task """
        # Find the next task to run
        if self.working:
            return

        nb = len(self.tasks)
        idx = self.currentidx % nb
        for i in range(nb):
            task = self.tasks[(idx + nb) % nb]
            if len(task.queue):
                self.working = True
                self.debug('Task %s has %d files in queue, starting' % (
                    task.name, len(task.queue)))
                task.start()
                break
            
    def addTask(self, task):
        """ Add a TranscoderTask """
        task.connect('done', self._taskDoneCb)
        task.connect('error', self._taskErrorCb)
        task.connect('newfile', self._taskNewFileCb)
        self.tasks.append(task)

    def _taskDoneCb(self, task, filename):
        self.log("DONE in task %s with filename %s" % (task.name, filename))
        self.info("Input file '%s' transcoded successfully." % filename)
        self.working = False
        self._nextTask()

    def _taskErrorCb(self, task, filename, reason):
        self.warning("ERROR in task %s with filename %s" % (task.name, filename))
        self.warning("Reason for ERROR : %s" % reason)
        self.working = False
        self._nextTask()

    def _taskNewFileCb(self, task, filename):
        self.info("New incoming file in task '%s' : %s" % (task.name, filename))
        self._nextTask()

def configure_transcoder(transcoder, configurationfile):
    """ Configure the transcoder with the given configuration file """
    # create a config parser and give the configuration file to it
    parser = ConfigParser.ConfigParser()
    parser.read(configurationfile)
    sections = parser.sections()
    sections.sort()

    tasks = {}

    for section in sections:
        contents = dict(parser.items(section))

        # each section has a name
        # the tasks are named without :
        # each profile in a task has : in the name
        if ':' not in section:
            # a task section
            task = TranscoderTask(section,
                                  contents['inputdirectory'],
                                  contents['outputdirectory'],
                                  contents.get('workdirectory', None),
                                  linkdirectory=contents.get('linkdirectory', None),
                                  urlprefix=contents.get('urlprefix', None),
                                  timeout=int(contents.get('timeout', 30)))
            tasks[section] = task

        else:
            # a profile section
            taskname = section.split(':')[0]
            profilename = section.split(':')[1]
            try:
                task = tasks[taskname]
            except:
                continue
            videowidth = contents.get('videowidth', None) and int(contents['videowidth'])
            videoheight = contents.get('videoheight', None) and int(contents['videoheight'])
            videopar = contents.get('videopar', None)
            if videopar:
                videopar = gst.Fraction(*[int(x.strip()) for x in videopar.split('/')])
            videoframerate = contents.get('videoframerate', None)
            if videoframerate:
                videoframerate = gst.Fraction(*[int(x.strip()) for x in videoframerate.split('/')])
            audiorate = contents.get('audiorate', None) and int(contents['audiorate'])
            audiochanns = contents.get('audiochanns', None) and int(contents['audiochanns'])
            profile = trans.Profile(profilename,
                                  contents['audioencoder'],
                                  contents['videoencoder'],
                                  contents['muxer'],
                                  videowidth, videoheight, videopar, videoframerate,
                                  audiorate, audiochanns)

            task.addProfile(profilename, profile, contents['extension'])
    for task in tasks.keys():
        transcoder.addTask(tasks[task])

    # from the parsed data, create TranscoderTask and pass it to the Transcoder
