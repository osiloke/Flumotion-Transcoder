================================
Flumotion Transcoder Instalation
================================

Prerequisites
=============

The transcoder needs other software in order to properly work:

  - Python > 2.4
  - GStreamer > 0.10.12
  - GStreamer Plugins
  - GStreamer Python Bindings (gst-python) > 0.10.6
  - Twisted >= 2.4
  - Flumotion > 0.4.2.1


Fluendo Packages
----------------

When using the RPM packages build at Fluendo, the exaustive list 
of packages installed on the flumotion platform is:

  - flumotion
  - gstreamer
  - gstreamer-plugins-base
  - gstreamer-plugins-good
  - gstreamer-plugins-bad
  - gstreamer-plugins-ugly
  - gstreamer-plugins-amrwb
  - gstreamer-python
  - gstreamer-tools
  - gstreamer-ffmpeg
  - gstreamer-pitfdll
  - win32-codecs
  - win32-codecs-encoders
  - gstreamer-fluendo-asfdemux
  - gstreamer-fluendo-asfmux
  - gstreamer-fluendo-flvmux
  - gstreamer-fluendo-isodemux
  - gstreamer-fluendo-mpeg2video
  - gstreamer-fluendo-mpegdemux
  - gstreamer-fluendo-qcp
  - gstreamer-fluendo-wmadec
  - gstreamer-fluendo-wmaenc
  - gstreamer-fluendo-wmvdec

To install all these packages use the following command::

  yum install flumotion gstreamer gstreamer-plugins-base \
  gstreamer-plugins-good gstreamer-plugins-bad gstreamer-plugins-ugly \
  gstreamer-plugins-amrwb gstreamer-python gstreamer-tools \
  gstreamer-ffmpeg gstreamer-pitfdll win32-codecs win32-codecs-encoders \
  gstreamer-fluendo-asfdemux gstreamer-fluendo-asfmux gstreamer-fluendo-flvmux \
  gstreamer-fluendo-isodemux gstreamer-fluendo-mpeg2video \
  gstreamer-fluendo-mpegdemux gstreamer-fluendo-qcp gstreamer-fluendo-wmadec \
  gstreamer-fluendo-wmaenc gstreamer-fluendo-wmvdec

To install the debug packages use the following command::

  yum install flumotion-debuginfo gstreamer-debuginfo \
  gstreamer-plugins-base-debuginfo gstreamer-plugins-good-debuginfo \
  gstreamer-plugins-bad-debuginfo gstreamer-plugins-ugly-debuginfo \
  gstreamer-plugins-amrwb-debuginfo gstreamer-python-debuginfo \
  gstreamer-ffmpeg-debuginfo gstreamer-pitfdll-debuginfo \
  gstreamer-fluendo-asfdemux-debuginfo gstreamer-fluendo-asfmux-debuginfo \
  gstreamer-fluendo-flvmux-debuginfo gstreamer-fluendo-isodemux-debuginfo \
  gstreamer-fluendo-mpeg2video-debuginfo gstreamer-fluendo-mpegdemux-debuginfo \
  gstreamer-fluendo-qcp-debuginfo gstreamer-fluendo-wmadec-debuginfo \
  gstreamer-fluendo-wmaenc-debuginfo gstreamer-fluendo-wmvdec-debuginfo

Build From Sources
==================

Checkout the Sources::

  $ svn checkout svn+ssh://svn@code.area51.fluendo.com/private/flumotion-advanced/flumotion-transcoder/trunk

Generate the Makefiles::

  $ cd trunk
  $ ./autogen.sh

Build the Transcoder::

$ ./make

