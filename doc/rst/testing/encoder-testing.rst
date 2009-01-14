==============================
Transcoder New Encoder Testing
==============================

Profiles Creation
=================

A new configuration file should be created for the new encoder,
and it should be saved on the dev cluster::

    /home/file/testing/transcoder/profiles/encoders/h264.ini

Then profiles should be added to the configuration.
At least the following profiles have to be created.

If a encoder support various containers (muxers), a configuration
file should be created for each containers. For example,
for *H264* encoder, a different configuration file should
be created for *FLV* and *MP4* containers.

Audio Encoder
-------------

If the encoder support extra post-processing like indexing or CRC check,
the profiles should include them.

 1. Basic Profile

    A profile with only one target with the most common parameters.
 
 2. Multi-Target Profile

    A profile with at least 6 targets with combination of differents
    bitrates, samplerates and channel numbers.

 3. Combination Profile

    A profile with the new encoder as one of the target,
    and at least 2 other supported audio encoders.

Video Encoder
-------------

 1. Basic Profile

    A profile with only one target using the most used parameters
    for video encoding, and the supported audio encoder most adapted
    with the most common parameters. A thumbnailing target should be
    added with 1 thumbnail taken at 10 % of the video. The size
    could be watever size not yet use to test encoders.

 2. Multi-Target Profile

    A profile with at least 6 targets with combination of different
    bitrates, framerate, and size. The audio encoder will be the most
    common suported one for the tested video encoder, and it should
    use the most common parameters. A thumbnailing target should be
    added that takes at least 3 thumbnails.

 3. Multi-Audio Profile

    A profile with the different combinations of audio encoding supported
    by the container (muxer) with different bitrates/samplerates/channels.
    A least 4 thumbnail targets should be added taking thumbnails at
    different places.

Testing
=======

Failure Testing
---------------

The transcoder should be configured to perform more than one
transcoding task at the same time.

For each of the encoder profiles, the `error set`_ should be copied
to incoming, and the transcoder should fail for all files
(at least the *error_* and *unsupported_* ones) without freezing. 

Sample Testing
--------------

The transcoder should be configured to perform more than one
transcoding task at the same time.

For each of the encoder profiles, the `sample set`_ should be copied
to incoming, and the transcoder should successfully transcode at least
98 % of the files.

Documentation
=============

Encoder information sould be added to the `encoder configuration`_ page.

Sample configuration for the file data-source should be created
and save in the transcoder source base *doc/profiles*.

The integration documentation should be added to `transcoder integration`_
and links to the `encoder configuration`_ and the sample profile should
be added.


.. _error set: media-sets.rst
.. _sample set: media-sets.rst
.. _encoder configuration: ../configuration/encoder-config.rst0
.. _transcoder integration: ../integration/supported-targets.rst
