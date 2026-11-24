"""
AutoConfigParser

This module read toml files and maps the toml names to python names tracking. When
a python variable is changed the top level config is marked as modified.

    A config section is represented by a list of attributes(typically in camel case) where each
    attribute is represemted by a tuple of the form
        (python name, default value, parser, formatter)

    If the either parser or formatter are missing it is assumed to be str.
"""
from collections.abc import Callable
from typing import Any
import os
import time
import tomlkit
from logger import info, debug, error

stupid_value = "this is 98721345980hgjvcxz*&^%^E$#JHG%gfdug876FTF&^"

class NoSectionError(Exception):
    """An explicit error for a missing section"""


class ConfigSectionHandler():
    """Reads and writes a single section of the toml file
    """
    variables:  set[str] = set()
    section: str = "unnamed"
    # attributes: dict[str,
    #                  tuple[str, Any, Callable[[Any], Any], Callable[[Any], Any]] |
    #                  tuple[str, Any]
    #                  ] = {}
    attributes = {}

    def __init__(self, config):
        self._config = config
        config._bind(self)

    def get_definition(self, n):
        """returns the definition for """
        # returns either a string default or a list (parser, formatter, default)
        # if None then it is an unknown attribute
        defn = self.attributes.get(n, None)

        if defn is None or len(defn) == 4:
            return defn

        if len(defn) == 1:
            return (defn[0], "", str , str)

        return defn + (str, str)

    def get_attribute_list(self):
        return self.attributes.keys()

    def modified(self):
        self._config.modified = True

    def clear(self):
        self._config.modified = True

    def to_config(self, config):
        if self.section not in config.toml:
            config.add_section(self.section)

        section_items = set(self.get_attribute_list())
        config_items = set(config.toml[self.section].keys())
        for n in section_items:
            config_items.discard(n)

            v = self.get(n)
            self.to_set(config, n, v)
            debug("to_config: %s %s %s", self.section, n, v)

        # get rid of values not in the section
        for n in config_items:
            config.toml[self.section].remove(n)

    def to_set(self, config, n, v):
        _, _, _, formatter = self.get_definition(n)
        config.toml[self.section][n] = formatter(v)

    def update(self, update_pairs):
        for n, v in update_pairs:
            member_name, default_value, parser, _ = self.get_definition(n)

            parsed_v = parser(v)
            debug("%s %s:%s = %s; %s", self.section, n, member_name, parsed_v, default_value)
            self.set(n, parsed_v if parsed_v is not None else default_value)

    def __setattr__(self, n, v):
        if n != "_config" and n not in self.variables:
            self._config.modified = True

        super().__setattr__(n, v)

    def from_config(self, config):
        if self.section not in config.toml:
            config.toml.add(self.section, tomlkit.table())

        config_items = set(config.toml[self.section].keys())
        section_items = set(self.get_attribute_list())

        for n in set.union(config_items, section_items):
            member_name, default_value, parser, _ = self.get_definition(n)

            try:
                value = parser(config.toml[self.section].get(n, default_value))
                self.set(n, value)
                debug("%s %s:%s = %s; %s", self.section, n, member_name, value, default_value)
            except TypeError:
                error("from_config: section=%s member_name=%s default_value=%s parser=%s",
                      self.section, member_name, default_value, parser)
                raise

    def set(self, n, v):
        member_name, _, _, _ = self.get_definition(n)
        debug("set: %s %s:%s %s", self.section, n, member_name, v)
        setattr(self, member_name, v)

    def get(self, n, _default=stupid_value):
        member_name, _, _, _ = self.get_definition(n)
        v = getattr(self, member_name)
        debug("get: %s %s:%s %s", self.section, n, member_name, v)
        return v

    def items(self):
        r = {}

        for n in self.get_attribute_list():
            r[n] = self.get(n)

        return r

    def __str__(self):
        return str({n: getattr(self, n) for n in self.get_attribute_list()})


