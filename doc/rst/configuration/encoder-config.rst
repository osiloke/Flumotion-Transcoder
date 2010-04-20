================================
Transcoding Target Configuration
================================

.. sectnum::

.. contents::

Place Holders
=============

SAMPLERATE: Audio sample rate in Hertz.

CHANNELS: The number of channels of the output file, 1 for mono and 2 for stereo.

AUDIO_BITRATE: Bitrate in bits per seconds.

AUDIO_KBITRATE: Bitrate in kilo bits per seconds.

VIDEO_BITRATE: Bitrate in bits per seconds.

VIDEO_KBITRATE: Bitrate in kilo bits per seconds.

FRAMERATE: Video frame per seconds, can be a fraction like 25/2.

VIDEO_HEIGHT: Height of the outgoing video.

VIDEO_WIDTH: Width of the outgoing video.

MIN_KF_DIST: Minimum keyframe distance

MAX_KF_DIST: Maximum keyframe distance

Audio Profiles
==============


QCP
---

1. Dependencies

 - gstreamer-fluendo-qcp

2. Configuration

================ ============
Audio Encoder    fluqcpenc
Audio Samplerate *SAMPLERATE*
Audio Channels   1
Muxer            identity
================ ============

3. Tested

========== =
SAMPLERATE
========== =
8000
========== =


AMR-NB
------

1. Dependencies

 - amrnb libraries

2. Configuration

================= ============
Audio Encoder     amrnbenc
Audio Samplerate  8000
Audio Channels    1
Muxer             ffmux_amr
================= ============


AMR-WB
------

1. Configuration

================= ============
Audio Encoder     amrwbenc
Audio Samplerate  16000
Audio Channels    1
Muxer             ffmux_amr
================= ============


ADPCM / MMF
-----------

1. Dependencies

 - mmf-crc binary

2. Configuration

================= ======================================================================
Audio Encoder     capsfilter caps=audio/x-raw-int,width=16,depth=16 ! ffenc_adpcm_yamaha
Audio Samplerate  *SAMPLERATE*
Audio Channels    *CHANNELS*
Muxer             ffmux_mmf
================= ======================================================================

3. Post-Processing

To add the CRC, the following command should be executed as a post-processing::

    /usr/bin/mmf-crc %(outputWorkPath)s

4. Tested

========== ========
SAMPLERATE CHANNELS
========== ========
8000       1
========== ========


MP3
---

1. Configuration

================= ================================================================================
Audio Encoder     lame bitrate=\ *AUDIO_KBITRATE* ! capsfilter caps=audio/mpeg,rate=\ *SAMPLERATE*
Audio Samplerate  *SAMPLERATE*
Audio Channels    *CHANNELS*
Muxer             identity
================= ================================================================================


2. Tested

========== ======== ==============
SAMPLERATE CHANNELS AUDIO_KBITRATE
========== ======== ==============
44100      2        128
44100      2        112
44100      1        112
44100      1        64
44100      1        48
22050      2        64
22050      1        56
22050      1        24
========== ======== ==============


AAC+ / FLV
----------

1. Dependencies

 - gstreamer-fluendo-mcaacenc

2. Configuration

================= =============================================================
Audio Encoder     flumcaacenc he=hev2 bitrate=\ *AUDIO_BITRATE* header-type=raw
Audio Samplerate  *SAMPLERATE*
Audio Channels    2
Muxer             fluflvmux
================= =============================================================

5. Limitations

AUDIO_BITRATE limitations:

========== ======== =========== ===========
Samplerate Channels Min Bitrate Max Bitrate
========== ======== =========== ===========
 16000 Hz      2     10000 bps   40000 bps
 22050 Hz      2     10000 bps   48000 bps
 24000 Hz      2     10000 bps   48000 bps
 32000 Hz      2     16000 bps   56000 bps
 44100 Hz      2     16000 bps   64000 bps
 48000 Hz      2     16000 bps   64000 bps
========== ======== =========== ===========
                                

4. Tested

======== ========== ==============
CHANNELS SAMPLERATE AUDIO_KBITRATE
======== ========== ==============
2        48000      64
2        48000      48
2        48000      32
2        48000      16
2        44100      64
2        44100      32
2        44100      16
2        32000      56
2        32000      16
2        24000      48
2        24000      10
2        22050      48
2        22050      10
2        16000      40
2        16000      10
1        44100      64
1        44100      16
1        22050      48
1        22050      16
======== ========== ==============


Video Profiles
==============

AMR-NB + H.263 / 3GP
--------------------

1. Dependencies

 - amrnb libraries

2. Configuration

