========================
Configure the Transcoder
========================

.. sectnum::

.. contents::

Target Configuration
====================

Specifications
~~~~~~~~~~~~~~

Section *profile:P*
----------------------

This section describes transcoding profile called "P".

Property *transcoding-priority*
...............................

Specify the profile priority.

The value is an integer between 0 and 999, and define
the relative priority between profiles of a same customer.

If the value is not specified in profile or transcoder config, the
default value will be::

  100

Usage example::

  transcoding-priority = 500

Property *notify-failed-mail-recipient*
.......................................

Specify the mail recipient in case of transcoding error. Example::

  notify-failed-mail-recipient = transcoder-failure@test.lan

Section *profile:P:target:T*
--------------------------------

Describe a target "T" for profile "P".

Property *type*
...............

Specify target type, either::

  Audio
  Video
  Audio/Video

If you want video-only transcoding, the type should be::

  type = Video

Property *extension*
....................

Target filename extension.

Example::

  extension = flv

Section *profile:P:target:T:config*
--------------------------------------

Configure the target "T" (of profile "P").

Property *video-encoder*
........................

GStreamer video encoder element configuation::

  video-encoder = flumch264enc bitrate=50000 profile=flash_low

Property *audio-encoder*
........................

GStreamer audio encoder element configuation::

  audio-encoder = flumcaacenc he=hev2 bitrate=12000 header-type=raw

