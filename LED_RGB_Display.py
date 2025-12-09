from Logger import error, warning, info, debug
import asyncio
import os
import time
import re
import sys
from collections import namedtuple

from rgbmatrix import RGBMatrix, RGBMatrixOptions

import argparse
import Hardware

from PIL import Image, ImageDraw, ImageFont

from AutoConfigParser import AutoConfigParser
from BaseDisplay import BaseDisplay
from FancyText import BaseFont

sections = ["Hardware"]

display = None

class Font(BaseFont):
    def __init__(self, name, font, id, size):
        ss = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRTSUVWXYZ"

        bbox = font.getbbox(ss, anchor='ls')
        ascender = -bbox[1]
        descender = bbox[3]
        
        super().__init__(name, font, id, size, ascender, descender, ascender + descender)

    def  getSize(self, text):
        bbox = self.font.getbbox(text, anchor='ls')
        return (bbox[2] - bbox[0], bbox[3] - bbox[1])

class Drawable:
    def __init__(self, canvas, owner):
        self.canvas = canvas
        self.owner = owner
        smallest_dimension = min(owner.width, owner.height)
        self.width = owner.width
        self.height = owner.height
        self.visible_pixel_dimension = int(smallest_dimension / 16)
        self.visible_pixels = (int(self.width / self.visible_pixel_dimension), int(self.height / self.visible_pixel_dimension))

    def start(self, clear=False):
        self.drawable = ImageDraw.Draw(self.canvas)
        self.drawable.fontmode = "1"
        
        if clear:
            self.clear()

        return self.drawable

    def clear(self):
        self.drawable.rectangle((0, 0, self.width, self.height), fill=self.owner.mapColour("black"))

    def end(self):
        self.drawable = None

    def show(self):
        if self.drawable:
            self.end()

        self.owner.show(self)

    def fill(self, colour):
        self.drawable.rectangle((0, 0, self.width, self.height), fill=self.owner.mapColour(colour))

    def drawPoint(self, x, y, colour=None):
        pd = self.visible_pixel_dimension

        colour = self.owner.mapColour(colour) if colour else None
        self.drawable.rectangle((x, y, x + pd - 1, y + pd - 1), fill=colour)

    def drawRect(self, x, y, width, height, fillColour=None, borderColour=None, borderWidth=0):
        borderColour = self.owner.mapColour(borderColour) if borderColour else None
        fillColour = self.owner.mapColour(fillColour) if fillColour else None
        self.drawable.rectangle((x, y, x + width, y + height),  width=borderWidth, outline=borderColour, fill=fillColour)

    def drawCircle(self, x, y, radius=5, fillColour=None, borderColour=None, borderWidth=0):
        borderColour = self.owner.mapColour(borderColour) if borderColour else None
        fillColour = self.owner.mapColour(fillColour) if fillColour else None
        self.drawable.circle((x, y), radius, width=borderWidth, outline=borderColour, fill=fillColour)

    def drawPolygon(self, pts, fillColour=None, borderColour=None, borderWidth=0):
        borderColour = self.owner.mapColour(borderColour) if borderColour else None
        fillColour = self.owner.mapColour(fillColour) if fillColour else None

        self.drawable.polygon(pts,  width=borderWidth, outline=borderColour, fill=fillColour)

    def drawText(self, font, x, y , text, colour):
        colour = self.owner.mapColour(colour)

        self.drawable.text((x, y), text, font=font.font, fill=colour, anchor="ls");

