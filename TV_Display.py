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
from BaseDisplay import BaseDisplay
from FancyText import BaseFont

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

class Font(BaseFont):
    def __init__(self, name, font, id, size):
        self.fontMetrics = QtGui.QFontMetrics(font)
        
        ss = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRTSUVWXYZ"

        ascender = self.fontMetrics.ascent()
        descender = self.fontMetrics.descent()
        
        super().__init__(name, font, id, size, ascender, descender, ascender + descender)

    def getSize(self, text):
        bbox = self.fontMetrics.boundingRect(QRect(0,0,6000,3000), Qt.AlignTop, text)
        return (bbox.width(), bbox.height())
    

class Drawable:
    def __init__(self, canvas, owner):
        self.canvas = canvas
        self.owner = owner
        smallest_dimension = min(owner.width, owner.height)
        self.width = owner.width
        self.height = owner.height
        self.visible_pixel_dimension = int(smallest_dimension / 32)
        self.visible_pixels = (int(self.width / self.visible_pixel_dimension), int(self.height / self.visible_pixel_dimension))

        self.brush = QtGui.QBrush()
        self.brush.setStyle(Qt.BrushStyle.SolidPattern)
        self.noBrush =  QtGui.QBrush()

        self.pen = QtGui.QPen()
        self.pen.setJoinStyle(Qt.MiterJoin)
        self.noPen = QtGui.QPen(Qt.NoPen)

    def start(self, clear=False):
        self.drawable = QtGui.QPainter(self.canvas)
        if clear:
            self.clear()

        return self.drawable

    def clear(self):
        drawable = self.drawable
        colour = self.owner.mapColour("black")

        drawable.setPen(self.noPen)
        self.brush.setColor(colour)
        drawable.setBrush(self.brush)

        drawable.drawRect(0, 0, self.owner.width, self.owner.height)

    def end(self):
        if self.drawable:
            self.drawable.end()
            self.drawable = None

    def show(self):
        if self.drawable:
            self.end()

        self.owner.show(self)

    def fill(self, clr):
        self.drawable.fill(self.owner.mapColour(colour))

    def drawPoint(self, x, y, colour):
        drawable = self.drawable
        colour = self.owner.mapColour(colour)

        drawable.setPen(self.noPen)

        self.brush.setColor(self.owner.mapColour(colour))
        drawable.setBrush(self.brush)

        pd = self.visible_pixel_dimension

        drawable.drawRect(x, y, pd, pd)

    def drawRect(self, x, y, width, height, fillColour=None, borderColour=None, borderWidth=None):
        drawable = self.drawable

        if borderColour:
            self.pen.setColor(self.owner.mapColour(borderColour))
            self.pen.setWidth( borderWidth if borderWidth else self.visible_pixel_dimension)
            drawable.setPen(self.pen)
        else:
            drawable.setPen(self.noPen)

        if fillColour:
            self.brush.setColor(self.owner.mapColour(fillColour))
            drawable.setBrush(self.brush)
        else:
            drawable.setBrush(self.noBrush)

        drawable.drawRect(x, y,  width, height)

    def drawCircle(self, x, y, radius=5, fillColour=None, borderColour=None, borderWidth=None):
        drawable = self.drawable
        if borderColour:
            self.pen.setColor(self.owner.mapColour(borderColour))
            self.pen.setWidth( borderWidth if borderWidth else self.visible_pixel_dimension)
            drawable.setPen(self.pen)
        else:
            drawable.setPen(self.noPen)

        if fillColour:
            self.brush.setColor(self.owner.mapColour(fillColour))
            drawable.setBrush(self.brush)
        else:
            drawable.setBrush(self.noBrush)

        drawable.drawEllipse(QPoint(x, y), radius, radius)

    def drawPolygon(self, pts, fillColour=None, borderColour=None, borderWidth=None):
        drawable = self.drawable
        if borderColour:
            self.pen.setColor(self.owner.mapColour(borderColour))
            self.pen.setWidth( borderWidth if borderWidth else self.visible_pixel_dimension)
            drawable.setPen(self.pen)
        else:
            drawable.setPen(self.noPen)

        if fillColour:
            self.brush.setColor(self.owner.mapColour(fillColour))
            drawable.setBrush(self.brush)
        else:
            drawable.setBrush(self.noBrush)

        pts = [QtCore.QPointF(x, y) for x,y in pts]
        drawable.drawPolygon(pts)

    def drawText(self, font, x, y , text, colour):
        colour = self.owner.mapColour(colour)

        drawable = self.drawable

        drawable.setFont(font.font)

        self.pen.setColor(self.owner.mapColour(colour))
        drawable.setPen(self.pen)
        drawable.drawText(x, y, text)


