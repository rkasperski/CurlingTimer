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
    def __init__(self, clockTimerDisplay, config, port=80, tokenAuthenticator=None, isIdle=lambda: False, user="pi", group="pi"):
        self.displayF = self.startUp
        self.isIdle = isIdle
        self.port = port

        self.publish(port=port)
        self.breakTimeDataVersion = None
        self.breakTimerDisplayStyle = "raw"
        self.checkSelectedSensorInfo = None
        self.pleaseDropPriviledgesNow = True
        self.kapow = None
        self.clockTimerDisplay = clockTimerDisplay
        self.user = user
        self.group = group
        self.config = config
        self.tokenAuthenticator = tokenAuthenticator
        self.displayBreakTimeTracker = BreakTimerClient.DisplayBreakTimeTracker()
        self.drawManager = Draws.createDrawManager()
        self.startTime = time.monotonic()
        self.breakTimeUpdateTime = 0
        self.timers = Timers(self.config.defaults, self.config.sheets.mySheet)
        self.rockThrowListener = None

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

    def publish(self, port=80):
        ZeroConfManager.publish("_clockdisplay._tcp.local.", port)

    def getView(self):
        return self.displayF

    def setView(self, func):
        oldView = self.displayF
        self.displayF = func

        self.clockTimerDisplay.abort()
        info("set view=%s", self.displayF)

        return oldView

    def registerRockThrowListener(self, listener):
        self.rockThrowListener = listener

    def setKapow(self, name):
        if name not in Kapow.registered:
            name = "life"

        self.kapow = Kapow.registered[name](self.clockTimerDisplay.drawableImage)
        self.setView(self.kapowNext)

    async def kapowNext(self):
        delay = self.kapow.next()
        self.clockTimerDisplay.swapCanvas()
        return delay

    def resetIdleTime(self, until=None):
        self.clockTimerDisplay.resetIdleTime(until)

    def forceIdle(self):
        self.clockTimerDisplay.forceIdle()

    def isActive(self):
        return self.clockTimerDisplay.isActive()

    async def startUp(self):
        hostIp = myIPAddress()

        mySheet = self.config.sheets.mySheet
        self.setView(self.scrollingText)
        self.clockTimerDisplay.resetIdleTime()

        if mySheet and mySheet.ip == hostIp:
            if hostIp == self.config.rink.clockServer:
                self.config.rink.batteryAlert = not HardwareClock.hasHardwareClock

            if self.config.server.setup == 0:
                if self.config.server.isDefaultSecretKey():
                    self.clockTimerDisplay.setScrollingText("setup: secretkey")
                else:
                    self.clockTimerDisplay.setScrollingText("setup: sheets")

                activeUntil = 300*60 + time.monotonic()
                self.resetIdleTime(activeUntil)

            elif self.config.rink.batteryAlert:
                if hostIp == self.config.rink.clockServer:
                    info("CurlingClockManager - clock - my battery is low")
                else:
                    info("CurlingClockManager - clock - Check battery on %s", self.config.rink.clockServer)
                    
                self.clockTimerDisplay.setScrollingText(f"Check battery on {self.config.rink.clockServer}")
                activeUntil = 30 + time.monotonic()
                self.resetIdleTime(activeUntil)
            else:
                self.clockTimerDisplay.setScrollingText(self.clockTimerDisplay.welcomeMessage)

            if self.config.defaults.ipOnStart:
                self.setView(self.showIpAtStart)
        else:
            self.clockTimerDisplay.setScrollingText(f"{hostIp}:{self.port}", colour="red")

    async def competitionUpdate(self):
        competition = self.timers.competition
        if competition.active():
            self.clockTimerDisplay.resetIdleTime()

        if self.config.defaults.largeActiveTeamTimer:
            teams = competition.teams
            activeTeam = teams[competition.activeTeam]
            if self.config.defaults.largeStoppedTeamTimer or activeTeam.active():
                self.clockTimerDisplay.updateTimer(str(activeTeam),
                                                   activeTeam.scoreboardColour,
                                                   f"team-{competition.activeTeam}")
                return 0.05

        self.clockTimerDisplay.competitionUpdate(competition)

        return 0.05

    async def scrollingText(self, text=None, howLong=None):
        if text is not None:
            self.clockTimerDisplay.setScrollingText(text)

        if howLong is not None:
            activeUntil = howLong + time.monotonic()
            self.resetIdleTime(activeUntil)

        self.clockTimerDisplay.abort()
        await self.clockTimerDisplay.displayScrollingText(self.clockTimerDisplay.scrollingText, colour=self.clockTimerDisplay.scrollingTextColour)

    async def showIpAtStart(self, showTime=60):
        curTime = time.monotonic()

        if curTime - self.startTime > showTime:
            self.setView(self.scrollingText)
        else:
            hostIp = myIPAddress()

            await self.clockTimerDisplay.twoLineText(hostIp, str(self.port), endTime=self.startTime + showTime)

    async def displayText(self, text=None, howLong=None):
        if text is not None:
            self.clockTimerDisplay.setScrollingText(text)

        if howLong is not None:
            activeUntil = howLong + time.monotonic()
            self.resetIdleTime(activeUntil)

        self.clockTimerDisplay.displayText(self.clockTimerDisplay.scrollingText, colour=self.clockTimerDisplay.scrollingTextColour)

    async def teamNames(self):
        await self.clockTimerDisplay.displayTeamNames(self.timers.competition.teams, self.config.defaults.scrollTeamsSeparator)

    async def teamNamesCountDown(self):
        await self.clockTimerDisplay.displayTeamNames(self.timers.competition.teams, self.config.defaults.scrollTeamsSeparator)

    async def elapsedTimeUpdate(self):
        elapsedTime = self.timers.elapsedTime
        if elapsedTime.active():
            self.clockTimerDisplay.resetIdleTime()

        self.clockTimerDisplay.elapsedTimeUpdate(elapsedTime)

    async def countDownUpdate(self):
        countDown = self.timers.countDown
        state = countDown.getState()
        if state == "running":
            if countDown.active():
                self.clockTimerDisplay.resetIdleTime()

            self.clockTimerDisplay.countDownUpdate(countDown)
        elif state == "onemore":
            self.setView(self.countDownFinished)
        else:
            self.setView(self.countDownLastEnd)

        return 0.05

    async def countDownFinished(self):
        self.clockTimerDisplay.abort()
        await self.clockTimerDisplay.displayScrollingText(self.clockTimerDisplay.countDown.finishedMessage if self.clockTimerDisplay.countDown.finishedMessage else "Done",
                                                          colour=self.clockTimerDisplay.countDown.finishedMessageColour if self.clockTimerDisplay.countDown.finishedMessageColour else "green",
                                                          displayTime=self.clockTimerDisplay.countDown.finishedMessageDisplayTime,
                                                          twoLineOK=False)
        if self.clockTimerDisplay.countDown.finishedMessage and self.clockTimerDisplay.countDown.finishedMessageDisplayTime:
            self.setView(self.countDownLastEnd)

    async def countDownLastEnd(self):
        self.clockTimerDisplay.abort()
        await self.clockTimerDisplay.displayScrollingText(self.clockTimerDisplay.countDown.lastEndMessage if self.clockTimerDisplay.countDown.lastEndMessage else "Last End",
                                                          colour=self.clockTimerDisplay.countDown.lastEndMessageColour if self.clockTimerDisplay.countDown.lastEndMessageColour else "red",
                                                          twoLineOK=False)

    async def intermissionUpdate(self):
        timer = self.timers.intermission

        if timer.active():
            self.clockTimerDisplay.resetIdleTime()

        if timer.timeRemaining() == 0:
            self.setView(self.competitionUpdate)
            return 0

        self.clockTimerDisplay.timerUpdate(timer)
        return 0.05

    async def betweenEndTimerUpdate(self):
        timer = self.timers.intermission
        self.clockTimerDisplay.timerUpdate(timer)

        if timer.active():
            self.clockTimerDisplay.resetIdleTime()

        if timer.timeRemaining() == 0:
            self.setView(self.competitionUpdate)

        return 0.05

    async def timeoutUpdate(self):
        timer = self.timers.timeout
        self.clockTimerDisplay.timerUpdate(timer)

        if timer.active():
            self.clockTimerDisplay.resetIdleTime()

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
        self.clockTimerDisplay.clockUpdate()
        return 0.05

    async def splashColour(self):
        self.clockTimerDisplay.splashColour()

    async def flashText(self):
        await self.clockTimerDisplay.displayFlashText(self.clockTimerDisplay.flashText, colour=self.clockTimerDisplay.flashTextColour)

    def breakTimesNeedsUpdate(self):
        self.breakTimeUpdateTime = 0

    async def breakTime(self):
        if self.rockThrowListener:
            breakTimeUpdateTime = self.rockThrowListener.getLastUpdateTime()
            if breakTimeUpdateTime > self.breakTimeUpdateTime:
                event = self.rockThrowListener.getEvent()
                if event:
                    for tm, clr, evName, speed in event[1][0: min(2, len(event[1]))]:
                        self.clockTimerDisplay.breakTimeSet(tm, clr)
                        
                self.breakTimeUpdateTime = breakTimeUpdateTime
        else:
            self.clockTimerDisplay.breakTimeClear()
            
        await self.clockTimerDisplay.breakTimeDisplay()
            
    async def showColour(self):
        self.clockTimerDisplay.showColour()

    def setSensorCheck(self, info):
        self.checkSelectedSensorInfo = info

    async def sensorSetup(self):
        sensor = self.checkSelectedSensorInfo

        startTime = time.monotonic()
        if sensor is None or sensor["ip"] == "Unassigned":
            self.clockTimerDisplay.displayText("No snsr", "white")
        else:
            name = sensor["name"]
            tkn = self.tokenAuthenticator.create(expires=int(time.time()) + BreakTimerClient.tokenValidTime, audience="sensor")

            response = await postUrlJSONResponse("SensorSetup",
                                                 f"{httpUtils.scheme}://{sensor['ip']}/sensor/state",
                                                 jsonData={"name": name},
                                                 headers={CLOCK_HDR: tkn})

            if response and response['state']:
                await self.clockTimerDisplay.twoLineText(name, "Yes", colour="green", centre=True)
            else:
                await self.clockTimerDisplay.twoLineText(name, "No", colour="red", centre=True)

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
                        self.clockTimerDisplay.blank()
                        await asyncio.sleep(0.05)
                        continue

                if self.displayF != lastDisplay:
                    info("display: %s", self.displayF.__name__)
                    lastDisplay = self.displayF

                waitTime = await self.displayF()

                await asyncio.sleep(waitTime if waitTime else 0.05)

        except asyncio.CancelledError:
            return
        except Exception:
            error("curlingtimer: update task", exc_info=True)
        except KeyboardInterrupt:
            raise
        finally:
            pass

        
def create(clockTimerDisplay, config, port=80, tokenAuthenticator=None, isIdle=lambda: False, user="pi", group="pi"):
    global manager

    if not manager:
        manager = CurlingClockManager(clockTimerDisplay, config, port=port, tokenAuthenticator=tokenAuthenticator, isIdle=isIdle,  user=user, group=group)

    return manager