class SampleBase:
    def __init__(self, hardwareConfigFN=None):
        if not hardwareConfigFN:
            hardwareConfigFN = "hardware.toml"
            
        hardwareConfigFile = AutoConfigParser(sections=sections, filename=hardwareConfigFN)
        hardwareConfig = Hardware.HardwareConfigSection(hardwareConfigFile)
        hardwareConfigFile.hardware = hardwareConfig

        self.hardwareConfig = hardwareConfigFile

        self.parser = argparse.ArgumentParser()
        self.matrix = None
        self.args = None

        self.parser.add_argument("-r", "--led-rows", action="store", help="Display rows. 16 for 16x32, 32 for 32x32. Default: 32", default=hardwareConfig.rows, type=int)
        self.parser.add_argument("--led-cols", action="store", help="Panel columns. Typically 32 or 64. (Default: 32)", default=hardwareConfig.cols, type=int)
        self.parser.add_argument("-c", "--led-chain", action="store", help="Daisy-chained boards. Default: 1.", default=hardwareConfig.chain, type=int)
        self.parser.add_argument("-P", "--led-parallel", action="store", help="For Plus-models or RPi2: parallel chains. 1..3. Default: 1", default=hardwareConfig.parallel, type=int)
        self.parser.add_argument("-p", "--led-pwm-bits", action="store", help="Bits used for PWM. Something between 1..11. Default: 11", default=hardwareConfig.pwmBits, type=int)
        self.parser.add_argument("-b", "--led-brightness", action="store", help="Sets brightness level. Default: 100. Range: 1..100", default=hardwareConfig.brightness, type=int)
        self.parser.add_argument("-m", "--led-gpio-mapping", help="Hardware Mapping: regular, adafruit-hat, adafruit-hat-pwm", choices=['regular', 'adafruit-hat', 'adafruit-hat-pwm'], default=hardwareConfig.gpioMapping, type=str)
        self.parser.add_argument("--led-scan-mode", action="store", help="Progressive or interlaced scan. 0 Progressive, 1 Interlaced (default)", default=hardwareConfig.scanMode, choices=range(2), type=int)
        self.parser.add_argument("--led-pwm-lsb-nanoseconds", action="store", help="Base time-unit for the on-time in the lowest significant bit in nanoseconds. Default: 130", default=hardwareConfig.pwmLsbNanoseconds, type=int)
        self.parser.add_argument("--led-show-refresh", action="store_true", help="Shows the current refresh rate of the LED panel", default=hardwareConfig.showRefresh)
        self.parser.add_argument("--led-slowdown-gpio", action="store", help="Slow down writing to GPIO. Range: 1..100. Default: 1", choices=range(5), type=int, default=hardwareConfig.slowdownGpio)
        self.parser.add_argument("--led-no-hardware-pulse", action="store", help="Don't use hardware pin-pulse generation")
        self.parser.add_argument("--led-rgb-sequence", action="store", help="Switch if your matrix has led colors swapped. Default: RGB", default=hardwareConfig.rgbSequence, type=str)
        self.parser.add_argument("--led-pixel-mapper", action="store", help="Apply pixel mappers. e.g \"Rotate:90\"", default=hardwareConfig.pixelMapper, type=str)
        self.parser.add_argument("--led-row-addr-type", action="store", help="0 = default; 1=AB-addressed panels;2=row direct", default=hardwareConfig.rowAddrType, type=int, choices=[0, 1, 2])
        self.parser.add_argument("--led-multiplexing", action="store", help="Multiplexing type: 0=direct; 1=strip; 2=checker; 3=spiral; 4=ZStripe; 5=ZnMirrorZStripe; 6=coreman; 7=Kaler2Scan; 8=ZStripeUneven (Default: 0)", default=hardwareConfig.multiplexing, type=int)
        self.parser.add_argument("--mirrored", help="mirror display", action="store_true", default=hardwareConfig.mirrored)
        
    def initMatrix(self):
        args = self.parseArgs()
        
        options = RGBMatrixOptions()
        options.drop_privileges = 0

        if self.args.led_gpio_mapping is not None:
            options.hardware_mapping = args.led_gpio_mapping
            
        options.rows = args.led_rows
        options.cols = args.led_cols
        options.chain_length = args.led_chain
        options.parallel = args.led_parallel
        options.row_address_type = args.led_row_addr_type
        options.multiplexing = args.led_multiplexing
        options.pwm_bits = args.led_pwm_bits
        options.brightness = args.led_brightness
        options.pwm_lsb_nanoseconds = args.led_pwm_lsb_nanoseconds
        options.led_rgb_sequence = args.led_rgb_sequence
        options.pixel_mapper_config = args.led_pixel_mapper
        
        if args.led_show_refresh:
            options.show_refresh_rate = 1

        if args.led_slowdown_gpio is not None:
            options.gpio_slowdown = args.led_slowdown_gpio
            
        if self.args.led_no_hardware_pulse:
            options.disable_hardware_pulsing = True

        self.matrix = RGBMatrix(options=options)

        debug(f"""{options.drop_privileges=}
{options.hardware_mapping=}
{options.rows=}
{options.cols=}
{options.chain_length=}
{options.parallel=}
{options.row_address_type=}
{options.multiplexing=}
{options.pwm_bits=}
{options.brightness=}
{options.pwm_lsb_nanoseconds=}
{options.led_rgb_sequence=}
{options.pixel_mapper_config=}
{options.show_refresh_rate=}
{options.gpio_slowdown=}
{options.disable_hardware_pulsing=}
""")
        return True
    

