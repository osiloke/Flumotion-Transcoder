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

import sys
import gobject
import gst

class PipelineVisitor(object):
    def startBranch(self, branch, node, element):
        pass
    def suspendBranch(self, branch, element):
        pass
    def joinBranches(self, branches, node, branch):
        pass
    def enterElement(self, branch, previous, element, next):
        return True

class PipelineCrawler(PipelineVisitor):
    """
    Crawls the pipeline assuming that the elements form a DAG.
    It guarentee than each added element's sources 
    has been previously added.
    """
    
    def __init__(self, visitor=None):
        self._visitor = visitor or self
        self._crawled = {}
        self._pending = {}
        
    def clean(self):
        self._crawled.clear()
        self._pending.clear()
        
    def crawlPipeline(self, pipeline):
        sources = list(pipeline.iterate_sources())
        for index, source in enumerate(sources):
            self._visitor.startBranch((index,), None, source)
            self._enterElement(source, (index,))
    
    def crawlBin(self, bin):
        index = 0
        for pad in bin.sink_pads():
            element = self._padElement(pad, gst.PAD_SRC)
            self._visitor.startBranch((index,), None, element)
            self._enterElement(element, (index,), True)
            index += 1
        
    def crawlElement(self, element):
        self._enterElement(element, (0,), True)

    def _sourcesOf(self, element):
        pads = [p for p in element.pads() 
                if p.is_linked() and (p.get_direction() == gst.PAD_SINK)]
        elements = [self._padElement(p, gst.PAD_SINK) for p in pads]
        #Reduce None elements in case of GStreamer internal changes
        return [e for e in elements if e != None]
    
    def _sinksOf(self, element):
        pads = [p for p in element.pads() 
                if p.is_linked() and (p.get_direction() == gst.PAD_SRC)]
        elements = [self._padElement(p, gst.PAD_SRC) for p in pads]
        #Reduce None elements in case of GStreamer internal changes
        return [e for e in elements if e != None]
        
    def _padElement(self, pad, direction):
        if isinstance(pad, gst.GhostPad):
            return self._padElement(pad.get_target(), direction)
        if pad.get_direction() == direction:
            return self._padElement(pad.get_peer(), direction)
        parent = pad.get_parent()
        if isinstance(parent, gst.GhostPad):
            return self._padElement(parent.get_peer(), direction)
        if parent == None:
            gst.warning("GStreamer internal behavior changed, "
                        + "cannot properly crawl the pipline")
        return parent

    def _enterElement(self, element, branch, force=False):
        name = element.get_name()
        previous = self._sourcesOf(element)
        #Suspend the crawling if all source has not been crawled before
        if not force:
            for e in previous:
                if not (e.get_name() in self._crawled):
                    if not (name in self._pending):
                        branches = list()
                        self._pending[name] = branches
                    else:
                        branches = self._pending[name]
                    branches.append(branch)
                    self._visitor.suspendBranch(branch, element)
                    return [element]
        self._crawled[name] = None
        #If the element has previously been suspended, join the branches
        if name in self._pending:
            branches = self._pending[name]
            branches.append(branch)
            #The new branch will be the common prefix of the pending branches
            prefix = []
            for v in zip(*branches):
                #if all element of v are equals...
                if v == (v[0],)*len(v):
                    prefix.append(v[0])
            branch = prefix
            self._visitor.joinBranches(branches, element, branch)
        next = self._sinksOf(element)
        if self._visitor.enterElement(branch, previous, element, next):
            count = len(next)
            if count > 1:
                pendings = []
                for index, e in enumerate(next):
                    newBranch = branch + (index,)
                    self._visitor.startBranch(newBranch, element, e)
                    result = self._enterElement(e, newBranch)
                    pendings.extend(result)
                return pendings
            if count > 0:
                return self._enterElement(next[0], branch)
        return []

class PrintVisitor(PipelineVisitor):
    def __init__(self, file=sys.stdout):
        self._out = file
    
    def _write(self, *args):
        for a in args:
            self._out.write(a)
        self._out.write("\n")
        
    def _getFactoryName(self, element):
        factory = element.get_factory()
        if factory:
            return factory.get_name()
        return element.__class__.__name__
    
    def startBranch(self, branch, node, element):
        if len(branch) > 1:
            self._write("|   " * (len(branch) - 2) + "+---+")
        else:
            self._write("+")

    def joinBranches(self, branches, node, branch):
        self._write("|   " * (len(branch) - 1) + "><")

    def suspendBranch(self, branch, element):
        self._write("|   " * (len(branch) - 1) + "...")

    def enterElement(self, branch, previous, element, next):
        prefix = "|   " * (len(branch) - 1)
        if len(next) > 0:
            prefix += "|"
        else:
            prefix += "\\"
        properties = ""
        for p in gobject.list_properties(element):
            defVal = p.default_value
            currVal = element.get_property(p.name)
            if currVal != defVal:
                #For enums
                if hasattr(currVal, "value_name"):
                    currVal = currVal.value_name
                properties += " %s=%s" % (p.name, currVal)
        self._write(prefix, self._getFactoryName(element), properties)
        return True

def crawlPipeline(pipeline, visitor):
    crawler = PipelineCrawler(visitor)
    crawler.crawlPipeline(pipeline)

def printPipeline(pipeline, file=sys.stdout):
    visitor = PrintVisitor(file)
    crawler = PipelineCrawler(visitor)
    crawler.crawlPipline(pipeline)