class AutoConfigParser():
    def __init__(self, filename="config.toml", sections=None):
        self.filename = os.path.abspath(filename)
        debug("config: Reading file: %s", self.filename)
        self.toml = None
        self.read(filename)
        self.__modified = False
        self.seq_no = 0
        self.quiet = True
        self.sections = set()

        if sections is not None:
            for s in sections:
                if s not in self.toml:
                    self.add_section(s)
                    self.__modified = True

        if "Config" not in self.toml:
            self.add_section("Config", {"sequenceNumber": 0})
        else:
            try:
                self.seq_no = int(self.toml["Config"].get("sequenceNumber", None))
            except (ValueError, KeyError, TypeError):
                self.set("Config", "sequenceNumber", "0")

        self.interface_handlers = []

    def _bind(self, interface_handler):
        interface_handler.config = self
        self.interface_handlers.append(interface_handler)
        interface_handler.from_config(self)

    def add_section(self, section, values=None):
        if values is None:
            values = {}

        config_table = tomlkit.table()
        config_table.update(values)
        self.toml.add(section, config_table)
        self.sections.add(section)
        self.__modified = True

    def read(self, file_name):
        with open(file_name, "r", encoding="utf-8") as fp:
            self.toml = tomlkit.load(fp)
            self.__modified = False

    def to_interface_readers(self):
        for ih in self.interface_handlers:
            ih.from_config(self)

    def from_interface_readers(self):
        for ih in self.interface_handlers:
            ih.to_config(self)

    def version(self):
        return int(self.toml["Config"].get("sequenceNumber", 0))

    def modification_date(self):
        return self.toml["Config"].get("modificationTime", None)

    def set(self, section, option, value):
        if section not in self.toml:
            self.add_section(section, {option: value})
        else:
            self.toml[section][option] = value

        self.__modified = True

    def remove_option(self, section, option):
        if section in self.toml:
            if option in self.toml[section]:
                self.toml[section].remove(option)
                self.__modified = True
                return True

        return False

    def remove_section(self, section, modified=True):
        res = False
        if section in self.toml:
            self.toml.remove(section)
            res = True

        self.__modified |= (modified & res)
        return res

    # """Can get options() without defaults
    # """
    # def options(self, section, no_defaults=False, **kwargs):
    #     if no_defaults:
    #         try:
    #             return list(self.sections[section].keys())
    #         except KeyError:
    #             raise NoSectionError(section)
    #     else:
    #         return super().options(section, **kwargs)

    # def check(self, section, item, default=None):
    #     try:
    #         return self.sections[section][item]
    #     except KeyError:
    #         if default is not None:
    #             return default

    #         raise

    def save(self, save_time=None, force=False, increment_sequence_no=True):
        if not (self.__modified or force):
            return True

        self.from_interface_readers()
        if "Config" not in self.toml:
            self.add_section("Config", {"sequenceNumber": 0,
                                        "modificationTime": ""})

        seq_no = int(self.toml["Config"].get("sequenceNumber", 0))
        if increment_sequence_no:
            seq_no += 1

        self.toml["Config"]["sequenceNumber"] = str(seq_no)
        self.toml["Config"]["modificationTime"] = time.ctime(save_time)

        toml_str = tomlkit.dumps(self.toml)
        create_name = self.filename + ".new"
        info("save config %s as Effective User ID: %s", create_name, os.geteuid())
        with open(create_name, 'w', encoding="utf-8") as configfile:
            self.__modified = False
            configfile.write(toml_str)

            os.rename(self.filename, self.filename + ".old")
            os.rename(create_name, self.filename)

            info("config: saved; renamed %s version=%s do_increment=%s", self.filename, seq_no, increment_sequence_no)
        return True

    def to_string(self, save_time=None):
        self.save(save_time)
        with open(self.filename, 'r', encoding="utf-8") as myfile:
            data = myfile.read()

        return data

    def from_string(self, s):
        create_filename = self.filename + ".new"
        with open(create_filename, 'w', encoding="utf-8") as myfile:
            myfile.write(s)

        info("config: saved from string %s", create_filename)
        self.read(create_filename)
        self.to_interface_readers()
        self.__modified = False

        os.rename(self.filename, self.filename + ".old")
        os.rename(create_filename, self.filename)
        info("config: saved from string; renamed %s", self.filename)


    @property
    def modified(self):
        return self.__modified

    @modified.setter
    def modified(self, v):
        if v and not self.quiet and not self.__modified:
            info("mark config as modified")

        self.__modified = v
