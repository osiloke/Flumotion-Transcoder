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

class SectionParser(object):

    def __init__(self, logger):
        self.logger = logger

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

def bool(s):
    if s.lower() in ("1", "true", "yes"):
        return True
    if s.lower() in ("0", "false", "no"):
        return False
    raise TypeError("Invalid boolean value '%s'" % s)

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
    @param sizemultiple:    The multiple of the height and width.
    @param videopar:        Pixel Aspect Ratio of the output video
    @type  videopar:        2-tuple of int
    @param videoframerate:  Framerate of the output video
    @type  videoframerate:  2-tuple of int
    @param audiorate:       Sampling rate of the output audio
    @param audiochannels:   Number of audio channels
    @param getrequest:      URL to be call for each target completed
    @param postprocess:     Command line to call for inplace post-process,
                            %(file)s will be replaced by the full path of the file.
                            %(relFile)s will be replaced by the relative path of the file.
                            %(inputRoot)s will be replaced by the incoming root directory.
                            %(outputRoot)s will be replaced by the outgoing root directory.
                            %(errorRoot) will be replaced by the errors root directory.
                            %(linkRoot) will be replaced by the links root directory.
                            %(workRoot) will be replaced by the working root directory.
    """
    def __init__(self, logger, name, confDict):
        SectionParser.__init__(self, logger)
        def fraction(str):
            num, denom = str.split('/')
            return int(num), int(denom)
        parseTable = {'mimecopy': ('mimeCopy', False, str, None),
                      'audioencoder': ('audioencoder', True, str, None),
                      'videoencoder': ('videoencoder', True, str, None),
                      'muxer': ('muxer', True, str, None),
                      'extension': ('extension', True, str, None),
                      'videowidth': ('videowidth', False, int, None),
                      'videoheight': ('videoheight', False, int, None),
                      'maxwidth': ('maxwidth', False, int, None),
                      'maxheight': ('maxheight', False, int, None),
                      'sizemultiple': ('sizemultiple', False, int, 1),
                      'videopar': ('videopar', False, fraction, None),
                      'videoframerate': ('videoframerate', False, fraction, None),
                      'audiorate': ('audiorate', False, int, None),
                      'audiochannels': ('audiochannels', False, int, None),
                      'postprocess': ('postprocess', False, str, None),
                      'appendext': ('appendExt', False, bool, False),
                      'getrequest': ('getRequest', False, str, None)}

        self.name = name
        self.parseFromTable(name, parseTable, confDict)

    def getOutputBasename(self, filename):
        """
        Returns the output basename for the given input file. This is
        done by taking the basename of the input file and adding
        our own extension.
        """
        if self.appendExt:
            return'.'.join([os.path.basename(filename), self.extension])
        else:
            prefix = os.path.basename(filename).rsplit('.', 1)[0]
            return '.'.join([prefix, self.extension])

class Customer(SectionParser):
    def __init__(self, logger, name, confDict):
        SectionParser.__init__(self, logger)
        parseTable = {'inputdirectory': ('inputDir', True, str, None),
                      'outputdirectory': ('outputDir', True, str, None),
                      'workdirectory': ('workDir', False, str, None),
                      'linkdirectory': ('linkDir', False, str, None),
                      'errordirectory': ('errorDir', False, str, None),
                      'urlprefix': ('urlPrefix', False, str, None),
                      'getrequest': ('getRequest', False, str, None),
                      'errgetreq': ('errGetRequest', False, str, None),
                      'errmail': ('errMail', False, str, None),
                      'timeout': ('timeout', False, int, 30),
                      'pptimeout': ('ppTimeout', False, int, 60),
                      'gettimeout': ('getTimeout', False, int, 60),
                      'transtimeout': ('transTimeout', False, int, 30),
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
                self.logger.debug("Creating directory '%s'", path)
                try:
                    os.makedirs(path)
                except OSError, e:
                    self.logger.warning("Could not create directory '%s'",
                                        path)
                    raise

    def alreadyProcessedFiles(self):
        def all(proc, seq):
            return (not seq) or (proc(seq[0]) and all(proc, seq[1:]))
        def outExists(profile, path):
            outFile = os.path.join(self.outputDir,
                                   profile.getOutputBasename(path))
            return os.path.exists(outFile)
        ret = []
        for infile in os.listdir(self.inputDir):
            if all(lambda p: outExists(p, infile), self.profiles.values()):
                self.logger.debug('%s was already processed, ignoring', infile)
                ret.append(infile)
        return ret

    def addProfile(self, profile):
        """
        Add a profile to the customer.
        """
        self.profiles[profile.name] = profile

class Config(SectionParser):
    def __init__(self, logger, confFile):
        SectionParser.__init__(self, logger)
        self.confFile = confFile
        self.customers = {}

        self.parse()

    def parse(self):
        parser = ConfigParser.ConfigParser()
        if not parser.read(self.confFile):
            raise RuntimeError, 'could not read conf file %s' % self.confFile
        sections = parser.sections()
        sections.sort()

        globalParseTable = {'maxjobs': ('maxJobs', False, int, 1),
                            'gstdebug': ('gstDebug', False, str, None),
                            'groupname': ('groupName', False, str, None),
                            'maxinterleave': ('maxInterleave', False, float, 1.0)}
        self.parseFromTable('global', globalParseTable, {})

        for section in sections:
            # set raw True so we can have getrequest contain %
            contents = dict(parser.items(section, raw=True))

            if ':' not in section:
                if section.lower() == 'global':
                    # the global configuration
                    self.parseFromTable('global', globalParseTable,
                                        contents)
                else:
                    # a customer
                    self.customers[section] = Customer(self.logger, section, contents)
            else:
                # a profile section
                customerName, profileName = section.split(':')
                customer = self.customers[customerName]
                customer.addProfile(Profile(self.logger, profileName, contents))
