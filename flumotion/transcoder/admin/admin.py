# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import stat
from datetime import datetime

from zope.interface import implements
from twisted.internet import reactor

from flumotion.common import eventcalendar
from flumotion.common import i18n
from flumotion.common.enum import EnumClass

from flumotion.inhouse import log, defer, utils, errors as iherrors

from flumotion.transcoder import errors
from flumotion.transcoder.enums import MonitorFileStateEnum
from flumotion.transcoder.enums import TranscodingOutcomeEnum
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.diagnostic import Diagnostician
from flumotion.transcoder.admin.janitor import Janitor
from flumotion.transcoder.admin.enums import TaskStateEnum
from flumotion.transcoder.admin.context.admin import AdminContext
from flumotion.transcoder.admin.datastore.store import AdminStore
from flumotion.transcoder.admin.datastore.reportsstore import ReportsStore
from flumotion.transcoder.admin.proxy.managerset import ManagerSet
from flumotion.transcoder.admin.proxy.componentset import ComponentSet
from flumotion.transcoder.admin.proxy.workerset import WorkerSet
from flumotion.transcoder.admin.proxy.transcoderset import TranscoderSet
from flumotion.transcoder.admin.proxy.monitorset import MonitorSet
from flumotion.transcoder.admin.monitoring import Monitoring
from flumotion.transcoder.admin.montask import MonitoringTask
from flumotion.transcoder.admin.transcoding import Transcoding
from flumotion.transcoder.admin.scheduler import Scheduler
from flumotion.transcoder.admin.notifier import Notifier, notifyEmergency, notifyDebug
from flumotion.transcoder.admin.api import apiserver


