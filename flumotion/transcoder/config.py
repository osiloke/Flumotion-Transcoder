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
import ConfigParser

from flumotion.common import log

class SectionParser(log.Loggable):
    def parseFromTable(self, name, table, confDict):
        for k, (attr, required, parser, default) in table.items():
            if required and k not in confDict:
                raise TypeError, ('While parsing %s: missing required '
                                  'key %s' % (name, k))
            setattr(self, attr, default)

        for k, v in confDict.items():
            try:
                attr, required, parser, default = table[k]
            except KeyError:
                raise KeyError, \
                      'Unknown conf key for %s: %s' % (name, k)
            setattr(self, attr, parser(v))
            self.log('%s = %r', attr, parser(v))
        
class Profile(SectionParser):
    """
    Encoding profile, describing settings for audio and video.

    @param name:         name of the configuration, must be unique in the task
    @param audioencoder: name and parameters of the audio encoder (gst-launch
                         syntax)
    @param videoencoder: name and parameters of the video encoder (gst-launch
                         syntax)
    @param muxer:        name and parameters of the muxer (gst-launch syntax)
    @param extension:    extension to give to the output files
    
    @param videowidth:      Width of the output video
    @param videoheight:     Height of the output video
    @param maxwidth:        Maximum width of the output video
    @param maxheight:       Maximum height of the output video
    @param videopar:        Pixel Aspect Ratio of the output video
    @type  videopar:        2-tuple of int
    @param videoframerate:  Framerate of the output video
    @type  videoframerate:  2-tuple of int
    @param audiorate:       Sampling rate of the output audio
    @param audiochannels:   Number of audio channels
    """
    def __init__(self, name, confDict):
        def fraction(str):
            num, denom = str.split('/')
            return int(num), int(denom)
        parseTable = {'audioencoder': ('audioencoder', True, str, None),
                      'videoencoder': ('videoencoder', True, str, None),
                      'muxer': ('muxer', True, str, None),
                      'extension': ('extension', True, str, None),
                      'videowidth': ('videowidth', False, int, None),
                      'videoheight': ('videoheight', False, int, None),
                      'maxwidth': ('maxwidth', False, int, None),
                      'maxheight': ('maxheight', False, int, None),
                      'videopar': ('videopar', False, fraction, None),
                      'videoframerate': ('videoframerate', False, fraction, None),
                      'audiorate': ('audiorate', False, int, 30),
                      'audiochannels': ('audiochannels', False, int, 30)}

        self.name = name
        self.parseFromTable(name, parseTable, confDict)

class Customer(SectionParser):
    def __init__(self, name, confDict):
        parseTable = {'inputdirectory': ('inputDir', True, str, None),
                      'outputdirectory': ('outputDir', True, str, None),
                      'workdirectory': ('workDir', False, str, None),
                      'linkdirectory': ('linkDir', False, str, None),
                      'errordirectory': ('errorDir', False, str, None),
                      'urlprefix': ('urlPrefix', False, str, None),
                      'getrequest': ('getRequest', False, str, None),
                      'timeout': ('timeout', False, int, 30),
                      'priority': ('priority', False, int, 50)}

        self.name = name
        # profile name -> profile
        self.profiles = {}

        self.parseFromTable(name, parseTable, confDict)

    def ensureDirs(self):
        __pychecker__ = 'no-classattr'
        for path in (self.inputDir, self.outputDir, self.linkDir,
                     self.workDir, self.errorDir):
            if path and not os.path.isdir(path):
                self.debug("Creating directory '%s'", path)
                try:
                    os.makedirs(path)
                except OSError, e:
                    self.warning("Could not create directory '%s'",
                                 path)
                    self.debug(log.getExceptionMessage(e))
                    raise

    def addProfile(self, profile):
        """
        Add a profile to the customer.
        """
        self.profiles[profile.name] = profile

class Config(SectionParser):
    def __init__(self, confFile):
        self.confFile = confFile
        self.customers = {}

        self.parse()

    def parse(self):
        parser = ConfigParser.ConfigParser()
        if not parser.read(self.confFile):
            raise RuntimeError, 'could not read conf file %s' % self.confFile
        sections = parser.sections()
        sections.sort()

        for section in sections:
            # set raw True so we can have getrequest contain %
            contents = dict(parser.items(section, raw=True))

            if ':' not in section:
                if section.lower() == 'global':
                    # the global configuration
                    parseTable = {'maxjobs': ('maxJobs', False, int, 1)}
                    self.parseFromTable('global', parseTable, contents)
                else:
                    # a customer
                    self.customers[section] = Customer(section, contents)
            else:
                # a profile section
                customerName, profileName = section.split(':')
                customer = self.customers[customerName]
                customer.addProfile(Profile(profileName, contents))
