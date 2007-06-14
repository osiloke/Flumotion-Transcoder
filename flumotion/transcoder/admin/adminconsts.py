# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

# The time a proxy wait after a SIGTERM to send a SIGKILL to a component
COMPONENT_WAIT_TO_KILL = 30

# The time between each monitor components set adjustments
MONITORSET_TUNE_PERIOD = 10

# Componenet label template
TRANSCODER_LABEL_TEMPLATE = "transcoder-%(customerName)s-%(profileName)s"
MONITOR_LABEL_TEMPLATE = "monitor-%(customerName)s"

# Maximum time to wait for the admin to load 
# and initialize all components stats
WAIT_IDLE_TIMEOUT = 30

# Maximum time to wait for a component to go happy
HAPPY_TIMEOUT = 60

# Maximum time to wait for component properties
TASKER_WAITPROPS_TIMEOUT = 30

# Maximum time for Monitoring to wait for monitor operations
MONITORING_LOAD_TIMEOUT = 30
MONITORING_START_DELAY = 3
MONITORING_UI_TIMEOUT = 10

# Forced component deletion constants
FORCED_DELETION_TIMEOUT = 10
FORCED_DELETION_MAX_RETRY = 3

LOAD_COMPONENT_TIMEOUT = 30.0


# AdminStore default values
DEFAULT_OUTPUT_MEDIA_TEMPLATE = "%(targetPath)s%(sourceFile)s%(targetExtension)s"
DEFAULT_OUTPUT_THUMB_TEMPLATE = "%(targetPath)s%(sourceFile)s.%%(index)03d%(targetExtension)s"
DEFAULT_LINK_FILE_TEMPLATE = "%(targetPath)s%(sourceFile)s.link"
DEFAULT_CONFIG_FILE_TEMPLATE = "%(sourcePath)s.ini"
DEFAULT_REPORT_FILE_TEMPLATE = "%(sourcePath)s.%%(id)s.rep"
DEFAULT_MONITORING_PERIOD = 5
DEFAULT_TRANSCODING_TIMEOUT = 60
DEFAULT_POSTPROCESS_TIMEOUT = 60
DEFAULT_PREPROCESS_TIMEOUT = 60
DEFAULT_MAIL_SUBJECT_TEMPLATE = "Default Mail Subject"
DEFAULT_MAIL_BODY_TEMPLATE = "Default Mail Body"
DEFAULT_GETREQUEST_TIMEOUT = 30
DEFAULT_GETREQUEST_RETRY_COUNT = 3
DEFAULT_GETREQUEST_RETRY_SLEEP = 60

# Default customer directories
DEFAULT_INPUT_DIR = "/%s/files/incoming"
DEFAULT_OUTPUT_DIR = "/%s/files/outgoing"
DEFAULT_FAILED_DIR = "/%s/files/failed"
DEFAULT_DONE_DIR = "/%s/files/done"
DEFAULT_LINK_DIR = "/%s/files/links"
DEFAULT_CONFIG_DIR = "/%s/configs"
DEFAULT_FAILEDREP_DIR = "/%s/reports/failed"
DEFAULT_DONEREP_DIR = "/%s/reports/done"
DEFAULT_WORK_DIR = "/%s/work"
