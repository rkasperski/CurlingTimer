import time
import asyncio
import re

from FancyText import BaseFont, FancyText, FancyTextSegment

def neverIdle():
    return False

class BaseDisplay:
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
    
    def __init__(self):
        self.setColours()
        self.colourCache = {}
        self.isIdle = lambda : False
        self.fontId = 0
        self.lastDisplay = ""
        self.firstTime = True
        self.splashColour = None
        self.sequenceNumber = 0
        self.breakTimes = []
        
        self.scrollDelay = 0.0500
        self.scrollAmt = 1

        self.setColours()
        self.colourCache = {}
        self.isIdle = neverIdle
        self.hardwareConfig = None
        
        self.pos = 1
        self.mirrored = False

        self.leadingOneAdjust = (0, 0)
        self.colonAdjust = (0, 0)

        self.white = (255, 255, 255)
        self.sofWhite = (180, 180, 180)

    def getColours(self):
        return list(self.colours.items())
        
    def setColours(self, colours=None):
        self.colourCache = {}

        self.colours = {}
        if colours is not None:
            for n, rgb in colours:
                self.colours[re.sub("\W*", "", n.lower())] = rgb
                
        for n, rgb in self.requiredColours:
            if n not in self.colours:
                self.colours[n] = rgb

        
    def abort(self):
        self.sequenceNumber += 1

    def setIsIdle(self, isIdle):
        self.isIdle = isIdle


    def competitionUpdate(self, displayTime1 , colour1, displayTime2, colour2):
        self.sequenceNumber += 1
        
        curDisplay = f"{colour1}:{displayTime1}:{colour2}:{displayTime2}"

        if self.lastDisplay == curDisplay:
            return

        self.lastDisplay = curDisplay

        drawable = self.getClearedDrawable()

        w1, h1 = self.twoTimeFont.getSize(displayTime1)
        w2, h2 = self.twoTimeFont.getSize(displayTime2)

        wmax = max(w1, w2)
        xoffset = int((self.width - wmax) / 2)
        xend = xoffset + wmax

        drawable.drawText(self.twoTimeFont, xend - w1, self.height * 0.45, displayTime1, colour1)
        drawable.drawText(self.twoTimeFont, xend - w2, self.height * 0.95, displayTime2, colour2)

        self.show(drawable)

    async def displayTeamNames(self, team1, colour1, team2, colour2, scrollTeamsSeparator=None):
        if scrollTeamsSeparator:
            separatorColour = self.mapColour("white") if colour1 != colour2 else self.mapColour("yellow")
            ft = FancyText(self.width,
                           FancyTextSegment(team1, self.textFont, self.mapColour(colour1)),
                           FancyTextSegment(f" {scrollTeamsSeparator} ", self.twoLineFont, separatorColour),
                           FancyTextSegment(team2, self.textFont, self.mapColour(colour2)))
            return await self.displayScrollingText(ft)
        else:
            return await self.twoLineText(team1, team2, colour1=colour1, colour2=colour2, centre=True)

    def setSplashColour(self, colour="white"):
        self.sequenceNumber += 1
        self.splashColour = self.colours.get(colour, (255, 255, 255)) if isinstance(colour, str) else colour

    def splashColour(self, colour=None):
        if colour is None:
            colour = "white" if self.splashColour is None else self.splashColour
            
        colour = self.mapColour(colour)

        self.sequenceNumber += 1

        drawable = self.getClearedDrawable()
        drawable.drawRect(0, 0 , self.width, self.height, fillColour=colour)
        self.show(drawable)

    def updateTimer(self, displayTime, colour, prefix, showTenths=False):
        curDisplay = prefix + displayTime

        if self.lastDisplay == curDisplay:
            return

        self.lastDisplay = curDisplay

        font = self.timerFont

        drawable = self.getClearedDrawable()

        if showTenths:
            displayTime, tenths = displayTime.rsplit(".", 1)
            y = font.ascender
        else:
            y = font.ascender + int((self.height - font.ascender) / 2)

        adjustment = self.leadingOneAdjust if displayTime[0] == "1" else (0, 0)

        colonAdjustment = sum(self.colonAdjust) * displayTime.count(":")

        widthT, heightT = font.getSize(displayTime)

        widthT -= sum(adjustment) + colonAdjustment
        pos = max(0, int((self.width - widthT) / 2)) - 1

        for c in displayTime:
            if c == ":":
                adjustment = self.colonAdjust

            pos -= adjustment[0]

            drawable.drawText(font, pos, y, c, colour)
            cwidth = self.timerFont.getSize(c)[0]
            pos += cwidth - adjustment[1]

            adjustment = (0, 0)

        if showTenths:
            szSeconds = self.secondsFont.getSize(tenths)
            
            drawable.drawText(self.secondsFont, pos - szSeconds[0] - int((cwidth - szSeconds[0])/ 2), y +  self.secondsFont.ascender, tenths, colour)

        self.show(drawable)

    async def displayScrollingText(self, my_text, colour="white", startTime=None, twoLineOK=False, displayTime=0):
        canvasWidth = self.width
        textColour = self.mapColour(colour)

        if twoLineOK and isinstance(my_text, str):
            sp = my_text.split(" ")
            if len(sp) == 2:
                textLen0, textHeight0 = self.twoLineFont.getSize(sp[0])
                textLen1, textHeight1 = self.twoLineFont.getSize(sp[1])
                if textLen0 < canvasWidth and textLen1 < canvasWidth:
                    return await self.twoLineText(sp[0], sp[1], colour=textColour, centre=True,
                                                  displayTime=displayTime, startTime=startTime)

        self.sequenceNumber += 1

        if isinstance(my_text, str):
            ft = FancyText(self.width, FancyTextSegment(my_text.strip(), self.textFont, textColour))
        else:
            ft = my_text
            
        self.lastDisplay = ft.signature()
        
        lengthT, heightT = ft.getSize()

        yOffset = int((self.height - heightT) / 2)

        curSequenceNumber = self.sequenceNumber
        if not startTime:
            startTime = time.monotonic()

        endTime = startTime + displayTime

        drawable = self.getClearedDrawable()
        if lengthT < canvasWidth:
            ft.draw(drawable, (int((canvasWidth - lengthT) / 2), yOffset))
            self.show(drawable)

            while curSequenceNumber == self.sequenceNumber and not self.isIdle():
                if displayTime and time.monotonic() >= endTime:
                    return True

                await asyncio.sleep(0.005)

            return False

        scrollLength = lengthT + canvasWidth
        sCnt = 1

        while curSequenceNumber == self.sequenceNumber and not self.isIdle():
            nextTime = startTime + self.scrollDelay * sCnt

            curTime = time.monotonic()
            if displayTime and  curTime > endTime:
                return True

            sCnt += 1
            tDiff = int((time.monotonic() - startTime) * self.scrollAmt / self.scrollDelay) % scrollLength

            drawable.start(clear=True)
            ft.draw(drawable, (-tDiff + canvasWidth, yOffset))
            self.show(drawable)

            while time.monotonic() < nextTime and curSequenceNumber == self.sequenceNumber:
                await asyncio.sleep(0.005)

        return False

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
                    drawable = self.getClearedDrawable()
                    self.show(drawable)

            await asyncio.sleep(0.05)        

    def blank(self):
        self.sequenceNumber += 1
        self.lastDisplay = "blank:"
        drawable = self.getClearedDrawable()
        self.show(drawable)
        return 0.25

    def findFont(self, textList, fontList):
        for f in fontList:
            fits = True
            for l in textList:
                textLen, textHeight = f.getSize(l)
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

        textColour = self.mapColour(colour)

        if '\n' in text:
            lines = text.split('\n', 1)
        else:
            lines = [text]

        displayFont = self.findFont(lines, [self.timerFont, self.textFont, self.smallFont])

        if displayFont == self.smallFont and len(lines) == 1:
            width = 0
            for i in range(len(text)):
                textLen, textHeight = displayFont.getSize(text[0: i])
                if textLen > self.width:
                    lines = [text[0:i - 1], text[i - 1:]]
                    break

        drawable = self.getClearedDrawable()
        vpos = 0
        for text in lines:
            textLen, textHeight = displayFont.getSize(text)
            vpos += displayFont.height
            if centre:
                hpos = int(max(0, (self.width - textLen) / 2))
            else:
                hpos = 0

            drawable.drawText(displayFont, hpos, vpos, text, textColour)

        self.show(drawable)

    async def twoLineText(self, line1, line2, colour=None, colour1="white", colour2="white", centre=False, startTime=None, displayTime=0, scroll=True):
        self.sequenceNumber += 1

        colour1 = (colour1 if colour1 else colour).lower()
        colour2 = (colour2 if colour2 else colour).lower()

        curDisplay = "twoline:" + line1 + "\n" + line2 + "\n" + colour1 + "\n" + colour2

        self.lastDisplay = curDisplay
            
        line1 = line1.rstrip()
        line2 = line2.rstrip()

        c1 = self.mapColour(colour1)
        c2 = self.mapColour(colour2)

        pos = self.width
        twoLineFont = self.twoLineFont
        len1, height1 = twoLineFont.getSize(line1)
        len2, height2 = twoLineFont.getSize(line2)

        curSequenceNumber = self.sequenceNumber
        if not startTime:
            startTime = time.monotonic()

        endTime = startTime + displayTime

        if (not scroll) or (len1 < pos and len2 < pos):
            drawable = self.getClearedDrawable()
            centre1 = int((self.width - len1) / 2) if centre else 0
            centre2 = int((self.width - len2) / 2) if centre else 0
            drawable.drawText(twoLineFont, centre1, self.height * 0.38 , line1, c1)
            drawable.drawText(twoLineFont, centre2, self.height * 0.88, line2, c2)
            self.show(drawable)

            while curSequenceNumber == self.sequenceNumber and not self.isIdle():
                await asyncio.sleep(0.005)
                if displayTime and time.monotonic() >= endTime:
                    return True

            return False

        pos = self.width
        maxLen = max(len1, len2)
        sCnt = 1
        scrollLength = max(len1, len2) + self.width

        drawable = self.getDrawable()
        while curSequenceNumber == self.sequenceNumber and not self.isIdle():
            nextTime = startTime + self.scrollDelay * sCnt
            curTime = time.monotonic()

            if displayTime and curTime > endTime:
                return

            sCnt += 1
            tDiff = int(sCnt * self.scrollAmt) % scrollLength

            drawXPos = -tDiff + self.width

            drawable.start(clear=True)
            drawable.drawText(twoLineFont, drawXPos, self.height * 0.38, line1, c1)
            drawable.drawText(twoLineFont, drawXPos, self.height * 0.88, line2, c2)
            self.show(drawable)

            while time.monotonic() < nextTime and curSequenceNumber == self.sequenceNumber:
                await asyncio.sleep(0.005)

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
            drawable = self.getClearedDrawable()

            if len(self.breakTimes) == 0:
                drawable.drawText(self.twoLineFont, int(self.width * 0.45), int(self.height * 0.5), "...", "white")
                curDisplay += "..."
            else:
                ypos = self.height * 0.47
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

                    drawable.drawText(self.twoLineFont, 0, ypos, txt, c)
                    curDisplay += str(c) + ":" + txt
                    ypos = self.height * 0.97

            self.lastDisplay = curDisplay
            self.show(drawable)

            return 5

            if self.lastDisplay == curDisplay:
                return 0.01

        except Exception as e:
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

        colour = self.mapColour(colour)

        drawable = self.getClearedDrawable()

        width = self.clockFont.getSize(displayTime)[0] - len(displayTime) + 1

        startPos = (self.width - width) / 2 - 1

        drawable.drawText(self.clockFont, startPos, self.clockFont.height - self.clockFont.descender, displayTime, colour)

        seconds = ("0" + str(localTime.tm_sec))[-2:] 
        if showTenths:
            seconds += '.' + str(tenths)

        szSeconds = self.secondsFont.getSize(seconds)

        drawable.drawText(self.secondsFont, startPos + width - szSeconds[0] + 1, self.clockFont.ascender + self.secondsFont.ascender, seconds, colour)

        self.show(drawable)
        return 0.05
        
