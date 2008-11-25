=============================
Transcoder Testing Media Sets
=============================


Error Sets
==========

There is two error sets, one for audio and one for audio/video.

They can be found on the dev cluster::
     
     /home/file/testing/transcoder/media/error/audio
     /home/file/testing/transcoder/media/error/video

Set Content
-----------

These set contains files of three defined types.

Bad Files
~~~~~~~~~

These file must fail because there are wrong.

It could be corrupted files, empty files, text files...

The filenames start with the prefix *bad_*, for example::

    bad_text.avi

Unsupported Files
~~~~~~~~~~~~~~~~~

These files are known to fail because we do not support them.

It doesn't mean the files are wrong, but the failure is expected.

The filenames start with the prefix *unsupported_*, for example::

    unsupported_indeo.avi

Files Known to Fail
~~~~~~~~~~~~~~~~~~~

These files are known to fail but the cause is unknown or not yet fixed.

The filenames start with the prefix *ticket_* followed by the number
of the ticket opened for this error, for example::

   ticket_4567_demo.mpg


Sample Sets
===========

These sample set contains at least 100 files with a varition
of codecs, size, duration.

The sets can be found on the dev cluster::

    /home/testing/transcoder/media/samples/audio
    /home/testing/transcoder/media/samples/video


Customer Sets
=============

These sets are representative subsets of customer files.

Fore each tested customer profiles, one corresponding set
of at least 10 representative files should exists. 

They can be found on the dev cluster::

     /home/testing/transcoder/media/customers

And each files will be in the incoming directory of the respective
regression profile and start with the prefix *cust_* followed
by a name to identify the customer, for example::

     /home/testing/transcoder/media/customers/a3webtv/files/incoming/video/cust_a3webtv_filename.flv


Regression Set
==============

Because the files are used with known profiles, they are
already separated in different directories to facilitate testing.

They can be found on the dev cluster::

     /home/testing/transcoder/media/regressions

And each files will be in the incoming directory of the respective
regression profile and start with the prefix *regression_*, for example::

     /home/testing/transcoder/media/regressions/regression_name/files/incoming/regression_file.mpg


Basic Profile Testing Set
=========================

Because the files are used with known profiles, they are
already separated in different directories to facilitate testing.

They can be found on the dev cluster::

     /home/testing/transcoder/media/functional

And each files will be in the incoming directory of the respective
regression profile and start with the prefix *functional_*, for example::

     /home/testing/transcoder/media/funcional/profile_name/files/incoming/test_name/functional_filename.mpg

Indexing Testing Set
====================

This is a special set of FLV files of different types
used to test indexing. These files must have been
created by other application than GStreamer.

The set contains:

 * MP3 in FLV
 * Sorenson with MP3 in FLV
 * Sorenson with AAC in FLV (if it's possible ?)
 * VP6 with MP3 in FLV
 * VP6 with AAC in FLV
 * H264 with MP3 in FLV
 * H264 with AAC in FLV
