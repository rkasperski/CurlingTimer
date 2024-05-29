import math
import collections
import random
from PIL import ImageDraw

__brightColours = None


def brightColours():
    global __brightColours

    if __brightColours:
        return __brightColours

    __brightColours = []
    for a in [0, 60, 255]:
        for b in [0, 60, 255]:
            for c in [0, 60, 255]:
                clr = (a, b, c)
                if clr != [0, 0, 0] and clr != [255, 255, 255]:
                    __brightColours.append(clr)

    return __brightColours


class Kapow:
    def __init__(self, drawableImage):
        self.drawableImage = drawableImage
        self.height = drawableImage.height
        self.width = drawableImage.width
        self.drawable = ImageDraw.Draw(self.drawableImage)
        self.drawable.fontmode = "1"

    def clear(self, clr=(0, 0, 0)):
        self.drawable.rectangle((0, 0, self.width, self.height), fill=clr)

    def next(self):
        pass

    
class RotatingBlock(Kapow):
    def __init__(self, drawableImage):
        super().__init__(drawableImage)
        self.cent_x = int(self.width / 2)
        self.cent_y = int(self.height / 2)

        rotate_square = min(self.width, self.height) * 1.41
        self.min_rotate = self.cent_x - rotate_square / 2
        self.max_rotate = self.cent_x + rotate_square / 2

        display_square = min(self.width, self.height) * 0.7
        self.min_display = self.cent_x - display_square / 2
        self.max_display = self.cent_x + display_square / 2

        self.deg_to_rad = 2 * 3.14159265 / 360
        self.rotation = 0
        
    def rotate(self, x, y, angle):
        return (x * math.cos(angle) - y * math.sin(angle), x * math.sin(angle) + y * math.cos(angle))

    def scale_col(self, val, lo, hi):
        if val < lo:
            return 0
        if val > hi:
            return 255
        return round(255 * (val - lo) / (hi - lo))

    def next(self):
        self.rotation += 1
        self.rotation %= 360

        self.clear()
        for x in range(int(self.min_rotate), int(self.max_rotate)):
            for y in range(int(self.min_rotate), int(self.max_rotate)):
                rot_x, rot_y = self.rotate(x - self.cent_x, y - self.cent_x, self.deg_to_rad * self.rotation)

                if x >= self.min_display and x < self.max_display and y >= self.min_display and y < self.max_display:
                    clr = (self.scale_col(x, self.min_display, self.max_display),
                           255 - self.scale_col(y, self.min_display, self.max_display),
                           self.scale_col(y, self.min_display, self.max_display))
                    xy = (rot_x + self.cent_x, rot_y + self.cent_y)

                    self.drawable.point([math.floor(t) for t in xy], clr)
                    self.drawable.point([round(t) for t in xy], clr)
                    self.drawable.point([math.ceil(t) for t in xy], clr)

                    
class Rain(Kapow):
    def __init__(self, drawableImage):
        super().__init__(drawableImage)
        self.clear()
        self.brightColours = brightColours()

        self.sz = 2
        self.w = int(self.width / self.sz)
        self.h = int(self.height / self.sz)
                        
        self.rain = [[i, self.brightColours[random.randrange(len(self.brightColours))], self.h + 1] for i in range(self.w)]

    def point(self, xy, clr):
        for x in range(xy[0] * self.sz, xy[0] * self.sz + self.sz):
            for y in range(xy[1] * self.sz, xy[1] * self.sz + self.sz):
                self.drawable.point((x, y), clr)
                
    def next(self):
        if not any([r[2] for r in self.rain]):
            self.rain = [[i, self.brightColours[random.randrange(len(self.brightColours))], self.h + 1] for i in range(self.w)]
            self.clear()

        active = list(filter(lambda c: c[2] > 0, self.rain))
        col = active[random.randrange(0, len(active))][0]
        self.rain[col][2] -= 1

        for col in range(self.w):
            if self.rain[col][2] <= self.h:
                self.point((col, self.h - self.rain[col][2]), self.rain[col][1])
                
        return 0.005

    
