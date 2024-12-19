RegisteredFonts = {}

class BaseFont:
    def __init__(self, name, font, id, size, ascender, descender, height):
        global RegisteredFonts

        self.name = name
        self.font = font
        self.id = id
        self.size = size
        self.ascender = ascender
        self.descender = descender
        self.height = height

        RegisteredFonts[name] = self

    def getSize(self, text):
        pass

class FancyTextSegment:
    def __init__(self, text, font, colour, vertical=None):
        """vertical can be one of None, middle, baseline"""
        self.text = text
        self.font = font
        self.colour = colour
        self.signature = f"\\f{font.id}\\c{str(colour)}\\r{text}"
        if vertical == "middle":
            self.signature = "\\vm" + self.signature

        # ok, this is a bit of a hack, break text into short segments so that writing to screen
        # can do the equivalent of clipping.
        self.charWidths = [self.font.getSize(c)[0] for c in self.text]
            
        self.size = self.font.getSize(self.text)

        self.ascender = font.ascender
        self.vertical = vertical
        self.height = font.height

    def draw(self, drawable, pos, height, ascender, displayWidth=64):
        if self.vertical == "middle":
            #top = pos[1] - ascender
            top = pos[1] - height
            pos = [pos[0], top + height / 2]

        x, y = pos
        for c, w in zip(self.text, self.charWidths):
            if x >= displayWidth:
                break

            if x + w >= 0:
                drawable.drawText(self.font, x, y, c, self.colour)

            x += w
        
        return self.size

    
class FancyText:
    def __init__(self, displayWidth, *args):
        self.displayWidth = displayWidth
        self.segments = args
        self.largestAscender = max([s.ascender for s in self.segments])
        self.height = max([s.height for s in self.segments])

    def getSize(self):
        w = 0
        h = 0
        for s in self.segments:
            ws, hs = s.size
            w += ws
            h = max(h, max(hs, s.height))

        return (w, h)

    def draw(self, drawable, pos):
        x, y = pos
        for s in self.segments:
            ws, hs = s.draw(drawable, (x, y + self.largestAscender), self.height, self.largestAscender, displayWidth=self.displayWidth)

            x += ws

    def signature(self):
        t = ""
        for s in self.segments:
            t += s.signature

        return t

