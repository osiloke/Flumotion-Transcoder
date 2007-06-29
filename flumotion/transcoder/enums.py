# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.common import enum


ComponentDomainEnum = enum.EnumClass('ComponentDomainEnum',
                                     ('atmosphere', 
                                      'flow'))

TargetTypeEnum = enum.EnumClass('TargetTypeEnum',
                                ('audio', 
                                 'video', 
                                 'audiovideo', 
                                 'thumbnails'),
                                 ('Audio', 
                                 'Video', 
                                 'Audio/Video', 
                                 'Thumbnails'))

PeriodUnitEnum = enum.EnumClass('PeriodUnitEnum',
                                  ('seconds', 
                                   'frames', 
                                   'keyframes', 
                                   'percent'),
                                   ('Seconds', 
                                   'Frames', 
                                   'Keyframes', 
                                   'Percent'))

ThumbOutputTypeEnum = enum.EnumClass('ThumbOutputTypeEnum',
                                     ('jpg', 
                                      'png'),
                                      ('jpg', 
                                      'png'))

VideoScaleMethodEnum = enum.EnumClass('VideoScaleMethodEnum',
                                      ('height', 
                                       'width', 
                                       'downscale', 
                                       'upscale'),
                                       ('Height', 
                                       'Width', 
                                       'Downscale', 
                                       'Upscale'))

JobStateEnum = enum.EnumClass('JobStateEnum',
                              ('pending', 
                               'starting', 
                               'stopping', 
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
                                'Pre-processing', 
                                'Transcoding',
                                'Target processing',
                                'Waiting Acknowledge',
                                'Input file moving',
                                'Output file moving',
                                'Terminated'))

TargetStateEnum = enum.EnumClass('TargetStateEnum',
                                 ('done', 
                                  'pending', 
                                  'skipped', 
                                  'analysis',
                                  'postprocessing', 
                                  'link_file_generation'),
                                 ('Done', 
                                  'Pending', 
                                  'Skipped', 
                                  'Analysis',
                                  'Post-processing', 
                                  'Link file generation'))

TranscoderStatusEnum = enum.EnumClass('TranscoderStatusEnum',
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

MonitorFileStateEnum = enum.EnumClass('MonitorFileStateEnum',
                                      ('pending', 
                                       'downloading', 
                                       'transcoding',
                                       'queued'), 
                                      ('Pending', 
                                       'Downloading', 
                                       'Transcoding',
                                       'Queued'))

AudioVideoToleranceEnum = enum.EnumClass('AudioVideoToleranceEnum',
                                         ('strict', 
                                          'allow_without_audio', 
                                          'allow_without_video'),
                                         ('Strict', 
                                          'Allow without audio', 
                                          'Allow without video'))
