# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.common.enum import EnumClass


ComponentDomainEnum = EnumClass('ComponentDomainEnum',
                                ('atmosphere', 
                                 'flow'))

TaskStateEnum = EnumClass("TaskStateEnum",
                          ("stopped",
                           "starting",
                           "started",
                           "pausing",
                           "paused",
                           "resuming",
                           "terminating",
                           "terminated"),
                          ("Stopped",
                           "Starting",
                           "Started",
                           "Pausing",
                           "Paused",
                           "Resuming",
                           "Terminating",
                           "Terminated"))

ActivityStateEnum = EnumClass("ActivityStateEnum",
                              ("unknown",
                               "stopped",
                               "started",
                               "paused",
                               "done",
                               "failed"),
                              ("Unknown",
                               "Stopped",
                               "Started",
                               "Paused",
                               "Done",
                               "Failed"))

ActivityTypeEnum =  EnumClass("ActivityTypeEnum",
                              ("transcoding",
                               "notification"),
                              ("Transcoding",
                               "Notification"))

NotificationTypeEnum =  EnumClass("NotificationTypeEnum",
                                  ("get_request",
                                   "email"),
                                   ("GET Request",
                                   "EMail"))

NotificationTriggerEnum =  EnumClass("NotificationTriggerEnum",
                                     ("done",
                                      "failed"),
                                      ("Done",
                                       "Failed"))

MailAttachmentEnum = EnumClass("MailAttachmentEnum",
                               ("report",
                                "log"),
                               ("Report",
                                "Log"))

MailAddressTypeEnum = EnumClass("MailAddressTypeEnum",
                                ("to",
                                 "cc",
                                 "bcc"),
                                ("TO",
                                 "CC",
                                 "BCC"))