class Life(Kapow):
    def __init__(self, drawableImage):
        super().__init__(drawableImage)

        self.torus = False
        self.sz = 3
        self.w = int(self.width / self.sz)
        self.h = int(self.height / self.sz)
        self.reset()

    def point(self, xy, clr):
        for x in range(xy[0] * self.sz, xy[0] * self.sz + self.sz - 1):
            for y in range(xy[1] * self.sz, xy[1] * self.sz + self.sz - 1):
                self.drawable.point((x, y), clr)

    def reset(self):
        self.clear()
        self.current = [[1 if random.randrange(5) == 0 else 0 for j in range(self.h)] for i in range(self.w)]
        self.old = [[0 for j in range(self.h)] for i in range(self.w)]
        self.generationHashes = collections.deque(maxlen=40)

    def numAliveNeighbours(self, values, x, y):
        num = 0
        width = self.w
        height = self.h
        
        if self.torus:
            # Edges are connected (torus)
            num += 1 if values[(x - 1 + width) % width][(y - 1 + height) % height] > 0 else 0
            num += 1 if values[(x - 1 + width) % width][y] > 0 else 0
            num += 1 if values[(x - 1 + width) % width][(y + 1) % height] > 0 else 0
            num += 1 if values[(x + 1) % width][(y - 1 + height) % height] > 0 else 0
            num += 1 if values[(x + 1) % width][y] > 0 else 0
            num += 1 if values[(x + 1) % width][(y + 1) % height] > 0 else 0
            num += 1 if values[x][(y - 1 + height) % height] > 0 else 0
            num += 1 if values[x][(y + 1) % height] > 0 else 0
        else:
            # Edges are not connected (no torus)
            if x > 0:
                if y > 0:
                    num += 1 if values[x - 1][y - 1] > 0 else 0
                    
                if y < height - 1:
                    num += 1 if values[x - 1][y + 1] > 0 else 0
                    
                num += 1 if values[x - 1][y] > 0 else 0
                
            if x < width - 1:
                if y > 0:
                    num += 1 if values[x + 1][y - 1] > 0 else 0
                    
                if y < height - 1:
                    num += 1 if values[x + 1][y + 1] > 0 else 0
                    
                num += 1 if values[x + 1][y] > 0 else 0
                
            if y > 0:
                num += 1 if values[x][y - 1] > 0 else 0
        
            if y < height - 1:
                num += 1 if values[x][y + 1] > 0 else 0
        
        return num
        
    def update(self):
        old = self.current
        current = self.old

        for x in range(self.w):
            for y in range(self.h):
                num = self.numAliveNeighbours(old, x, y)
                 
                if old[x][y] > 0:
                    if num >= 2 and num <= 3:
                        current[x][y] += 1
                    else:
                        current[x][y] = -1
                        
                elif num == 3:
                    current[x][y] = 1

                else:
                    current[x][y] = 0

        self.current = current
        self.old = old

    def hashGeneration(self, values):
        return "".join(["".join(["1" if values[x][y] > 0 else "0" for y in range(self.h)]) for x in range(self.w)])
        
    def next(self):
        self.update()
        values = self.current

        genHash = self.hashGeneration(values)

        if genHash in self.generationHashes:
            self.reset()
            values = self.current

        self.generationHashes.append(genHash)
        
        for x in range(self.w):
            for y in range(self.h):
                v = values[x][y]
                
                if v == 0:  # unused pixel
                    self.point((x, y), (0, 0, 0))
                elif v == 1:  # newly born
                    self.point((x, y), (0, 120, 0))
                elif v > 0:  # already living
                    b = min(200, int(200 * v / 20))
                    self.point((x, y), (b, 50 + b, 50 + b))
                else:  # newly dead
                    self.point((x, y), (80, 0, 0))

        return 2

    
class Symbols(Kapow):
    star_vertices = ((000, 300), (300, 300), (400, 000), (500, 300), (800, 300), (550, 500), (650, 800), (400, 600), (150, 800), (250, 500))
    
    def __init__(self, drawableImage, shape="star", direction="out"):
        super().__init__(drawableImage)
        self.brightColours = brightColours()
        self.displayed = collections.deque(maxlen=self.width)

        self.symbols = {"star": self.drawStar,
                        "square": self.drawRect,
                        "circle": self.drawEllipse}
        self.active = self.symbols.get(shape, self.drawStar)
        self.direction = self.inout if direction == "in" else self.outin

        self.clrN = 1000
        self.pixelLimit = None
        self.clear()

    def inout(self, lst):
        return lst[::-1]

    def outin(self, lst):
        return lst
    
    def drawStar(self, where, outline=None, width=0, fill=None):
        x0, y0, x1, y1 = where
        xw = x1 - x0
        yh = y1 - y0

        for i in range(max(width, 1)):
            pts = [(int(x / 800 * xw + 0.5) + x0, int(y / 800 * yh + 0.5) + y0) for x, y in self.star_vertices]
                
            self.drawable.polygon(pts, outline=outline)
            xw -= 2
            yh -= 2
            x0 += 1
            y0 += 1

        return 1.5

    def drawRect(self, where, outline=None, width=0, fill=None):
        self.drawable.rectangle(where, width=width, outline=outline)
        return 1.0
        
    def drawEllipse(self, where, outline=None, width=0, fill=None):
        self.drawable.ellipse(where, width=width, outline=outline)
        return 1.42

    def next(self):
        width = 1
        offset = 1
        self.displayed.appendleft(random.choice(self.brightColours))
            
        xm = self.width / 2
        ym = self.height / 2
        for c in self.direction(list(self.displayed)[0:min(self.clrN, len(self.displayed))]):
            mp = self.active((xm - offset, ym - offset, xm + offset, ym + offset), outline=c, width=width)

            if not self.pixelLimit:
                self.pixelLimit = int(max(xm * mp, ym * mp))
                    
            if offset >= self.pixelLimit:
                self.clrN = width
                break

            offset += width
            width += 1

        return 0.2

            
registered = {"block": RotatingBlock,
              "rain": Rain,
              "life": Life,
              "star": lambda x: Symbols(x, "star"),
              "square": lambda x: Symbols(x, "square"),
              "circle": lambda x: Symbols(x, "circle")}
