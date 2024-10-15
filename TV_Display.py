from Logger import error, warning, info, debug
import asyncio
import traceback
import os
import time
import re
import sys
from collections import namedtuple

from PySide6 import QtCore, QtGui, QtWidgets

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtAsyncio.events import QAsyncioEventLoopPolicy
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor
import PySide6.QtAsyncio as QtAsyncio
import qasync


import argparse
import Hardware

from AutoConfigParser import AutoConfigParser

def excepthook(type_, value, traceback_):
    traceback.print_exception(type_, value, traceback_)
    QtCore.qFatal('')

sys.excepthook = excepthook

sections = ["Hardware"]

app = qasync.QApplication(sys.argv)

event_loop = qasync.QEventLoop(app)
asyncio.set_event_loop(event_loop)

screen = app.primaryScreen()
size = screen.size()
screenWidth = size.width()
screenHeight = size.height()

print(f"{screenWidth=} {screenHeight=}")

display = None

Font = namedtuple("Font", "name font id size ascender descender height fontMetrics")

requiredColours = (("red", (255, 0, 0)),
                   ("cyan", (0, 255, 255)),
                   ("yellow", (255, 255, 0)),
                   ("white", (255, 255, 255)),
                   ("black", (0, 0, 0)),
                   ("green", (0, 255, 0)),
                   ("pink", (255, 153, 153)),
                   ("orange", (255, 95, 31)),
                   ("blue", (120, 120, 255)),
                   ("purple", (255, 0, 255)),
                   )

def inferTextMetrics(fontMetrics):
    #ss = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRTSUVWXYZ"

    #bbox = f.getbbox(ss, anchor='ls')
    ascender = fontMetrics.ascent()
    descender = fontMetrics.descent()
    return (ascender, descender)


def getsize(f, s):
    #bbox = f.font.getbbox(s, anchor='ls')
    bbox = f.fontMetrics.boundingRect(QRect(0,0,6000,3000), Qt.AlignTop, s)
    return (bbox.width(), bbox.height())


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
        self.charWidths = [getsize(self.font, c)[0] for c in self.text]
            
        self.size = getsize(self.font, self.text)

        self.ascender = font.ascender
        self.vertical = vertical
        self.height = font.height

    def draw(self, drawable, pos, height, ascender, displayWidth=64):
        drawable.setFont(self.font.font)
        drawable.setPen(QColor(*self.colour))
        anchor = "ls"
        top = None
        if self.vertical == "middle":
            anchor = "lm"
            top = pos[1] - ascender
            pos = [pos[0], top + height / 2]

        x, y = pos
        for c, w in zip(self.text, self.charWidths):
            if x >= displayWidth:
                break

            if x + w >= 0:
                #drawable.drawText(x, y, c, font=self.font.font, fill=self.colour, anchor=anchor)
                drawable.drawText(x, y, c)

            x += w
        
        return self.size

    
class FancyText:
    def __init__(self, displayWidth, *args):
        self.displayWidth = displayWidth
        self.segments = args
        self.largestAscender = max([s.ascender for s in self.segments])
        self.height = max([s.height for s in self.segments])

    def getsize(self):
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

