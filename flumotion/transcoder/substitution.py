# Flumotion - a streaming media server
# vi:si:et:sw=4:sts=4:ts=4
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import urllib

from flumotion.inhouse import utils, fileutils


def escape_url_value(value):
    return (isinstance(value, (str, unicode)) and urllib.quote(value)) or value


class Variables(object):
    
    def __init__(self, *otherVars):
        self._variables = {}
        for s in reversed(otherVars):
            if s:
                self._variables.update(s._variables)

    def substitute(self, value, escape=None):
        #FIXME: Better error handling
        format = utils.filterFormat(value, self._variables)
        if escape is None:
            return format % self._variables
        vars = dict([(k, escape(v)) for k, v in self._variables.iteritems()])
        return format % vars
    
    def substituteURL(self, value):
        return self.substitute(value, escape=escape_url_value)
            
    def __iter__(self):
        return iter(self._variables)
            
    def __getitem__(self, name):
        return self._variables[name]
    
    def __setitem__(self, name, value):
        if not name in self._variables:
            raise KeyError(name)
        self._variables[name] = value
        
    def __contains__(self, name):
        return name in self._variables
        
    def addVar(self, name, value):
        self._variables[name] = value
        
    def addFileVars(self, filePath, kind, extension=None):
        """
        Add the diffrent parts of the file to the substitution set
        like following:
        The extension can be specified explicitly
        to support multi-dot extensions. In this case the extension
        is not extracted from the file path.
        
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
        path, file, ext = fileutils.splitPath(filePath, extension == None)
        if extension: 
            ext = extension
            self._variables[kind + "Path"] = filePath + extension
        else:
            self._variables[kind + "Path"] = filePath
        self._variables[kind + "File"] = file + ext
        self._variables[kind + "Extension"] = ext
        self._variables[kind + "Basename"] = file        
        self._variables[kind + "Dir"] = path
