import asyncio
import traceback
import os
import time
import sys
from collections import namedtuple
from pathlib import Path
import argparse

from PySide6 import QtCore, QtGui, QtWidgets

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtAsyncio.events import QAsyncioEventLoopPolicy
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QFontDatabase
import qasync

from logger import error, warning, info, debug
from base_display import BaseDisplay
from fancy_text import BaseFont

def excepthook(type_, value, traceback_):
    traceback.print_exception(type_, value, traceback_)
    QtCore.qFatal('')

sys.excepthook = excepthook

sections = ["Hardware"]

app = qasync.QApplication(sys.argv)

event_loop = qasync.QEventLoop(app)
asyncio.set_event_loop(event_loop)

screen = app.primaryScreen()
size= screen.size()
screen_width = size.width()
screen_height = size.height()

print(f"{screen_width=} {screen_height=}")

display = None

Font = namedtuple("Font", "name font id size ascender descender height font_metrics")

class Font(BaseFont):
    def __init__(self, name, font, font_id, font_size):
        self.font_metrics = QtGui.QFontMetrics(font)

        ss = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRTSUVWXYZ"

        ascender = self.font_metrics.ascent()
        descender = self.font_metrics.descent()

        super().__init__(name, font, font_id, font_size, ascender, descender, ascender + descender)

    def get_size(self, text):
        bbox = self.font_metrics.boundingRect(QRect(0,0,6000,3000), Qt.AlignTop, text)
        return (bbox.width(), bbox.height())


class Drawable:
    def __init__(self, canvas, owner):
        self.canvas = canvas
        self.owner = owner
        self.drawable = None
        smallest_dimension = min(owner.width, owner.height)
        self.width = owner.width
        self.height = owner.height
        self.visible_pixel_dimension = int(smallest_dimension / 32)
        self.visible_pixels = (int(self.width / self.visible_pixel_dimension), int(self.height / self.visible_pixel_dimension))

        self.brush = QtGui.QBrush()
        self.brush.setStyle(Qt.BrushStyle.SolidPattern)
        self.no_brush =  QtGui.QBrush()

        self.pen = QtGui.QPen()
        self.pen.setJoinStyle(Qt.MiterJoin)
        self.no_pen = QtGui.QPen(Qt.NoPen)

    def start(self, clear=False):
        self.drawable = QtGui.QPainter()
        self.drawable.begin(self.canvas)
        if clear:
            self.clear()

        return self.drawable

    def clear(self):
        drawable = self.drawable
        colour = self.owner.map_colour("black")

        drawable.setPen(self.no_pen)
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

    def fill(self, colour):
        self.drawable.fill(self.owner.map_colour(colour))

    def draw_point(self, x, y, colour):
        drawable = self.drawable
        colour = self.owner.map_colour(colour)

        drawable.setPen(self.no_pen)

        self.brush.setColor(self.owner.map_colour(colour))
        drawable.setBrush(self.brush)

        pd = self.visible_pixel_dimension

        drawable.drawRect(x, y, pd, pd)

    def draw_rect(self, x, y, width, height, fill_colour=None, border_colour=None, border_width=None):
        drawable = self.drawable

        if border_colour:
            self.pen.setColor(self.owner.map_colour(border_colour))
            self.pen.setWidth( border_width if border_width else self.visible_pixel_dimension)
            drawable.setPen(self.pen)
        else:
            drawable.setPen(self.no_pen)

        if fill_colour:
            self.brush.setColor(self.owner.map_colour(fill_colour))
            drawable.setBrush(self.brush)
        else:
            drawable.setBrush(self.no_brush)

        drawable.drawRect(x, y,  width, height)

    def draw_circle(self, x, y, radius=5, fill_colour=None, border_colour=None, border_width=None):
        drawable = self.drawable
        if border_colour:
            self.pen.setColor(self.owner.map_colour(border_colour))
            self.pen.setWidth(border_width if border_width else self.visible_pixel_dimension)
            drawable.setPen(self.pen)
        else:
            drawable.setPen(self.no_pen)

        if fill_colour:
            self.brush.setColor(self.owner.map_colour(fill_colour))
            drawable.setBrush(self.brush)
        else:
            drawable.setBrush(self.no_brush)

        drawable.drawEllipse(QPoint(x, y), radius, radius)

    def draw_polygon(self, pts, fill_colour=None, border_colour=None, border_width=None):
        drawable = self.drawable
        if border_colour:
            self.pen.setColor(self.owner.map_colour(border_colour))
            self.pen.setWidth(border_width if border_width else self.visible_pixel_dimension)
            drawable.setPen(self.pen)
        else:
            drawable.setPen(self.no_pen)

        if fill_colour:
            self.brush.setColor(self.owner.map_colour(fill_colour))
            drawable.setBrush(self.brush)
        else:
            drawable.setBrush(self.no_brush)

        pts = [QtCore.QPointF(x, y) for x,y in pts]
        drawable.drawPolygon(pts)

    def draw_text(self, font, x, y , text, colour):
        colour = self.owner.map_colour(colour)

        drawable = self.drawable

        drawable.setFont(font.font)

        self.pen.setColor(self.owner.map_colour(colour))
        drawable.setPen(self.pen)
        drawable.drawText(x, y, text)


