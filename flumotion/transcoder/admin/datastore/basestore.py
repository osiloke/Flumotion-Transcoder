# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.twisted.compat import implementsInterface
from flumotion.transcoder import log
from flumotion.transcoder.admin import adminelement
from flumotion.transcoder.admin.datasource import datasource


class BaseStore(adminelement.AdminElement):
    
    def __init__(self, logger, parent, dataSource, listenerInterface):
        assert implementsInterface(dataSource, datasource.IDataSource)
        adminelement.AdminElement.__init__(self, logger, parent, 
                                           listenerInterface)
        self._dataSource = dataSource


    ## Public Methods ##

    def getLabel(self):
        return ""


    ## Overriden Methods ##
    
    def _doPrepareInit(self, chain):
        def waitDatasource(result):
            d = self._dataSource.waitReady
            # Keep the result value
            d.addCallback(lambda r, v: v, result)
            return d
        chain.addCallback(waitDatasource)
        chain.addErrback(self.__dataSourceError)

    def _doPrepareActivation(self, chain):
        #FIXME: Remove this, its only for testing
        from twisted.internet import reactor, defer
        def async(result):
            d = defer.Deferred()
            reactor.callLater(0.2, d.callback, result)
            return d
        chain.addCallback(async)
            

    ## Private Methods ##

    def __dataSourceError(self, failure):
        #FIXME: Error Handling
        self.warning("Store data source error: %s",
                     log.getFailureMessage(failure))
        return failure
        
