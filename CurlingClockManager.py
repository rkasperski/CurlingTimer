import sys
from Logger import exception, error, info
import asyncio

import time
import ZeroConfManager
import BreakTimerClient
import ConfigurationManager
import HardwareClock

from Utils import dropRootPrivileges, myIPAddress
from HTTP_Utils import postUrlJSONResponse, CLOCK_HDR
import HTTP_Utils as httpUtils
from CurlingClockTimers import Timers

import Draws
import Kapow

manager = None


class CurlingClockManager:
    def __init__(self, display, config, port=80, tokenAuthenticator=None, user="pi", group="pi"):
        self.displayF = self.startUp
        self.port = port

        self.blankTime = 300
        self.nextBlankTime = None
        self.lastInteractionTime = time.monotonic()
        self.lastInteractionResetter = "main"

        #if self.args.start_message is not None:
        #    self.scrollingText = self.args.start_message

        self.publish(port=port)
        self.breakTimeDataVersion = None
        self.breakTimerDisplayStyle = "raw"
        self.checkSelectedSensorInfo = None
        self.pleaseDropPriviledgesNow = True
        self.kapow = None
        self.display = display
        self.user = user
        self.group = group
        self.config = config
        self.tokenAuthenticator = tokenAuthenticator
        self.displayBreakTimeTracker = BreakTimerClient.DisplayBreakTimeTracker()
        self.drawManager = Draws.createDrawManager()
        self.startTime = time.monotonic()
        self.breakTimeUpdateTime = 0
        self.timers = Timers(self.config.defaults, self.config.sheets.mySheet, self.isIdle)
        self.rockThrowListener = None
        self.welcomeMessage = "welcome unset"
        self.scrollingText = "scrolling unset"
        self.scrollingTextColour = "white"
        self.flashText = "flash unset"
        self.flashTextColour = "white"
        self.white = (255, 255, 255)

    async def startTasks(self, app):
        await ConfigurationManager.startTasks(app)
        await self.drawManager.startTasks(app)

        app['display_text'] = asyncio.create_task(self.updateTask(app))

    async def stopTasks(self, app):
        if self.rockThrowListener:
            await self.rockThrowListener.close()
            
        info("CurlingClockManager: stop tasks - start")
        info("CurlingClockManager: stop tasks - Zero Conf")
        await ZeroConfManager.close()

        info("CurlingClockManager: stop tasks - configuration manager")
        await ConfigurationManager.stopTasks(app)

        info("CurlingClockManager: stop tasks - draw manager")
        await self.drawManager.stopTasks(app)

        info("CurlingClockManager: stop tasks - display manager")
        app['display_text'].cancel()
        await app['display_text']
        info("CurlingClockManager: stop tasks - done")

    def setColours(self, colours):
        self.display.setColours(colours)

    def getColours(self):
        return self.display.getColours()

    def isIdle(self):
        curTime = time.monotonic()
        if self.nextBlankTime:
            if self.nextBlankTime >= curTime:
                return False

            self.nextBlankTime = None

        idle = self.lastInteractionTime + self.blankTime < curTime
        return idle

    def setBlankTime(self, blankTime):
        self.blankTime = blankTime

    def resetIdleTime(self, activeUntil=None):
        self.nextBlankTime = activeUntil
        self.lastInteractionTime = time.monotonic()
        self.lastInteractionResetter = sys._getframe().f_back.f_code.co_name

    def adjustIdleTime(self, amt):
        self.lastInteractionTime += amt

    def forceIdle(self):
        self.lastInteractionTime = 0

    def getIdleTime(self):
        return time.monotonic() - self.lastInteractionTime

    def getIdleResetter(self):
        return self.lastInteractionResetter

    def publish(self, port=80):
        ZeroConfManager.publish("_clockdisplay._tcp.local.", port)

    def getView(self):
        return self.displayF

    def setView(self, func):
        oldView = self.displayF
        self.displayF = func

        self.abort()
        #info("set view=%s", self.displayF, stack_info=True)
        info("set view=%s", self.displayF)

        return oldView

    def abort(self):
        self.display.abort()

    def registerRockThrowListener(self, listener):
        self.rockThrowListener = listener

    def setKapow(self, name):
        if name not in Kapow.registered:
            name = "life"

        self.kapow = Kapow.registered[name](self.display.drawableImage)
        self.setView(self.kapowNext)

    async def kapowNext(self):
        delay = self.kapow.next()
        self.display.swapCanvas()
        return delay

    def isActive(self):
        return self.display.isActive()

    def setFlashText(self, text, colour="white"):
        self.flashText = text.strip()
        self.flashTextColour = colour
        
    def setScrollingText(self, text, colour="white"):
        self.scrollingText = text.rstrip()
        self.scrollingTextColour = colour

    async def startUp(self):
        hostIp = myIPAddress()

        mySheet = self.config.sheets.mySheet
        self.setView(self.displayScrollingText)
        self.resetIdleTime()

        if mySheet and mySheet.ip == hostIp:
            if hostIp == self.config.rink.clockServer:
                self.config.rink.batteryAlert = not HardwareClock.hasHardwareClock

            if self.config.server.setup == 0:
                if self.config.server.isDefaultSecretKey():
                    self.setScrollingText("setup: secretkey")
                else:
                    self.setScrollingText("setup: sheets")

                activeUntil = 300*60 + time.monotonic()
                self.resetIdleTime(activeUntil)

            elif self.config.rink.batteryAlert:
                if hostIp == self.config.rink.clockServer:
                    info("CurlingClockManager - clock - my battery is low")
                else:
                    info("CurlingClockManager - clock - Check battery on %s", self.config.rink.clockServer)
                    
                self.setScrollingText(f"Check battery on {self.config.rink.clockServer}")
                activeUntil = 30 + time.monotonic()
                self.resetIdleTime(activeUntil)
            else:
                self.setScrollingText(self.welcomeMessage)

            if self.config.defaults.ipOnStart:
                self.setView(self.showIpAtStart)
        else:
            self.setScrollingText(f"{hostIp}:{self.port}", colour="red")

    async def competitionUpdate(self):
        competition = self.timers.competition
        if competition.active():
            self.resetIdleTime()

        teams = competition.teams
        if self.config.defaults.largeActiveTeamTimer:
            activeTeam = teams[competition.activeTeam]
            if self.config.defaults.largeStoppedTeamTimer or activeTeam.active():
                self.display.updateTimer(str(activeTeam),
                                         activeTeam.scoreboardColour,
                                         f"team-{competition.activeTeam}")
        else:
            displayTime1 = str(teams[0])
            displayTime2 = str(teams[1])
            colour = teams[competition.activeTeam].scoreboardColour
            self.display.competitionUpdate(displayTime1, teams[0].scoreboardColour, displayTime2, teams[1].scoreboardColour)

        return 0.05

    async def displayScrollingText(self, text=None, howLong=None):
        if text is not None:
            self.setScrollingText(text)

        if howLong is not None:
            activeUntil = howLong + time.monotonic()
            self.resetIdleTime(activeUntil)

        self.abort()
        await self.display.displayScrollingText(self.scrollingText, colour=self.scrollingTextColour)

    async def showIpAtStart(self, showTime=60):
        curTime = time.monotonic()

        if curTime - self.startTime > showTime:
            self.setView(self.displayScrollingText)
        else:
            hostIp = myIPAddress()

            await self.display.twoLineText(hostIp, str(self.port), endTime=self.startTime + showTime)

    async def displayText(self, text=None, howLong=None):
        if text is not None:
            self.setScrollingText(text)

        if howLong is not None:
            activeUntil = howLong + time.monotonic()
            self.resetIdleTime(activeUntil)

        self.display.displayText(self.scrollingText, colour=self.scrollingTextColour)

    async def teamNames(self):
        teams = self.timers.competition.teams
        await self.display.displayTeamNames(teams[0].name, teams[0].colour, teams[1].name, teams[1].colour, self.config.defaults.scrollTeamsSeparator)

    async def teamNamesCountDown(self):
        teams = self.timers.competition.teams
        await self.display.displayTeamNames(teams[0].name, teams[0].colour, teams[1].name, teams[1].colour, self.config.defaults.scrollTeamsSeparator)

    async def elapsedTimeUpdate(self):
        elapsedTime = self.timers.elapsedTime
        if elapsedTime.active():
            self.resetIdleTime()

        t = elapsedTime.parts()

        displayTime = elapsedTime.format(t)

        self.display.updateTimer(displayTime, self.white, "elt:")

    async def countDownUpdate(self):
        countDown = self.timers.countDown
        state = countDown.getState()
        if state == "running":
            if countDown.active():
                self.resetIdleTime()

            displayTime = str(countDown)
            self.display.updateTimer(displayTime, self.white, "cdt:")
        elif state == "onemore":
            self.setView(self.countDownFinished)
        else:
            self.setView(self.countDownLastEnd)

        return 0.05

    async def countDownFinished(self):
        self.abort()
        countDown = self.timers.countDown
        await self.display.displayScrollingText(countDown.finishedMessage if countDown.finishedMessage else "Done",
                                                colour=countDown.finishedMessageColour if countDown.finishedMessageColour else "green",
                                                displayTime=countDown.finishedMessageDisplayTime,
                                                twoLineOK=False)
        
        if countDown.finishedMessage and countDown.finishedMessageDisplayTime:
            self.setView(self.countDownLastEnd)

    async def countDownLastEnd(self):
        self.abort()
        countDown = self.timers.countDown
        await self.display.displayScrollingText(countDown.lastEndMessage if countDown.lastEndMessage else "Last End",
                                                colour=countDown.lastEndMessageColour if countDown.lastEndMessageColour else "red",
                                                twoLineOK=False)

    async def intermissionUpdate(self):
        timer = self.timers.intermission

        if timer.active():
            self.resetIdleTime()

        if timer.timeRemaining() == 0:
            self.setView(self.competitionUpdate)
            return 0

        self.display.timerUpdate(str(timer), timer.colour)
        return 0.05

    async def betweenEndTimerUpdate(self):
        timer = self.timers.intermission
        self.display.timerUpdate(str(timer), timer.colour)

        if timer.active():
            self.resetIdleTime()

        if timer.timeRemaining() == 0:
            self.setView(self.competitionUpdate)

        return 0.05

    async def timeoutUpdate(self):
        timer = self.timers.timeout
        self.display.timerUpdate(str(timer), timer.colour)

        if timer.active():
            self.resetIdleTime()

        if timer.timeRemaining() == 0:
            timer.team.remainingTimeouts -= 1
            timer.pause()
            if timer.teamId == "team1":
                self.timers.competition.resumeTeam1()
            elif timer.teamId == "team2":
                self.timers.competition.resumeTeam2()

            self.setView(self.competitionUpdate)

        return 0.05

    async def clockUpdate(self):
        self.display.clockUpdate()
        return 0.05

    async def splashColour(self):
        self.display.splashColour()

    async def displayFlashText(self):
        await self.display.displayFlashText(self.flashText, colour=self.flashTextColour)

    def breakTimesNeedsUpdate(self):
        self.breakTimeUpdateTime = 0

    async def breakTime(self):
        if self.rockThrowListener:
            breakTimeUpdateTime = self.rockThrowListener.getLastUpdateTime()
            if breakTimeUpdateTime > self.breakTimeUpdateTime:
                event = self.rockThrowListener.getEvent()
                if event:
                    for tm, clr, evName, speed in event[1][0: min(2, len(event[1]))]:
                        self.display.breakTimeSet(tm, clr)
                        
                self.breakTimeUpdateTime = breakTimeUpdateTime
        else:
            self.display.breakTimeClear()
            
        await self.display.breakTimeDisplay()
            
    async def showColour(self):
        self.display.showColour()

    def setSensorCheck(self, info):
        self.checkSelectedSensorInfo = info

    async def sensorSetup(self):
        sensor = self.checkSelectedSensorInfo

        startTime = time.monotonic()
        if sensor is None or sensor["ip"] == "Unassigned":
            self.display.displayText("No snsr", "white")
        else:
            name = sensor["name"]
            tkn = self.tokenAuthenticator.create(expires=int(time.time()) + BreakTimerClient.tokenValidTime, audience="sensor")

            response = await postUrlJSONResponse("SensorSetup",
                                                 f"{httpUtils.scheme}://{sensor['ip']}/sensor/state",
                                                 jsonData={"name": name},
                                                 headers={CLOCK_HDR: tkn})

            if response and response['state']:
                await self.display.twoLineText(name, "Yes", colour="green", centre=True)
            else:
                await self.display.twoLineText(name, "No", colour="red", centre=True)

            await asyncio.sleep(max(0, 0.2 - (time.monotonic() - startTime)))

    async def updateTask(self, app):
        await asyncio.sleep(1)

        if self.pleaseDropPriviledgesNow:
            dropRootPrivileges(self.user, groups=[self.group, "adm"])
            self.pleaseDropPriviledgesNow = False

        nextCheckTime = time.monotonic() + 1
        lastDisplay = None
        try:
            while True:
                curTime = time.monotonic()
                if curTime > nextCheckTime:
                    if self.isIdle():
                        self.display.blank()
                        await asyncio.sleep(0.05)
                        continue

                if self.displayF != lastDisplay:
                    info("display: %s", self.displayF.__name__)
                    lastDisplay = self.displayF

                waitTime = await self.displayF()

                await asyncio.sleep(waitTime if waitTime else 0.05)

        except asyncio.CancelledError:
            return
        except KeyboardInterrupt:
            raise
        except Exception:
            error("curlingtimer: update task", exc_info=True)
        finally:
            pass

        
def create(display, config, port=80, tokenAuthenticator=None, user="pi", group="pi"):
    global manager

    if not manager:
        manager = CurlingClockManager(display, config, port=port, tokenAuthenticator=tokenAuthenticator, user=user, group=group)

    return manager
