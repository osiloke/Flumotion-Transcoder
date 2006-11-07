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
import sys
import optparse
import shutil

from gst.extend.discoverer import Discoverer
from twisted.internet import reactor, defer
from flumotion.common import common, log
from flumotion.transcoder import config, trans

usage="usage: flumotion-transcoder-job [OPTIONS] CONF-FILE INPUT-FILE PROFILE1 PROFILE2..."

GET_REQUEST_TIMEOUT = 60

class Job(log.Loggable):
    def __init__(self, infile, customer, profiles):
        self.processing = infile
        self.config = customer
        self.profiles = profiles
        self.unrecognized_outputs = []
        self.pending_outputs = []

        for profile in self.profiles:
            outfile = self.get_output_filename(profile)
            self.pending_outputs.append(outfile)

    def get_output_filename(self, profile):
        """
        Returns the output filename for the given profile.
        The returned filename is the basename, it does not contain the full
        path.
        """
        return profile.getOutputBasename(self.processing)

    def fail(self, message):
        self.warning('Error processing %s: %s', self.processing,
                     message)
        print 'Error processing %s\n' % self.processing
        print message
        sys.exit(1)

    def finish(self):
        if not self.unrecognized_outputs:
            print 'Success processing %s' % self.processing
            sys.exit(0)
        else:
            print 'Some outputs failed: %r' % ([p.name for p in
                                                self.unrecognized_outputs],)
            sys.exit(2)

    def start(self):
        name = os.path.basename(self.processing)
        mt = trans.MultiTranscoder(name, self.processing)
        for profile in self.profiles:
            outputFilename = self.get_output_filename(profile)
            outputPath = os.path.join(self.config.workDir, outputFilename)
            mt.addOutput(outputPath, profile)

        mt.connect('done', self.transcode_done)
        mt.connect('error', self.transcode_error)
        mt.start()

    def transcode_done(self, mt):
        if self.config.linkDir:
            for profile in self.profiles:
                workfile = os.path.join(self.config.workDir,
                                        self.get_output_filename(profile))
                self.debug("Analyzing transcoded file '%s'", workfile)
                discoverer = Discoverer(workfile)
                discoverer.connect('discovered',
                                   self.output_discovered, profile,
                                   mt._discoverer.is_audio,
                                   mt._discoverer.is_video)
                discoverer.discover()
        else:
            self.finish()

    def transcode_error(self, mt, message):
        self.fail(message)

    def output_discovered(self, discoverer, ismedia, profile, is_audio,
                          is_video):
        if ismedia and (discoverer.is_audio == is_audio
                        and discoverer.is_video == is_video):
            args = self.output_recognized(profile, discoverer)
            if args and self.config.getRequest:
                d = self.perform_get_request(profile, *args)
                d.addCallback(lambda _: self.move_output_file(profile))
            else:
                self.move_output_file(profile)
        else:
            self.warning("Couldn't recognize the output for profile %s",
                         profile.name)
            if ismedia:
                gota, gotv = discoverer.is_audio, discoverer.is_video
                self.warning("Expected %saudio and %svideo, but got "
                             "%saudio and %svideo", is_audio or 'no ',
                             is_video or 'no ', gota or 'no ', gotv or
                             'no ')
            self.unrecognized_outputs.append(profile)
            self.move_output_file(profile)

    def output_recognized(self, profile, discoverer):
        relpath = self.get_output_filename(profile)
        workfile = os.path.join(self.config.workDir, relpath)
        self.debug("Work file '%s' has mime type %s", workfile,
                   discoverer.mimetype)
        if discoverer.mimetype != 'application/ogg':
            self.debug("File '%s' not an ogg file, not writing link" %
                workfile)
            return None
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
        argString = "&".join("%s=%s" % (k, v) for (k, v) in args.items())
        outRelPath = self.get_output_filename(profile)
        link = self.config.urlPrefix + outRelPath + ".m3u?" + argString
        # make sure we have width and height for audio too
        if not args.has_key('c-width'):
            args['c-width'] = 320
        if not args.has_key('c-height'):
            args['c-height'] = 40

        linkPath = os.path.join(self.config.linkDir, outRelPath) + '.link'
        handle = open(linkPath, 'w')
        handle.write(
            '<iframe src="%s" width="%s" height="%s" '
            'frameborder="0" scrolling="no" '
            'marginwidth="0" marginheight="0" />\n' % (
                link, args['c-width'], args['c-height']))
        handle.close()
        self.info("Written link file %s" % linkPath)
        return args, duration

    def perform_get_request(self, profile, args, duration):
        self.debug('Preparing get request')
        args = args.copy()
        outRelPath = self.get_output_filename(profile)
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

        url = self.config.getRequest % args

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

        def getPageEb(failure, url, triesLeft):
            if triesLeft == 0:
                self.warning('Could not inform server for %s' % outRelPath)
                return
            self.debug('failure: %s' % log.getFailureMessage(failure))
            triesLeft -= 1
            self.debug('%d tries left' % triesLeft)
            self.info('Could not do get request for %s, '
                'trying again in %d seconds' % (
                    outRelPath, GET_REQUEST_TIMEOUT))
            d = defer.Deferred()
            d.addCallback(lambda _: doGetRequest(url, triesLeft))
            reactor.callLater(GET_REQUEST_TIMEOUT, d.callback(None))
            return d

        return doGetRequest(url)

    def move_output_file(self, profile):
        """
        move the output file from the work directory to the output directory.
        """
        outRelPath = self.get_output_filename(profile)
        workfile = os.path.join(self.config.workDir, outRelPath)
        outfile = os.path.join(self.config.outputDir, outRelPath)
        try:
            shutil.move(workfile, outfile)
        except IOError, e:
            self.warning('Could not save transcoded file: %s',
                         log.getExceptionMessage(e))

        self.pending_outputs.remove(outRelPath)
        if not self.pending_outputs:
            self.debug('Totally finished dude')
            self.finish()

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
