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

# Log categories
ADMIN_LOG_CATEGORY = "admin"
STORES_LOG_CATEGORY = "stores"
PROXIES_LOG_CATEGORY = "proxy"
DATASOURCE_LOG_CATEGORY = "datasource"
MONITORING_LOG_CATEGORY = "monitoring"
TRANSCODING_LOG_CATEGORY = "transcoding"
SCHEDULER_LOG_CATEGORY = "scheduler"
NOTIFIER_LOG_CATEGORY = "notifier"
IDLE_LOG_CATEGORY = "idle"
JANITOR_LOG_CATEGORY = "janitor"

GET_REQUEST_AGENT = "Flumotion Transcoder"

# The generic timeout used for remote method call
REMOTE_CALL_TIMEOUT = 60

# The time to let the workers to log back in the manager before resuming
RESUME_DELAY = 20

# The time a proxy wait after a SIGTERM to send a SIGKILL to a component
COMPONENT_WAIT_TO_KILL = 30

# The time between each monitor components set adjustments
MONITORSET_TUNE_PERIOD = 10

# Label templates
ACTIVITY_LABEL_TEMPLATE = "%(customerName)s/%(profileName)s:%(sourcePath)s"
TRANSCODER_LABEL_TEMPLATE = "%(customerName)s/%(profileName)s:%(sourcePath)s"
MONITOR_LABEL_TEMPLATE = "Monitor for %(customerName)s"

# Maximum time to wait for the admin to load
# and initialize all components stats
WAIT_IDLE_TIMEOUT = 30

# Maximum time to wait for an elemnt to be active
WAIT_ACTIVE_TIMEOUT = 30

# Maximum time to wait for a worker instance
# when the worker name is set to a component state
WAIT_WORKER_TIMEOUT = 30

# Maximum time to wait for component properties
TASKMANAGER_WAITPROPS_TIMEOUT = 30
TASKMANAGER_IDLE_TIMEOUT = 30

# Maximum time for admin tasks to wait for a component to be loaded
TASK_LOAD_TIMEOUT = 30
# Maximum time for admin tasks to wait for a component becoming happy
TASK_HAPPY_TIMEOUT = 60
# First delay to wait when retrying to load a component
TASK_START_DELAY = 3
# The factor to apply to the delay
TASK_START_DELAY_FACTOR = 4
# Maximum time to hold a lost component before starting another one
TASK_HOLD_TIMEOUT = 60
# Maximum time to look for a valid component before starting a new one
TASK_POTENTIAL_COMPONENT_TIMEOUT = 20
# Maximum time to wait when retrieving component UI State
TASK_UISTATE_TIMEOUT = 20

# Maximum time the janitor wait before forcing the component deletion
JANITOR_WAIT_FOR_DELETE = 20

MONITOR_STATE_UPDATE_PERIOD = 1
MONITOR_MAX_RETRIES = 3
MONITORING_POTENTIAL_WORKER_TIMEOUT = 20

# Maximum time an elected transcoder can stay sad before starting another one
TRANSCODER_SAD_TIMEOUT = 120
# Maximum time a component can take to acknowledge.
# Take into account that a lots of files are copied/moved
# during acknowledgement, so it can take a long time
TRANSCODER_ACK_TIMEOUT = 60*12
TRANSCODER_MAX_RETRIES = 2
TRANSCODING_POTENTIAL_WORKER_TIMEOUT = 20

# Startup timeouts
MONITORING_START_TIMEOUT = 30
MONITORING_PAUSE_TIMEOUT = 30
MONITORING_RESUME_TIMEOUT = 30
MONITORING_ACTIVATION_TIMEOUT = 30
TRANSCODING_START_TIMEOUT = 30
TRANSCODING_PAUSE_TIMEOUT = 30
TRANSCODING_RESUME_TIMEOUT = 30
SCHEDULER_START_TIMEOUT = 30
SCHEDULER_PAUSE_TIMEOUT = 30
SCHEDULER_RESUME_TIMEOUT = 30
NOTIFIER_START_TIMEOUT = 30

# Maximum time to wait for a datasource to be ready
WAIT_DATASOURCE_TIMEOUT = 60

# Forced component deletion constants
FORCED_DELETION_TIMEOUT = 10
FORCED_DELETION_BUZY_TIMEOUT = 30
FORCED_DELETION_MAX_RETRY = 3
LOAD_COMPONENT_TIMEOUT = 30.0


GLOBAL_MAIL_NOTIFY_TIMEOUT = 60
GLOBAL_MAIL_NOTIFY_RETRIES = 5

# AdminStore default values
DEFAULT_ACCESS_FORCE_USER = None
DEFAULT_ACCESS_FORCE_GROUP = None
DEFAULT_ACCESS_FORCE_DIR_MODE = None
DEFAULT_ACCESS_FORCE_FILE_MODE = None
DEFAULT_OUTPUT_MEDIA_TEMPLATE = "%(targetPath)s"
DEFAULT_OUTPUT_THUMB_TEMPLATE = "%(targetDir)s%(targetBasename)s.%(index)03d%(targetExtension)s"
DEFAULT_LINK_FILE_TEMPLATE = "%(targetPath)s.link"
DEFAULT_CONFIG_FILE_TEMPLATE = "%(sourcePath)s.ini"
DEFAULT_REPORT_FILE_TEMPLATE = "%(sourcePath)s.%(id)s.rep"
DEFAULT_MONITORING_PERIOD = 5
DEFAULT_TRANSCODING_TIMEOUT = 60
DEFAULT_POSTPROCESS_TIMEOUT = 60
DEFAULT_PREPROCESS_TIMEOUT = 60
DEFAULT_MAIL_TIMEOUT = 30
DEFAULT_MAIL_RETRY_MAX = 3
DEFAULT_MAIL_RETRY_SLEEP = 60
DEFAULT_HTTPREQUEST_TIMEOUT = 30
DEFAULT_HTTPREQUEST_RETRY_MAX = 3
DEFAULT_HTTPREQUEST_RETRY_SLEEP = 60
DEFAULT_SQL_TIMEOUT = 30
DEFAULT_SQL_RETRY_MAX = 3
DEFAULT_SQL_RETRY_SLEEP = 60
DEFAULT_PROCESS_PRIORITY = 100
DEFAULT_TRANSCODING_PRIORITY = 100

DEFAULT_MAIL_SUBJECT_TEMPLATE = "%(customerName)s/%(profileName)s transcoding %(trigger)s"
DEFAULT_MAIL_BODY_TEMPLATE = """
Transcoding Report
==================

Customer Name: %(customerName)s
Profile Name:  %(profileName)s
--------------

  File: '%(inputRelPath)s'

  Message: %(errorMessage)s

"""


# Default CustomerStore values
DEFAULT_CUSTOMER_PRIORITY = 100

# Default customer directories
DEFAULT_INPUT_DIR = "/%s/files/incoming"
DEFAULT_OUTPUT_DIR = "/%s/files/outgoing"
DEFAULT_FAILED_DIR = "/%s/files/failed"
DEFAULT_DONE_DIR = "/%s/files/done"
DEFAULT_LINK_DIR = "/%s/files/links"
DEFAULT_CONFIG_DIR = "/%s/configs"
DEFAULT_TEMPREP_DIR = "/%s/reports/pending"
DEFAULT_FAILEDREP_DIR = "/%s/reports/failed"
DEFAULT_DONEREP_DIR = "/%s/reports/done"
DEFAULT_WORK_DIR = "/%s/work"

FILE_MONITOR = "file-monitor"
HTTP_MONITOR = "http-monitor"