================= ====================================
Audio Encoder     amrnbenc
Audio Samplerate  8000
Audio Channels    1
Video Encoder     ffenc_h263 bitrate=\ *VIDEO_BITRATE*
Video Framerate   *FRAMERATE*
Video Width       *VIDEO_WIDTH*
Video Height      *VIDEO_HEIGHT*
Muxer             ffmux_3gp
================= ====================================

3. Tested

=========== ============ ========= =============
VIDEO_WIDTH VIDEO_HEIGHT FRAMERATE VIDEO_BITRATE
=========== ============ ========= =============
176         144          25/2      128000
=========== ============ ========= =============


Sorenson + MP3 / FLV
--------------------

1. Dependencies

 - flvlib for indexing

2. Configuration

================= ===========================================================================
Audio Encoder     lame bitrate=\ *AUDIO_KBITRATE* ! audio/mpeg,rate=\ *SAMPLERATE* ! mp3parse
Audio Samplerate  *SAMPLERATE*
Audio Channels    *CHANNELS*
Video Encoder     ffenc_flv bitrate=\ *VIDEO_BITRATE*
Video Framerate   *FRAMERATE*
Video Width       *VIDEO_WIDTH*
Video Height      *VIDEO_HEIGHT*
Muxer             fluflvmux
================= ===========================================================================

3. Post-Processing

To add the seeking capabilities, the output file must be indexed using
the following command should be executed as a post-processing::

    index-flv -U %(outputWorkPath)s

4. Tested

=========== ============ ========= ============= ======== ========== ==============
VIDEO_WIDTH VIDEO_HEIGHT FRAMERATE VIDEO_BITRATE CHANNELS SAMPLERATE AUDIO_KBITRATE
=========== ============ ========= ============= ======== ========== ==============
360         \*           25/2      128000        1        22050      32
=========== ============ ========= ============= ======== ========== ==============


MP4 + AMR-NB / MOV
------------------

1. Dependencies

 - amrnb libraries

2. Configuration

================= =====================================
Audio Encoder     amrnbenc
Audio Samplerate  8000
Audio Channels    1
Video Encoder     ffenc_mpeg4 bitrate=\ *VIDEO_BITRATE*
Video Framerate   *FRAMERATE*
Video Width       *VIDEO_WIDTH*
Video Height      *VIDEO_HEIGHT*
Muxer             ffmux_mov
================= =====================================

3. Tested

=========== ============ ========= =============
VIDEO_WIDTH VIDEO_HEIGHT FRAMERATE VIDEO_BITRATE
=========== ============ ========= =============
176         144          25/2      128000
=========== ============ ========= =============


VP6 + MP3 / FLV
---------------

1. Dependencies

 - gstreamer-fluendo-vp6enc
 - flvlib for indexing

2. Configuration

================= ===========================================================================
Audio Encoder     lame bitrate=\ *AUDIO_KBITRATE* ! audio/mpeg,rate=\ *SAMPLERATE* ! mp3parse
Audio Samplerate  *SAMPLERATE*
Audio Channels    *CHANNELS*
Video Encoder     videoflip method=5 ! fluvp6enc bitrate=\ *VIDEO_KBITRATE*
Video Framerate   *FRAMERATE*
Video Width       *VIDEO_WIDTH*
Video Height      *VIDEO_HEIGHT*
Muxer             fluflvmux
================= ===========================================================================

3. Post-Processing

To add the seeking capabilities, the output file must be indexed using
the following command should be executed as a post-processing::

    index-flv -U %(outputWorkPath)s

4. Tested

=========== ============ ========= ============== ======== ========== ==============
VIDEO_WIDTH VIDEO_HEIGHT FRAMERATE VIDEO_KBITRATE CHANNELS SAMPLERATE AUDIO_KBITRATE
=========== ============ ========= ============== ======== ========== ==============
752         560          25/1      700            2        44100      64
480         368          25/1      380            2        44100      48
384         288          25/1      300            2        22050      48
=========== ============ ========= ============== ======== ========== ==============

VP6 + AAC+ / FLV
----------------

1. Dependencies

 - gstreamer-fluendo-vp6enc
 - gstreamer-fluendo-mcaacenc
 - flvlib for indexing

2. Configuration

================= ===========================================================================
Audio Encoder     flumcaacenc he=hev2 bitrate=\ *AUDIO_BITRATE* header-type=raw
Audio Samplerate  *SAMPLERATE*
Audio Channels    *CHANNELS*
Video Encoder     videoflip method=5 ! fluvp6enc bitrate=\ *VIDEO_KBITRATE*
Video Framerate   *FRAMERATE*
Video Width       *VIDEO_WIDTH*
Video Height      *VIDEO_HEIGHT*
Muxer             fluflvmux
================= ===========================================================================

3. Post-Processing

