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

The input files must be taken from the media sets described
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

Testing Profiles
================

Basic Profile
-------------

This profile configration can be found at::

  /home/file/testing/transcoder/profiles/functional/basic.ini

The incoming directory is::

  /home/file/testing/transcoder/roots/functional/files/incoming/audio

Test Cases
==========

Simple Transcoding
------------------

Profile to use: *basic.ini*

+------------------------------------------------------------------+------------------------------+
|Action                                                            |Expectation                   |
+==================================================================+==============================+
|                                                                  |A *file-monitor* component for|
|                                                                  |the profile *basic* is running|
|                                                                  |and happy, and it doesn't have|
|                                                                  |any files pending or queued.  |
+------------------------------------------------------------------+------------------------------+
|Copy an audio file to the audio incoming of the profile *basic*.  |The file should be detected in|
|                                                                  |at most 10 seconds.           |
+------------------------------------------------------------------+------------------------------+
|                                                                  |A *file-transcoder* copmonent |
|                                                                  |should be started after a     |
|                                                                  |maximum of 20 seconds.        |
+------------------------------------------------------------------+------------------------------+
|Wait                                                              |The transcoding task should   |
|                                                                  |succeed, the *file-transcoder*|
|                                                                  |component should desapear and |
|                                                                  |the *file-monitor* component  |
|                                                                  |list of files should be empty.|
+------------------------------------------------------------------+------------------------------+

Killing a *file-monitor*
------------------------

Profile to use: *basic.ini*

+----------------------------------------------------------------------------+------------------------------+
|Action                                                                      |Expectation                   |
+============================================================================+==============================+
|                                                                            |A *file-monitor* component for|
|                                                                            |the profile *basic* is running|
|                                                                            |and happy, and it doesn't have|
|                                                                            |any files pending or queued.  |
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

Blocking a *file-monitor*
-------------------------

Profile to use: *basic.ini*