class TV_Widget(QtWidgets.QLabel):
    """
    Custom Qt Widget to show a power bar and dial.
    Demonstrating compound and custom-drawn widget.
    """

    def __init__(self, steps=5, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #self.canvas1 = QtGui.QPixmap(100, 100)
        #self.canvas2 = QtGui.QPixmap(100, 100)
        self.canvas = QtGui.QPixmap(100, 100)
        self.width, self.height = (100, 100)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        size = event.size()
        self.width, self.height = (size.width(), size.height())
        #self.canvas1 = QtGui.QPixmap(self.width, self.height)
        #self.canvas2 = QtGui.QPixmap(self.width, self.height)
        self.canvas = QtGui.QPixmap(self.width, self.height)

class ClockTimerDisplaySingleton(TV_Widget, BaseDisplay):
    def __init__(self, args, displayString=None, hardwareConfigFN=None, fontPath=["fonts"]):
        TV_Widget.__init__(self)
        BaseDisplay.__init__(self)

        self.scrollAmt = screenWidth / 100
        self.scrollDelay = 0.033

        self.parser = argparse.ArgumentParser()
        self.args = None

        self.fontPath = [fontPath] if isinstance(fontPath, str) else fontPath

        #self.parser.set_defaults(led_rows=16, led_cols=32)

        self.parser.add_argument("--twoline-font", action="store", type=str,
                                 help="the twoline font", default=f"EncodeSansSemiCondensed-Light.ttf:{int(screenHeight * 0.45)}")
        self.parser.add_argument("--twotime-font", action="store", type=str,
                                 help="the twotime font - should be monospaced",
                                 default=f"IBMPlexSansCondensed-Light.ttf:{int(screenHeight * 0.55)}")
        self.parser.add_argument("--timer-font", action="store", type=str,
                                 help="the timer font", default=f"RobotoCondensed-Light.ttf:{int(screenHeight * 0.65)}")
        self.parser.add_argument("--small-font", action="store", type=str,
                                 help="the small font", default=f"RobotoCondensed-Light.ttf:{int(screenHeight * 0.28)}")
        self.parser.add_argument("--clock-font", action="store", type=str,
                                 help="the clock font", default=f"RobotoCondensed-Light.ttf:{int(screenHeight * 0.75)}")
        self.parser.add_argument("--seconds-font", action="store", type=str,
                                 help="the clock seconds font", default=f"RobotoCondensed-Light.ttf:{int(screenHeight * 0.25)}")
        self.parser.add_argument("--text-font", action="store", type=str,
                                 help="the text font", default=f"Lato-Light.ttf:{int(screenHeight * 0.9)}")

        self.parser.add_argument("--test", action="store_true",
                                 help="creates window in test mode. 1280x720 with borders not maximized")

        self.parser.add_argument("--start-message", help="message to display at the start", type=str, default=None)
        self.parser.add_argument("--port", help="start in given port", type=str, default=None)

        self.args = self.parser.parse_args()

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

        # want to vertical centre numbers. Assume same height as capital letters. Need to move
        # rendered text up by half the difference of ascender - capital height.
        self.timer_font_vertical_offset = - int((self.timerFont.ascender - self.timerFont.fontMetrics.capHeight()) / 2)

        w, h = self.clockFont.getSize("1")
        self.leadingOneAdjust = (w * 0.1, w * 0.2)
        self.colonAdjust = (w * 0.1, w * 0.1)


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
                        font.setPixelSize(size)
                else:
                    font = ImageFont.load(fontPath)

                f =  Font(name, font, self.fontId, size)
                info("pillow: %s loaded font: %s(%d) size=%d ascender=%s descender=%s height=%s", name, fontPath, self.fontId, size, f.ascender, f.descender, f.height)
                return f

            error("pillow: %s font not found: %s", name, fontPath)

        if default:
            warning("pillow: %s loading default font for: %s", name, fontFileName)

            font = QtGui.QFont()
            font.setFamily('Times')
            font.setBold(True)
            #ptSize = int(self.height * 0.3)
            ptSize = int(screenHeight * 0.6)
            font.setPointSize(ptSize)
            return Font(name, font, self.fontId, ptSize)

        return None

    def mapColour(self, c):
        if isinstance(c, QColor):
            return c
        if isinstance(c, (list, tuple)):
            return QColor(*c)
        elif isinstance(c, str):
            try:
                return self.colourCache[c]
            except KeyError:
                rgb = QColor(*self.colours.get(c.lower(), (255, 255, 255)))
                self.colourCache[c] = rgb
                return rgb
        else:
            print(f"what {c=}")
            return c

    def getDrawable(self):
        return Drawable(self.canvas, self)

    def getClearedDrawable(self):
        drawable = Drawable(self.canvas, self)

        drawable.start(clear=True)

        return drawable

    def show(self, drawable):
        drawable.end()

        self.setPixmap(drawable.canvas)

    def run(self):
        loop = qasync.QEventLoop(app)
        return loop


class MainWindow(QMainWindow):
    def __init__(self, args, displayString, hardwareConfigFN, fontPath, test=False):
        global screenWidth, screenHeight

        self.tvWidget = None
        super().__init__()
        self.tvWidget = ClockTimerDisplaySingleton(args, displayString=displayString, hardwareConfigFN=hardwareConfigFN, fontPath=fontPath)

        if test or self.tvWidget.parseArgs().test:
            # throw away the first widgetcreated. change the size the of the
            # n and then recreate the widget. This adjusts the fonts szzes
            screenWidth = 1280
            screenHeight = 720

            self.tvWidget.setParent(None)
            self.tvWidget.deleteLater()

            self.tvWidget = ClockTimerDisplaySingleton(args, displayString=displayString, hardwareConfigFN=hardwareConfigFN, fontPath=fontPath)
            self.resize(screenWidth, screenHeight)
            self.show()
        else:
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
            self.showFullScreen()

        self.setCentralWidget(self.tvWidget)

        print(f"{self.width()=}")
        print(f"{self.height()=}")

    def keyPressEvent(self, event):
        print(f"{event.key()=} {event.text()=}")
        if event.text() in ["q", "Q"]:
            self.tvWidget.abort()
            time.sleep(0.5)
            sys.exit()
        elif event.text() in ["r", "R"]:
            print("unmaximize window")
            self.setWindowState(Qt.WindowNoState)
            self.resize(500,500);
            self.show();
        elif  event.text() in ["m", "M"]:
            print("maximize window")
            self.showMaximized()


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
        window = MainWindow(args, displayString, hardwareConfigFN, fontPath, test=False)

        display = window.tvWidget
        display.startDisplay()
        display.hardwareConfig = None

    return display
