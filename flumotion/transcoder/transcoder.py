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

# Transcoder

class TranscoderTaskConfiguration(log.Loggable):
    """
    Configuration for a TranscoderTask.

    Required:
    _ name : the name of the configuration, must be unique in the task
    _ audioencoder : the name and parameters of the audio encoder (gst-launch
      syntax)
    _ videoencoder : the name and parameters of the video encoder (gst-launch
      syntax)
    _ muxer : the name and parameters of the muxer (gst-launch syntax)
    _ extension : the extension for the output filename, must be unique in the
      the task
    
    Optional:
    _ videowidth : Width of the output video
    _ videoheight : Height of the output video
    _ videopar : Pixel Aspect Ratio of the output video (gst.Fraction)
    _ videoframerate : Framerate of the output video (gst.Fraction)
    _ audiorate : Sampling rate of the output audio
    """

    def __init__(self, name, audioencoder, videoencoder, muxer, extension,
                 videowidth=None, videoheight=None, videopar=None,
                 videoframerate=None, audiorate=None):
        self.log("name:%s , audioencoder:%s , videoencoder:%s, muxer:%s" % (name, audioencoder, videoencoder, muxer))
        self.log("extension:%s , videowidth:%s, videoheight:%s" % (extension, videowidth, videoheight))
        self.log("par:%s, framerate:%s , audiorate:%s" % (videopar, videoframerate, audiorate))
        self.name = name
        self.audioencoder = audioencoder
        self.videoencoder = videoencoder
        self.muxer = muxer
        self.extension = str(extension)
        self.videowidth = videowidth
        self.videoheight = videoheight
        self.videopar = videopar
        self.videoframerate = videoframerate
        self.audiorate = audiorate

        self._validateArguments()

    def _validateArguments(self):
        """ Makes sure the given arguments are valid """
        for fac in [self.audioencoder, self.videoencoder, self.muxer]:
            try:
                elt = gst.parse_launch(fac)
            except:
                raise TypeError, "Given factory [%s] is not valid" % fac
            if isinstance(elt, gst.Pipeline):
                raise TypeError, "Given factory [%s] should be a simple element, and not a gst.Pipeline" % fac
            del elt
        if self.videowidth:
            self.videowidth = int(self.videowidth)
        if self.videoheight:
            self.videoheight = int(self.videoheight)
        if self.videopar and not isinstance(self.videopar, gst.Fraction):
            raise TypeError, "videopar should be a gst.Fraction"
        if self.videoframerate and not isinstance(self.videoframerate, gst.Fraction):
            raise TypeError, "videoframerate should be a gst.Fraction"
        if self.audiorate:
            self.audiorate = int(self.audiorate)

    def getOutputFilename(self, filename):
        """
        Returns the output filename for the given filename.
        The returned filename is the basename, it does not contain the full
        path.
        """
        prefix = os.path.basename(filename).rsplit('.', 1)[0]
        return string.join([prefix, self.extension], '.')

    def getOutputVideoCaps(self, discoverer):
        """
        Return the output video caps, according to the information from the
        discoverer and the configuration.
        Returns None if there was an error.
        """
        if not discoverer.is_video:
            return None
        inpar = dict(discoverer.videocaps[0]).get('pixel-aspect-ratio', gst.Fraction(1,1))
        inwidth = discoverer.videowidth
        inheight = discoverer.videoheight

        gst.log('inpar:%s , inwidth:%d , inheight:%d' % (inpar, inwidth, inheight))
        
        # rate is straightforward
        rate = self.videoframerate or discoverer.videorate
        gst.log('rate:%s' % rate)
        gst.log('outpar:%s , outwidth:%s, outheight:%s' % (self.videopar,
                                                           self.videowidth,
                                                           self.videoheight))
        
        # if we have fixed width,height,par then it's simple too
        if self.videowidth and self.videoheight and self.videopar:
            width = self.videowidth
            height = self.videoheight
            par = self.videopar
        else:
            # now for the tricky part :)
            # the Display Aspect ratio is going to stay the same whatever
            # happens
            dar = gst.Fraction(inwidth * inpar.denom, inheight * inpar.num)

            gst.log('DAR is %s' % dar)
            
            if self.videowidth:
                width = self.videowidth
                if self.videoheight:
                    height = self.videoheight
                    # calculate PAR, from width, height and DAR
                    par = gst.Fraction(dar.num * height, dar.denom * width)
                    gst.log('outgoing par:%s , width:%d , height:%d' % (par, width, height))
                else:
                    if self.videopar:
                        par = self.videopar
                    else:
                        par = inpar
                    # Calculate height from width, PAR and DAR
                    height = (par.num * width * dar.denom) / (par.denom * dar.num)
                    gst.log('outgoing par:%s , width:%d , height:%d' % (par, width, height))
            elif self.videoheight:
                height = self.videoheight
                if self.videopar:
                    par = self.videopar
                else:
                    # take input PAR
                    par = inpar
                # Calculate width from height, PAR and DAR
                width = (dar.num * par.denom * height) / (dar.denom * par.num)
                gst.log('outgoing par:%s , width:%d , height:%d' % (par, width, height))
            elif self.videopar:
                # no width/heigh, just PAR
                par = self.videopar
                height = inheight
                width = (dar.num * par.denom * height) / (dar.denom * par.num)
                gst.log('outgoing par:%s , width:%d , height:%d' % (par, width, height))
            else:
                # take everything from incoming
                par = inpar
                width = inwidth
                height = inheight
                gst.log('outgoing par:%s , width:%d , height:%d' % (par, width, height))

        svtempl = "width=%d,height=%d,pixel-aspect-ratio=%d/%d,framerate=%d/%d" % (width, height,
                                                                                   par.num, par.denom,
                                                                                   rate.num, rate.denom)
        fvtempl = "video/x-raw-yuv,%s;video/x-raw-rgb,%s" % (svtempl, svtempl)
        return gst.caps_from_string(fvtempl)
                
