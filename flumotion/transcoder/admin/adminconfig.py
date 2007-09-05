# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

"""
    Transcoder Configuration File.
    
    This file setup the basic configuration properties 
    for the transcoder administration.
    Following is an example of the configuration properties.
    If the specified value is the default, the line will be commented.
    For more information see the section 3-2 of the document specification.odt
    
    -----
    
    # Global properties
    [global]
    
    # Flumotion debug level. Can be overrided 
    # with the command line option -d
    # See specification.odt:1 for more information
    debug = *:2
    
    # The template used to generate the transcoder components label. 
    # See section 4-1 of specification.odt for more information
    #transcoder-label-template = "%(customerName)s/%(profileName)s:%(sourcePath)s"
    
    # The template used to generate the monitor components label. 
    # See section 4-1 of specification.odt for more information
    #monitor-label-template = "Monitor for %(customerName)s"
    
    # The template used to generate the activity labels.
    # See section 4-2 of specification.odt for more information
    #activity-label-template = "%(customerName)s/%(profileName)s:%(sourcePath)s"
    
    # Administration Properties
    [admin]
    
    # The administration's virtual roots
    # See section 1-1 of specification.odt for more information
    roots#default = /home/file
    
    # Admin's Data-Source Properties
    [admin:data-source]
    
    # Path to the file data-source global configuration
    data-file = /etc/flumotion/transcoder/transcoder-data.ini
    
    # Admin's Notifier Properties
    [admin:notifier]
    
    # SMTP server host used to send mail notifications
    smtp-server = mail.fluendo.com
    
    # SMTP username and password used if authentication is needed
    #smtp-username = 
    #smtp-password = 
    
    # eMail used to send notification, debug and emergency mails
    mail-notify-sender = Transcoder Admin <transcoder-notify@fluendo.com>
    mail-debug-sender = Transcoder Debug <transcoder-debug@fluendo.com>
    mail-emergency-sender = Transcoder Emergency <transcoder-emergency@fluendo.com>
    
    # Recipients of the debug and emergency mails
    mail-emergency-recipients = emergency-list@fluendo.com, sebastien@fluendo.com
    mail-debug-recipients = debug-list@fluendo.com, sebastien@fluendo.com
    
    # Manager Properties
    [manager]
    
    # Hostname and port used to connect to the transcoding manager
    host = manager.dev.fluendo.lan
    port = 7632
    
    # Username and password used to login to the manager
    username = user
    password = test
    
    # Properties to use SSL to connect to the manager
    #use-ssl = False
    #certificate = 
    
    # Default Worker Properties
    [worker-defaults]
    
    # The workers' default virtual path roots
    # See section 1-1 of specification.odt for more information
    roots#default = /home/file
    roots#temp = /var/tmp/flumotion/transcoder
    
    # The default maximum simultaneous transcoding tasks 
    max-task = 2
    
    # GStreamer debug modifier; Not used yet
    gst-debug = *:2
    
    # The workers default properties can be overriden 
    # by worker name. For example:
    [workers:repeater.dev]
    roots#default = /storage/transcoder/file/
    
    [workers:streamer1.dev]
    max-task = 3
    
    ------------------------------------------------------------"""

from flumotion.transcoder import properties
from flumotion.transcoder.admin import adminconsts

class ManagerConfig(properties.PropertyBag):
    host = properties.String('host', None, True)
    port = properties.Integer('port', None, True)
    username = properties.String('username', None, True)
    password = properties.String('password', None, True)
    useSSL = properties.Boolean('use-ssl', False)
    certificate = properties.String('certificate', None)


class WorkerConfig(properties.PropertyBag):
    roots = properties.Dict(properties.String('roots'))
    maxTask = properties.Integer('max-task', 1, False, True)
    gstDebug = properties.String('gst-debug', None)


class DataSourceConfig(properties.PropertyBag):
    dataFile = properties.String('data-file', None, True)

class NotifierConfig(properties.PropertyBag):
    smtpServer = properties.String('smtp-server', None, True)
    smtpRequireTLS = properties.Boolean('smtp-require-tls', True)
    smtpUsername = properties.String('smtp-username', None, False)
    smtpPassword = properties.String('smtp-password', None, False)
    mailNotifySender = properties.String('mail-notify-sender', None, True)
    mailEmergencySender = properties.String('mail-emergency-sender', None, True)
    mailEmergencyRecipients = properties.String('mail-emergency-recipients', None, True)
    mailDebugSender = properties.String('mail-debug-sender', None, True)
    mailDebugRecipients = properties.String('mail-debug-recipients', None, True)

class AdminConfig(properties.PropertyBag):
    datasource = properties.Child("data-source", DataSourceConfig)
    notifier = properties.Child("notifier", NotifierConfig)
    roots = properties.Dict(properties.String('roots'))

class ClusterConfig(properties.RootPropertyBag):
    
    VERSION = (1, 0)
    COMMENTS = __doc__.split('\n')
    
    debug = properties.String("debug")
    admin = properties.Child("admin", AdminConfig)
    manager = properties.Child("manager", ManagerConfig)
    workerDefaults = properties.Child('worker-defaults', WorkerConfig)
    workers = properties.ChildDict('workers', WorkerConfig)
    transcoderLabelTemplate = properties.String("transcoder-label-template",
                                                adminconsts.TRANSCODER_LABEL_TEMPLATE)
    monitorLabelTemplate = properties.String("monitor-label-template",
                                             adminconsts.MONITOR_LABEL_TEMPLATE)
    activityLabelTemplate = properties.String("activity-label-template",
                                             adminconsts.ACTIVITY_LABEL_TEMPLATE)
    