+----------------------------------------------------------------------------+------------------------------+
|Action                                                                      |Expectation                   |
+============================================================================+==============================+
|                                                                            |A *file-monitor* component for|
|                                                                            |the profile *basic* is running|
|                                                                            |and happy, and it doesn't have|
|                                                                            |any files pending or queued.  |
+----------------------------------------------------------------------------+------------------------------+
|Transcode an audio file (See `Simple Transcoding`_)                         |Transcoding should succeed.   |
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
|Transcode an audio file (See `Simple Transcoding`_)                         |Transcoding should succeed.   |
+----------------------------------------------------------------------------+------------------------------+
|Stop the process again with *kill -STOP $PID*                               |                              |
+----------------------------------------------------------------------------+------------------------------+
|Wait ~ 30 seconds.                                                          |The component should goes     |
|                                                                            |*lost*.                       |
+----------------------------------------------------------------------------+------------------------------+
|Wait ~ 60 seconds more.                                                     |A new monitor component should|
|                                                                            |be started automicaly.        |
+----------------------------------------------------------------------------+------------------------------+
|Transcode an audio file (See `Simple Transcoding`_)                         |Transcoding should succeed.   |
+----------------------------------------------------------------------------+------------------------------+
|Resume the stopped component with *kill -CONT $PID*.                        |The lost component should goes|
|                                                                            |happy again, and then is      |
|                                                                            |should be automaticaly stoped |
|                                                                            |and deleted.                  |
+----------------------------------------------------------------------------+------------------------------+
|Transcode an audio file (See 'Simple Transcoding`_)                         |Transcoding should succeed.   |
+----------------------------------------------------------------------------+------------------------------+

File Removed Before Transcoding
-------------------------------

Profile to use: *basic.ini*

+------------------------------+------------------------------+
|Actions                       |Expectations                  |
+==============================+==============================+
|                              |A *file-monitor* component for|
|                              |the profile *basic* is running|
|                              |and happy, and it doesn't have|
|                              |any files pending or queued.  |
+------------------------------+------------------------------+
|Copy a file to the incoming of|The file should be detected in|
|the profile *basic*           |less than 10 seconds.         |
+------------------------------+------------------------------+
|Remove the file from incoming |The file should desapear from |
|before the *file-transcoder*  |the monitor list, and no      |
|component got started (at most|transcoding component should  |
|10 seconds after detection)   |be started (wait a litle to be|
|                              |sure)                         |
+------------------------------+------------------------------+

File Removed After Transcoding Starts
-------------------------------------

Profile to use: *basic.ini*

+------------------------------+------------------------------+
|Actions                       |Expectations                  |
+==============================+==============================+
|                              |A *file-monitor* component for|
|                              |the profile *basic* is running|
|                              |and happy, and it doesn't have|
|                              |any files pending or queued.  |
+------------------------------+------------------------------+
|Copy an audio file to the     |The file should be detected in|
|audio incoming of the profile |less than 10 seconds.         |
|*basic*                       |                              |
+------------------------------+------------------------------+
|Wait for the *file-transcoder*|                              |
|component to be started.      |                              |
+------------------------------+------------------------------+
|Remove the file from incoming |The file should desapear from |
|before the *file-transcoder*  |the monitor list, and the     |
|component finish transcoding. |transcoding component should  |
|                              |be stoped and deleted.        |
+------------------------------+------------------------------+

Killing *file-transcoder* Components
------------------------------------

Profile to use: *basic.ini*

+------------------------------+------------------------------+
|Actions                       |Expectations                  |
+==============================+==============================+
|                              |A *file-monitor* component for|
|                              |the profile *basic* is running|
|                              |and happy, and it doesn't have|
|                              |any files pending or queued.  |
+------------------------------+------------------------------+
|Copy an audio file to the     |The file should be detected in|
|audio incoming of the profile |less than 10 seconds.         |
|*basic*                       |                              |
+------------------------------+------------------------------+
|Wait for the *file-transcoder*|                              |
|component to be started.      |                              |
+------------------------------+------------------------------+
|Kill the *file-transcoder*    |The component should goes     |
|copmonent with the command    |*sad*, and a new one should be|
|*kill -KILL $PID*.            |started.                      |
+------------------------------+------------------------------+
|Kill the newly started        |The component should goes     |
|*file-transcoder* component.  |*sad* and after a little time |
|                              |a new component should be     |
|                              |started automaticaly.         |
+------------------------------+------------------------------+
|Kill again the newly started  |The component should goes     |
|component.                    |*sad* and after a some time, a|
|                              |new one should be started.    |
+------------------------------+------------------------------+
|Kill the last started         |The component should goes     |
|component.                    |*sad*, but no new             |
|                              |*file-transcoder* component   |
|                              |should start (wait a little to|
|                              |be sure).                     |
+------------------------------+------------------------------+

Blocking a *file-transcoder* Component
--------------------------------------

Profile to use: *basic.ini*

+------------------------------+------------------------------+
|Actions                       |Expectations                  |
+==============================+==============================+
|                              |A *file-monitor* component for|
|                              |the profile *basic* is running|
|                              |and happy, and it doesn't have|
|                              |any files pending or queued.  |
+------------------------------+------------------------------+
|Copy an audio file to the     |The file should be detected in|
|audio incoming of the profile |less than 10 seconds.         |
|*basic*                       |                              |
+------------------------------+------------------------------+
|Wait for the *file-transcoder*|                              |
|component to be started.      |                              |
+------------------------------+------------------------------+
|Block the *file-transcoder*   |Nothing should append         |
|copmonent with the command    |rightaway.                    |
|*kill -STOP $PID*.            |                              |
+------------------------------+------------------------------+
|Wait 30 seconds.              |The component should goes     |
|                              |*lost*.                       |
+------------------------------+------------------------------+
|Resume the transcoding        |The component should goes back|
|component with *kill -CONT    |to *happy* and continue to    |
|$PID*                         |transcode.                    |
|                              |                              |
+------------------------------+------------------------------+
|Wait the transcoding to       |The file should transcode     |
|finish.                       |successfully.                 |
+------------------------------+------------------------------+
|Copy another audio file to    |The file should be detected by|
|incoming.                     |the monitor.                  |
+------------------------------+------------------------------+
|Wait for the transocding      |                              |
|component to be started.      |                              |
+------------------------------+------------------------------+
|Block the *file-transcoder*   |Nothing should append         |
|copmonent with the command    |rightaway.                    |
|*kill -STOP $PID*.            |                              |
+------------------------------+------------------------------+
|Wait 30 seconds.              |The component should goes     |
|                              |*lost*.                       |
+------------------------------+------------------------------+
|Wait 60 seconds more.         |A new transcoding component   |
|                              |should be started.            |
+------------------------------+------------------------------+
|Resume the transcoding        |The old component should goes |
|component with *kill -CONT    |back to *happy*, and then it  |
|$PID*                         |should be stopped and deleted |
|                              |automatically.                |
+------------------------------+------------------------------+
|Wait the transcoding to       |The file should transcode     |
|finish.                       |successfully.                 |
+------------------------------+------------------------------+

Admin Resuming Transcoding Components
-------------------------------------

Profile to use: *basic.ini*

+------------------------------+------------------------------+
|Actions                       |Expectations                  |
+==============================+==============================+
|                              |A *file-monitor* component for|
|                              |the profile *basic* is running|
|                              |and happy, and it doesn't have|
|                              |any files pending or queued.  |
+------------------------------+------------------------------+
|Copy a group of audio file (> |A group of transcoding        |
|8) to the audio incoming of   |component should be started.  |
|the profile *basic*           |                              |
|                              |                              |
+------------------------------+------------------------------+
|Before any transcoding finish,|No transcoding task should be |
|stop the transcoder admin with|stopped or deleted.           |
|*service                      |                              |
|flumotion-transcoder-admin    |                              |
|stop*                         |                              |
+------------------------------+------------------------------+
|Before the transcoding        |All transcoding components    |
|component finish and goes to  |should continue to transcode, |
|the state *Waiting for        |no new copmonent should be    |
|acknowledgment*, restart the  |started before one of the old |
|transcoder admin with *service|ones finish successfully.  No |
|flumotion-transcoder-admin    |transcoding copmonent should  |
|start*                        |be deleted before finishing.  |
+------------------------------+------------------------------+
|Wait for all files to be      |All files should be           |
|transcoded.                   |successfully transcoder.      |
+------------------------------+------------------------------+

Admin Resuming Components Waiting For Acknowledgment
----------------------------------------------------

Profile to use: *basic.ini*

+------------------------------+------------------------------+
|Actions                       |Expectations                  |
+==============================+==============================+
|                              |A *file-monitor* component for|
|                              |the profile *basic* is running|
|                              |and happy, and it doesn't have|
|                              |any files pending or queued.  |
+------------------------------+------------------------------+
|Copy a group of audio file (> |A group of transcoding        |
|8) to the audio incoming of   |component should be started.  |
|the profile *basic*           |                              |
|                              |                              |
+------------------------------+------------------------------+
|Before any transcoding finish,|No transcoding task should be |
|stop the transcoder admin with|stopped or deleted.           |
|*service                      |                              |
|flumotion-transcoder-admin    |                              |
|stop*                         |                              |
+------------------------------+------------------------------+
|Wait for the transcoding tasks|                              |
|to be in state *waiting for   |                              |
|acknowledgment*.              |                              |
+------------------------------+------------------------------+
|Restart the transcoder admin  |All transcoding component     |
|with *service                 |should be acknowledged and new|
|flumotion-transcoder-admin    |transcoding component should  |
|start*                        |be started **for new files**. |
|                              |No transcoding component      |
|                              |shoudlbe deleted without      |
|                              |beeing acknowledged.          |
+------------------------------+------------------------------+
|Wait for all files to be      |All files should be           |
|transcoded.                   |successfully transcoder.      |
+------------------------------+------------------------------+

.. _Testing Media Sets: media-sets.rst