To add the seeking capabilities, the output file must be indexed using
the following command should be executed as a post-processing::

    index-flv -U %(outputWorkPath)s

4. Limitations

AUDIO_BITRATE limitations:

========== ======== =========== ===========
Samplerate Channels Min Bitrate Max Bitrate
========== ======== =========== ===========
 16000 Hz      2     10000 bps   40000 bps
 22050 Hz      2     10000 bps   48000 bps
 24000 Hz      2     10000 bps   48000 bps
 32000 Hz      2     16000 bps   56000 bps
 44100 Hz      2     16000 bps   64000 bps
 48000 Hz      2     16000 bps   64000 bps
========== ======== =========== ===========

5. Tested

=========== ============ ========= ============== ======== ========== =============
VIDEO_WIDTH VIDEO_HEIGHT FRAMERATE VIDEO_KBITRATE CHANNELS SAMPLERATE AUDIO_BITRATE
=========== ============ ========= ============== ======== ========== =============
768         576          30/1      512            2        44100      48000
384         288          24/1      1024           2        44100      64000
384         288          24/1      256            2        44100      24000
256         144          12/1      512            2        44100      32000
=========== ============ ========= ============== ======== ========== =============


WMV + WMA / ASF (pitfdll)
-------------------------

**!! Warning !! Deprected !!**

Pitfdll encoder must only be used for one target at a time.

Use the next WMV+WMA/ASF profile.

1. Dependencies

 - gstreamer-fluendo-wmaenc
 - gstreamer-fluendo-asfmux

2. Configuration

================= ===========================================
Audio Encoder     fluwmaenc bitrate=\ *AUDIO_BITRATE*
Audio Samplerate  *SAMPLERATE*
Audio Channels    *CHANNELS*
Video Encoder     dmoenc_wmvdmoe2v3 bitrate=\ *VIDEO_BITRATE*
Video Framerate   *FRAMERATE*
Video Width       *VIDEO_WIDTH*
Video Height      *VIDEO_HEIGHT*
Muxer             fluasfmux
================= ===========================================

3. Tested

=========== ============ ========= ============= ======== ========== =============
VIDEO_WIDTH VIDEO_HEIGHT FRAMERATE VIDEO_BITRATE CHANNELS SAMPLERATE AUDIO_BITRATE
=========== ============ ========= ============= ======== ========== =============
384         288          25/1      3000000       2        22050      48000
=========== ============ ========= ============= ======== ========== =============


WMV + WMA / ASF
---------------

1. Dependencies

 - gstreamer-fluendo-wmaenc
 - gstreamer-fluendo-wmvenc
 - gstreamer-fluendo-asfmux

2. Configuration

================= ===================================
Audio Encoder     fluwmaenc bitrate=\ *AUDIO_BITRATE*
Audio Samplerate  *SAMPLERATE*
Audio Channels    *CHANNELS*
Video Encoder     fluwmvenc bitrate=\ *VIDEO_BITRATE*
Video Framerate   *FRAMERATE*
Video Width       *VIDEO_WIDTH*
Video Height      *VIDEO_HEIGHT*
Muxer             fluasfmux
================= ===================================

3. Tested

=========== ============ ========= ============= ======== ========== =============
VIDEO_WIDTH VIDEO_HEIGHT FRAMERATE VIDEO_BITRATE CHANNELS SAMPLERATE AUDIO_BITRATE
=========== ============ ========= ============= ======== ========== =============
640         360          25/1      1051000       2        44100      96000
384         216          25/1      720000        2        44100      48000
384         288          25/1      400000        2        44100      48000
384         288          25/1      300000        2        22050      48000
=========== ============ ========= ============= ======== ========== =============


H.264 / FLV
-----------

1. Dependencies

 - gstreamer-fluendo-mch264enc
 - flvlib for indexing

2. Configuration

================= ===========================================================================
Video Encoder     flumch264enc bitrate=\ *VIDEO_BITRATE*
Video Framerate   *FRAMERATE*
Video Width       *VIDEO_WIDTH*
Video Height      *VIDEO_HEIGHT*
Muxer             fluflvmux
================= ===========================================================================

3. Tested

=========== ============ ========= ==============
VIDEO_WIDTH VIDEO_HEIGHT FRAMERATE VIDEO_KBITRATE
=========== ============ ========= ==============
480         368          25/1      400
=========== ============ ========= ==============


H.264 + MP3 / FLV
-----------------

1. Dependencies

 - gstreamer-fluendo-mch264enc
 - flvlib for indexing

2. Configuration

