from collections import namedtuple
from auto_config_parser import ConfigSectionHandler

RGB = namedtuple("RGB", "red, green, blue")


def colour_parser(cs):
    sp = cs.split(",")
    if len(sp) != 3:
        sp = ["127", "127", "127"]
    return RGB(*[int(s) for s in sp])


def colour_formatter(c):
    return f"{c[0]},{c[1]},{c[2]}"


class ColoursConfigSection(dict, ConfigSectionHandler):
    section = "Colours"

    def __init__(self, config):
        dict.__init__(self)
        ConfigSectionHandler.__init__(self, config)

    def get_attribute_list(self):
        return list(self.keys())

    def get_definition(self, n):
        return (n, None, colour_parser, colour_formatter)

    def set(self, n, v):
        self[n] = v

    def add_colour(self, colour, rgbc):
        self[colour] = RGB(*rgbc)

    def add_colours(self, colours, clear=False):
        if clear:
            self.clear()

        for colour, rgb in colours:
            self.add_colour(colour, rgb)

        self.modified()

    def clear(self):
        dict.clear(self)
        ConfigSectionHandler.clear(self)

    def get_colours(self):
        return list(self.items())
