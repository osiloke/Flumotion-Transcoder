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

import os
import ConfigParser

from flumotion.transcoder import properties

DEFAULT_SECTION_SEP = ':'
DEFAULT_PROPERTY_SEP = '#'

class ConfigParserAdapter(properties.PropertySourceAdapter):
    
    def __init__(self, parser, rootSectionName,
                 secSep=DEFAULT_SECTION_SEP, 
                 propSep=DEFAULT_PROPERTY_SEP):
        self.rootSectionName = rootSectionName
        self.parser = parser        
        self.secSep = secSep
        self.propSep = propSep
    
    def _loc2sec(self, locator):
        section = self.secSep.join(locator)
        if section == '':
            return self.rootSectionName
        return section
    
    def _sec2loc(self, section):
        locator = tuple(section.split(self.secSep))
        if locator[0] == self.rootSectionName:
            return locator[1:]
        return locator
    
    def _des2opt(self, descriptor):
        return self.propSep.join(descriptor)

    def _opt2des(self, option):
        return tuple(option.split(self.propSep))
    
    def hasLocation(self, locator):
        section = self._loc2sec(locator)
        return self.parser.has_section(section)
    
    def listLocations(self):
        return [self._sec2loc(s) for s in self.parser.sections()]
    
    def addLocation(self, locator):
        section = self._loc2sec(locator)
        try:
            self.parser.add_section(section)
        except ConfigParser.DuplicateSectionError:
            raise properties.PropertyError("Location already exists", locator)
    
    def hasProperty(self, locator, descriptor):
        section = self._loc2sec(locator)
        option = self._des2opt(descriptor)
        return self.parser.has_option(section, option)
    
    def listProperties(self, locator):
        section = self._loc2sec(locator)
        return [self._opt2des(o) for o in self.parser.options(section)]
    
    def getProperty(self, locator, descriptor):
        section = self._loc2sec(locator)
        option = self._des2opt(descriptor)
        value = self.parser.get(section, option, True)
        if value.startswith("'") and value.endswith("'"):
            value = value[1:-1].decode('string_escape')
        return value
    
    def setProperty(self, locator, descriptor, value):
        section = self._loc2sec(locator)
        option = self._des2opt(descriptor)
        escaped = value.encode('string_escape')
        striped = value.strip()
        if (escaped != value) or (value != striped):
            value = "'%s'" % escaped
        self.parser.set(section, option, value)


class IniFile(object):

    def __init__(self, rootSectionName="global",
                 secSep=DEFAULT_SECTION_SEP, 
                 propSep=DEFAULT_PROPERTY_SEP):
        self.rootSectionName = rootSectionName
        self.secSep = secSep
        self.propSep = propSep

    def loadFromFile(self, propBag, filename):
        assert isinstance(filename, str)
        if not os.path.exists(filename):
            raise properties.PropertyError("File '%s' not found" 
                                           % filename)
        parser = ConfigParser.SafeConfigParser()        
        try:
            results = parser.read(filename)
            parser.remove_section("HEADER")
            adapter = ConfigParserAdapter(parser, self.rootSectionName,
                                          self.secSep, self.propSep)
            propBag.loadFromAdapter(adapter)
            return results
        except IOError, e:
            raise properties.PropertyError("Cannot read file '%s': %s" 
                               % (filename, str(e)), None, None, e)
        except properties.PropertyError, e:
            raise self._updateException(e, "While reading file '%s'" % filename)
    
    def saveToFile(self, propBag, path):
        
        def storeSection(file, parser, section):
            file.write("[%s]\n" % section)
            options = parser.options(section)
            options.sort()
            for o in options:
                file.write("%s = %s\n" % (o, parser.get(section, o, True)))
            file.write("\n")
        
        parser = ConfigParser.SafeConfigParser()
        try:
            adapter = ConfigParserAdapter(parser, self.rootSectionName,
                                          self.secSep, self.propSep)
            propBag.saveToAdapter(adapter)
            f = open(path, "wt")
            try:
                #The ConfigParser doesn't write the sections and properties ordered
                #so I have to do it myself for the file to be more readable
                #parser.write(f)
                #First store the comments if present as commented lines
                header = getattr(propBag, "COMMENTS", None)
                if header:
                    for line in header:
                        f.write("# %s\n" % line)
                    f.write("\n")
                #Next store the header fields if present
                version = getattr(propBag, "VERSION", None)
                if version:
                    f.write("[HEADER]\n")
                    f.write("version = %s\n\n" % '.'.join(map(str, version)))
                sections = parser.sections()
                # Make sure the global section is saved first
                if "global" in sections:
                    sections.remove("global")
                    storeSection(f, parser, "global")
                sections.sort()                    
                for s in sections:
                    storeSection(f, parser, s)
            finally:
                f.close()
        except IOError, e:
            raise properties.PropertyError("Cannot write file '%s': %s" 
                               % (path, str(e)), None, None, e)
        except properties.PropertyError, e:
            raise self._updateException(e, "While saving file '%s'" % path)

    def _updateException(self, e, msg):
        if e.locator != None:
            locator = e.locator
            if len(locator) == 0:
                locator = (self.rootSectionName,)
            msg += " for section '%s'" % self.secSep.join(locator)
        if e.descriptor != None:
            msg += " for property '%s'" % self.propSep.join(e.descriptor)
        msg += ": %s" % str(e)
        e.args = (msg,)
        return e