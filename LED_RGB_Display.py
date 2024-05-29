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

sections = ["Hardware"]

display = None

fontId = 0
Font = namedtuple("Font", "name font id size ascender descender height")

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

def inferTextMetrics(f):
    ss = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRTSUVWXYZ"

    bbox = f.getbbox(ss, anchor='ls')
    ascender = -bbox[1]
    descender = bbox[3]
    return (ascender, descender)


def loadFont(name, fontFileName, default=True, fontPathList=[]):
    global fontId
    
    fontId += 1
    
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
            debug("pillow: %s loading font: %s(%d) size=%d", name, fontPath, fontId, size)
            if fontPath.lower().endswith(".ttf"):
                font = ImageFont.truetype(fontPath, size=size)
            else:
                font = ImageFont.load(fontPath)

            ascender, descender = inferTextMetrics(font)
            info("pillow: %s loaded font: %s(%d) size=%d ascender=%s descender=%s", name, fontPath, fontId, size, ascender, descender)
            return Font(name, font, fontId, size, ascender, descender, ascender + descender)

        error("pillow: %s font not found: %s", name, fontPath)
            
    if default:
        warning("pillow: %s loading default font for: %s", name, fontFileName)
        return Font(name, ImageFont.load_default(), fontId, 12, 0, 0, -4, 0, 12)
        
    return None


def getsize(f, s):
    bbox = f.font.getbbox(s, anchor='ls')
    return (bbox[2] - bbox[0], bbox[3] - bbox[1])


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
                drawable.text((x, y), c, font=self.font.font, fill=self.colour, anchor=anchor)

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

    
class SampleBase(object):
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
        
    def parseArgs(self):
        if not self.args:
            self.args = self.parser.parse_args()
            
        return self.args
        
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
        return True
    

