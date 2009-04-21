===========================================
Flumotion Transcoder Production Instalation
===========================================

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
  - flumotion-inhouse
  - flumotion-transcoder
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
  - gstreamer-fluendo-aacdec
  - gstreamer-fluendo-ac3dec
  - gstreamer-fluendo-asfdemux
  - gstreamer-fluendo-asfmux
  - gstreamer-fluendo-flvmux
  - gstreamer-fluendo-h264dec
  - gstreamer-fluendo-isodemux
  - gstreamer-fluendo-lpcmdec
  - gstreamer-fluendo-mcaacenc
  - gstreamer-fluendo-mch264enc
  - gstreamer-fluendo-mpeg2video
  - gstreamer-fluendo-mpeg4video
  - gstreamer-fluendo-mpegdemux
  - gstreamer-fluendo-qcp
  - gstreamer-fluendo-sorensondec
  - gstreamer-fluendo-vp6dec
  - gstreamer-fluendo-vp6enc
  - gstreamer-fluendo-wmadec
  - gstreamer-fluendo-wmaenc
  - gstreamer-fluendo-wmvdec
  - gstreamer-fluendo-wmvenc
  - mmf-crc
  - flvlib
  - python-twisted-core
  - python-twisted-names
  - python-twisted-mail
  - python-twisted-web

To install all these packages use the following command::

  yum install flumotion flumotion-inhouse flumotion-transcoder gstreamer \
  gstreamer-plugins-base gstreamer-plugins-good gstreamer-plugins-bad \
  gstreamer-plugins-ugly gstreamer-python gstreamer-tools gstreamer-ffmpeg \
  gstreamer-pitfdll win32-codecs win32-codecs-encoders \
  gstreamer-fluendo-aacdec gstreamer-fluendo-ac3dec \
  gstreamer-fluendo-asfdemux gstreamer-fluendo-asfmux \
  gstreamer-fluendo-flvmux gstreamer-fluendo-h264dec \
  gstreamer-fluendo-isodemux gstreamer-fluendo-lpcmdec \
  gstreamer-fluendo-mcaacenc gstreamer-fluendo-mch264enc \
  gstreamer-fluendo-mpeg2video gstreamer-fluendo-mpeg4video \
  gstreamer-fluendo-mpegdemux gstreamer-fluendo-qcp \
  gstreamer-fluendo-sorensondec gstreamer-fluendo-vp6dec \
  gstreamer-fluendo-vp6enc gstreamer-fluendo-wmadec gstreamer-fluendo-wmaenc\
  gstreamer-fluendo-wmvdec gstreamer-fluendo-wmvenc mmf-crc flvlib \
  python-twisted-core python-twisted-names python-twisted-mail \
  python-twisted-web

To install the debug packages use the following command::

  yum install flumotion-debuginfo flumotion-inhouse-debuginfo \
  flumotion-transcoder-debuginfo gstreamer-debuginfo \
  gstreamer-plugins-base-debuginfo gstreamer-plugins-good-debuginfo \
  gstreamer-plugins-bad-debuginfo gstreamer-plugins-ugly-debuginfo \
  gstreamer-python-debuginfo gstreamer-ffmpeg-debuginfo \
  gstreamer-tools-debuginfo gstreamer-pitfdll-debuginfo \
  win32-codecs-debuginfo win32-codecs-encoders-debuginfo


Database connection configuration
---------------------------------

Before running the transcoder you need to configure the database connection, as
described in `Transcoder Admin Configuration`_. Make sure you have a MySQL
database cluster running and you are able to connect to it from the transcoder
admin machine.

The database schema for the transcoder will be installed in::

  /usr/share/flumotion-transcoder-X.X.X.X/database/mysql

To create the database instance and the necessary tables you need to execute::

  cat /usr/share/flumotion-transcoder-X.X.X.X/database/mysql/preamble.sql \
      /usr/share/flumotion-transcoder-X.X.X.X/database/mysql/schema.sql \
      | mysql -h HOSTNAME -u USER

Where HOSTNAME and USER are the hostnmae of your database and the user you
will user to access the database. You might not have the permission to create
the transcoder database yourself, in which case you need to ask the DBA for
help.

Then you need to copy and modify the users configuration file::

  cp /usr/share/flumotion-transcoder-X.X.X.X/database/mysql/user_setup.sql ~
  vim user_setup.sql

Edit the line beginning with `grant` and set the password for the `transcoder`
user. Then create the `transcoder` user in the database and remove the modified
SQL script by running::

  cat /usr/share/flumotion-transcoder-X.X.X.X/database/mysql/preamble.sql \
      user_setup.sql | mysql -h HOSTNAME -u USER
  rm user_setup.sql

Here also you need to provide the correct hostname and username for the
database connection and ask the DBA for help if necessary.

Make sure to then set the correct password in the
`Transcoder Admin Configuration`_ file.

.. _Transcoder Admin Configuration: ../configuration/admin-config.rst