================= ===========================================================================
Audio Encoder     lame bitrate=\ *AUDIO_KBITRATE* ! audio/mpeg,rate=\ *SAMPLERATE* ! mp3parse
Audio Samplerate  *SAMPLERATE*
Audio Channels    *CHANNELS*
Video Encoder     flumch264enc bitrate=\ *VIDEO_BITRATE*
Video Framerate   *FRAMERATE*
Video Width       *VIDEO_WIDTH*
Video Height      *VIDEO_HEIGHT*
Muxer             fluflvmux
================= ===========================================================================

3. Post-Processing

To add the seeking capabilities, the output file must be indexed using
the following command should be executed as a post-processing::

    index-flv -U %(outputWorkPath)s

4. Tested

=========== ============ ========= ============== ======== ========== ==============
VIDEO_WIDTH VIDEO_HEIGHT FRAMERATE VIDEO_KBITRATE CHANNELS SAMPLERATE AUDIO_KBITRATE
=========== ============ ========= ============== ======== ========== ==============
480         368          25/1      1024           2        44100      96
480         368          12/1      1024           2        44100      96
480         368          25/1      400            2        44100      96
480         368          12/1      400            2        44100      96
480         368          25/1      400            2        44100      128
480         368          25/1      400            1        22050      96
384         288          25/1      400            2        44100      96
320         240          25/1      400            2        44100      96
320         240          25/1      1024           2        44100      96
320         240          12/1      400            2        44100      96
320         240          12/1      1024           2        44100      96
=========== ============ ========= ============== ======== ========== ==============


H.264 + AAC+ / FLV
------------------

1. Dependencies

 - gstreamer-fluendo-mcaacenc
 - gstreamer-fluendo-mch264enc
 - flvlib for indexing

2. Configuration

================= ===========================================================================
Audio Encoder     flumcaacenc he=hev2 bitrate=\ *AUDIO_BITRATE* header-type=raw
Audio Samplerate  *SAMPLERATE*
Audio Channels    *CHANNELS*
Video Encoder     flumch264enc bitrate=\ *VIDEO_BITRATE*
Video Framerate   *FRAMERATE*
Video Width       *VIDEO_WIDTH*
Video Height      *VIDEO_HEIGHT*
Muxer             fluflvmux
================= ===========================================================================

3. Post-Processing

To add the seeking capabilities, the output file must be indexed using
the following command should be executed as a post-processing::

    index-flv -U %(outputWorkPath)s

4. Limitations

AUDIO_BITRATE limitations:

========== ======== =========== ===========
Samplerate Channels Min Bitrate Max Bitrate
========== ======== =========== ===========
 16000 Hz      2     10000 bps   40000 bps
 22050 Hz      2     10000 bps   48000 bps
 24000 Hz      2     10000 bps   48000 bps
 32000 Hz      2     16000 bps   56000 bps
 44100 Hz      2     16000 bps   64000 bps
 48000 Hz      2     16000 bps   64000 bps
========== ======== =========== ===========

5.Tested

=========== ============ ========= ============= ======== ========== =============
VIDEO_WIDTH VIDEO_HEIGHT FRAMERATE VIDEO_BITRATE CHANNELS SAMPLERATE AUDIO_BITRATE
=========== ============ ========= ============= ======== ========== =============
480         368          25/1      400000        2        22050      24000
480         368          25/1      400000        2        48000      48000
=========== ============ ========= ============= ======== ========== =============


MPEG4 + MP3 / MP4
-----------------

1. Configuration

================= ===========================================================================
Audio Encoder     lame bitrate=\ *AUDIO_KBITRATE* ! audio/mpeg,rate=\ *SAMPLERATE* ! mp3parse
Audio Samplerate  *SAMPLERATE*
Audio Channels    *CHANNELS*
Video Encoder     ffenc_mpeg4
Video Framerate   *FRAMERATE*
Video Width       *VIDEO_WIDTH*
Video Height      *VIDEO_HEIGHT*
Muxer             ffmux_mp4
================= ===========================================================================


H.264 / MP4
------------------

1. Dependencies

 - gstreamer-fluendo-mch264enc
 - gst-plugins-bad (qtmux)

2. Configuration

================ ===========================================================================================================================
Video Encoder     flumch264enc bitrate=\ *VIDEO_BITRATE* min-keyframe-distance=\ *MIN_KF_DISTANCE* max-keyframe-distance=\ *MAX_KF_DISTANCE*
Video Framerate   *FRAMERATE*
Video Width       *VIDEO_WIDTH*
Video Height      *VIDEO_HEIGHT*
Muxer             qtmux
================ ===========================================================================================================================

5.Tested

=========== ============ ========= =============
VIDEO_WIDTH VIDEO_HEIGHT FRAMERATE VIDEO_BITRATE
=========== ============ ========= =============
128         96           1/2       500000       
=========== ============ ========= =============
