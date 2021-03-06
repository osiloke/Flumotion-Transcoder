=================
Features Overview
=================

Features for Customers
======================

Distributed Transcoding
-----------------------

The transcoding jobs are automatically distributed amongst a set of servers.
If any server was disconnected for a certain amount of time or crashed,
the jobs would be automatically restarted on another server.

Another big advantage is the scalability of the platform,
if more transcoding power is needed, just add a server and the platform
will be able to process more media files.

Prioritized Transcoding
-----------------------

There is two different kind of priority management:

  - **Transcoding Queue Priority:**

    The transcoding queue priority define the order in witch the transcoding job
    are started. When a transcoder task can be started, the profiles with higher
    transcoding queue priority will be chosen first.

    This could be used to create a set of profiles with different priority
    and choose when dropping a file the relative order of transcodification.

    Each transcoding profile has its own transcoding priority value.

  - **Transcoding Task Priority:**

    This define the priority of transcoding task to use server CPU resources.
    When two transcoding tasks are running at the same time on a server,
    the one with higher task priority will have a bigger share of CPU time
    meaning that it will run and terminate faster.

    This could be used for testing profiles, to prevent a transcoding test
    to slow down production transcoding.

    Each transcoding profile has its own transcoding priority value.


Integrated Thumbnailing
-----------------------

The thumbnail generation is integrated inside the transcoding process,
it's not an external post-processing. It means that if a file can be
transcoded the thumbnails extraction is guaranteed, and that the full
quality of the source media file will be used for the thumbnail creation.

Video Dimensions Control
------------------------

There is various options to specify the dimensions of the output files:

  - **Without Specification:**

    When only the output pixel aspect ratio is specified, the transcoder
    will deduce the output dimension respecting the source display aspect ratio.
    The profile can be configured to preserve the input video height or width,
    or prefer to upscale or downscale the input video.

  - **Partial Specification:**

    Only one of the dimension is specified. The other one is deduced by
    the transcoder in respect to the source dimensions and pixel aspect ratio.

  - **Complete Specification:**

    The width and height can be specified directly. If the source dimensions
    and pixel aspect ratio is not compatible with the specified dimensions,
    black bands will be added on top and bottom or left and right to respect
    the specified dimensions without deforming the source video.

In addition, there is options to control the deduced dimensions:

  - **Maximum Dimensions:**

    The maximum width and height of the output video can be specified.
    In allow at the same time to not upscale low resolution video
    by not specifying static dimensions, but control the maximum
    dimensions to prevent very high resolution videos.

Thumbnail Dimensions Control
----------------------------

In the same way as for the video targets, the thumbnails dimensions
can be specified partially or completely adding black bands to
respect the display aspect ratio of the source video.

Frame Sampling
--------------

More than one thumbnail can be extracted from an input video
by specifying an period value, an period unit and the maximum
number of thumbnail to extract.

The period unit can be:

  * Video Frames
  * Seconds
  * Duration Percentage

For example, the profile can be setup to generate a maximum of
9 thumbnails each 10 percents of the input video. This would
sample 9 thumbnails evenly independently of the input video
duration.

Stateless Monitoring
--------------------

The transcoder monitor a directory usually named *incoming*.
When a file is drop in this directory, it schedule a transcoding job
for it. When the transcoding job terminate, the input file is moved
either to the *done* or *failed* directory.

This behavior make possible to transcode media files with identical name
more than one time, note that the new output files will overwrite the
old ones. This could be used to update a video that content change
without modifying all the references to it.

Flexible Output Structure
-------------------------

The transcoding targets can be configured to add change the name
of the output file or store in in a sub-directory.

For example, with the input file ``incoming/test.avi``,
the output file could be:

  * ``outgoing/test.flv``
  * ``outgoing/test.avi.flv``
  * ``outgoing/test.hq.flv``
  * ``outgoing/high/test.flv``
  * ``outgoing/high/test.avi.flv``
  * ``other/high/test.hq.flv``
  * ...

Subdirectory Replication
------------------------

If the input file is uploaded in a sub-directory of the profile's monitored
directories, usually named ''incoming'', the sub-directory will be automatically
replicated in the ''outgoing'', ''done'', and ''failed'' directories.

For example, if the incoming file is ``incoming/video/test.avi``, we will have:

  :Outgoing File:  ``outgoing/video/high/test.flv``
  :Done File:      ``done/video/test.avi``
  :Failed File:    ``failed/video/test.avi``

Multiple Notification
---------------------

The transcoder can notify external application by performing GET requests.
A list of URLs can be specified to be triggered by:

  * Profile's Transcoding Done
  * Profile's Transcoding Fail
  * Target's Transcoding Done
  * Target's Transcoding Fail

Notification Queue
------------------

The notifications are queued, and if the transcoder fail to perform them,
it will retry later. The number of retry intents and the time between intents
are parameters that can be changed.

Notification Customization
--------------------------

The GET request URL can contain variables that will be substituted at runtime
with information about the transcoding session.

For example, following are some of the variables that can be specified:

  ====================  =======================
  Input File            ``test.avi``
  Output File           ``test.flv``
  Input Relative Path   ``video/test.avi``
  Output Relative Path  ``video/high/test.flv``
  Success               ``0`` or ``1``
  Trigger               ``done`` or ``failed``
  Profile Name          ``video``
  Target Name           ``Flash High Quality``
  Media Duration        ``123.54``
  Source Height         ``480``
  Target Width          ``174``
  ...                   ...
  ====================  =======================

There is more than 35 different variables that could be substituted
when performing GET requests. Not all are available for all kind
of requests, for example the target-related variables are not available
when performing a profile-level notification, and informations about
the media may not be available for the failure notifications.

Target Post-Processing
----------------------

A post-processing command can be specified for each target.
For example, this can be used perform some special indexing.

Identity Target
---------------

If the input files can be used as is or only a post-processing
is needed, an identity target can be used. This special kind
of target will not transcode anything, it will just check
the input file is a valid media file, execute the post-processing
if any has been specified, and copy it to the outgoing directory.

This could be used at the same time as real transcoding profiles,
for example if all the input files are final WMV files but flash
files are wanted too, the transcoding profile can be setup with
an identity target that will only copy the WMV file to the correct
outgoing directory, and a transcoding target that will transcode
the WMV to flash video and put it in the outgoing directory.


