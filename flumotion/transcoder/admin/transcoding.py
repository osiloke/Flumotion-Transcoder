# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from zope.interface import Interface, implements
from twisted.internet import defer, reactor
from twisted.python.failure import Failure

from flumotion.common.planet import moods

from flumotion.transcoder import log
from flumotion.transcoder import utils
from flumotion.transcoder.errors import OperationTimedOutError
from flumotion.transcoder.admin import adminconsts
from flumotion.transcoder.admin.taskmanager import TaskManager
from flumotion.transcoder.admin.transbalancer import TranscoderBalancer
from flumotion.transcoder.admin.proxies.workerset import WorkerSetListener
from flumotion.transcoder.admin.proxies.transcoderset import TranscoderSetListener
from flumotion.transcoder.admin.proxies.transcoderproxy import TranscoderListener

#FIXME: Better handling of listener subclassing

class ITranscodingListener(Interface):
    def onTranscodingTaskAdded(self, takser, task):
        pass
    
    def onTranscodingTaskRemoved(self, tasker, task):
        pass

    
class TranscodingListener(object):
    
    implements(ITranscodingListener)

    def onTranscodingTaskAdded(self, takser, task):
        pass
    
    def onTranscodingTaskRemoved(self, tasker, task):
        pass


class Transcoding(TaskManager, WorkerSetListener, 
                 TranscoderSetListener, TranscoderListener):
    
    logCategory = adminconsts.TRANSCODING_LOG_CATEGORY
    
    def __init__(self, workerset, transcoderset):
        TaskManager.__init__(self, ITranscodingListener)
        self._workers = workerset
        self._transcoders = transcoderset
        self._balancer = TranscoderBalancer()
        self._workers.addListener(self)
        self._workers.syncListener(self)
        self._transcoders.addListener(self)
        self._transcoders.syncListener(self)
        

    ## Public Method ##
    

    ## Overrided Virtual Methods ##

    def _doStart(self):
        self.log("Ready to start transcoding, waiting to idle")
        d = self._transcoders.waitIdle(adminconsts.WAIT_IDLE_TIMEOUT)
        d.addBoth(self.__cbTranscoderSetGoesIdle)
        return d
    
    def _doResume(self):
        self.log("Ready to resume transcoding, waiting to idle")
        d = self._transcoders.waitIdle(adminconsts.WAIT_IDLE_TIMEOUT)
        d.addBoth(self.__cbTranscoderSetGoesIdle)
        return d
    
    def _doAbort(self):
        self.log("Aborting transcoding")
        self._balancer.clearTasks()

    def _onTaskAdded(self, task):
        if self._started:
            self._balancer.addTask(task)
            self._balancer.balance()
    
    def _onTaskRemoved(self, task):
        if self._started:
            self._balancer.removeTask(task)
            self._balancer.balance()

            
    ## IWorkerSetListener Overrided Methods ##
    
    def onWorkerAddedToSet(self, workerset, worker):
        self.log("Worker '%s' added to transcoding", worker.getLabel())
        self._balancer.addWorker(worker)
        self._balancer.balance()
    
    def onWorkerRemovedFromSet(self, workerset, worker):
        self.log("Worker '%s' removed from transcoding", worker.getLabel())
        self._balancer.removeWorker(worker)
        self._balancer.balance()


    ## ITranscoderSetListener Overrided Methods ##
    
    def onTranscoderAddedToSet(self, transcoderset, transcoder):
        self.log("Transcoder '%s' added to transcoding", transcoder.getLabel())
        d = self.addComponent(transcoder)
        d.addErrback(self.__ebAddComponentFailed, transcoder.getName())
    
    def onTranscoderRemovedFromSet(self, transcoderset, transcoder):
        self.log("Transcoder '%s' removed from transcoding", transcoder.getLabel())
        d = self.removeComponent(transcoder)
        d.addErrback(self.__ebRemoveComponentFailed, transcoder.getName())


    ## Overriden Methods ##
    
    def _doSyncListener(self, listener):
        for t in self._taks.itervalues():
            self._fireEventTo(t, listener, "TranscodingTaskAdded")


    ## Private Methods ##
    
    def __cbTranscoderSetGoesIdle(self, result):
        if (isinstance(result, Failure) 
            and not result.check(OperationTimedOutError)):
            self.warning("Failure during waiting transcoder set "
                         "to become idle: %s",
                         log.getFailureMessage(result))
            self.debug("%s", log.getFailureTraceback(result))
        self.log("Starting/Resuming transcoding")
        d = defer.Deferred()
        for task in self.iterTasks():
            d.addCallback(self.__cbRetrieveActiveWorker, task)
        d.addCallback(utils.dropResult, self._balancer.balance)
        d.addErrback(self.__ebStartingFailure)
        d.callback(defer._nothing)

    def __cbRetrieveActiveWorker(self, _, task):
        d = task.waitActiveWorker(adminconsts.TRANSCODER_ACTIVE_WORKER_TIMEOUT)
        # Call self._balancer.addTask(task, worker)
        d.addCallback(utils.shiftResult, self._balancer.addTask, 1, task)
        return d

    def __ebStartingFailure(self, failure):
        self.warning("Failure during transcoding starting/resuming: %s",
                     log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))

    def __ebAddComponentFailed(self, failure, name):
        self.warning("Failed to add transcoder '%s' "
                     "to transcoding manager: %s", 
                     name, log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
    
    def __ebRemoveComponentFailed(self, failure, name):
        self.warning("Failed to remove transcoder '%s' "
                     "from transcoding manager: %s",
                     name, log.getFailureMessage(failure))
        self.debug("%s", log.getFailureTraceback(failure))