class TranscoderTask(gobject.GObject, log.Loggable):
    """
    Task for the transcoder

    Handles the work directories and the output settings

    Signals:
    _ done : the given filename has succesfully been transcoded
    _ error: An error happened on the given filename
    _ newfile : A new file has arrived in the incoming directory
    """
    __gsignals__ = {
        "done" : ( gobject.SIGNAL_RUN_LAST,
                   gobject.TYPE_NONE,
                   (gobject.TYPE_STRING, )),
        "error": ( gobject.SIGNAL_RUN_LAST,
                   gobject.TYPE_NONE,
                   (gobject.TYPE_STRING, )),
        "newfile" : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_STRING, ))
        }

    def __init__(self, name, inputdirectory, outputdirectory,
                 workdirectory=None,
                 timeout=3):
        gobject.GObject.__init__(self)
        self.name = name
        self.inputdirectory = inputdirectory
        self.outputdirectory = outputdirectory
        self.workdirectory = workdirectory
        self.timeout = timeout

        # list of transcoding configurations
        self.configs = {}

        # list of temporary files to encode
        # we need to do this since a file might still being transfered when we
        # see it. List of (filename, filesize)
        self.tempqueue = {}
        # list of queued complete files to encode
        self.queue = []
        # current processing file
        self.processing = None

        # list of processed files
        self.processed = []

        self.discoverer = None
        self.pipeline = None
        self.bus = None
        self._validateArguments()

    def _validateArguments(self):
        """ Makes sure given arguments are valid """
        if not os.path.isdir(self.inputdirectory):
            raise IOError, "Given input directory does not exist : %s" % self.inputdirectory
        if not os.path.isdir(self.outputdirectory):
            raise IOError, "Given output directory does not exist : %s" % self.outputdirectory
        if not self.workdirectory:
            self.workdirectory = os.path.join(self.outputdirectory, "temp")
        if not os.path.exists(self.workdirectory):
            os.makedirs(self.workdirectory)

    def addConfiguration(self, name, audioencoder, videoencoder, muxer, extension,
                         videowidth=None, videoheight=None, videopar=None,
                         videoframerate=None, audiorate=None):
        """
        Add a configuration to the Task

        Will create the TranscoderTaskConfiguration.
        """
        config = TranscoderTaskConfiguration(name, audioencoder, videoencoder, muxer,
                                             extension, videowidth, videoheight,
                                             videopar, videoframerate,
                                             audiorate)
        self.addTaskConfiguration(config)

    def addTaskConfiguration(self, configuration):
        """
        Add a TranscoderTaskConfiguration to the Task.
        If a configuration with the same name already exists, it will be
        overridden.
        """
        if not isinstance(configuration, TranscoderTaskConfiguration):
            raise TypeError, "Given configuration is not a TranscoderTaskConfiguration"
        self.configs[configuration.name] = configuration

    def setUp(self):
        """
        Sets up the Task.
        Fills up the queue with existing non-processed files,
        Starts a watcher on the incoming directory.
        """
        self.log("setup")
        # analyze incoming directory
        infiles = os.listdir(self.inputdirectory)
        # check which files from the queue have already been processed
        outputfiles = os.listdir(self.outputdirectory)

        for infile in infiles:
            done = True
            for config in self.configs.itervalues():
                if not config.getOutputFilename(infile) in outputfiles:
                    done = False
                    break
            fullname = os.path.join(self.inputdirectory, infile)
            if done:
                self.processed.append(fullname)
            else:
                # append it to temporary queue
                self.tempqueue[fullname] = os.path.getsize(fullname)
        
        gobject.timeout_add(1000 * self.timeout, self._timeoutCb)

    def _checkDirectory(self):
        """
        Go over the contents of the input directory, and add new files to the
        queue.
        """
        self.log("checking %s" % self.inputdirectory)
        files = [os.path.join(self.inputdirectory, f) for f in os.listdir(self.inputdirectory)]
        newfiles = [f for f in files if not (f in self.queue or f in self.processed or f == self.processing)]

        for filen in self.tempqueue.keys():
            if not filen in newfiles:
                newfiles.extend(filen)
                
        newcomplete = []
        for newfile in newfiles:
            fullname = os.path.join(self.inputdirectory, newfile)
            if newfile in self.tempqueue.keys():
                if os.path.getsize(fullname) == self.tempqueue[newfile]:
                    newcomplete.append(newfile)
                    del self.tempqueue[newfile]
                else:
                    self.tempqueue[newfile] = os.path.getsize(fullname)
            else:
                self.tempqueue[fullname] = os.path.getsize(fullname)
                
        if newcomplete:
            self.log("newcomplete: %r" % newcomplete)
            self.queue.extend(newcomplete)
            self.emit('newfile', newfiles[0])

    def _timeoutCb(self):
        self._checkDirectory()
        return True

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
            self.log("Already processing a file !")
            return False
        self.processing = self.queue.pop(0)
        self.log("Start processing %s" % self.processing)

        # discover the media
        self.discoverer = Discoverer(self.processing)
        self.discoverer.connect('discovered', self._discoveredCb)
        self.discoverer.discover()
        return True

    def _discoveredCb(self, discoverer, ismedia):
        if not ismedia:
            self.log("%s is not a media file, ignoring" % self.processing)
            self.log("not media")
            filename = self.processing
            self._shutDownPipeline()
            self.emit('error', filename)
            return
        
        self.log("%s is a media file, transcoding" % self.processing)
        self.pipeline = self._makePipeline(self.processing, discoverer)
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self._busMessageCb)
        
        ret = self.pipeline.set_state(gst.STATE_PLAYING)
        if ret == gst.STATE_CHANGE_FAILURE:
            filename = self.processing
            self._shutDownPipeline()
            self.emit('error', filename)
            return

    ## pipeline related

    def _busMessageCb(self, bus, message):
        if message.type == gst.MESSAGE_ERROR:
            filename = self.processing
            gstgerror, debug = message.parse_error()
            self.log("ERROR: %s" % gstgerror.message)
            self.log("additional debug info: %s" % debug)
            self._shutDownPipeline()
            self.emit('error', filename)
        elif message.type == gst.MESSAGE_EOS:
            filename = self.processing
            self._shutDownPipeline()
            for config in self.configs.itervalues():
                # move files from temporary directories to outgoing directory
                workfile = os.path.join(self.workdirectory, config.getOutputFilename(filename))
                outfile = os.path.join(self.outputdirectory, config.getOutputFilename(filename))
                try:
                    shutil.move(workfile, outfile)
                except IOError, e:
                    self.warning('Could not save transcoded file: %s' % (
                        log.getExceptionMessage(e)))
                self.log('Finished transcoding file to %s' % outfile)
            self.emit('done', filename)
        else:
            self.log('Unhandled message %r' % message)

    def _shutDownPipeline(self):
        if self.bus:
            self.bus.remove_signal_watch()
        self.bus = None
        if self.pipeline:
            self.log("about to set pipeline to NULL")
            self.pipeline.set_state(gst.STATE_NULL)
            self.log("pipeline set to NULL")
        self.pipeline = None
        filename = self.processing
        self.processing = None
        self.processed.append(filename)
        if self.discoverer:
            self.discoverer.set_state(gst.STATE_NULL)
        self.discoverer = None
        

    def _makePipeline(self, filename, discoverer):
        """
        Build a gst.Pipeline for the given input filename and Discoverer.
        """
        pipeline = gst.Pipeline("%s-%s" % (self.name, filename))

        src = gst.element_factory_make("filesrc")
        src.props.location = filename
        dbin = gst.element_factory_make("decodebin")

        pipeline.add(src, dbin)
        src.link(dbin)

        dbin.connect('no-more-pads', self._decodebinNoMorePadsCb)
        
        return pipeline

    def _decodebinNoMorePadsCb(self, dbin):
        self.log('All encoded streams found, adding encoders')
        # go over pads, adding encoding bins, creating tees, linking
        encbins = [self._buildConfigEncodingBin(self.processing, self.discoverer, config) for config in self.configs.itervalues()]

        # add encoding bins to pipeline and set them to paused
        for bin in encbins:
            self.pipeline.add(bin)
            bin.set_state(gst.STATE_PLAYING)
        
        for srcpad in dbin.src_pads():
            tee = gst.element_factory_make("tee")
            self.pipeline.add(tee)
            srcpad.link(tee.get_pad("sink"))
            tee.set_state(gst.STATE_PLAYING)
            if srcpad.get_caps().to_string().startswith('video/x-raw'):
                sinkp = "videosink"
            else:
                sinkp = "audiosink"
            for bin in encbins:
                tee.get_pad("src%d").link(bin.get_pad(sinkp))

    def _buildConfigEncodingBin(self, filename, discoverer, config):
        """ Create an Encoding bin for the given file, config and information """
        bin = gst.Bin("encoding-%s-%s" % (config.name, filename))

        # filesink
        filesink = gst.element_factory_make("filesink")
        filesink.props.location = os.path.join(self.workdirectory, config.getOutputFilename(filename))
        # muxer
        muxer = gst.parse_launch(config.muxer)

        bin.add(muxer, filesink)
        muxer.link(filesink)

        ## Audio
        aenc = gst.parse_launch(config.audioencoder)
        aqueue = gst.element_factory_make("queue", "audioqueue")
        aconv = gst.element_factory_make("audioconvert")
        ares = gst.element_factory_make("audioresample")

        bin.add(aqueue, ares, aconv, aenc)
        gst.element_link_many(aqueue, ares, aconv)

        if (config.audiorate):
            atmpl = "audio/x-raw-int,rate=%d;audio/x-raw-float,rate=%d"
            caps = gst.caps_from_string(atmpl % (config.audiorate, config.audiorate))
            aconv.link(aenc, caps)
        else:
            aconv.link(aenc)

        aenc.link(muxer)
        
        bin.add_pad(gst.GhostPad("audiosink", aqueue.get_pad("sink")))

        ## Video

        venc = gst.parse_launch(config.videoencoder)
        vqueue = gst.element_factory_make("queue", "videoqueue")
        cspace = gst.element_factory_make("ffmpegcolorspace")
        videorate = gst.element_factory_make("videorate")
        videoscale = gst.element_factory_make("videoscale")

        bin.add(vqueue, cspace, videorate, videoscale, venc)
        gst.element_link_many(vqueue, cspace, videorate, videoscale)

        # FIXME : Implement proper filtered caps !!!
        caps = config.getOutputVideoCaps(discoverer)
        if caps:
            gst.log("%s" % caps.to_string())
            videoscale.link(venc, caps)
        else:
            videoscale.link(venc)

        venc.link(muxer)

        bin.add_pad(gst.GhostPad("videosink", vqueue.get_pad("sink")))

        return bin

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
        self.working = False
        for i in range(nb):
            if len(self.tasks[(idx + nb) % nb].queue):
                self.working = True
                self.tasks[(idx + nb) % nb].start()
                break
            
    def addTask(self, task):
        """ Add a TranscoderTask """
        task.connect('done', self._taskDoneCb)
        task.connect('error', self._taskErrorCb)
        task.connect('newfile', self._taskNewFileCb)
        self.tasks.append(task)

    def _taskDoneCb(self, task, filename):
        self.log("DONE in task %s with filename %s" % (task.name, filename))
        self.working = False
        self._nextTask()

    def _taskErrorCb(self, task, filename):
        self.log("ERROR in task %s with filename %s" % (task.name, filename))
        self.working = False
        self._nextTask()

    def _taskNewFileCb(self, task, filename):
        self.info("New incoming file '%s' in profile '%s'" % (
            filename, task.name))
        self.log("NEWFILE in task %s with filename %s" % (task.name, filename))
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
        if ':' in section:
            taskname = section.split(':')[0]
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

            task.addConfiguration(section.split(':')[1],
                                  contents['audioencoder'],
                                  contents['videoencoder'],
                                  contents['muxer'],
                                  contents['extension'],
                                  videowidth, videoheight, videopar, videoframerate,
                                  audiorate)
        else:
            # task
            task = TranscoderTask(section,
                                  contents['inputdirectory'],
                                  contents['outputdirectory'],
                                  contents.get('workdirectory', None),
                                  int(contents.get('timeout', 30)))
            tasks[section] = task

    for task in tasks.keys():
        transcoder.addTask(tasks[task])

    # from the parsed data, create TranscoderTask and pass it to the Transcoder
