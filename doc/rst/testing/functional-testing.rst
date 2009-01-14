=============================
Transcoder Functional Testing
=============================

.. sectnum::

.. contents::

Where
=====

The functional testing must be done on the development cluster.
All package to be used in production after the release must be installed
on each development machines. This includes flumotion, flumotion-inhouse,
flumotion-transcoder, gstreamer and all gstreamer's plugins.

Configuration
=============

Shares Configuration
--------------------

All machines must mount a NFS share for */home/file*, */var/tmp/flumotion*
and */var/log/flumotion*. The file */etc/fstab* should contains::

  h01.dev.fluendo.lan:/mnt/backup/repeater.dev/home/file /home/file nfs defaults,tcp,hard,intr,rw,user,port=2049 0 0
  h01.dev.fluendo.lan:/mnt/backup/repeater.dev/home/file/shared/$HOSTNAME/temp /var/tmp/flumotion nfs defaults,tcp,hard,intr,rw,user,port=2049 0 0
  h01.dev.fluendo.lan:/mnt/backup/repeater.dev/home/file/shared/$HOSTNAME/logs /var/log/flumotion nfs defaults,tcp,hard,intr,rw,user,port=2049 0 0

Where *$HOSTNAME* is the short hostname for the machine:

 - *admin1.p4.fsp*
 - *manager1.p4.fsp*
 - *gk1.p4.fsp*
 - *gk2.p4.fsp*
 - *repeater001.p4.fsp*
 - *repeater002.p4.fsp*
 - *streamer001.p4.fsp*
 - *streamer002.p4.fsp*

Mount the shares::

 mount -a

The transcoder administration configuration files to use for
functional testing can be found at::

  /home/file/testing/transcoder/configs/functional

The transcoding profiles used during functional testing can be found at::

  /home/file/testing/transcoder/profiles/functional


Admin Configuration
-------------------

On *admin.p4.fsp.fluendo.lan* the configration for functional
testing must be setup.

The easiest way to configure the transcoder to use these files are
to change the configuration file to use in the file::

  /etc/sysconfig/flumotion-transcoder-admin

