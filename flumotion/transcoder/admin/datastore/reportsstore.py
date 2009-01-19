# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder.admin.datastore import base, activity

class ReportsStore(base.SimpleStore):

    def __init__(self, dataSource):
        base.SimpleStore.__init__(self, None,
                                  identifier="store.statistics",
                                  label="Statistics Store")
        self._dataSource = dataSource

    def newTranscodeReportStore(self):
        return TranscodeReportStore(self, self._dataSource.newTranscodeReport())


class TranscodeReportStore(base.DataStore):

    identifier = activity.ReadWriteProxy("identifier")

    customerId = activity.ReadWriteProxy("customerId")
    profileId = activity.ReadWriteProxy("profileId")
    relativePath = activity.ReadWriteProxy("relativePath")
    reportPath = activity.ReadWriteProxy("reportPath")
    fileChecksum = activity.ReadWriteProxy("fileChecksum")
    fileSize = activity.ReadWriteProxy("fileSize")
    fileType = activity.ReadWriteProxy("fileType")
    mimeType = activity.ReadWriteProxy("mimeType")
    audioCodec = activity.ReadWriteProxy("audioCodec")
    videoCodec = activity.ReadWriteProxy("videoCodec")
    detectionTime = activity.ReadWriteProxy("detectionTime")
    creationTime = activity.ReadWriteProxy("creationTime")
    modificationTime = activity.ReadWriteProxy("modificationTime")
    queueingTime = activity.ReadWriteProxy("queueingTime")
    transcodingStartTime = activity.ReadWriteProxy("transcodingStartTime")
    transcodingFinishTime = activity.ReadWriteProxy("transcodingFinishTime")
    totalCpuTime = activity.ReadWriteProxy("totalCpuTime")
    totalRealTime = activity.ReadWriteProxy("totalRealTime")
    attemptCount = activity.ReadWriteProxy("attemptCount")
    machineName = activity.ReadWriteProxy("machineName")
    workerName = activity.ReadWriteProxy("workerName")
    failure = activity.ReadWriteProxy("failure")
    outcome = activity.ReadWriteProxy("outcome")
    successful = activity.ReadWriteProxy("successful")

    _deleted = False

    def __init__(self, parentStore, data):
        base.DataStore.__init__(self, parentStore, data)

    def store(self):
        self.parent._dataSource.store(self)

    def _touche(self):
        pass
