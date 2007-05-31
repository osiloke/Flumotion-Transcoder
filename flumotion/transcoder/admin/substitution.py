# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

from flumotion.transcoder.admin import utils


class Variables(object):
    
    def __init__(self, *otherVars):
        self._variables = {}
        for s in reversed(otherVars):
            if s:
                self._variables.update(s._variables)

    def substitute(self, value):
        #FIXME: Better error handling
        return value % self._variables
            
    def __iter__(self):
        return iter(self._variables)
            
    def __getitem__(self, name):
        return self._variables[name]
        
    def __contains__(self, name):
        return name in self._variables
        
    def addVar(self, name, value):
        self._variables[name] = value
        
    def addFileVars(self, filePath, kind):
        """
        Add the diffrent parts of the file to the substitution set
        like following:
        
        Parameters:
            filePath: /my.sub/folder/file.name.ext 
            kind: "input"
        
        Added vars:
            "inputPath" (str): "/my.sub/folder/file.name.ext",
            "inputFile" (str): "file.name.ext",
            "inputBasename" (str): "file.name",
            "inputExtension" (str): ".ext",
            "inputDir" (str): "/my.sub/folder/"
        """
        path, file, ext = utils.splitPath(filePath)
        self._variables[kind + "Path"] = filePath
        self._variables[kind + "File"] = file + ext
        self._variables[kind + "Basename"] = file
        self._variables[kind + "Extension"] = ext
        self._variables[kind + "Dir"] = path