Update the variable *TRANSCODER_CONFIG* this way (don't forget to uncomment)::

  TRANSCODER_CONFIG=/home/file/testing/transcoder/configs/functional/transcoder-admin.ini


Test Media
==========

The input files must be taken from the media set described
in `Testing Media Sets`_, but the original files must not
be moved but copied or linked. Then the testing files can
freely be moved around. This is to prevent loosing track
of the media sets files.

Before Every Tests
==================

Before every tests, the installation must be left in a clean
state. For this the scripts in */home/file/testing/transcoder/bin*
can be used:

*stop-all*:

  It will stops every services related to the transcoder,
  admin, workers and manager on the corresponding machines.
  It can be executed from any machin including your local
  machine, and if not executed as root, the *-u* option
  sould be used:: 

    /home/file/testing/transcoder/bin/stop-all -u root
 
*cleanup-all*:

  It will clean all transcoder files on the different machines.
  **WARNING**: this command will delete the **flumotion log files**,
  the **core files** in */var/cache/flumotion*, the
  **flumotion temporary files** and the transcoder admin
  **activities**. If some of these files must be keeped, they must
  by copied to a safe place before running this command.
  It can be executed from any machin including your local
  machine, and if not executed as root, the *-u* option
  sould be used:: 

    /home/file/testing/transcoder/bin/cleanup-all -u root

*start-all*:

  It will starts every transcoder related services, manager,
  workers and admin on the corresponding machines
  It can be executed from any machin including your local
  machine, and if not executed as root, the *-u* option
  sould be used:: 

    /home/file/testing/transcoder/bin/start-all -u root

Flumotion Admin
===============

To start the flumotion admin UI and connect to the mananger
use the following command on your local machine::

  flumotion-admin -m user:test@manager1.p4.fsp:7632

Test Cases
==========

Simple Transcoding
------------------

Profile to use: *basic.ini*

+----------------------------------------------------------------------------+------------------------------+
|Action                                                                      |Expectation                   |
+============================================================================+==============================+
|Cleanup                                                                     |                              |
+----------------------------------------------------------------------------+------------------------------+
|Start flumotion-admin                                                       |A *file-monitor* component    |
|                                                                            |should be running.            |
+----------------------------------------------------------------------------+------------------------------+
|Copy an audio file to                                                       |The file should be detected in|
|*/home/file/testing/transcoder/roots/functional/basic/files/incoming/audio*.|at most 5 seconds.            |
+----------------------------------------------------------------------------+------------------------------+
|                                                                            |A *file-transcoder* copmonent |
|                                                                            |should be started after a     |
|                                                                            |maximum of 10 seconds.        |
+----------------------------------------------------------------------------+------------------------------+
|Wait                                                                        |- The transcoding task should |
|                                                                            |succeed, the *file-transcoder*|
|                                                                            |component should desapear, and|
|                                                                            |the *file-monitor* component  |
|                                                                            |list of files should be empty.|
+----------------------------------------------------------------------------+------------------------------+

Killing a *file-monitor*
------------------------

Profile to use: *basic.ini*

+----------------------------------------------------------------------------+------------------------------+
|Action                                                                      |Expectation                   |
+============================================================================+==============================+
|Cleanup                                                                     |                              |
+----------------------------------------------------------------------------+------------------------------+
|Start flumotion-admin                                                       |A *file-monitor* component    |
|                                                                            |should be running.            |
+----------------------------------------------------------------------------+------------------------------+
|Look at the host and PID of the *file-monitor* component, and kill the      |The component should goes     |
|process with *kill -KILL $PID*                                              |*sad*, and a new one should be|
|                                                                            |started.                      |
+----------------------------------------------------------------------------+------------------------------+
|Kill newly started components tree times.                                   |Each times the component      |
|                                                                            |should goes *sad* and a new   |
|                                                                            |one should be started         |
|                                                                            |automaticaly.                 |
+----------------------------------------------------------------------------+------------------------------+

Blocking a *file-transcoder*
----------------------------

+----------------------------------------------------------------------------+------------------------------+
|Action                                                                      |Expectation                   |
+============================================================================+==============================+
|Cleanup                                                                     |                              |
+----------------------------------------------------------------------------+------------------------------+
|Start flumotion-admin                                                       |A *file-monitor* component    |
|                                                                            |should be running.            |
+----------------------------------------------------------------------------+------------------------------+
|Transcode an audio file (See 'Simple Transcoding`_)                         |Transcoding should succeed.   |
+----------------------------------------------------------------------------+------------------------------+
|Look at the host and PID of the *file-monitor* component, and stop the      |Nothing append right away.    |
|process with *kill -STOP $PID*                                              |                              |
+----------------------------------------------------------------------------+------------------------------+
|Wait ~ 30 seconds.                                                          |The component should goes     |
|                                                                            |*lost*.                       |
+----------------------------------------------------------------------------+------------------------------+
|Resume the component's process with *kill -CONT $PID*.                      |The component should goes     |
|                                                                            |happy again.                  |
+----------------------------------------------------------------------------+------------------------------+
|Transcode an audio file (See 'Simple Transcoding`_)                         |Transcoding should succeed.   |
+----------------------------------------------------------------------------+------------------------------+
|Stop the process again with *kill -STOP $PID*                               |                              |
+----------------------------------------------------------------------------+------------------------------+
|Wait ~ 30 seconds.                                                          |The component should goes     |
|                                                                            |*lost*.                       |
+----------------------------------------------------------------------------+------------------------------+
|Wait ~ 60 seconds more.                                                     |A new monitor component should|
|                                                                            |be started automicaly.        |
+----------------------------------------------------------------------------+------------------------------+
|Transcode an audio file (See 'Simple Transcoding`_)                         |Transcoding should succeed.   |
+----------------------------------------------------------------------------+------------------------------+
|Resume the stopped component with *kill -CONT $PID*.                        |The lost component should goes|
|                                                                            |happy again, and then is      |
|                                                                            |should be automaticaly stoped |
|                                                                            |and deleted.                  |
+----------------------------------------------------------------------------+------------------------------+
|Transcode an audio file (See 'Simple Transcoding`_)                         |Transcoding should succeed.   |
+----------------------------------------------------------------------------+------------------------------+


.. _Testing Media Sets: media-sets.rst