class ClockTimerDisplaySingleton(SampleBase):
    def __init__(self, args, displayString=None, hardwareConfigFN=None, fontPath=["fonts"]):
        super().__init__(hardwareConfigFN=hardwareConfigFN)

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

        self.scrollingText = displayString if displayString else "Welcome"

        self.nextBlankTime = None
        self.lastInteractionTime = time.monotonic()
        self.lastInteractionResetter = "main"
        self.mirrored = False
        self.scrollDelay = 0.050

        self.setColours()
        self.colourCache = {}
        self.blankTime = 300

    def clearDrawable(self):
        self.drawable.rectangle((0, 0, self.width, self.height), fill=(0, 0, 0, 0))

    def resetIdleTime(self, activeUntil=None):
        self.nextBlankTime = activeUntil
        self.lastInteractionTime = time.monotonic()
        self.lastInteractionResetter = sys._getframe().f_back.f_code.co_name

    def forceIdle(self):
        self.lastInteractionTime = 0
        
    def adjustIdleTime(self, amt):
        self.lastInteractionTime += amt

    def getIdleTime(self):
        return time.monotonic() - self.lastInteractionTime

    def getIdleResetter(self):
        return self.lastInteractionResetter

    def _colour(self, c):
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

    def setBlankTime(self, blankTime):
        self.blankTime = blankTime
            
    def isIdle(self):
        curTime = time.monotonic()
        if self.nextBlankTime:
            if self.nextBlankTime >= curTime:
                return False

            self.nextBlankTime = None

        idle = self.lastInteractionTime + self.blankTime < curTime
        return idle
        
    def process(self):
        if self.initMatrix():
            self.offscreen_canvas = self.matrix.CreateFrameCanvas()

            self.width = self.offscreen_canvas.width
            self.height = self.offscreen_canvas.height

            self.timerFont = loadFont("Timer", self.args.timer_font, fontPathList=self.fontPath)
            self.smallFont = loadFont("Small", self.args.small_font, fontPathList=self.fontPath)
            self.twoLineFont = loadFont("TwoLine", self.args.twoline_font, fontPathList=self.fontPath)
            self.twoTimeFont = loadFont("TwoTime", self.args.twotime_font, fontPathList=self.fontPath)
            self.clockFont = loadFont("Clock", self.args.clock_font, fontPathList=self.fontPath)
            self.secondsFont = loadFont("Seconds", self.args.seconds_font, fontPathList=self.fontPath)
            self.textFont = loadFont("Text", self.args.text_font, fontPathList=self.fontPath)

            self.offscreen_canvas = self.matrix.CreateFrameCanvas()

            self.white = (255, 255, 255)
            self.sofWhite = (180, 180, 180)
            self.pos = 1
            self.mirrored = self.args.mirrored
            if self.mirrored:
                self.width = int(self.width / 2)

        self.welcomeMessage = self.scrollingText
        self.lastDisplay = ""

        self.firstTime = True

        self.scrollingTextColour = "white"

        self._splashColour = None

        self.sequenceNumber = 0

        if self.args.start_message is not None:
            self.scrollingText = self.args.start_message

        self.breakTimes = []
        self.drawableImage = Image.new("RGB", (self.width, self.height))
        self.drawable = ImageDraw.Draw(self.drawableImage)
        self.drawable.fontmode = "1"
        
    def abort(self):
        self.sequenceNumber += 1
        
    def setScrollingText(self, text, colour="white"):
        self.scrollingText = text.rstrip()
        self.scrollingTextColour = colour
        self.sequenceNumber += 1

    def setFlashText(self, text, colour="white"):
        self.flashText = text
        self.flashTextColour = colour
        self.sequenceNumber += 1

    def competitionUpdate(self, competition):
        self.sequenceNumber += 1
        
        teams = competition.teams
        displayTime1 = str(teams[0])
        displayTime2 = str(teams[1])
        curDisplay = teams[competition.activeTeam].scoreboardColour + ":" + displayTime1 + ":" + displayTime2

        if self.lastDisplay == curDisplay:
            return

        self.lastDisplay = curDisplay

        self.clearDrawable()

        w1 = self.twoTimeFont.font.getlength(displayTime1)
        w2 = self.twoTimeFont.font.getlength(displayTime2)
        wmax = max(w1, w2)
        xoffset = int((self.width - wmax) / 2)
        xend = xoffset + wmax
        self.drawable.text((xend - w1, 0), displayTime1, font=self.twoTimeFont.font, fill=self._colour(teams[0].scoreboardColour.lower()), anchor="lt")
        self.drawable.text((xend - w2, self.height), displayTime2, font=self.twoTimeFont.font, fill=self._colour(teams[1].scoreboardColour.lower()), anchor="lb")
        self.swapCanvas()

    async def displayTeamNames(self, teams, scrollTeamsSeparator):
        if scrollTeamsSeparator:
            separatorColour = self._colour("white") if teams[0].colour != teams[1].colour else self._colour("yellow")
            ft = FancyText(self.width,
                           FancyTextSegment(teams[0].name, self.textFont, self._colour(teams[0].colour)),
                           FancyTextSegment(f" {scrollTeamsSeparator} ", self.twoLineFont, separatorColour, vertical="middle"),
                           FancyTextSegment(teams[1].name, self.textFont, self._colour(teams[1].colour)))
            await self.displayScrollingText(ft)
        else:
            await self.twoLineText(teams[0].name, teams[1].name, colour1=teams[0].colour, colour2=teams[1].colour, centre=True)

    def setSplashColour(self, colour="white"):
        self.sequenceNumber += 1
        self._splashColour = self.colours.get(colour, (255, 255, 255)) if isinstance(colour, str) else colour

    def splashColour(self, colour=None):
        if colour is None:
            colour = "white" if self._splashColour is None else self._splashColour
            
        colour = self.colours.get(colour, (255, 255, 255)) if isinstance(colour, str) else colour

        self.clearDrawable()
        self.sequenceNumber += 1

        clr = (colour[0], colour[1], colour[2])

        top = 4
        h = self.height - 2 * top
        w = h

        left = (self.width - w) / 2
        for t in range(top, h + top):
            self.drawable.line((left, t, (left + w), t), clr)
        
        self.swapCanvas()

    def updateTimer(self, displayTime, colour, prefix):
        curDisplay = prefix + displayTime

        if self.lastDisplay == curDisplay:
            return

        self.lastDisplay = curDisplay

        widthT, heightT = getsize(self.timerFont, displayTime)
        self.clearDrawable()
        pos = max(0, int((self.width - (widthT - len(displayTime) - 2)) / 2))
        firstChar = True
        for c in displayTime:
            if c == ":":
                pos -= 2

            xAdjust = 1 if firstChar and c == "1" else 0
            self.drawable.text((pos + xAdjust, self.height / 2), c, font=self.timerFont.font, fill=colour, anchor="lm")
            pos += self.timerFont.font.getlength(c) - 1
            firstChar = False
            
            if c == ":":
                pos -= 1
                firstChar = True

        self.swapCanvas()

    def countDownUpdate(self, timer):
        self.sequenceNumber += 1

        displayTime = str(timer)
        self.updateTimer(displayTime, self.white, "cdt:")
        return 0.005

    def elapsedTimeUpdate(self, timer):
        self.sequenceNumber += 1

        t = timer.parts()

        displayTime = timer.format(t)

        self.updateTimer(displayTime, self.white, "elt:")
        return 0.005

    def swapCanvas(self):
        self.offscreen_canvas.SetImage(self.drawableImage)
        
        if self.mirrored:
            self.offscreen_canvas.SetImage(self.drawableImage, self.width)
        
        self.offscreen_canvas = self.matrix.SwapOnVSync(self.offscreen_canvas)

    def intermissionUpdate(self, timer):
        self.displayText(str(timer).strip(), "white")
        return 0.005

    def timeoutUpdate(self, timer):
        self.displayText(str(timer).strip(), self.timeout.colour)
        return 0.005

    async def displayScrollingText(self, my_text, colour="white", startTime=None, twoLineOK=False, displayTime=0):
        canvasWidth = self.width
        textColour = self._colour(colour)

        if twoLineOK and isinstance(my_text, str):
            sp = my_text.split(" ")
            if len(sp) == 2:
                if self.twoLineFont.font.getlength(sp[0]) < canvasWidth and self.twoLineFont.font.getlength(sp[1]) < canvasWidth:
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

            self.clearDrawable()
            ft.draw(self.drawable, (int((canvasWidth - lengthT) / 2), yOffset))
            self.swapCanvas()
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
            tDiff = int((time.monotonic() - startTime) / self.scrollDelay) % scrollLength
            
            self.clearDrawable()
            ft.draw(self.drawable, (-tDiff + canvasWidth, yOffset))

            self.swapCanvas()

            await asyncio.sleep(0.005)
            while time.monotonic() < nextTime and curSequenceNumber == self.sequenceNumber:
                await asyncio.sleep(0.005)

    async def displayFlashText(self, my_text, delay=0.5, displayCount=1, colour="white", length=5.0):
        self.sequenceNumber += 1

        my_text = my_text.rstrip()
        self.lastDisplay = "ft:" + my_text
        textColour = self._colour(colour if colour else "white")

        curSequenceNumber = self.sequenceNumber
        display = True
        displayFont = self.smallFont

        for f in [self.textFont, self.twoLineFont, self.smallFont]:
            textLen, textHeight = getsize(f, my_text)
            if textLen <= self.width:
                displayFont = f
                break

        textLen, textHeight = getsize(displayFont, my_text)
        lines = [[my_text, textLen, 0]]
        if textLen > self.width:
            width = 0
            for i in range(len(my_text)):
                cw = displayFont.font.getlength(my_text[i])
                if width > self.width:
                    ll = [my_text[0:i], my_text[i:]]
                    lines = [[ll[0], displayFont.font.getlength(ll[0]), 0],
                             [ll[1], displayFont.font.getlength(ll[1]), 16]]
                    break
                width += cw

        startTime = time.monotonic()
        while displayCount > 0 and curSequenceNumber == self.sequenceNumber and not self.isIdle():
            curTime = time.monotonic()
            self.clearDrawable()
            if display:
                for text, textLen, vpos in lines:
                    hpos = int(max(0, (self.width - textLen) / 2))
                    self.drawable.text((hpos, vpos), text, font=displayFont.font, fill=textColour, anchor="lt")

            self.swapCanvas()
            display = (time.monotonic() - startTime) > length or not display

            diffTime = time.monotonic() - curTime
            await asyncio.sleep(max(delay - diffTime, 5))

    def blank(self):
        self.sequenceNumber += 1
        self.lastDisplay = "blank:"
        self.clearDrawable()
        self.swapCanvas()
        return 0.25

    def displayText(self, text, colour="white"):
        text = text.rstrip()
        self.sequenceNumber += 1

        self.lastDisplay = "dt:" + text
        textColour = self._colour(colour)

        displayFont = self.smallFont

        for f in [self.timerFont, self.textFont, self.twoLineFont, self.smallFont]:
            textLen, textHeight = getsize(f, text)
            if textLen <= self.width:
                displayFont = f
                break

        textLen, textHeight = getsize(displayFont, text)

        if displayFont == self.twoLineFont and textLen > self.width:
            for i in range(len(text)):
                first = text[0:i]
                width = displayFont.font.getlength(first)
                if width > self.width:
                    first = text[0:i-1]
                    second = text[i-1:]
                    lines = [[first, displayFont.font.getlength(first), 0, "lt"],
                             [second, displayFont.font.getlength(second), self.height, "lb"]]
                    break
        else:
            lines = [[text, textLen, int((self.height) / 2), "lm"]]

        self.clearDrawable()
        for text, textLen, vpos, anchor in lines:
            hpos = int(max(0, (self.width - textLen) / 2))
            self.drawable.text((hpos, vpos), text, fill=textColour, font=displayFont.font, anchor=anchor)

        self.swapCanvas()

    async def twoLineText(self, line1, line2, colour=None, colour1="white", colour2="white", centre=False, endTime=None):
        self.sequenceNumber += 1

        line1 = line1.rstrip()
        line2 = line2.rstrip()

        self.clearDrawable()

        colour1 = (colour if colour else colour1).lower()
        colour2 = (colour if colour else colour2).lower()

        c1 = self._colour(colour1)
        c2 = self._colour(colour2)

        pos = self.width
        twoLineFont = self.twoLineFont
        len1, height1 = getsize(twoLineFont, line1)
        len2 = twoLineFont.font.getlength(line2)
        
        if len1 < pos and len2 < pos:
            curDisplay = "twoline:" + line1 + "\n" + line2 + "\n" + colour1 + "\n" + colour2

            if self.lastDisplay == curDisplay:
                return

            self.lastDisplay = curDisplay
            
            self.clearDrawable()

            centre1 = int((self.width - len1) / 2) if centre else 0
            centre2 = int((self.width - len2) / 2) if centre else 0
            self.drawable.text((centre1, 0), line1, font=twoLineFont.font, spacing=0, fill=c1, anchor="lt")
            self.drawable.text((centre2, self.height), line2, font=twoLineFont.font, spacing=0, fill=c2, anchor="lb")
            self.swapCanvas()
            return

        curSequenceNumber = self.sequenceNumber

        pos = self.width
        maxLen = max(len1, len2)
        while curSequenceNumber == self.sequenceNumber and not self.isIdle():
            curTime = time.monotonic()
            if endTime:
                if curTime > endTime:
                    return

            self.clearDrawable()
            self.drawable.text((pos, 0), line1, font=twoLineFont.font, spacing=0, fill=c1, anchor="lt")
            
            self.drawable.text((pos, self.height), line2, font=twoLineFont.font, spacing=0, fill=c2, anchor="lb")
            pos -= 1
            if pos + maxLen < 0:
                pos = self.width
                continue

            self.swapCanvas()
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
            self.clearDrawable()
            if len(self.breakTimes) == 0:
                self.drawable.text((8, 16), "...", font=self.twoTimeFont.font, fill=(255, 255, 255))
                curDisplay += "..."
            else:
                ypos, anchor = 0, "lt"
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

                    self.drawable.text((0, ypos), txt, font=self.twoTimeFont.font, fill=self._colour(c), anchor=anchor)
                    curDisplay += str(c) + ":" + txt
                    ypos, anchor = self.height, "lb"

            self.lastDisplay = curDisplay
            self.swapCanvas()
            
            if self.lastDisplay == curDisplay:
                return 0.005

        except Exception as e:
            error("timerdisplay: displayBreakTimes exception=%s", e, exc_info=True)

        return 0.005
        
    def clockUpdate(self, showTenths=False):
        self.sequenceNumber += 1

        curTime = time.time()
        localTime = time.localtime(curTime)
        tenths = (int(curTime * 10) % 10) if showTenths else 0
        displayTime = time.strftime("%H:%M", localTime)
        colour = self.white

        curDisplay = f"localTime:{localTime}.{tenths}"

        if self.lastDisplay == curDisplay:
            return

        self.lastDisplay = curDisplay

        self.clearDrawable()
        pos = -1

        for offset, c in enumerate(displayTime):
            self.drawable.text((pos - offset, 0), c, font=self.clockFont.font, fill=colour, anchor="lt")
            tWidth, tHeight = getsize(self.clockFont, c)
            pos += tWidth

        if showTenths:
            self.drawable.text((38, self.height), ("0" + str(localTime.tm_sec))[-2:] + '.' + str(tenths), font=self.secondsFont.font, fill=colour, anchor="lb")

        else:
            self.drawable.text((50, self.height), ("0" + str(localTime.tm_sec))[-2:], font=self.secondsFont.font, fill=colour, anchor="lb")

        self.swapCanvas()
        return 0.005

    
def create(args, displayString=None, hardwareConfigFN=None, fontPath=["fonts"]):
    global display

    if not display:
        display = ClockTimerDisplaySingleton(args, displayString=displayString, hardwareConfigFN=hardwareConfigFN, fontPath=fontPath)

    return display
    
