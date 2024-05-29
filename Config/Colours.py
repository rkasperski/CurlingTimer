from collections import namedtuple
from AutoConfigParser import ConfigSectionHandler

rgb = namedtuple("rgb", "red, green, blue")


def colourParser(cs):
    sp = cs.split(",")
    if len(sp) != 3:
        sp = ["127", "127", "127"]
    return rgb(*[int(s) for s in sp])


def colourFormatter(c):
    return "%s,%s,%s" % c
    

class ColoursConfigSection(dict, ConfigSectionHandler):
    section = "Colours"
    
    def __init__(self, config):
        dict.__init__(self)
        ConfigSectionHandler.__init__(self, config)

    def clear(self):
        dict.clear(self)
        ConfigSectionHandler.clear(self)

    def addColour(self, colour, rgbc):
        self[colour] = rgb(*rgbc)

    def addColours(self, colours, clear=False):
        if clear:
            self.clear()
            
        for colour, rgb in colours:
            self.addColour(colour, rgb)

        self.modified()

    def getAttributeList(self):
        return list(self.keys())

    def getDefinition(self, n):
        return (colourParser, colourFormatter, None)

    def set(self, n, v):
        self[n] = v

    def get(self, n):
        return self[n]

    def getColours(self):
        return list(self.items())