class ClockTimerDisplaySingleton(SampleBase, BaseDisplay):
    def __init__(self, args, displayString=None, hardwareConfigFN=None, fontPath=["fonts"]):
        BaseDisplay.__init__(self)
        SampleBase.__init__(self, hardwareConfigFN=hardwareConfigFN)

        self.fontPath = [fontPath] if isinstance(fontPath, str) else fontPath

        # self.parser.set_defaults(led_rows=16, led_cols=32)

        self.parser.add_argument("--twoline-font", action="store", type=str,
                                 help="the twoline font", default="EncodeSansSemiCondensed-Light.ttf:15")
        self.parser.add_argument("--twotime-font", action="store", type=str,
                                 help="the twotime font - should be monospaced",
                                 default="IBMPlexSansCondensed-Light.ttf:21")
        self.parser.add_argument("--timer-font", action="store", type=str,
                                 help="the timer font", default="RobotoCondensed-Light.ttf:26")
        self.parser.add_argument("--small-font", action="store", type=str,
                                 help="the small font", default="RobotoCondensed-Light.ttf:10")
        self.parser.add_argument("--clock-font", action="store", type=str,
                                 help="the clock font", default="RobotoCondensed-Light.ttf:26")
        self.parser.add_argument("--seconds-font", action="store", type=str,
                                 help="the clock seconds font", default="RobotoCondensed-Light.ttf:14")
        self.parser.add_argument("--text-font", action="store", type=str,
                                 help="the text font", default="Lato-Light.ttf:32")

        self.parser.add_argument("--start-message", help="message to display at the start", type=str, default=None)
        self.parser.add_argument("--port", help="start in given port", type=str, default=None)

        self.mirrored = False
        self.leadingOneAdjust = (3, 2)
        self.colonAdjust = (2, 1)

    def parseArgs(self):
        if not self.args:
            self.args = self.parser.parse_args()

        return self.args

    def startDisplay(self):
        if self.initMatrix():
            self.offscreen_canvas = self.matrix.CreateFrameCanvas()

            self.width = self.offscreen_canvas.width
            self.height = self.offscreen_canvas.height

            self.timerFont = self.loadFont("Timer", self.args.timer_font, fontPathList=self.fontPath)
            self.smallFont = self.loadFont("Small", self.args.small_font, fontPathList=self.fontPath)
            self.twoLineFont = self.loadFont("TwoLine", self.args.twoline_font, fontPathList=self.fontPath)
            self.twoTimeFont = self.loadFont("TwoTime", self.args.twotime_font, fontPathList=self.fontPath)
            self.clockFont = self.loadFont("Clock", self.args.clock_font, fontPathList=self.fontPath)
            self.secondsFont = self.loadFont("Seconds", self.args.seconds_font, fontPathList=self.fontPath)
            self.textFont = self.loadFont("Text", self.args.text_font, fontPathList=self.fontPath)

            self.offscreen_canvas = self.matrix.CreateFrameCanvas()

            self.pos = 1
            self.mirrored = self.args.mirrored
            if self.mirrored:
                self.width = int(self.width / 2)

        self.canvas = Image.new("RGB", (self.width, self.height))
        
    def loadFont(self, name, fontFileName, default=True, fontPathList=[]):
        self.fontId += 1

        sp = fontFileName.split(":")
        fontFileName = sp[0]
        size = 12

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
                    font = ImageFont.truetype(fontPath, size=size)
                else:
                    font = ImageFont.load(fontPath)

                f = Font(name, font, self.fontId, size)
                info("pillow: %s loaded font: %s(%d) size=%d ascender=%s descender=%s height=%s", name, fontPath, self.fontId, f.size, f.ascender, f.descender, f.height)
                return f

        error("pillow: %s font not found: %s", name, fontPath)

        if default:
            warning("pillow: %s loading default font for: %s", name, fontFileName)
            return Font(name, ImageFont.load_default(), self.fontId, 12)

        return None

    def getDrawable(self):
        return Drawable(self.canvas, self)

    def getClearedDrawable(self):
        drawable = Drawable(self.canvas, self)

        drawable.start(clear=True)

        return drawable

    def show(self, drawable):
        self.offscreen_canvas.SetImage(self.canvas)

        if self.mirrored:
            self.offscreen_canvas.SetImage(self.canvas, self.width)

        self.offscreen_canvas = self.matrix.SwapOnVSync(self.offscreen_canvas)

    def mapColour(self, c):
        if isinstance(c, list):
            return c
        elif isinstance(c, str):
            try:
                return self.colourCache[c]
            except KeyError:
                rgb = self.colours.get(c.lower(), (255, 255, 255))
                self.colourCache[c] = rgb
                return rgb
        else:
            return c

    def run(self):
        loop = asyncio.get_event_loop()
        return loop

    
def create(args, displayString=None, hardwareConfigFN=None, fontPath=["fonts"]):
    global display

    if not display:
        display = ClockTimerDisplaySingleton(args, displayString=displayString, hardwareConfigFN=hardwareConfigFN, fontPath=fontPath)

    return display
    
