# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import implements

from flumotion.inhouse import log
from flumotion.inhouse import defer
from flumotion.inhouse import database

from flumotion.transcoder.admin.datasource import datasource
from flumotion.transcoder.admin.datastore import store


class TranscodeReport(object):

    def __init__(self):
        self.identifier = None

        self.customerId = None
        self.profileId = None
        self.relativePath = None
        self.reportPath = None
        self.fileChecksum = None
        self.fileSize = None
        self.fileType = None
        self.mimeType = None
        self.audioCodec = None
        self.videoCodec = None
        self.detectionTime = None
        self.creationTime = None
        self.modificationTime = None
        self.queueingTime = None
        self.transcodingStartTime = None
        self.transcodingFinishTime = None
        self.totalCpuTime = None
        self.totalRealTime = None
        self.attemptCount = None
        self.machineName = None
        self.workerName = None
        self.failure = None
        self.outcome = None
        self.successful = None


class SQLDataSource(log.Loggable):

    logCategory = 'SQL Data Source'

    queryTemplate = """
INSERT INTO transcoder_reports(
  customer_id,
  profile_id,
  relative_path,
  report_path,
  file_checksum,
  file_size,
  file_type,
  mime_type,
  audio_codec,
  video_codec,
  detection_time,
  creation_time,
  modification_time,
  queueing_time,
  transcoding_start_time,
  transcoding_finish_time,
  total_cpu_time,
  total_real_time,
  attempt_count,
  machine_name,
  worker_name,
  failure_id,
  outcome,
  successful
)
VALUES
  (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
   %s, %s, %s, %s, %s)
  """

    implements(datasource.IReportsSource)

    def __init__(self, config):
        self._connectionInfo = config.connectionInfo
        self._connection = database.Connection()

    def initialize(self):
        self.debug("Initializing SQL Data Source")
        self._connection.open(self._connectionInfo)
        self.debug("Opened an SQL connection to %s", self._connectionInfo)
        return defer.succeed(None)

    def newTranscodeReport(self):
        return TranscodeReport()

    def store(self, *reports):
        # FIXME: do this atomically in a transaction
        for report in reports:
            failure_id = None
            if report.failure is not None:
                failure_id = report.failure.failure_id
            params = (report.customerId,
                      report.profileId,
                      report.relativePath,
                      report.reportPath,
                      report.fileChecksum,
                      report.fileSize,
                      report.fileType,
                      report.mimeType,
                      report.audioCodec,
                      report.videoCodec,
                      report.detectionTime,
                      report.creationTime,
                      report.modificationTime,
                      report.queueingTime,
                      report.transcodingStartTime,
                      report.transcodingFinishTime,
                      report.totalCpuTime,
                      report.totalRealTime,
                      report.attemptCount,
                      report.machineName,
                      report.workerName,
                      failure_id,
                      report.outcome,
                      report.successful)

            self.debug("Running query %s with params %r", self.queryTemplate, params)

            d = self._connection.query(self.queryTemplate, params)
            return d

    def reset(self, *data):
        raise NotImplementedError

    def delete(self, *data):
        raise NotImplementedError

