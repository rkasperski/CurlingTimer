import sys
import asyncio
import time

from Logger import error, info

import ZeroConfManager
import BreakTimerClient
import ConfigurationManager
import HardwareClock

from Utils import dropRootPrivileges, myIPAddress, strToSeconds
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
        self.display = display
        self.user = user
        self.group = group
        self.config = config

        self.blankTime = strToSeconds(config.defaults.blankTime)
        self.nextBlankTime = 0
        self.lastInteractionTime = time.monotonic()
        self.lastInteractionResetter = "main"

        self.publish(port=port)
        self.breakTimeDataVersion = None
        self.breakTimerDisplayStyle = "raw"
        self.checkSelectedSensorInfo = None
        self.pleaseDropPriviledgesNow = True
        self.kapow = None
        self.tokenAuthenticator = tokenAuthenticator
        self.displayBreakTimeTracker = BreakTimerClient.DisplayBreakTimeTracker()
        self.drawManager = Draws.createDrawManager()
        self.startTime = time.monotonic()
        self.breakTimeUpdateTime = 0
        self.timers = Timers(self.config.defaults, self.config.sheets.mySheet, self.isIdle)
        self.rockThrowListener = None
        self.welcomeMessage = config.defaults.welcomeMessage
        self.scrollingText = "scrolling unset"
        self.scrollingTextColour = "white"
        self.flashText = "flash unset"
        self.flashTextColour = "white"
        self.white = (255, 255, 255)
        self.setDefaultsFromConfig()
        self.callOnViewChange = None

    def getSheets(self):
        return self.config.sheets
            
    def setCallOnViewChange(self, callOnViewChange):
        self.callOnViewChange = callOnViewChange

    def unsetCallOnViewChange(self, callOnViewChange):
        if self.callOnViewChange == callOnViewChange:
            self.callOnViewChange = None

    def setDefaultsFromConfig(self):
        defaults = self.config.defaults
        self.welcomeMessage = defaults.welcomeMessage

        self.setScrollingText(self.welcomeMessage)
        self.blankTime = strToSeconds(defaults.blankTime)

        countDown = self.timers.countDown
        countDown.setFinishedMessage(defaults.finishedMessage,
                                     defaults.finishedMessageColour,
                                     defaults.finishedMessageDisplayTime)
        countDown.setLastEndMessage(defaults.lastEndMessage,
                                    defaults.lastEndMessageColour,
                                    defaults.lastEndMessageDisplayTime)

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

    def getDrawable(self):
        return self.display.getDrawable()

    def isIdle(self):
        if self.lastInteractionTime == 0:
            return True
        
        cur_time = time.monotonic()
        if self.nextBlankTime:
            if self.nextBlankTime >= cur_time:
                return False

            info("isIdle: display period expired: curTime=%s blankTime=%s", cur_time, self.nextBlankTime)
            self.nextBlankTime = 0
            self.forceIdle()

            return True

        idle = self.lastInteractionTime + self.blankTime < cur_time
        return idle

    def setBlankTime(self, blankTime):
        self.blankTime = blankTime

    def resetIdleTime(self, activeUntil=None, activeInterval=None):
        mTime = time.monotonic()
        if activeUntil is not None:
            # activeUntil is local time so convert to monotonic time
            curLclTime = time.time()
            self.nextBlankTime = mTime + max(activeUntil - curLclTime, 0)
            info("resetIdleTime curTime=%s mTime=%s until=%s:%s", curLclTime, mTime, self.nextBlankTime, self.nextBlankTime - mTime, stacklevel=2)
        else:
            self.nextBlankTime = 0

        if activeInterval:
            info("resetIdleTime for=%s", activeInterval, stacklevel=2)

            self.nextBlankTime = max(self.nextBlankTime, mTime + activeInterval)

        self.lastInteractionTime = mTime
        self.lastInteractionResetter = sys._getframe().f_back.f_code.co_name

    def adjustIdleTime(self, amt):
        self.lastInteractionTime += amt

    def forceIdle(self, current_view=None):
        """forces the display to go blank. If current_view is given then it must match the
        current view for the foce idle to bb done. When succesful the  display view
        is returned else None"""
        if current_view and current_view != self.displayF:
            return None

        if self.callOnViewChange:
            self.callOnViewChange(None)
            self.callOnViewChange = None

        self.abort()
        self.lastInteractionTime = 0
        return self.displayF

    def getIdleTime(self):
        return time.monotonic() - self.lastInteractionTime

    def getIdleResetter(self):
        return self.lastInteractionResetter

    def publish(self, port=80):
        try:
            ZeroConfManager.publish("_clockdisplay._tcp.local.", port)
        except Exception as e:
            error("curlingtimer: startup: failed to register clock displa %s", e)

    def getView(self):
        return self.displayF

    def setView(self, new_view=None, reset_idle=True, current_view=None):
        """Sets the view what's to be displayed. If current_view is supplied it must match
        the displayview for the new view to be applied. If the new view is applied then
        the old view is returned else None"""
        old_view = self.displayF

        if current_view and current_view != old_view:
            return None

        if new_view != self.displayF:
            if self.callOnViewChange:
                self.callOnViewChange(new_view)
                self.callOnViewChange = None

        self.abort()
        self.displayF = new_view

        if reset_idle:
            self.resetIdleTime()

        info("set view=%s", self.displayF.__name__, stacklevel=2)

        return old_view

    def abort(self):
        self.display.abort()

    def registerRockThrowListener(self, listener):
        self.rockThrowListener = listener

    def setKapow(self, name):
        if name not in Kapow.registered:
            name = "life"

        self.kapow = Kapow.registered[name](self.getDrawable())
        self.setView(self.kapowNext)

    async def kapowNext(self):
        delay = await self.kapow.next()
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

        if hostIp == self.config.rink.clockServer:
            self.config.rink.batteryAlert = not HardwareClock.hasHardwareClock

        if self.config.defaults.ipOnStart:
            self.setView(self.showIpAtStart)
        else:
            self.show_startup_msg()
        
    def show_startup_msg(self):
        mySheet = self.config.sheets.mySheet
        self.resetIdleTime()
        hostIp = myIPAddress()

        self.setScrollingText(self.welcomeMessage)
        self.setView(self.displayScrollingText)
        
        if self.config.server.setup == 0:
            if self.config.server.isDefaultSecretKey():
                self.setScrollingText("setup: secretkey")
            else:
                self.setScrollingText("setup: sheets")

            self.resetIdleTime(activeInterval=300)
            return

        if (not mySheet) or mySheet.ip != hostIp:
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
            self.resetIdleTime(activeInterval=howLong)

        self.abort()
        await self.display.displayScrollingText(self.scrollingText, colour=self.scrollingTextColour)

    async def showIpAtStart(self, showTime=60):
        curTime = time.monotonic()

        if curTime - self.startTime > showTime:
            self.show_startup_msg()
        else:
            hostIp = myIPAddress()

            await self.display.twoLineText(hostIp, str(self.port), displayTime=showTime)

    async def displayText(self, text=None, howLong=None):
        if text is not None:
            self.setScrollingText(text)

        if howLong is not None:
            self.resetIdleTime(activeInterval=howLong)

        self.display.displayText(self.scrollingText, colour=self.scrollingTextColour)

    async def update_null(self):
        pass
    
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
            if self.setView(self.countDownFinished, reset_idle=False, current_view=self.countDownUpdate):
                self.resetIdleTime(activeInterval=countDown.finishedMessageDisplayTime)
        else:
            self.setView(self.countDownLastEnd, current_view=self.countDownUpdate)

        return 0.05

    async def countDownFinished(self):
        self.abort()
        countDown = self.timers.countDown
        if await self.display.displayScrollingText(countDown.finishedMessage if countDown.finishedMessage else "Done",
                                                   colour=countDown.finishedMessageColour if countDown.finishedMessageColour else "green",
                                                   displayTime=countDown.finishedMessageDisplayTime,
                                                   twoLineOK=False):
            if countDown.lastEndMessage and countDown.lastEndMessageDisplayTime:
                if self.setView(self.countDownLastEnd, reset_idle=False, current_view=self.countDownFinished):
                    self.resetIdleTime(activeInterval=countDown.lastEndMessageDisplayTime)
            else:
                self.forceIdle(current_view=self.countDownFinished)
        else:
            print("countDownFinished aborted")
                
    async def countDownLastEnd(self):
        self.abort()
        countDown = self.timers.countDown
        if await self.display.displayScrollingText(countDown.lastEndMessage if countDown.lastEndMessage else "Last End",
                                                   colour=countDown.lastEndMessageColour if countDown.lastEndMessageColour else "red",
                                                   displayTime=countDown.lastEndMessageDisplayTime,
                                                   twoLineOK=False):
            self.forceIdle()

    async def intermissionUpdate(self):
        timer = self.timers.intermission

        if timer.active():
            self.resetIdleTime()

        if timer.timeRemaining() == 0:
            self.setView(self.competitionUpdate)
            return 0

        self.display.updateTimer(str(timer), timer.colour, "intermission:")
        return 0.05

    async def betweenEndTimerUpdate(self):
        timer = self.timers.intermission
        self.display.updateTimer(str(timer), timer.colour, "intra:")

        if timer.active():
            self.resetIdleTime()

        if timer.timeRemaining() == 0:
            self.setView(self.competitionUpdate)

        return 0.05

    async def timeoutUpdate(self):
        timer = self.timers.timeout
        self.display.updateTimer(str(timer), timer.colour, "timeout:")

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
                events = self.rockThrowListener.getEvents()
                if events:
                    for event in events:
                        for tm, clr, evName, speed in event[1][0: min(2, len(event[1]))]:
                            self.display.breakTimeSet(tm, clr)
                        
                self.breakTimeUpdateTime = breakTimeUpdateTime
        else:
            self.display.breakTimeClear()

        await self.display.breakTimeDisplay()

    def breakTimeClear(self):
        self.display.breakTimeClear()
        self.breakTimeUpdateTime = 0
        if self.rockThrowListener:
            self.rockThrowListener.clearEvents()

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

        last_display = self.update_null
        is_idle = self.isIdle()

        while True:
            try:
                wait_time = None
                if self.isIdle():
                    if not is_idle:
                        info("idle: blanking screen ct=%s nbt=%s lit=%s", time.monotonic(), self.nextBlankTime, self.lastInteractionTime)
                        if self.callOnViewChange:
                            self.callOnViewChange(None)
                            self.callOnViewChange = None

                        is_idle = True
                        self.display.blank()
                else:
                    if is_idle:
                        info("idle: showing screen ct=%s nbt=%s lit=%s", time.monotonic(), self.nextBlankTime, self.lastInteractionTime)
                        is_idle = False

                    if self.displayF != last_display:
                        info("display: %s from %s", self.displayF.__name__, last_display.__name__)
                        last_display = self.displayF

                    wait_time = await self.displayF()

                await asyncio.sleep(wait_time if wait_time else 0.05)

            except asyncio.CancelledError:
                return
            except KeyboardInterrupt:
                raise
            except Exception:
                error("curlingtimer: update task", exc_info=True)

        
def create(display, config, port=80, tokenAuthenticator=None, user="pi", group="pi"):
    global manager

    if not manager:
        manager = CurlingClockManager(display, config, port=port, tokenAuthenticator=tokenAuthenticator, user=user, group=group)

    return manager
