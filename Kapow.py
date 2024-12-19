import math
import collections
import random

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
                if sum(clr) >= 60:
                    __brightColours.append(clr)

    return __brightColours


class Kapow:
    def __init__(self, drawable):
        self.width, self.height = drawable.visible_pixels
        self.vpd = drawable.visible_pixel_dimension
        self.displayWidth = drawable.width
        self.displayHeight = drawable.height
        self.drawable = drawable

    def start(self):
        self.drawable.start()

    def clear(self, clr=(0, 0, 0)):
        self.drawable.drawRect(0, 0, self.displayWidth, self.displayHeight, fillColour=clr)

    def show(self):
        self.drawable.show()

    async def next(self):
        self.start()
        wait = self.frame()
        self.show()

        return wait

    def frame(self):
        pass

    
class RotatingBlock(Kapow):
    def __init__(self, drawable):
        super().__init__(drawable)
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

    def frame(self):
        self.rotation += 1
        self.rotation %= 360

        vpd = self.vpd

        self.clear()

        for x in range(int(self.min_rotate), int(self.max_rotate)):
            for y in range(int(self.min_rotate), int(self.max_rotate)):
                rot_x, rot_y = self.rotate(x - self.cent_x, y - self.cent_x, self.deg_to_rad * self.rotation)

                if x >= self.min_display and x < self.max_display and y >= self.min_display and y < self.max_display:
                    clr = (self.scale_col(x, self.min_display, self.max_display),
                           255 - self.scale_col(y, self.min_display, self.max_display),
                           self.scale_col(y, self.min_display, self.max_display))
                    xy = (rot_x + self.cent_x, rot_y + self.cent_y)

                    self.drawable.drawPoint(vpd * math.floor(xy[0]), vpd * math.floor(xy[1]), clr)
                    self.drawable.drawPoint(vpd * round(xy[0]), vpd * round(xy[1]), clr)
                    self.drawable.drawPoint(vpd * math.ceil(xy[0]), vpd * math.ceil(xy[1]), clr)

                    
class Rain(Kapow):
    def __init__(self, drawable):
        super().__init__(drawable)
        self.brightColours = brightColours()

        self.rain = None

    def frame(self):
        if self.rain is None or not any([r[2] for r in self.rain]):
            self.rain = [[i, self.brightColours[random.randrange(len(self.brightColours))], self.height + 1] for i in range(self.width)]
            self.clear()

        active = list(filter(lambda c: c[2] > 0, self.rain))
        col = active[random.randrange(0, len(active))][0]
        self.rain[col][2] -= 1

        vpd = self.vpd
        for col in range(self.width):
            if self.rain[col][2] <= self.height:
                self.drawable.drawPoint(col * vpd , (self.height - self.rain[col][2]) * vpd, self.rain[col][1])
                
        return 0.005

    
class Life(Kapow):
    def __init__(self, drawable):
        super().__init__(drawable)

        self.torus = False
        self.current = None

        self.current = None
        self.old = None
        self.generationHashes = collections.deque(maxlen=40)

    def reset(self):
        self.clear()
        self.current = [[1 if random.randrange(5) == 0 else 0 for j in range(self.height)] for i in range(self.width)]
        self.old = [[0 for j in range(self.height)] for i in range(self.width)]
        self.generationHashes = collections.deque(maxlen=40)

    def numAliveNeighbours(self, values, x, y):
        num = 0
        width = self.width
        height = self.height

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
        if self.current is None:
            self.reset()
            return

        old = self.current
        current = self.old

        for x in range(self.width):
            for y in range(self.height):
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
        return "".join(["".join(["1" if values[x][y] > 0 else "0" for y in range(self.height)]) for x in range(self.width)])
        
    def frame(self):
        self.update()
        values = self.current

        genHash = self.hashGeneration(values)

        if genHash in self.generationHashes:
            self.reset()
            values = self.current

        self.generationHashes.append(genHash)

        vpd = self.vpd
        
        for x in range(self.width):
            for y in range(self.height):
                v = values[x][y]
                
                if v == 0:  # unused pixel
                    self.drawable.drawPoint(x * vpd, y * vpd, (0, 0, 0))
                elif v == 1:  # newly born
                    self.drawable.drawPoint(x * vpd, y * vpd, (0, 180, 0))
                elif v > 0:  # already living
                    b = min(255, int(v * 10) + 140)
                    self.drawable.drawPoint(x * vpd, y * vpd, (b, b, b))
                else:  # newly dead
                    self.drawable.drawPoint(x * vpd, y * vpd, (80, 0, 0))

        return 2

    
class Symbols(Kapow):
    star_vertices = [(-1.0, -0.25), (-0.25, -0.25), (0.0, -1.0), (0.25, -0.25), (1.0, -0.25), (0.375, 0.25), (0.625, 1.0), (0.0, 0.5), (-0.625, 1.0), (-0.375, 0.25)]
    # star_vertices = ((000, 300), (300, 300), (400, 000), (500, 300), (800, 300), (550, 500), (650, 800), (400, 600), (150, 800), (250, 500))

    def __init__(self, drawable, shape="star"):
        super().__init__(drawable)
        self.brightColours = brightColours()
        self.displayed = collections.deque(maxlen=self.width)

        self.symbols = {"star": self.drawStar,
                        "square": self.drawRect,
                        "circle": self.drawEllipse}
        self.active = self.symbols.get(shape, self.drawStar)
        self.reset = True
        self.index = 0

    def drawStar(self, x, y, width, colour):
        vpd = self.vpd
        vpda = self.vpd * 1.2

        width2 = width + width
        pts = [(int(sx * width2 * vpda + x * vpd), int(sy * width2 * vpda + y * vpd)) for sx, sy in self.star_vertices]

        self.drawable.drawPolygon(pts, borderWidth=vpd, borderColour=colour)

        return width2 >= min(self.width, self.height)

    def drawRect(self, x, y, width, colour):
        vpd = self.vpd
        self.drawable.drawRect((x - width) * vpd,
                               (y - width) * vpd,
                               width * 2 * vpd,
                               width * 2 * vpd,
                               borderWidth=vpd, borderColour=colour)
        return 2 * width > min(self.width, self.height)

    def drawEllipse(self, x, y, width, colour):
        vpd = self.vpd
        self.drawable.drawCircle(x * vpd,
                                 y * vpd,
                                 width * vpd,
                                 borderWidth=vpd, borderColour=colour)
        return 2 * width > min(self.width, self.height)

    def frame(self):
        if self.reset:
            self.clear()
            self.index = 1

        colour = random.choice(self.brightColours)
            
        xm = self.width / 2
        ym = self.height / 2

        self.reset = self.active(xm, ym, self.index, colour)
        self.index += 1

        return 0.2

            
registered = {"block": RotatingBlock,
              "rain": Rain,
              "life": Life,
              "star": lambda x: Symbols(x, "star"),
              "square": lambda x: Symbols(x, "square"),
              "circle": lambda x: Symbols(x, "circle")}