class TranscoderAdmin(log.Loggable):

    logCategory = adminconsts.ADMIN_LOG_CATEGORY

    def __init__(self, config):
        self._adminCtx = AdminContext(config)
        self._datasource = self._adminCtx.getDataSource()
        self._reportsDataSource = self._adminCtx.getReportsDataSource()
        self._adminStore = AdminStore(self._datasource)
        self._reportsStore = ReportsStore(self._reportsDataSource)
        self._transcodeReports = {}
        self._storeCtx = self._adminCtx.getStoreContextFor(self._adminStore)
        notifierCtx = self._adminCtx.getNotifierContext()
        self._notifier = Notifier(notifierCtx, self._storeCtx)
        self._managerPxySet = ManagerSet(self._adminCtx)
        self._compPxySet = ComponentSet(self._managerPxySet)
        self._workerPxySet = WorkerSet(self._managerPxySet)
        self._diagnostician = Diagnostician(self._adminCtx, self._managerPxySet,
                                            self._workerPxySet, self._compPxySet)
        self._prognostician = self._adminCtx.getPrognostician()
        self._janitor = Janitor(self._adminCtx, self._compPxySet)
        self._transPxySet = TranscoderSet(self._managerPxySet)
        self._monPxySet = MonitorSet(self._managerPxySet)
        self._monitoring = Monitoring(self._workerPxySet, self._monPxySet)
        self._transcoding = Transcoding(self._workerPxySet, self._transPxySet)
        schedulerCtx = self._adminCtx.getSchedulerContext()
        self._scheduler = Scheduler(schedulerCtx, self._storeCtx, self._notifier,
                                    self._transcoding, self._diagnostician)
        self._translator = i18n.Translator()
        self._api = apiserver.Server(self._adminCtx.getAPIContext(), self)
        self._state = TaskStateEnum.stopped
        reactor.addSystemEventTrigger("before", "shutdown", self.__abort)


    ## Public Methods ##

    def initialize(self):
        self.info("Initializing Transcoder Administration")
        d = defer.Deferred()
        d.addCallback(defer.dropResult, self._datasource.initialize)
        d.addCallback(defer.dropResult, self._adminStore.initialize)
        d.addCallback(defer.dropResult, self._reportsDataSource.initialize)
        d.addCallback(defer.dropResult, self._notifier.initialize)
        d.addCallback(defer.dropResult, self._managerPxySet.initialize)
        d.addCallback(defer.dropResult, self._compPxySet.initialize)
        d.addCallback(defer.dropResult, self._workerPxySet.initialize)
        d.addCallback(defer.dropResult, self._monPxySet.initialize)
        d.addCallback(defer.dropResult, self._transPxySet.initialize)
        d.addCallback(defer.dropResult, self._scheduler.initialize)
        d.addCallback(defer.dropResult, self._monitoring.initialize)
        d.addCallback(defer.dropResult, self._transcoding.initialize)
        d.addCallback(defer.dropResult, self._janitor.initialize)
        d.addCallback(defer.dropResult, self._diagnostician.initialize)
        d.addCallback(defer.dropResult, self._api.initialize)
        d.addCallbacks(self.__cbAdminInitialized,
                       self.__ebAdminInitializationFailed)
        # Register listeners
        self._adminStore.connectListener("customer-added", self,
                                         self.__onCustomerStoreAdded)
        self._adminStore.connectListener("customer-removed", self,
                                         self.__onCustomerStoreRemoved)
        self._managerPxySet.connectListener("attached", self,
                                            self.__onAttached)
        self._managerPxySet.connectListener("detached", self,
                                            self.__onDetached)
        self._compPxySet.connectListener("component-added", self,
                                         self.__onComponentAddedToSet)
        self._compPxySet.connectListener("component-removed", self,
                                         self.__onComponentRemovedFromSet)
        self._scheduler.connectListener("profile-queued", self,
                                        self.__onProfileQueued)
        self._scheduler.connectListener("transcoding-started", self,
                                        self.__onTranscodingStarted)
        self._scheduler.connectListener("transcoding-failed", self,
                                        self.__onTranscodingFailed)
        self._scheduler.connectListener("transcoding-done", self,
                                        self.__onTranscodingDone)
        self._monitoring.connectListener("task-added", self,
                                         self.__onMonitoringTaskAdded)
        self._monitoring.connectListener("task-removed", self,
                                         self.__onMonitoringTaskRemoved)
        self._adminStore.refreshListener(self)
        self._managerPxySet.refreshListener(self)
        self._scheduler.refreshListener(self)
        self._monitoring.refreshListener(self)
        # fire the initialization
        d.callback(None)
        return d

    def getWorkerProxySet(self):
        return self._workerPxySet

    def getStoreContext(self):
        return self._storeCtx

    def getScheduler(self):
        return self._scheduler


    ## ManagerSet Event Listeners ##

    def __onDetached(self, managerPxySet):
        if self._state == TaskStateEnum.started:
            self.debug("Transcoder admin has been detached, "
                       "pausing transcoding")
            self.__pause()


    def __onAttached(self, managerPxySet):
        if self._state == TaskStateEnum.paused:
            self.debug("Transcoder admin attached, "
                       "resuming transcoding")
            self.__resume()


    ## ComponentSet Event Listners ##

    def __onComponentAddedToSet(self, compPxySet, compPxy):
        compPxy.connectListener("message", self,
                                self.__onComponentMessage)

    def __onComponentRemovedFromSet(self, compPxySet, compPxy):
        compPxy.disconnectListener("message", self)


    ## Component Event Listeners ##

    def __onComponentMessage(self, compPxy, message):
        if self._diagnostician.filterComponentMessage(message):
            return
        text = self._translator.translate(message)
        debug = message.debug
        level = {1: "ERROR", 2: "WARNING", 3: "INFO"}[message.level]
        workerPxy = compPxy.getWorkerProxy()
        if workerPxy:
            msg = ("Component '%s' on worker '%s' post a %s message"
                   % (compPxy.label, workerPxy.label, level))
        else:
            msg = ("Orphan component '%s' post a %s message"
                   % (compPxy.label, level))
        d = self._diagnostician.diagnoseComponentMessage(compPxy, message)
        args = (msg, text, debug)
        d.addCallbacks(self.__cbMessageDiagnosticSucceed,
                       self.__ebMessageDiagnosticFailed,
                       callbackArgs=args, errbackArgs=args)


    ## Store Event Listeners ##

    def __onCustomerStoreAdded(self, admin, custStore):
        self.debug("Customer '%s' Added", custStore.label)
        custStore.connectListener("profile-added", self,
                                  self.__onProfileStoreAdded)
        custStore.connectListener("profile-removed", self,
                                  self.__onProfileStoreRemoved)
        custStore.refreshListener(self)
        custCtx = self._storeCtx.getCustomerContextFor(custStore)
        task = MonitoringTask(self._monitoring, custCtx)
        self._monitoring.addTask(custCtx.identifier, task)


    def __onCustomerStoreRemoved(self, admin, custStore):
        self.debug("Customer '%s' Removed", custStore.label)
        custStore.disconnectListener("profile-added", self)
        custStore.disconnectListener("profile-removed", self)
        custCtx = self._storeCtx.getCustomerContextFor(custStore)
        self._monitoring.removeTask(custCtx.identifier)


    ## CustomerStore Event Listeners ##

    def __onProfileStoreAdded(self, custStore, profStore):
        self.debug("Profile '%s' Added", profStore.label)
        profStore.connectListener("target-added", self,
                                  self.__onTargetStoreAdded)
        profStore.connectListener("target-removed", self,
                                  self.__onTargetStoreRemoved)
        profStore.refreshListener(self)

    def __onProfileStoreRemoved(self, custStore, profStore):
        self.debug("Profile '%s' Removed", profStore.label)
        profStore.disconnectListener("target-added", self)
        profStore.disconnectListener("target-removed", self)


    ## ProfileStore Event Listeners ##

    def __onTargetStoreAdded(self, profStore, targStore):
        self.debug("Target '%s' Added", targStore.label)

    def __onTargetStoreRemoved(self, profStore, targStore):
        self.debug("Target '%s' Removed", targStore.label)


    ## Monitoring Event Listeners ##

    def __onMonitoringTaskAdded(self, takser, task):
        self.debug("Monitoring task '%s' added", task.label)
        task.connectListener("file-added", self,
                             self.__onMonitoredFileAdded)
        task.connectListener("file-state-changed", self,
                             self.__onMonitoredFileStateChanged)
        task.connectListener("file-removed", self,
                             self.__onMonitoredFileRemoved)
        task.connectListener("fail-to-run", self,
                             self.__onFailToRunOnWorker)
        task.refreshListener(self)

    def __onMonitoringTaskRemoved(self, tasker, task):
        self.debug("Monitoring task '%s' removed", task.label)
        task.disconnectListener("file-added", self)
        task.disconnectListener("file-state-changed", self)
        task.disconnectListener("file-removed", self)
        task.disconnectListener("fail-to-run", self)


    ## MonitoringTask Event Listeners ##

    def __onMonitoredFileAdded(self, montask, profCtx, state, fileinfo,
                               detection_time, mime_type, checksum, params):
        self.log("Monitoring task '%s' added profile '%s'",
                 montask.label, profCtx.inputPath)

        key = profCtx.inputBase, profCtx.inputRelPath
        if key not in self._transcodeReports:
            # TODO add params
            transcodeReportStore = self._reportsStore.newTranscodeReportStore()

            custCtx = profCtx.getCustomerContext()
            # TODO: maybe find something that uniquely identifies this transcod job and use it as a primary key?
            transcodeReportStore.customerId = custCtx.identifier
            transcodeReportStore.profileId = profCtx.identifier
            transcodeReportStore.relativePath = profCtx.inputRelPath
            if fileinfo:
                transcodeReportStore.creationTime = datetime.utcfromtimestamp(fileinfo[stat.ST_CTIME])
                transcodeReportStore.modificationTime = datetime.utcfromtimestamp(fileinfo[stat.ST_MTIME])
                transcodeReportStore.fileSize = fileinfo[stat.ST_SIZE]
            transcodeReportStore.detectionTime = detection_time
            transcodeReportStore.mimeType = mime_type
            #FIXME: check if checksum is None?
            transcodeReportStore.fileChecksum = checksum
            # FIXME: what happens if the transcoding is stopped and
            # then restarted? Or the admin never gets notified about a
            # job ending? Can we leak memory here?  Won't the
            # self._transcodeReports dictionary grow enormously? We
            # may need to add a remote method to query the dictionary size...
            self._transcodeReports[key] = transcodeReportStore

        self.__fileStateChanged(montask, profCtx, state, params)

    def __onMonitoredFileStateChanged(self, montask, profCtx, state,
                                      fileinfo, mime_type, checksum, params):
        self.log("Monitoring task '%s' profile '%s' state "
                 "changed to %s with fileinfo %r", montask.label,
                 profCtx.inputPath, state, fileinfo)

        # TODO Add params
        key = profCtx.inputBase, profCtx.inputRelPath
        transcodeReportStore = self._transcodeReports.get(key, None)
        if transcodeReportStore:
            if fileinfo:
                transcodeReportStore.fileSize = fileinfo[stat.ST_SIZE]
                transcodeReportStore.modificationTime = datetime.utcfromtimestamp(fileinfo[stat.ST_MTIME])
            transcodeReportStore.mimeType = mime_type
            transcodeReportStore.fileChecksum = checksum

        self.__fileStateChanged(montask, profCtx, state, params)

    def __onMonitoredFileRemoved(self, montask, profCtx, state):
        self.log("Monitoring task '%s' removed profile '%s'",
                 montask.label, profCtx.inputPath)
        self._scheduler.removeProfile(profCtx)

    def __onFailToRunOnWorker(self, task, workerPxy):
        msg = ("Monitoring task '%s' could not be started on worker '%s'"
               % (task.label, workerPxy.label))
        notifyEmergency(msg)


    ## Scheduler Event Listeners ##

    def __onProfileQueued(self, scheduler, profCtx):
        key = profCtx.inputBase, profCtx.inputRelPath
        transcodeReportStore = self._transcodeReports.get(key, None)
        if transcodeReportStore:
            now = datetime.utcnow()
            transcodeReportStore.queueingTime = now

        self.__setInputFileState(profCtx, MonitorFileStateEnum.queued)

    def __onTranscodingStarted(self, scheduler, task):
        profCtx = task.getProfileContext()
        key = profCtx.inputBase, profCtx.inputRelPath
        transcodeReportStore = self._transcodeReports.get(key, None)
        if transcodeReportStore:
            now = datetime.utcnow()
            transcodeReportStore.transcodingStartTime = now

        self.__setInputFileState(profCtx,
                                 MonitorFileStateEnum.transcoding)

    def __onTranscodingFailed(self, scheduler, task, report):
        # mind that report might be None, if the scheduler failed to retrieve it!
        profCtx = task.getProfileContext()
        key = profCtx.inputBase, profCtx.inputRelPath
        transcodeReportStore = self._transcodeReports.get(key, None)
        if transcodeReportStore:
            now = datetime.utcnow()
            transcodeReportStore.transcodingFinishTime = now
            transcodeReportStore.outcome = False
            transcodeReportStore.successful = False

            if report:
                transcodeReportStore.reportPath = ""+report.reportPath.__str__()
                # get info from the report and inserts it into the d
                self.__passReportInfo(report, task, transcodeReportStore)

                # decides, based on the information we have, if the file should
                # have failed to transcode
                self.__prognose(report, transcodeReportStore)

            transcodeReportStore.store()

            del self._transcodeReports[key]

        self.__setInputFileState(profCtx,
                                 MonitorFileStateEnum.failed)
        if not task.isAcknowledged():
            # If a transcoding fail without acknowledgment,
            # it propably segfault or has been killed.
            # So we have to move the input file to the
            # "fail" directory ourself.
            profCtx = task.getProfileContext()
            self.debug("Transcoding task for '%s' segfaulted "
                       "or has been kill", profCtx.inputPath)
            self.__moveFailedInputFiles(profCtx)

    def __onTranscodingDone(self, scheduler, task, report):
        # mind that report might be None, if the scheduler failed to retrieve it!
        profCtx = task.getProfileContext()
        key = profCtx.inputBase, profCtx.inputRelPath
        transcodeReportStore = self._transcodeReports.get(key, None)
        if transcodeReportStore:
            now = datetime.utcnow()
            transcodeReportStore.transcodingFinishTime = now
            transcodeReportStore.outcome = True
            transcodeReportStore.successful = True

            if report:
                # FIXME get the real path, not a template string with things like %(id)s
                # transcodeReportStore.reportPath = profCtx.doneRepRelPath
                transcodeReportStore.reportPath = report.reportPath.__str__()
                # get info from the report and inserts it into the d
                self.__passReportInfo(report, task, transcodeReportStore)

                # decides, based on the information we have, if the file should
                # have failed. to transcode.
                # It is probably not necessary to do it when the transcoding was
                # successful, but I'll leave it for now.
                self.__prognose(report, transcodeReportStore)

            transcodeReportStore.store()
            del self._transcodeReports[key]

        self.__setInputFileState(task.getProfileContext(),
                                 MonitorFileStateEnum.done)


    ## Private Methods ##

    """Gets information from the report and inserts it into the DB"""
    def  __passReportInfo(self, report, task, store):
        if not report or not store:
            return

        usage = report.cpuUsageTotal
        if usage:
            cpuTime, realTime, percent = usage
            store.totalCpuTime = cpuTime
            store.totalRealTime = realTime

        if report.source:
            store.fileType = report.source.fileType
            store.machineName = report.source.machineName
            analysis = report.source.analysis
            if report.source.analysis:
                store.audioCodec = analysis.otherTags.get("audio-codec", None)
                store.videoCodec = analysis.otherTags.get("video-codec", None)

        if report.local:
            store.workerName = report.local.name
        store.attemptCount = task.getAttemptCount()

    def __prognose(self, report, store):
        prog = self._prognostician
        data = {prog.type_key: report.source.fileType,
                prog.mime_key: store.mimeType,
                prog.file_size_key: report.source.fileSize,
                prog.has_video_key: report.source.analysis.hasVideo
                }
        prognosis = self._prognostician.prognose(data)
        store.failure = prognosis

    def __cbMessageDiagnosticSucceed(self, diagnostic, msg, text, debug):
        notifyDebug(msg, info=text, debug=debug, documents=diagnostic)

    def __ebMessageDiagnosticFailed(self, failure, msg, text, debug):
        notifyDebug(msg, info=text, debug=debug)
        log.notifyFailure(self, failure, "Failure during component message diagnostic")

    def __fileStateChanged(self, montask, profCtx, state, params=None):

        def changeState(newState):
            inputBase = profCtx.inputBase
            relPath = profCtx.inputRelPath
            montask.setFileState(inputBase, relPath, newState, profCtx.name)

        # Schedule new file if not already scheduled
        # and synchronize the file states
        queued = self._scheduler.isProfileQueued(profCtx)
        active = self._scheduler.isProfileActive(profCtx)
        if state == MonitorFileStateEnum.pending:
            if queued:
                changeState(MonitorFileStateEnum.queued)
                return
            if active:
                changeState(MonitorFileStateEnum.transcoding)
                return
            self._scheduler.addProfile(profCtx, params)
            return
        if state == MonitorFileStateEnum.queued:
            if active:
                changeState(MonitorFileStateEnum.transcoding)
                return
            if queued:
                return
            self._scheduler.addProfile(profCtx, params)
            return
        if state == MonitorFileStateEnum.transcoding:
            if queued:
                changeState(MonitorFileStateEnum.queued)
                return
            if active:
                return
            self._scheduler.addProfile(profCtx, params)
            return

    def pepe_es_un_capullo(self):
        return True

    def __moveFailedInputFiles(self, profCtx):
        custCtx = profCtx.getCustomerContext()
        inputBase = profCtx.inputBase
        failedBase = profCtx.failedBase
        relPath = profCtx.inputRelPath
        task = self._monitoring.getTask(custCtx.identifier)
        if not task:
            self.warning("No monitoring task found for customer '%s'; "
                         "cannot move files from '%s' to '%s'",
                         custCtx.label, inputBase, failedBase)
            return
        task.moveFiles(inputBase, failedBase, [relPath])

    def __setInputFileState(self, profCtx, state):
        custCtx = profCtx.getCustomerContext()
        inputBase = profCtx.inputBase
        task = self._monitoring.getTask(custCtx.identifier)
        if not task:
            self.warning("No monitoring task found for customer '%s'; "
                         "cannot set file '%s' state to %s",
                         custCtx.label, inputBase, state.name)
            return
        relPath = profCtx.inputRelPath
        task.setFileState(inputBase, relPath, state, profCtx.name)

    def __startup(self):
        if not (self._state == TaskStateEnum.stopped):
            raise errors.TranscoderError("Cannot start transcoder admin when %s"
                                         % self._state.name)
        self.info("Starting Transcoder Administration")
        self._state = TaskStateEnum.starting
        d = defer.Deferred()
        d.addCallback(defer.bridgeResult, self.debug,
                      "Starting monitoring manager")
        d.addCallback(defer.dropResult, self._monitoring.start,
                      adminconsts.MONITORING_START_TIMEOUT)
        # Wait monitor components to be activated before continuing
        d.addCallback(defer.bridgeResult, self.debug,
                      "Waiting for monitoring to become active")
        d.addCallback(defer.dropResult, self._monitoring.waitActive,
                      adminconsts.MONITORING_ACTIVATION_TIMEOUT)
        d.addErrback(self.__ebMonitoringNotReady)
        d.addCallback(defer.bridgeResult, self.debug,
                      "Starting transcoding manager")
        d.addCallback(defer.dropResult, self._transcoding.start,
                      adminconsts.TRANSCODING_START_TIMEOUT)
        d.addCallback(defer.bridgeResult, self.debug,
                      "Starting scheduler manager")
        d.addCallback(defer.dropResult, self._scheduler.start,
                      adminconsts.SCHEDULER_START_TIMEOUT)
        d.addCallback(defer.bridgeResult, self.debug,
                      "Starting notification manager")
        d.addCallback(defer.dropResult, self._notifier.start,
                      adminconsts.NOTIFIER_START_TIMEOUT)
        d.addCallbacks(self.__cbSartupSucceed, self.__ebSartupFailed)
        d.callback(None)

    def __resume(self):
        if not (self._state == TaskStateEnum.paused):
            raise errors.TranscoderError("Cannot resume transcoder admin when %s"
                                         % self._state.name)
        self.info("Resuming Transcoder Administration")
        self._state = TaskStateEnum.resuming
        d = defer.Deferred()
        # Wait a moment to let the workers the oportunity
        # to log back to the manager.
        d.addCallback(defer.bridgeResult, self.debug,
                      "Waiting for workers to log back")
        d.addCallback(defer.delayedSuccess, adminconsts.RESUME_DELAY)
        d.addCallback(defer.bridgeResult, self.debug,
                      "Resuming monitoring manager")
        d.addCallback(defer.dropResult, self._monitoring.resume,
                      adminconsts.MONITORING_RESUME_TIMEOUT)
        # Wait monitor components to be activated before continuing
        d.addCallback(defer.bridgeResult, self.debug,
                      "Waiting for monitoring to become active")
        d.addCallback(defer.dropResult, self._monitoring.waitActive,
                      adminconsts.MONITORING_ACTIVATION_TIMEOUT)
        d.addErrback(self.__ebMonitoringNotReady)
        d.addCallback(defer.bridgeResult, self.debug,
                      "Resuming transcoding manager")
        d.addCallback(defer.dropResult, self._transcoding.resume,
                      adminconsts.TRANSCODING_RESUME_TIMEOUT)
        d.addCallback(defer.bridgeResult, self.debug,
                      "Resuming scheduler")
        d.addCallback(defer.dropResult, self._scheduler.resume,
                      adminconsts.SCHEDULER_RESUME_TIMEOUT)
        d.addCallbacks(self.__cbResumingSucceed, self.__ebResumingFailed)
        return d.callback(None)

    def __pause(self):
        if not (self._state == TaskStateEnum.started):
            raise errors.TranscoderError("Cannot pause transcoder admin when %s"
                                         % self._state.name)
        self.info("Pausing Transcoder Administration")
        d = defer.Deferred()
        d.addCallback(defer.bridgeResult, self.debug,
                      "Pausing scheduler")
        d.addCallback(defer.dropResult, self._scheduler.pause,
                      adminconsts.SCHEDULER_PAUSE_TIMEOUT)
        d.addCallback(defer.bridgeResult, self.debug,
                      "Pausing transcoding manager")
        d.addCallback(defer.dropResult, self._transcoding.pause,
                      adminconsts.TRANSCODING_PAUSE_TIMEOUT)
        d.addCallback(defer.bridgeResult, self.debug,
                      "Pausing monitoring manager")
        d.addCallback(defer.dropResult, self._monitoring.pause,
                      adminconsts.MONITORING_PAUSE_TIMEOUT)
        d.addCallbacks(self.__cbPausingSucceed, self.__ebPausingFailed)
        d.callback(None)

    def __abort(self):
        if self._state == TaskStateEnum.terminated:
            return
        self._state = TaskStateEnum.terminated

    def __cbAdminInitialized(self, result):
        self.info("Waiting Transcoder Administration to become Idle")
        self.debug("Waiting store to become idle")
        d = self._adminStore.waitIdle(adminconsts.WAIT_IDLE_TIMEOUT)
        d.addErrback(defer.bridgeResult, self.warning,
                     "Data store didn't became idle; trying to continue")
        d.addBoth(defer.bridgeResult, self.debug,
                  "Waiting managers to become idle")
        d.addBoth(defer.dropResult, self._managerPxySet.waitIdle,
                  adminconsts.WAIT_IDLE_TIMEOUT)
        d.addErrback(defer.bridgeResult, self.warning,
                     "Managers didn't became idle; trying to continue")
        d.addBoth(defer.bridgeResult, self.debug,
                  "Waiting components to become idle")
        d.addBoth(defer.dropResult, self._compPxySet.waitIdle,
                  adminconsts.WAIT_IDLE_TIMEOUT)
        d.addErrback(defer.bridgeResult, self.warning,
                     "Components didn't became idle; trying to continue")
        d.addBoth(defer.bridgeResult, self.debug,
                  "Waiting monitoring manager to become idle")
        d.addBoth(defer.dropResult, self._monitoring.waitIdle,
                  adminconsts.WAIT_IDLE_TIMEOUT)
        d.addErrback(defer.bridgeResult, self.warning,
                     "Monitoring tasks didn't became idle; trying to continue")
        d.addBoth(defer.bridgeResult, self.debug,
                  "Waiting transcoding manager to become idle")
        d.addBoth(defer.dropResult, self._transcoding.waitIdle,
                  adminconsts.WAIT_IDLE_TIMEOUT)
        d.addErrback(defer.bridgeResult, self.warning,
                     "Transcoding tasks didn't became idle; trying to continue")
        d.addBoth(defer.bridgeResult, self.debug,
                  "Waiting scheduler to become idle")
        d.addBoth(defer.dropResult, self._scheduler.waitIdle,
                  adminconsts.WAIT_IDLE_TIMEOUT)
        d.addErrback(defer.bridgeResult, self.warning,
                     "Scheduler didn't became idle; trying to continue")
        d.addBoth(defer.dropResult, self.__startup)
        return d.addCallback(defer.overrideResult, self)

    def __ebAdminInitializationFailed(self, failure):
        log.notifyFailure(self, failure,
                          "Failure during Transcoder Administration Initialization")
        reactor.stop()

    def __ebMonitoringNotReady(self, failure):
        if failure.check(iherrors.TimeoutError):
            log.notifyFailure(self, failure, "Monitoring fail to activate, no worker ?")
            return None
        return failure

    def __cbSartupSucceed(self, result):
        self.info("Transcoder Administration Successfully Started")
        self._state = TaskStateEnum.started

    def __ebSartupFailed(self, failure):
        log.notifyFailure(self, failure,
                          "Failed to startup administration")
        self._state = TaskStateEnum.stopped

    def __cbResumingSucceed(self, result):
        self.info("Transcoder Administration Successfully Resumed")
        self._state = TaskStateEnum.started

    def __ebResumingFailed(self, failure):
        log.notifyFailure(self, failure,
                          "Failed to resume administration")
        self._state = TaskStateEnum.paused

    def __cbPausingSucceed(self, result):
        self.info("Transcoder Administration Successfully Paused")
        self._state = TaskStateEnum.paused

    def __ebPausingFailed(self, failure):
        log.notifyFailure(self, failure,
                          "Failed to pause administration")
        self._state = TaskStateEnum.started
