# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.
# flumotion-platform - Flumotion Streaming Platform

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import common

import tempfile
import ConfigParser
import StringIO
from twisted.trial import unittest
from flumotion.transcoder import config

globalSection = """
[global]
maxjobs=3
"""

customer = """
[CustomerName]
# directory to monitor for incoming files
inputdirectory=/srv/flumotion/transcoder/CustomerName/incoming/
# directory where transcoded files will be placed
outputdirectory=/srv/flumotion/transcoder/CustomerName/outgoing/
# temporary work directory
workdirectory=/var/tmp/flumotion/transcoder/CustomerName
# directory where cortado links will be put
linkdirectory=/src/flumotion/transcoder/CustomerName/
# directory where incoming files with problems will be put
errordirectory=/srv/flumotion/transcoder/CustomerName/error/

# for integration with cortado, we can output URL's that can be used in an
# iframe
# the urlprefix should match the path to which the outputdirectory maps
urlprefix=http://gk.bcn.fluendo.net/CustomerName/

# on completion of transcoded files, we can also do a GET request on
# another site; this will be tried three times with one-minute intervals
getrequest=http://localhost/publish.php?video=%(incomingPath)s&duracion=%(hours)02d:%(minutes)02d:%(seconds)02d

# timeout in seconds for checking arrival of new files
timeout = 20
"""

smalloggprofile = """
[CustomerName:SmallOgg]
# the three following fields are gst-parse-launch compatible arguments
videoencoder = theoraenc quality=32
audioencoder = vorbisenc bitrate=32000
muxer = oggmux
extension = ogg

videoframerate = 25/2
videopar = 1/1
videowidth = 320
# since we dont specify videoheight, it will be calculated from the incoming
# video resolution and par and the output videopar and videowidth.
# The opposite would also be true if we had put videoheight and not
# videowidth.

audiorate=22050
"""

class TestConfigParser(unittest.TestCase):
    def testParseProfile(self):
        parser = ConfigParser.ConfigParser()
        f = StringIO.StringIO(smalloggprofile)
        parser.readfp(f)
        sections = parser.sections()
        self.assertEquals(sections, ['CustomerName:SmallOgg'])
        contents = dict(parser.items('CustomerName:SmallOgg', raw=True))
        c = config.Profile('SmallOgg', contents)
        ae = self.assertEquals
        ae(c.name, 'SmallOgg')
        ae(c.videoencoder, 'theoraenc quality=32')
        ae(c.audioencoder, 'vorbisenc bitrate=32000')
        ae(c.muxer, 'oggmux')
        ae(c.extension, 'ogg')
        ae(c.videoframerate, (25, 2))
        ae(c.videopar, (1, 1))
        ae(c.videowidth, 320)
        ae(c.audiorate, 22050)
        ae(c.getOutputBasename('foo.mp3'), 'foo.ogg')
        ae(c.getOutputBasename('foo.bar.mp3'), 'foo.bar.ogg')
        ae(c.getOutputBasename('/krazy/path/foo.bar.mp3'), 'foo.bar.ogg')

    def testParseCustomer(self):
        parser = ConfigParser.ConfigParser()
        f = StringIO.StringIO(customer)
        parser.readfp(f)
        sections = parser.sections()
        self.assertEquals(sections, ['CustomerName'])
        contents = dict(parser.items('CustomerName', raw=True))
        c = config.Customer('CustomerName', contents)
        ae = self.assertEquals
        ae(c.name, 'CustomerName')
        ae(c.inputDir, '/srv/flumotion/transcoder/CustomerName/incoming/') 
        ae(c.outputDir, '/srv/flumotion/transcoder/CustomerName/outgoing/') 
        ae(c.workDir, '/var/tmp/flumotion/transcoder/CustomerName') 
        ae(c.linkDir, '/src/flumotion/transcoder/CustomerName/') 
        ae(c.errorDir, '/srv/flumotion/transcoder/CustomerName/error/') 
        ae(c.urlPrefix, 'http://gk.bcn.fluendo.net/CustomerName/') 
        ae(c.getRequest, 'http://localhost/publish.php?video=%(incomingPath)s&duracion=%(hours)02d:%(minutes)02d:%(seconds)02d') 
        ae(c.timeout, 20)

    def testParseFull(self):
        tmp = tempfile.NamedTemporaryFile()
        tmp.write(globalSection + customer + smalloggprofile)
        tmp.flush()
        conf = config.Config(tmp.name)
        # makes the file will go away
        del tmp

        self.assertEquals(conf.customers.keys(), ['CustomerName'])
        self.assertEquals(conf.customers['CustomerName'].profiles.keys(),
                          ['SmallOgg'])
        self.assertEquals(conf.maxJobs, 3)
