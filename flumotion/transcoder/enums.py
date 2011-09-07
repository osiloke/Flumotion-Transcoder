# vi:si:et:sw=4:sts=4:ts=4

# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007,2008,2009 Fluendo, S.L.
# Copyright (C) 2010,2011 Flumotion Services, S.A.
# All rights reserved.
#
# This file may be distributed and/or modified under the terms of
# the GNU Lesser General Public License version 2.1 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.LGPL" in the source distribution for more information.
#
# Headers in this file shall remain intact.

from flumotion.common.enum import EnumClass


TargetTypeEnum = EnumClass('TargetTypeEnum',
                           ('audio',
                            'video',
                            'audiovideo',
                            'thumbnails',
                            'identity'),
                           ('Audio',
                            'Video',
                            'Audio/Video',
                            'Thumbnails',
                            'Identity'))

PeriodUnitEnum = EnumClass('PeriodUnitEnum',
                           ('seconds',
                            'frames',
                            'keyframes',
                            'percent'),
                           ('Seconds',
                            'Frames',
                            'Keyframes',
                            'Percent'))

ThumbOutputTypeEnum = EnumClass('ThumbOutputTypeEnum',
                                ('jpg',
                                 'png'),
                                ('jpg',
                                 'png'))

VideoScaleMethodEnum = EnumClass('VideoScaleMethodEnum',
                                 ('height',
                                  'width',
                                  'downscale',
                                  'upscale'),
                                 ('Height',
                                  'Width',
                                  'Downscale',
                                  'Upscale'))

JobStateEnum = EnumClass('JobStateEnum',
                         ('pending',
                          'starting',
                          'stopping',
                          'analyzing',
                          'preprocessing',
                          'transcoding',
                          'target_processing',
                          'waiting_ack',
                          'input_file_moving',
                          'output_file_moving',
                          'terminated'),
                         ('Pending',
                          'Starting',
                          'Stopping',
                          'Analyzing',
                          'Pre-processing',
                          'Transcoding',
                          'Target processing',
                          'Waiting Acknowledge',
                          'Input file moving',
                          'Output file moving',
                          'Terminated'))

TargetStateEnum = EnumClass('TargetStateEnum',
                            ('done',
                             'pending',
                             'skipped',
                             'analyzing',
                             'postprocessing',
                             'link_file_generation'),
                            ('Done',
                             'Pending',
                             'Skipped',
                             'Analyzing',
                             'Post-processing',
                             'Link file generation'))

TranscoderStatusEnum = EnumClass('TranscoderStatusEnum',
                                 ('pending',
                                  'checking',
                                  'setting_up',
                                  'working',
                                  'done',
                                  'failed',
                                  'error',
                                  'unexpected_error'),
                                 ('Pending',
                                  'Checking',
                                  'Setting up',
                                  'Working',
                                  'Done',
                                  'Failed',
                                  'Error',
                                  'Unexpected Error'))

MonitorFileStateEnum = EnumClass('MonitorFileStateEnum',
                                 ('pending',
                                  'downloading',
                                  'transcoding',
                                  'queued',
                                  'done',
                                  'failed'),
                                 ('Pending',
                                  'Downloading',
                                  'Transcoding',
                                  'Queued',
                                  'Done',
                                  'Failed'))

AudioVideoToleranceEnum = EnumClass('AudioVideoToleranceEnum',
                                    ('strict',
                                     'allow_without_audio',
                                     'allow_without_video'),
                                    ('Strict',
                                     'Allow without audio',
                                     'Allow without video'))

# REMEMBER to keep in sync with the transcoder_outcomes database table
TranscodingOutcomeEnum = EnumClass("TranscodingOutcomeEnum",
                                   ("expected_failure",
                                    "unexpected_failure",
                                    "success"),
                                   ("Expected failure",
                                    "Unexpected failure",
                                    "Success"),
                                   outcome_id=(1, 2, 3))

TranscodingFailureEnum = EnumClass("TranscodingFailureEnum",
                                   ("wrong_mime_type",
                                    "wrong_file_type",
                                    "video_too_small",
                                    "audio_too_small"),
                                   ("Wrong mime type",
                                    "Wrong file type",
                                    "Video too small",
                                    "Audio too small"),
                                   failure_id=(1,2,3,4))
