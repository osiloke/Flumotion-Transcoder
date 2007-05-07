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

IntervalUnitEnum = enum.EnumClass('IntervalUnitEnum',
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
                               'done',
                               'preprocessing', 
                               'transcoding',
                               'target_processing',
                               'input_file_moving',
                               'output_file_moving'),
                               ('Pending', 
                                'Starting', 
                                'Stopping', 
                                'Done',
                                'Pre-processing', 
                                'Transcoding',
                                'Target processing',
                                'Input file moving',
                                'Output file moving'))

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
                                       'setting_up', 
                                       'working',
                                       'done', 
                                       'failed'), 
                                      ('Pending', 
                                       'Setting up', 
                                       'Working',
                                       'Done', 
                                       'Failed'))

MonitorFileStateEnum = enum.EnumClass('MonitorFileStateEnum',
                                      ('pending', 
                                       'downloading', 
                                       'transcoding'), 
                                      ('Pending', 
                                       'Downloading', 
                                       'Transcoding'))