class TV_Widget(QtWidgets.QLabel):
    """
    Custom Qt Widget to show a power bar and dial.
    Demonstrating compound and custom-drawn widget.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #self.canvas1 = QtGui.QPixmap(100, 100)
        #self.canvas2 = QtGui.QPixmap(100, 100)
        self.canvas = QtGui.QPixmap(100, 100)
        self.width, self.height = (100, 100)

    def resizeEvent(self, event):
        global size

        super().resizeEvent(event)
        size = event.size()
        self.width, self.height = (size.width(), size.height())
        #self.canvas1 = QtGui.QPixmap(self.width, self.height)
        #self.canvas2 = QtGui.QPixmap(self.width, self.height)
        self.canvas = QtGui.QPixmap(self.width, self.height)

class ClockTimerDisplaySingleton(TV_Widget, BaseDisplay):
    def __init__(self, args,
                 font_path=["fonts"]):
        TV_Widget.__init__(self)
        BaseDisplay.__init__(self)

        self.scroll_amount = screen_width / 100
        self.scroll_delay = 0.033
        self.two_time_display_vertical_offset = -int(screen_height * 0.05)

        self.parser = argparse.ArgumentParser()
        self.args = None

        self.font_path = [font_path] if isinstance(font_path, str) else font_path

        #self.parser.set_defaults(led_rows=16, led_cols=32)

        self.parser.add_argument("--two-line-font", action="store", type=str,
                                 help="the twoline font",
                                 default=f"EncodeSansSemiCondensed-Light.ttf:{int(screen_height * 0.45)}")
        self.parser.add_argument("--two-time-font", action="store", type=str,
                                 help="the twotime font - should be monospaced",
                                 default=f"IBMPlexSansCondensed-Light.ttf:{int(screen_height * 0.55)}")
        self.parser.add_argument("--timer-font", action="store", type=str,
                                 help="the timer font",
                                 default=f"RobotoCondensed-Light.ttf:{int(screen_height * 0.65)}")
        self.parser.add_argument("--small-font", action="store", type=str,
                                 help="the small font",
                                 default=f"RobotoCondensed-Light.ttf:{int(screen_height * 0.28)}")
        self.parser.add_argument("--clock-font", action="store", type=str,
                                 help="the clock font",
                                 default=f"RobotoCondensed-Light.ttf:{int(screen_height * 0.75)}")
        self.parser.add_argument("--seconds-font", action="store", type=str,
                                 help="the clock seconds font",
                                 default=f"RobotoCondensed-Light.ttf:{int(screen_height * 0.25)}")
        self.parser.add_argument("--text-font", action="store", type=str,
                                 help="the text font",
                                 default=f"Lato-Light.ttf:{int(screen_height * 0.9)}")

        self.parser.add_argument("--test", action="store_true",
                                 help="creates window in test mode. 1280x720 with borders not maximized")

        self.parser.add_argument("--start-message", help="message to display at the start", type=str, default=None)
        self.parser.add_argument("--port", help="start in given port", type=str, default=None)

        self.args = self.parser.parse_args()

    def parse_args(self):
        return self.args

    def start_display(self):
        self.timer_font = self.load_font("Timer", self.args.timer_font, font_path_list=self.font_path)
        self.small_font = self.load_font("Small", self.args.small_font, font_path_list=self.font_path)
        self.two_line_font = self.load_font("TwoLine", self.args.two_line_font, font_path_list=self.font_path)
        self.two_time_font = self.load_font("TwoTime", self.args.two_time_font, font_path_list=self.font_path)
        self.clock_font = self.load_font("Clock", self.args.clock_font, font_path_list=self.font_path)
        self.seconds_font = self.load_font("Seconds", self.args.seconds_font, font_path_list=self.font_path)
        self.text_font = self.load_font("Text", self.args.text_font, font_path_list=self.font_path)

        # want to vertical centre numbers. Assume same height as capital letters. Need to move
        # rendered text up by half the difference of ascender - capital height.
        self.timer_font_vertical_offset = - int((self.timer_font.ascender - \
                                                 self.timer_font.font_metrics.capHeight()) / 2)

        w, h = self.clock_font.get_size("1")
        self.leading_one_adjust = (w * 0.1, w * 0.2)
        self.colon_adjust = (w * 0.1, w * 0.1)


    def load_font(self, name, font_filename, default=True, font_path_list=[]):
        self.font_id += 1

        sp = font_filename.split(":")
        font_filename = sp[0]
        ft_size = int(screen_height * 0.3)

        if len(sp) > 1:
            ft_size = int(sp[1])

        for path in font_path_list:
            if os.path.exists(font_filename):
                font_path = font_filename
            else:
                font_path = os.path.join(path, font_filename)

            file_path = Path(font_path)
            if file_path.is_file():
                debug("pillow: %s loading font: %s(%d) size=%d", name, font_path, self.font_id, ft_size)

                if file_path.suffix.lower() in {".ttf", ".otf", ".ttc", }:
                    qt_font_id = QFontDatabase.addApplicationFont(font_path)
                    families = QFontDatabase.applicationFontFamilies(qt_font_id)
                    if len(families) > 1:
                        if "light" in font_path.lower():
                            families = list(filter(lambda x: "light" in x.lower(), families))
                        else:
                            families = list(filter(lambda x: "light" not in x.lower(), families))

                        font = QtGui.QFontDatabase.font(families[0], "", ft_size)
                        font.setPixelSize(ft_size)
                else:
                    error("font must be a ttf font: %s", font_path)
                    sys.exit()

                f =  Font(name, font, self.font_id, ft_size)
                info("pillow: %s loaded font: %s(%d) size=%d ascender=%s descender=%s height=%s",
                     name, font_path, self.font_id, ft_size, f.ascender, f.descender, f.height)
                return f

            error("pillow: %s font not found: %s", name, font_path)

        if default:
            warning("pillow: %s loading default font for: %s", name, font_filename)

            font = QtGui.QFont()
            font.setFamily('Times')
            font.setBold(True)
            #approximage_font_size_in_pts = int(self.height * 0.3)
            approximage_font_size_in_pts = int(screen_height * 0.6)
            font.setPointSize(approximage_font_size_in_pts)
            return Font(name, font, self.font_id, approximage_font_size_in_pts)

        return None

    def map_colour(self, c):
        if isinstance(c, QColor):
            return c

        if isinstance(c, (list, tuple)):
            return QColor(*c)

        if isinstance(c, str):
            try:
                return self.colour_cache[c]
            except KeyError:
                rgb = QColor(*self.colours.get(c.lower(), (255, 255, 255)))
                self.colour_cache[c] = rgb
                return rgb
        else:
            error("unexpected colour c=%s", c)
            return c

    def get_drawable(self):
        return Drawable(self.canvas, self)

    def get_cleared_drawable(self):
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
    def __init__(self, args,
                 _unused_display_string,
                 _unsued_hardware_config_filename,
                 font_path,
                 test=False):
        global screen_width, screen_height

        self.tv_widget = None
        super().__init__()
        self.tv_widget = ClockTimerDisplaySingleton(args,
                                                   font_path=font_path)

        if test or self.tv_widget.args.test:
            # throw away the first widgetcreated. change the size the of the
            # n and then recreate the widget. This adjusts the fonts szzes
            screen_width = 1280
            screen_height = 720

            self.tv_widget.setParent(None)
            self.tv_widget.deleteLater()

            self.tv_widget = ClockTimerDisplaySingleton(args,
                                                       font_path=font_path)
            self.resize(screen_width, screen_height)
            self.show()
        else:
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
            self.showFullScreen()

        self.setCentralWidget(self.tv_widget)

        warning("w=%s h=%s", self.width(), self.height())

    def keyPressEvent(self, event):
        warning("event.key=%s event.text=%s", event.key(), event.text())
        if event.text() in ["q", "Q"]:
            self.tv_widget.abort()
            time.sleep(0.5)
            sys.exit()
        elif event.text() in ["r", "R"]:
            warning("unmaximize window")
            self.setWindowState(Qt.WindowNoState)
            self.resize(500,500)
            self.show()
        elif  event.text() in ["m", "M"]:
            warning("maximize window")
            self.showMaximized()


    #def resizeEvent(self, event):
    #    global display
    #    print("MainWindow resize")
    #    print(f"{self.tv_widget=} {self.testFn=}")
    #    if self.tv_widget and self.testFn:
    #        asyncio.ensure_future(self.delayedTest())

window = None
def create(args, display_string=None, hardware_config_filename=None, font_path=["fonts"]):
    global display, window

    if not display:
        window = MainWindow(args, display_string, hardware_config_filename, font_path, test=False)

        display = window.tv_widget
        display.start_display()
        display.hardware_config = None

    return display
