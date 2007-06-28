# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

# Log categories
ADMIN_LOG_CATEGORY = "admin"
STORES_LOG_CATEGORY = "stores"
PROXIES_LOG_CATEGORY = "proxies"
DATASOURCE_LOG_CATEGORY = "datasource"
MONITORING_LOG_CATEGORY = "monitoring"
TRANSCODING_LOG_CATEGORY = "transcoding"


# The time a proxy wait after a SIGTERM to send a SIGKILL to a component
COMPONENT_WAIT_TO_KILL = 30

# The time between each monitor components set adjustments
MONITORSET_TUNE_PERIOD = 10

# Componenet label template
TRANSCODER_LABEL_TEMPLATE = "%(customerName)s/%(profileName)s:%(sourcePath)s"
MONITOR_LABEL_TEMPLATE = "Monitor for %(customerName)s"

# Maximum time to wait for the admin to load 
# and initialize all components stats
WAIT_IDLE_TIMEOUT = 30

# Maximum time to wait for a worker instance 
# when the worker name is set to a component state
WAIT_WORKER_TIMEOUT = 30

# Maximum time to wait for component properties
TASKMANAGER_WAITPROPS_TIMEOUT = 30
TASKMANAGER_SYNCH_TIMEOUT = 30

# Maximum time for admin tasks to wait for a component to be loaded
TASK_LOAD_TIMEOUT = 30
# Maximum time for admin tasks to wait for a component becoming happy
TASK_HAPPY_TIMEOUT = 60
# First delay to wait when retrying to load a component
TASK_START_DELAY = 2
# The factor to apply to the delay 
TASK_START_DELAY_FACTOR = 2.7182818284590451
# Maximum time to hold a lost component before starting another one
TASK_HOLD_TIMEOUT = 60
# Maximum time to look for a valid component before starting a new one
TASK_POTENTIAL_COMPONENT_TIMEOUT = 20
# Maximum time to wait when retrieving component UI State
TASK_UISTATE_TIMEOUT = 20


MONITOR_MAX_RETRIES = 4
MONITORING_START_TIMEOUT = 30
MONITORING_ACTIVE_WORKER_TIMEOUT = 20

TRANSCODER_STATUS_TIMEOUT = 20
TRANSCODER_MAX_RETRIES = 3
TRANSCODING_START_TIMEOUT = 30
TRANSCODING_ACTIVE_WORKER_TIMEOUT = 20


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
