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

TranscodingTypeEnum = EnumClass("TranscodingTypeEnum",
                              ("normal",),
                              ("Normal",))

NotificationTypeEnum =  EnumClass("NotificationTypeEnum",
                                  ("http_request",
                                   "email",
                                   "sql"),
                                   ("HTTP Request",
                                   "EMail",
                                   "SQL"))

NotificationTriggerEnum =  EnumClass("NotificationTriggerEnum",
                                     ("done",
                                      "failed"),
                                      ("Done",
                                       "Failed"))

MailAddressTypeEnum = EnumClass("MailAddressTypeEnum",
                                ("to",
                                 "cc",
                                 "bcc"),
                                ("TO",
                                 "CC",
                                 "BCC"))

DocumentTypeEnum = EnumClass("DocumentTypeEnum",
                             ("trans_report",
                              "trans_config",
                              "trans_log",
                              "diagnostic"),
                             ("Transcoding Report",
                              "Transcoding Configuration",
                              "Transcoding Log",
                              "Error Diagnostic"))

APIBouncerEnum = EnumClass("APIBouncerEnum",
                           ("saltedsha256",),
                           ("salted-sha256",))
