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
  - gstreamer-fluendo-mcaacdec
  - gstreamer-fluendo-mcaacenc
  - gstreamer-fluendo-mch264dec
  - gstreamer-fluendo-mch264enc
  - gstreamer-fluendo-mpeg2video
  - gstreamer-fluendo-mpeg4video
  - gstreamer-fluendo-mpegdemux
  - gstreamer-fluendo-qcp
  - gstreamer-fluendo-vp6enc
  - gstreamer-fluendo-wmadec
  - gstreamer-fluendo-wmaenc
  - gstreamer-fluendo-wmvdec
  - gstreamer-fluendo-wmvenc
  

To install all these packages use the following command::

  yum install flumotion gstreamer gstreamer-plugins-base \
  gstreamer-plugins-good gstreamer-plugins-bad gstreamer-plugins-ugly \
  gstreamer-python gstreamer-tools gstreamer-ffmpeg gstreamer-pitfdll \
  win32-codecs win32-codecs-encoders gstreamer-fluendo-asfdemux \
  gstreamer-fluendo-asfmux gstreamer-fluendo-flvmux \
  gstreamer-fluendo-isodemux gstreamer-fluendo-mcaacdec \
  gstreamer-fluendo-mcaacenc gstreamer-fluendo-mch264dec \
  gstreamer-fluendo-mch264enc gstreamer-fluendo-mpeg2video \
  gstreamer-fluendo-mpeg4video gstreamer-fluendo-mpegdemux \
  gstreamer-fluendo-qcp gstreamer-fluendo-vp6enc gstreamer-fluendo-wmadec \
  gstreamer-fluendo-wmaenc gstreamer-fluendo-wmvdec gstreamer-fluendo-wmvenc

To install the debug packages use the following command::

  yum install  flumotion-debuginfo gstreamer-debuginfo \
  gstreamer-plugins-base-debuginfo gstreamer-plugins-good-debuginfo \
  gstreamer-plugins-bad-debuginfo gstreamer-plugins-ugly-debuginfo \
  gstreamer-python-debuginfo gstreamer-tools-debuginfo \
  gstreamer-ffmpeg-debuginfo gstreamer-pitfdll-debuginfo \
  win32-codecs-debuginfo win32-codecs-encoders-debuginfo \
  gstreamer-fluendo-asfdemux-debuginfo gstreamer-fluendo-asfmux-debuginfo \
  gstreamer-fluendo-flvmux-debuginfo gstreamer-fluendo-isodemux-debuginfo \
  gstreamer-fluendo-mcaacdec-debuginfo gstreamer-fluendo-mcaacenc-debuginfo \
  gstreamer-fluendo-mch264dec-debuginfo \
  gstreamer-fluendo-mch264enc-debuginfo \
  gstreamer-fluendo-mpeg2video-debuginfo \
  gstreamer-fluendo-mpeg4video-debuginfo \
  gstreamer-fluendo-mpegdemux-debuginfo \
  gstreamer-fluendo-qcp-debuginfo \
  gstreamer-fluendo-vp6enc-debuginfo \
  gstreamer-fluendo-wmadec-debuginfo \
  gstreamer-fluendo-wmaenc-debuginfo \
  gstreamer-fluendo-wmvdec-debuginfo \
  gstreamer-fluendo-wmvenc-debuginfo
  

Build From Sources
==================

Checkout the Sources::

  $ svn checkout svn+ssh://svn@code.area51.fluendo.com/private/flumotion-advanced/flumotion-transcoder/trunk

Generate the Makefiles::

  $ cd trunk
  $ ./autogen.sh

Build the Transcoder::

$ ./make

