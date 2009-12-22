========================
Configure the Transcoder
========================

.. sectnum::

.. contents::

Customer Configuration File
===========================

The customer configuration files are a hierarchy:

 - customer section
 - profile section
 - target section
 - target configuration

Some properties can be specified in more than one section.
For example, when a property value is needed for a target,
it's first lookup in target section, if not found, it's
lookup in profile section, then in customer section, and
if no value is found the default value is taken from the
file `transcoder-data.ini`_.

Configuration Example
~~~~~~~~~~~~~~~~~~~~~

Example files can be found in:

 - */usr/share/flumotion-transcoder-XXX/examples/customers/fluendo.ini*
   for the installed transcoder.
 - Sub-directory *doc/examples/customers/fluendo.ini*
   of the uninstalled transcoder.

::

  [HEADER]
  version = 1.1
  
  [global]
  name = Test Customer
  monitoring-period = 30
  post-process-timeout = 120
  post-process-command = index-flv -U %(outputWorkPath)s
  
  [profile:video]
  transcoding-priority = 200
  notify-failed-mail-recipient = transcoder-failure@test.lan
  
  [profile:video:target:high-flv]
  type = Audio/Video
  subdir = flv
  extention = high.flv
  post-processing-enabled = True
  output-file-template = %(targetDir)s%(sourceBasename)s%(targetExtension)s
  
  [profile:video:target:high-flv:config]
  audio-rate = 44100
  audio-channels = 2
  audio-encoder = lame bitrate=96 ! audio/mpeg,rate=44100 ! mp3parse
  video-framerate = 25/1
  video-width = 512
  video-height = 288
  video-par = 1/1
  video-encoder = videoflip method=5 ! fluvp6enc bitrate=750
  tolerance = Allow without audio

  [profile:video:target:low-flv]
  type = Audio/Video
  subdir = flv
  extention = low.flv
  post-processing-enabled = True
  output-file-template = %(targetDir)s%(sourceBasename)s%(targetExtension)s

  [profile:video:target:low-flv:config]
  audio-rate = 44100
  audio-channels = 2
  audio-encoder = lame bitrate=64 ! audio/mpeg,rate=44100 ! mp3parse
  video-framerate = 25/1
  video-width = 256
  video-height = 144
  video-par = 1/1
  video-encoder = videoflip method=5 ! fluvp6enc bitrate=350
  tolerance = Allow without audio

  [profile:video:target:asf]
  type = Audio/Video
  extention = asf
  output-file-template = %(targetDir)s%(sourceBasename)s%(targetExtension)s

  [profile:video:target:asf:config]
  audio-rate = 44100
  audio-channels = 2
  audio-encoder = fluwmaenc 64000
  video-framerate = 25/1
  video-width = 512
  video-height = 288
  video-par = 1/1
  video-encoder = fluwmvenc bitrate=750000
  tolerance = Allow without audio

  [profile:video:target:thumb]
  type = Thumbnails
  extention = jpg
  output-file-template = %(targetDir)s%(sourceBasename)s%(targetExtension)s

  [profile:video:target:thumb:config]
  period-value = 30
  period-unit = percent
  max-count = 1
  thumbs-width = 256
  thumbs-height = 144


.. _transcoder-data.ini: transcoder-config.rst
