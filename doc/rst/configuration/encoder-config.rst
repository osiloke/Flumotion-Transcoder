================================
Transcoding Target Configuration
================================

Index
=====


Place Holders
=============

SAMPLERATE
    Audio sample rate in Hertz.

CHANNELS
    The number of channels of the output file, 1 for mono and 2 for stereo.

AUDIO_BITRATE
    Bitrate in bits per seconds.

AUDIO_KBITRATE
    Bitrate in kilo bits per seconds.

VIDEO_BITRATE
    Bitrate in bits per seconds.

VIDEO_KBITRATE
    Bitrate in kilo bits per seconds.

FRAMERATE
    Video frame per seconds, can be a fraction like 25/2.

VIDEO_HEIGHT
    Height of the outgoing video.

VIDEO_WIDTH
    Width of the outgoing video.


Audio Profiles
==============


QCP
---

Dependencies
~~~~~~~~~~~~

 - gstreamer-fluendo-qcp

Configuration
~~~~~~~~~~~~~

================ ============
Audio Encoder    fluqcpenc
Audio Samplerate *SAMPLERATE*
Audio Channels   1
Muxer            identity
================ ============

Tested
~~~~~~

========== =
SAMPLERATE
========== =
8000 
========== =


AMR-NB
------

Dependencies
~~~~~~~~~~~~

 - amrnb libraries

Configuration
~~~~~~~~~~~~~

================= ============
Audio Encoder     amrnbenc
Audio Samplerate  8000
Audio Channels    1
Muxer             ffmux_amr
================= ============


AMR-WB
------

Configuration
~~~~~~~~~~~~~

================= ============
Audio Encoder     amrwbenc
Audio Samplerate  16000
Audio Channels    1
Muxer             ffmux_amr
================= ============


ADPCM/MMF
---------

Dependencies
~~~~~~~~~~~~

 - mmf-crc binary

Configuration
~~~~~~~~~~~~~

================= ==================
Audio Encoder     ffenc_adpcm_yamaha
Audio Samplerate  *SAMPLERATE*
Audio Channels    *CHANNELS*
Muxer             ffmux_mmf
================= ==================

Post-Processing
~~~~~~~~~~~~~~~

To add the CRC, the following command should be executed as a post-processing::

    /usr/bin/mmf-crc %(outputWorkPath)s

Tested
~~~~~~

========== ========
SAMPLERATE CHANNELS
========== ========
8000       1
========== ========


MP3
---

Configuration
~~~~~~~~~~~~~

================= ================================================================
Audio Encoder     lame bitrate=\ *AUDIO_KBITRATE* ! audio/mpeg,rate=\ *SAMPLERATE*
Audio Samplerate  *SAMPLERATE*
Audio Channels    *CHANNELS*
Muxer             identity
================= ================================================================

Tested
~~~~~~

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


Video Profiles
==============

AMR-NB+H263/3GP
---------------

Dependencies
~~~~~~~~~~~~

 - amrnb libraries

Configuration
~~~~~~~~~~~~~

================= ===================================================
Audio Encoder     amrnbenc
Audio Samplerate  8000
Audio Channels    1
Video Encoder     ffenc_h263 bitrate=\ *VIDEO_BITRATE* me-method=epzs
Video Framerate   *FRAMERATE*
Video Width       *VIDEO_WIDTH*
Video Height      *VIDEO_HEIGHT*
Muxer             ffmux_3gp
================= ===================================================

Tested
~~~~~~

=========== ============ ========= =============
VIDEO_WIDTH VIDEO_HEIGHT FRAMERATE VIDEO_BITRATE
=========== ============ ========= =============
176         144          25/2      128000
=========== ============ ========= =============


Sorenson+MP3/FLV
----------------

Dependencies
~~~~~~~~~~~~

 - flvtool2 for indexing

Configuration
~~~~~~~~~~~~~

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

Post-Processing
~~~~~~~~~~~~~~~

To add the seeking capabilities, the output file must be indexed using
the following command should be executed as a post-processing::

    flvtool2 -U %(outputWorkPath)s

Tested
~~~~~~

=========== ============ ========= ============= ======== ========== ==============
VIDEO_WIDTH VIDEO_HEIGHT FRAMERATE VIDEO_BITRATE CHANNELS SAMPLERATE AUDIO_KBITRATE
=========== ============ ========= ============= ======== ========== ==============
360         \*           25/2      128000        1        22050      32
=========== ============ ========= ============= ======== ========== ==============


MP4+AMR-NB/MOV
--------------

Dependencies
~~~~~~~~~~~~

 - amrnb libraries

Configuration
~~~~~~~~~~~~~

================= ====================================================
Audio Encoder     amrnbenc
Audio Samplerate  8000
Audio Channels    1
Video Encoder     ffenc_mpeg4 bitrate=\ *VIDEO_BITRATE* me-method=epzs
Video Framerate   *FRAMERATE*
Video Width       *VIDEO_WIDTH*
Video Height      *VIDEO_HEIGHT*
Muxer             ffmux_mov
================= ====================================================

Tested
~~~~~~

=========== ============ ========= =============
VIDEO_WIDTH VIDEO_HEIGHT FRAMERATE VIDEO_BITRATE
=========== ============ ========= =============
176         144          25/2      128000
=========== ============ ========= =============


VP6+MP3/FLV
-----------

Dependencies
~~~~~~~~~~~~

 - gstreamer-fluendo-vp6enc
 - flvtool2 for indexing

Configuration
~~~~~~~~~~~~~

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

Post-Processing
~~~~~~~~~~~~~~~

To add the seeking capabilities, the output file must be indexed using
the following command should be executed as a post-processing::

    flvtool2 -U %(outputWorkPath)s

Tested
~~~~~~

=========== ============ ========= ============== ======== ========== ==============
VIDEO_WIDTH VIDEO_HEIGHT FRAMERATE VIDEO_KBITRATE CHANNELS SAMPLERATE AUDIO_KBITRATE
=========== ============ ========= ============== ======== ========== ==============
752         560          25/1      700            2        44100      64
480         368          25/1      380            2        44100      48
384         288          25/1      300            2        22050      48
=========== ============ ========= ============== ======== ========== ==============


WMV+WMA/ASF (pitfdll)
---------------------

!! Warning !! Deprected !!

Pitfdll encoder must only be used for one target at a time.

Use the next WMV+WMA/ASF profile.

Dependencies
~~~~~~~~~~~~

 - gstreamer-fluendo-wmaenc
 - gstreamer-fluendo-asfmux

Configuration
~~~~~~~~~~~~~

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

Tested
~~~~~~

=========== ============ ========= ============= ======== ========== =============
VIDEO_WIDTH VIDEO_HEIGHT FRAMERATE VIDEO_BITRATE CHANNELS SAMPLERATE AUDIO_BITRATE
=========== ============ ========= ============= ======== ========== =============
384         288          25/1      3000000       2        22050      48000
=========== ============ ========= ============= ======== ========== =============


WMV+WMA/ASF
-----------

Dependencies
~~~~~~~~~~~~

 - gstreamer-fluendo-wmaenc
 - gstreamer-fluendo-wmvenc
 - gstreamer-fluendo-asfmux

Configuration
~~~~~~~~~~~~~

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

Tested
~~~~~~