class TV_Widget(QtWidgets.QLabel):
    """
    Custom Qt Widget to show a power bar and dial.
    Demonstrating compound and custom-drawn widget.
    """

    def __init__(self, steps=5, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.canvas1 = QtGui.QPixmap(100, 100)
        self.canvas2 = QtGui.QPixmap(100, 100)
        self.offscreen_canvas = self.canvas1
        self.width, self.height = (100, 100)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        size = event.size()
        self.width, self.height = (size.width(), size.height())
        self.canvas1 = QtGui.QPixmap(self.width, self.height)
        self.canvas2 = QtGui.QPixmap(self.width, self.height)
        self.offscreen_canvas = self.canvas1

def neverIdle():
    return False

class ClockTimerDisplaySingleton(TV_Widget):
    def __init__(self, args, displayString=None, hardwareConfigFN=None, fontPath=["fonts"]):
        super().__init__()

        #if not hardwareConfigFN:
        #    hardwareConfigFN = "hardware.toml"

        #hardwareConfigFile = AutoConfigParser(sections=sections, filename=hardwareConfigFN)
        #hardwareConfig = Hardware.HardwareConfigSection(hardwareConfigFile)
        #hardwareConfigFile.hardware = hardwareConfig

        #self.hardwareConfig = hardwareConfigFile

        self.parser = argparse.ArgumentParser()
        self.args = None

        self.fontPath = [fontPath] if isinstance(fontPath, str) else fontPath
        self.fontId = 0

        #self.parser.set_defaults(led_rows=16, led_cols=32)

        self.parser.add_argument("--twoline-font", action="store", type=str,
                                 help="the twoline font", default=f"EncodeSansSemiCondensed-Light.ttf:{int(screenHeight * 0.30)}")
        self.parser.add_argument("--twotime-font", action="store", type=str,
                                 help="the twotime font - should be monospaced",
                                 default=f"IBMPlexSansCondensed-Light.ttf:{int(screenHeight * 0.45)}")
        self.parser.add_argument("--timer-font", action="store", type=str,
                                 help="the timer font", default=f"RobotoCondensed-Light.ttf:{int(screenHeight * 0.5)}")
        self.parser.add_argument("--small-font", action="store", type=str,
                                 help="the small font", default=f"RobotoCondensed-Light.ttf:{int(screenHeight * 0.28)}")
        self.parser.add_argument("--clock-font", action="store", type=str,
                                 help="the clock font", default=f"RobotoCondensed-Light.ttf:{int(screenHeight * 0.65)}")
        self.parser.add_argument("--seconds-font", action="store", type=str,
                                 help="the clock seconds font", default=f"RobotoCondensed-Light.ttf:{int(screenHeight * 0.25)}")
        self.parser.add_argument("--text-font", action="store", type=str,
                                 help="the text font", default=f"Lato-Light.ttf:{int(screenHeight * 0.8)}")

        self.parser.add_argument("--start-message", help="message to display at the start", type=str, default=None)
        self.parser.add_argument("--port", help="start in given port", type=str, default=None)

        self.scrollDelay = 0.01
        self.scrollAmt = 5

        self.setColours()
        self.colourCache = {}
        self.isIdle = neverIdle
        self.args = self.parser.parse_args()
        self.hardwareConfig = None


        self.white = (255, 255, 255)
        self.sofWhite = (180, 180, 180)
        self.pos = 1
        self.mirrored = False

        self.lastDisplay = ""

        self.firstTime = True

        self._splashColour = None

        self.sequenceNumber = 0

        self.breakTimes = []


    def parseArgs(self):
        return self.args

    def startDisplay(self):
        self.timerFont = self.loadFont("Timer", self.args.timer_font, fontPathList=self.fontPath)
        self.smallFont = self.loadFont("Small", self.args.small_font, fontPathList=self.fontPath)
        self.twoLineFont = self.loadFont("TwoLine", self.args.twoline_font, fontPathList=self.fontPath)
        self.twoTimeFont = self.loadFont("TwoTime", self.args.twotime_font, fontPathList=self.fontPath)
        self.clockFont = self.loadFont("Clock", self.args.clock_font, fontPathList=self.fontPath)
        self.secondsFont = self.loadFont("Seconds", self.args.seconds_font, fontPathList=self.fontPath)
        self.textFont = self.loadFont("Text", self.args.text_font, fontPathList=self.fontPath)

    def loadFont(self, name, fontFileName, default=True, fontPathList=[]):
        self.fontId += 1

        sp = fontFileName.split(":")
        fontFileName = sp[0]
        size = int(screenHeight * 0.3)

        if len(sp) > 1:
            size = int(sp[1])

        for path in fontPathList:
            if os.path.exists(fontFileName):
                fontPath = fontFileName
            else:
                fontPath = os.path.join(path, fontFileName)

            if os.path.exists(fontPath):
                debug("pillow: %s loading font: %s(%d) size=%d", name, fontPath, self.fontId, size)
                if fontPath.lower().endswith(".ttf"):

                    QtFontId = QtGui.QFontDatabase().addApplicationFont(fontPath)
                    families = QtGui.QFontDatabase.applicationFontFamilies(QtFontId)
                    if len(families) > 1:
                        if "light" in fontPath.lower():
                            families = list(filter(lambda x: "light" in x.lower(), families))
                        else:
                            families = list(filter(lambda x: "light" not in x.lower(), families))

                    font = QtGui.QFontDatabase.font(families[0], "", size)
                else:
                    print("shouldn't be here")
                    font = ImageFont.load(fontPath)

                fontMetrics = QtGui.QFontMetrics(font)

                ascender, descender = inferTextMetrics(fontMetrics)
                info("pillow: %s loaded font: %s(%d) size=%d ascender=%s descender=%s", name, fontPath, self.fontId, size, ascender, descender)
                return Font(name, font, self.fontId, size, ascender, descender, ascender + descender, fontMetrics)

            error("pillow: %s font not found: %s", name, fontPath)

        if default:
            warning("pillow: %s loading default font for: %s", name, fontFileName)

            font = QtGui.QFont()
            font.setFamily('Times')
            font.setBold(True)
            #ptSize = int(self.height * 0.3)
            ptSize = int(screenHeight * 0.6)
            font.setPointSize(ptSize)
            fontMetrics = QtGui.QFontMetrics(font)
            ascender, descender = inferTextMetrics(fontMetrics)
            return Font(name, font, self.fontId, ptSize, ascender, descender, ascender + descender, fontMetrics)

        return None

    def setIsIdle(self, isIdle):
        self.isIdle = isIdle

    def clearDrawable(self):
        self.offscreen_canvas.fill(QColor(0, 0, 0))
        return QtGui.QPainter(self.offscreen_canvas)

    def swapCanvas(self, drawable):
        drawable.end()
        self.setPixmap(self.offscreen_canvas)

        self.canvas1, self.canvas2 = self.canvas2, self.canvas1
        self.offscreen_canvas = self.canvas1

    def _colour(self, c):
        if isinstance(c, list):
            return c
        elif isinstance(c, str):
            try:
                return self.colourCache[c]
            except KeyError:
                rgb = self.colours.get(c.lower(), QColor(255, 255, 255))
                self.colourCache[c] = rgb
                return rgb
        else:
            return c

    def getColours(self):
        return list(self.colours.items())
        
    def setColours(self, colours=None):
        self.colourCache = {}

        self.colours = {}
        if colours is not None:
            for n, rgb in colours:
                self.colours[re.sub("\W*", "", n.lower())] = rgb
                
        for n, rgb in requiredColours:
            if n not in self.colours:
                self.colours[n] = rgb

    def abort(self):
        self.sequenceNumber += 1

    def competitionUpdate(self, displayTime1 , colour1, displayTime2, colour2):
        self.sequenceNumber += 1
        
        curDisplay = f"{colour1}:{displayTime1}:{colour2}:{displayTime2}"

        if self.lastDisplay == curDisplay:
            return

        self.lastDisplay = curDisplay

        drawable = self.clearDrawable()
        drawable.setFont(self.twoTimeFont.font)

        w1, h1 = getsize(self.twoTimeFont, displayTime1)
        w2, h2 = getsize(self.twoTimeFont, displayTime2)

        wmax = max(w1, w2)
        xoffset = int((self.width - wmax) / 2)
        xend = xoffset + wmax

        drawable.setPen(QColor(*self._colour(colour1)))
        drawable.drawText(xend - w1, self.height * 0.45, displayTime1)

        drawable.setPen(QColor(*self._colour(colour2)))
        drawable.drawText(xend - w2, self.height * 0.95, displayTime2)

        self.swapCanvas(drawable)

    async def displayTeamNames(self, team1, colour1, team2, colour2, scrollTeamsSeparator=None):
        if scrollTeamsSeparator:
            separatorColour = self._colour("white") if colour1 != colour2 else self._colour("yellow")
            ft = FancyText(self.width,
                           FancyTextSegment(team1, self.textFont, self._colour(colour1)),
                           FancyTextSegment(f" {scrollTeamsSeparator} ", self.twoLineFont, separatorColour, vertical="middle"),
                           FancyTextSegment(team2, self.textFont, self._colour(colour2)))
            await self.displayScrollingText(ft)
        else:
            await self.twoLineText(team1, team2, colour1=colour1, colour2=colour2, centre=True)

    def setSplashColour(self, colour="white"):
        self.sequenceNumber += 1
        self._splashColour = self.colours.get(colour, (255, 255, 255)) if isinstance(colour, str) else colour

    def splashColour(self, colour=None):
        if colour is None:
            colour = "white" if self._splashColour is None else self._splashColour
            
        colour = self.colours.get(colour, (255, 255, 255)) if isinstance(colour, str) else colour

        drawable = self.clearDrawable()
        self.sequenceNumber += 1

        clr = QColor(colour[0], colour[1], colour[2])

        drawable.setPen(clr)
        brush = QtGui.QBrush()
        brush.setColor(clr)
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        drawable.setBrush(brush)
        drawable.drawRect(0, 0, self.width, self.height)

        self.swapCanvas(drawable)

    def updateTimer(self, displayTime, colour, prefix):
        curDisplay = prefix + displayTime

        if self.lastDisplay == curDisplay:
            return

        self.lastDisplay = curDisplay

        widthT, heightT = getsize(self.timerFont, displayTime)
        drawable = self.clearDrawable()
        drawable.setFont(self.timerFont.font)
        drawable.setPen(QColor(*colour))

        pos = max(0, int((self.width - (widthT - len(displayTime) - 2)) / 2))
        firstChar = True
        for c in displayTime:
            if c == ":":
                pos -= 2

            xAdjust = 1 if firstChar and c == "1" else 0
            drawable.drawText(pos + xAdjust, heightT + (self.height - heightT) / 2, c)
            cwidth = getsize(self.timerFont, c)[0]
            pos += cwidth * 0.9
            firstChar = False
            
            if c == ":":
                pos -= 1
                firstChar = True

        self.swapCanvas(drawable)

    def timerUpdate(self, time, colour):
        self.displayText(time.strip(), colour)
        return 0.005

    async def displayScrollingText(self, my_text, colour="white", startTime=None, twoLineOK=False, displayTime=0):
        canvasWidth = self.width
        textColour = self._colour(colour)

        if twoLineOK and isinstance(my_text, str):
            sp = my_text.split(" ")
            if len(sp) == 2:
                textLen0, textHeight0 = getsize(self.twoLineFont, sp[0])
                textLen1, textHeight1 = getsize(self.twoLineFont, sp[1])
                if textLen0 < canvasWidth and textLen1 < canvasWidth:
                    await self.twoLineText(sp[0], sp[1], colour=textColour, centre=True)
                    return

        self.sequenceNumber += 1

        if isinstance(my_text, str):
            ft = FancyText(self.width, FancyTextSegment(my_text.strip(), self.textFont, textColour))
        else:
            ft = my_text
            
        prevDisplay = self.lastDisplay
        self.lastDisplay = ft.signature()
        
        lengthT, heightT = ft.getsize()
        yOffset = int((self.height - heightT) / 2)

        if lengthT < canvasWidth:
            if self.lastDisplay == prevDisplay:
                return

            drawable = self.clearDrawable()

            ft.draw(drawable, (int((canvasWidth - lengthT) / 2), yOffset))
            self.swapCanvas(drawable)
            return

        curSequenceNumber = self.sequenceNumber
        if not startTime:
            startTime = time.monotonic()

        scrollLength = lengthT + canvasWidth
        sCnt = 1
        
        while curSequenceNumber == self.sequenceNumber and not self.isIdle():
            nextTime = startTime + self.scrollDelay * sCnt
            assert nextTime - time.monotonic() < 1
            if displayTime:
                if startTime + displayTime < time.monotonic():
                    return

            sCnt += 1
            tDiff = int((time.monotonic() - startTime) * self.scrollAmt / self.scrollDelay) % scrollLength
            
            drawable = self.clearDrawable()
            ft.draw(drawable, (-tDiff + canvasWidth, yOffset))

            self.swapCanvas(drawable)

            await asyncio.sleep(0.001)
            while time.monotonic() < nextTime and curSequenceNumber == self.sequenceNumber:
                await asyncio.sleep(0.0001)

    async def displayFlashText(self, my_text, colour="white", delay=1.0, displayCount=1000, length=5.0):
        self.sequenceNumber += 1

        my_text = my_text.rstrip()
        self.lastDisplay = "ft:" + my_text

        curSequenceNumber = self.sequenceNumber
        displayed = None
        startTime = time.monotonic()

        while displayCount > 0 and curSequenceNumber == self.sequenceNumber and not self.isIdle():
            curTime = time.monotonic()

            showing = (int((curTime - startTime) / delay) % 2) == 1
            if displayed != showing:
                displayed = showing

                if displayed:
                    displayCount -= 1
                    self.displayText(my_text, colour, centre=True, sequenceUpdate=False)
                else:
                    drawable = self.clearDrawable()
                    self.swapCanvas(drawable)

            await asyncio.sleep(0.05)        

    def blank(self):
        self.sequenceNumber += 1
        self.lastDisplay = "blank:"
        drawable = self.clearDrawable()
        self.swapCanvas(drawable)
        return 0.25

    def findFont(self, textList, fontList):
        for f in fontList:
            fits = True
            for l in textList:
                textLen, textHeight = getsize(f, l)
                if textLen > self.width:
                    fits = False

            if fits:
                return f

        return fontList[-1]

    def displayText(self, text, colour="white", centre=False, sequenceUpdate=True):
        text = text.rstrip()
        if sequenceUpdate:
            self.sequenceNumber += 1
            self.lastDisplay = "dt:" + text

        textColour = self._colour(colour)

        if '\n' in text:
            lines = text.split('\n', 1)
        else:
            lines = [text]

        displayFont = self.findFont(lines, [self.timerFont, self.textFont, self.smallFont])

        if displayFont == self.smallFont and len(lines) == 1:
            width = 0
            for i in range(len(text)):
                textLen, textHeight = getsize(displayFont, text[0: i])
                if textLen > self.width:
                    lines = [text[0:i - 1], text[i - 1:]]
                    break

        drawable = self.clearDrawable()
        drawable.setFont(displayFont.font)
        drawable.setPen(QColor(*textColour))

        vpos = 0
        for text in lines:
            textLen, textHeight = getsize(displayFont, text)
            vpos += textHeight
            if centre:
                hpos = int(max(0, (self.width - textLen) / 2))
            else:
                hpos = 0

            drawable.drawText(hpos, vpos, text)

        self.swapCanvas(drawable)

    async def twoLineText(self, line1, line2, colour="white", colour1=None, colour2=None, centre=False, endTime=None, scroll=True):
        self.sequenceNumber += 1

        colour1 = (colour1 if colour1 else colour).lower()
        colour2 = (colour2 if colour2 else colour).lower()

        curDisplay = "twoline:" + line1 + "\n" + line2 + "\n" + colour1 + "\n" + colour2

        if self.lastDisplay == curDisplay:
            return

        self.lastDisplay = curDisplay
            
        line1 = line1.rstrip()
        line2 = line2.rstrip()

        c1 = self._colour(colour1)
        c2 = self._colour(colour2)

        pos = self.width
        twoLineFont = self.twoLineFont
        len1, height1 = getsize(twoLineFont, line1)
        len2, height2 = getsize(twoLineFont, line2)

        if (not scroll) or (len1 < pos and len2 < pos):
            drawable = self.clearDrawable()
            drawable.setFont(twoLineFont.font)

            centre1 = int((self.width - len1) / 2) if centre else 0
            centre2 = int((self.width - len2) / 2) if centre else 0
            drawable.setPen(QColor(*c1))
            drawable.drawText(centre1, self.height * 0.38 , line1)

            drawable.setPen(QColor(*c2))
            drawable.drawText(centre2, self.height * 0.88, line2)
            self.swapCanvas(drawable)
            return

        curSequenceNumber = self.sequenceNumber

        pos = self.width
        maxLen = max(len1, len2)
        while curSequenceNumber == self.sequenceNumber and not self.isIdle():
            curTime = time.monotonic()
            if endTime:
                if curTime > endTime:
                    return

            drawable = self.clearDrawable()
            drawable.setFont(twoLineFont.font)

            drawable.setPen(QColor(*c1))
            drawable.drawText(pos, self.height * 0.38, line1)
            
            drawable.setPen(QColor(*c2))
            drawable.drawText(pos, self.height * 0.88, line2)
            self.swapCanvas(drawable)

            pos -= self.scrollAmt
            if pos + maxLen < 0:
                pos = self.width
                continue

            diffTime = time.monotonic() - curTime
            await asyncio.sleep(max(self.scrollDelay - diffTime, 0))

    def breakTimeSet(self, t, c):
        if len(self.breakTimes) == 0:
            self.breakTimes = [[t, c]]
        else:
            self.breakTimes = [[t, c], self.breakTimes[0]]

    def breakTimeClear(self):
        self.breakTimes = []
            
    async def breakTimeDisplay(self):
        try:
            self.sequenceNumber += 1

            curDisplay = "breaktime:"
            drawable = self.clearDrawable()
            drawable.setFont(self.twoLineFont.font)

            if len(self.breakTimes) == 0:
                drawable.setPen(QColor(255,255,255))
                drawable.drawText(int(self.width * 0.45), int(self.height * 0.5), "...")
                curDisplay += "..."
            else:
                ypos, anchor = self.height * 0.47, "lt"
                for t, c in self.breakTimes[0: min(2, len(self.breakTimes))]:
                    if t < 1:
                        txt = "%.5f" % t
                    elif t < 10:
                        txt = "%.4f" % t
                    else:
                        txt = "%.3f" % t

                    # trim off leading 0
                    if t < 1:
                        txt = txt[1:]

                    drawable.setPen(QColor(*self._colour(c)))
                    drawable.drawText(0, ypos, txt)
                    curDisplay += str(c) + ":" + txt
                    ypos, anchor = self.height * 0.97, "lb"

            self.lastDisplay = curDisplay
            self.swapCanvas(drawable)

            return 5

            if self.lastDisplay == curDisplay:
                return 0.01

        except Exception as e:
            print("bad me")
            error("timerdisplay: displayBreakTimes exception=%s", e, exc_info=True)
            raise

        return 0.005
        
    def clockUpdate(self, showTenths=False, colour="white"):
        self.sequenceNumber += 1

        curTime = time.time()
        localTime = time.localtime(curTime)
        tenths = (int(curTime * 10) % 10) if showTenths else 0
        displayTime = time.strftime("%H:%M", localTime)

        curDisplay = f"localTime:{localTime}.{tenths}"

        if self.lastDisplay == curDisplay:
            return 0.05

        self.lastDisplay = curDisplay

        pos = -1

        colour=self._colour(colour)

        drawable = self.clearDrawable()
        drawable.setFont(self.clockFont.font)
        drawable.setPen(QColor(*colour))

        for offset, c in enumerate(displayTime):
            drawable.drawText(pos - offset, self.clockFont.size, c)
            tWidth, tHeight = getsize(self.clockFont, c)
            pos += int(tWidth - tWidth * 0.1)

        drawable.setFont(self.secondsFont.font)
        oWidth, oHeight = getsize(self.secondsFont, "0")
        if showTenths:
            drawable.drawText(int(self.width * 0.65), int(self.height * 0.75 + self.secondsFont.ascender), ("0" + str(localTime.tm_sec))[-2:] + '.' + str(tenths))
        else:
            drawable.drawText(pos - oWidth * 2, int(self.clockFont.size + self.secondsFont.ascender), ("0" + str(localTime.tm_sec))[-2:])

        self.swapCanvas(drawable)
        return 0.05

    def run(self):
        loop = qasync.QEventLoop(app)
        return loop


class MainWindow(QMainWindow):
    def __init__(self, args, displayString, hardwareConfigFN, fontPath):
        self.tvWidget = None
        super().__init__()
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.tvWidget = ClockTimerDisplaySingleton(args, displayString=displayString, hardwareConfigFN=hardwareConfigFN, fontPath=fontPath)
        self.showFullScreen()

        print(f"{args=}\n{displayString=}\n{hardwareConfigFN=}\n{fontPath=}")

        self.setCentralWidget(self.tvWidget)

        print(f"{self.width()=}")
        print(f"{self.height()=}")

    def keyPressEvent(self, event):
        print(f"{event.key()=} {event.text()=}")
        if event.text() in ["q", "Q"]:
            self.tvWidget.abort()
            time.sleep(0.5)
            sys.exit()

    #def resizeEvent(self, event):
    #    global display
    #    print("MainWindow resize")
    #    print(f"{self.tvWidget=} {self.testFn=}")
    #    if self.tvWidget and self.testFn:
    #        asyncio.ensure_future(self.delayedTest())

window = None
def create(args, displayString=None, hardwareConfigFN=None, fontPath=["fonts"]):
    global display, window

    if not display:
        window = MainWindow(args, displayString, hardwareConfigFN, fontPath)

        display = window.tvWidget
        display.startDisplay()

    return display
