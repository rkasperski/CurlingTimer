from Logger import info, debug
import tomlkit
import os
import time

stupidValue = "this is 98721345980hgjvcxz*&^%^E$#JHG%gfdug876FTF&^"

# a config file entry definition are defined by a three tuple
# 1. parser: this accepts a string and return the parsed item.
# 2. formatter: this accepts the item and returns the string representation
# 3. if the item isn't in the file the default value
#    - a default value of None means that the item won't be written to the
#      config file if the item has a value of None.
# if a config entry is a string then (str, str, value) is assumed for the three tuple


class NoSectionError(Exception):
    pass


class ConfigSectionHandler():
    variables = set()
    section = "unnamed"
    attributes = {}
    
    def __init__(self, config):
        self._config = config
        config._bind(self)

    def getDefinition(self, n):
        # returns either a string default or a list (parser, formatter, default)
        # if None then it is an unknown attribute
        return self.attributes.get(n, None)

    def getAttributeList(self):
        return self.attributes.keys()

    def modified(self):
        self._config._modified = True

    def clear(self):
        self._config._modified = True

    def toConfig(self, config):
        if self.section not in config.toml:
            config.addSection(self.section)

        sectionItems = set(self.getAttributeList())
        configItems = set(config.toml[self.section].keys())
        for n in sectionItems:
            configItems.discard(n)
            
            defn = self.getDefinition(n)
            if defn is None:
                continue
            
            defn = (str, str, defn) if isinstance(defn, str) else defn
            
            value = self.get(n)
            if value is not None:
                self.toSet(config, n, defn[1](value))

        # get rid of values not in the section
        for n in configItems:
            config.toml[self.section].remove(n)

    def toSet(self, config, n, v):
        config.toml[self.section][n] = str(v)

    def __setattr__(self, v, n):
        if v != "_config" and v not in self.variables:
            self._config._modified = True

        super().__setattr__(v, n)
        
    def fromConfig(self, config):
        if self.section not in config.toml:
            config.toml.add(self.section, tomlkit.table())

        configItems = set(config.toml[self.section].keys())
        sectionItems = set(self.getAttributeList())

        for n in set.union(configItems, sectionItems):
            defn = self.getDefinition(n)
            if defn is None:
                continue
            
            defn = (str, str, defn) if isinstance(defn, str) else defn
            value = config.toml[self.section][n] if n in config.toml[self.section] else defn[2]
            
            self.set(n, value if value is None else defn[0](value))
            
    def set(self, n, v):
        self._config._modified = True
        setattr(self, n, v)

    def get(self, n, default=stupidValue):
        return getattr(self, n)

    def items(self):
        r = {}

        for n in self.getAttributeList():
            r[n] = self.get(n)

        return r
    
    def __str__(self):
        return str({n: getattr(self, n) for n in self.getAttributeList()})

    
class AutoConfigParser():
    def __init__(self, *args, filename="config.toml", sections=None, autosave=True, **kwargs):
        self.filename = os.path.abspath(filename)
        debug("config: Reading file: %s", self.filename)
        self.toml = None
        self.read(filename)
        self._modified = False
        self.seqNo = 0
        
        if sections is not None:
            for s in sections:
                if s not in self.toml:
                    self.addSection(s)
                    self._modified = True

        if "Config" not in self.toml:
            self.addSection("Config", {"sequenceNumber": 0})
        else:
            try:
                self.seqNo = int(self.toml["Config"].get("sequenceNumber", None))
            except (ValueError, KeyError, TypeError):
                self.set("Config", "sequenceNumber", "0")

        self.interfaceHandlers = []

    def _bind(self, interfaceHandler):
        interfaceHandler.config = self
        self.interfaceHandlers.append(interfaceHandler)
        interfaceHandler.fromConfig(self)

    def addSection(self, section, values={}):
        configTable = tomlkit.table()
        configTable.update(values)
        self.toml.add(section, configTable)
        self._modified = True
    
    def read(self, fileName):
        with open(fileName) as fp:
            self.toml = tomlkit.load(fp)
            self.__modified = False
         
    def toInterfaceReaders(self):
        for ih in self.interfaceHandlers:
            ih.fromConfig(self)
            
    def fromInterfaceReaders(self):
        for ih in self.interfaceHandlers:
            ih.toConfig(self)

    def version(self):
        return int(self.toml["Config"].get("sequenceNumber", 0))

    def modificationDate(self):
        return self.toml["Config"].get("modificationTime", None)

    def set(self, section, option, value):
        if section not in self.toml:
            self.addSection(section, {option: value})
        else:
            self.toml[section][option] = value
            
        self._modified = True

    def remove_option(self, section, option):
        if section in self.toml:
            if option in self.toml[section]:
                self.toml[section].remove(option)
                self._modified = True
                return True

        return False

    def remove_section(self, section, modified=True):
        res = False
        if section in self.toml:
            self.toml.remove(section)
            res = True
            
        self._modified |= (modified & res)
        return res

    """Can get options() without defaults
    """
    def options(self, section, no_defaults=False, **kwargs):
        if no_defaults:
            try:
                return list(self._sections[section].keys())
            except KeyError:
                raise NoSectionError(section)
        else:
            return super().options(section, **kwargs)

    def check(self, section, item, default=None):
        try:
            return self.sections[section][item]
        except KeyError:
            if default is not None:
                return default

            raise

    def save(self, saveTime=None, force=False):
        if not self._modified:
            return True
        
        self.fromInterfaceReaders()
        if "Config" not in self.toml:
            self.toml.addSection("Config", {"sequenceNumber": 0,
                                            "modificationTime": ""})
                
        if self._modified:
            seqNo = int(self.toml["Config"].get("sequenceNumber", 0))
            self.toml["Config"]["sequenceNumber"] = str(seqNo + 1)
            self.toml["Config"]["modificationTime"] = time.ctime(saveTime)

            tomlStr = tomlkit.dumps(self.toml)
            createName = self.filename + ".new"
            with open(createName, 'w') as configfile:
                self._modified = False
                configfile.write(tomlStr)
                os.rename(self.filename, self.filename + ".old")
                os.rename(createName, self.filename)

            debug("config: saved %s", self.filename);
            return True

        return False

    def toString(self, saveTime=None):
        self.save(saveTime)
        with open(self.filename, 'r') as myfile:
            data = myfile.read()

        return data

    def fromString(self, s):
        with open(self.filename, 'w') as myfile:
            myfile.write(s)

        self.read(self.filename)
        self.toInterfaceReaders()
        self._modified = False

    @property
    def modified(self):
        return self._modified

    @modified.setter
    def modified(self, v):
        self._modified = v
        
