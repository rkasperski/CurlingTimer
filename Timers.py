from Logger import warning, info, debug
import time
from Utils import secondsToStr, strToSeconds


class CountDownTimer:
    def __init__(self, timeAmt=40*60, hasHours=False):
        self.hasHours = False
        self.setTime(timeAmt, hasHours)
        self.finishedMessage = None
        self.finishedMessageColour = "green"
        self.finishedMessageDisplayTime = 0
        self.lastEndMessage = None
        self.lastEndMessageColour = "red"
        self.lastEndMessageDisplayTime = 0
        self.__expired = False
        self.expiredTime = None

    def setTime(self, timeAmt, hasHours=False):
        if isinstance(timeAmt, str):
            timeAmt = strToSeconds(timeAmt, default=60)

        self.time = timeAmt
        self.timeLeft = timeAmt
        self.__paused = True
        self.timerStartTime = 0.0
        self.hasHours = hasHours
        self.__expired = self.timeLeft < 0
        self.expiredTime = time.monotonic() if self.__expired else None

    def setFinishedMessage(self, msg, colour="white", displayTime=0):
        if isinstance(displayTime, str):
            displayTime = strToSeconds(displayTime)

        self.finishedMessage = msg
        self.finishedMessageColour = colour
        self.finishedMessageDisplayTime = displayTime

    def setLastEndMessage(self, msg, colour="white", displayTime=0):
        if isinstance(displayTime, str):
            displayTime = strToSeconds(displayTime)

        self.lastEndMessage = msg
        self.lastEndMessageColour = colour
        self.lastEndMessageDisplayTime = displayTime

    def paused(self):
        return self.__paused or self.__expired

    def active(self):
        return not self.paused()

    def expired(self):
        return self.__expired

    def resume(self, curTime=None):
        if self.__paused:
            self.__paused = False
            self.timerStartTime = curTime if curTime else time.monotonic()

    def pause(self, curTime=None):
        if not self.__paused:
            self.__paused = True
            self.timeLeft = max(0, self.timeLeft - ((curTime if curTime else time.monotonic()) - self.timerStartTime))

    def timeRemaining(self):
        t = self.timeLeft
        if not self.__paused:
            t = max(0, t - (time.monotonic() - self.timerStartTime))

        self.__expired = t <= 0
        if self.__expired and self.expiredTime is None:
            self.expiredTime = time.monotonic() + t
        
        return t

    def getState(self):
        if not self.__expired:
            return "running"

        if self.finishedMessageDisplayTime == 0:
            return "onemore"

        return "onemore" if self.finishedMessageDisplayTime + self.expiredTime > time.monotonic() else "lastend"

    def setState(self, state):
        self.state = state

    def ajaxResponse(self, values={}):
        t = self.timeRemaining()
        result = {"active": not self.paused(), "time": secondsToStr(t), "seconds": t, "state": self.getState()}
        result.update(values)
        return result

    def __str__(self):
        displayTime = self.timeRemaining() + 0.99
        if self.hasHours or displayTime > 3600:
            formatted = str(int(displayTime/3600.0)) + ":" + ("0" + str(int(displayTime / 60 % 60.0)))[-2:] + ":" + ("0" + str(int(displayTime % 60)))[-2:]
        else:
            formatted = (" " + str(int(displayTime/60.0)))[-2:] + ":" + ("0" + str(int(displayTime % 60)))[-2:]

        return formatted

    
class ElapsedTimeTimer:
    def __init__(self, timeAmt=40*60, hasHours=False, showTenths=False):
        self.hasHours = hasHours
        self.setInitialTime(timeAmt)
        self.showTenths = showTenths

    def setInitialTime(self, timeAmt):
        if isinstance(timeAmt, str):
            timeAmt = strToSeconds(timeAmt)

        self.time = timeAmt
        self.timePassed = timeAmt
        self.__paused = True
        self.timerStartTime = 0.0

    def resume(self, curTime=None):
        if self.__paused:
            self.__paused = False
            self.timerStartTime = curTime if curTime else time.monotonic()

    def paused(self):
        return self.__paused

    def active(self):
        return not self.__paused

    def pause(self, curTime=None):
        if not self.__paused:
            self.__paused = True
            self.timePassed = self.timePassed + ((curTime if curTime else time.monotonic()) - self.timerStartTime)

    def timeElapsed(self):
        t = self.timePassed
        if not self.__paused:
            t = t + (time.monotonic() - self.timerStartTime)

        return t

    def ajaxResponse(self, values={}):
        t = self.timeElapsed()
        result = {"active": not self.paused(), "time": secondsToStr(t), "seconds": t}
        result.update(values)
        return result

    def parts(self):
        t = self.timeElapsed()

        return (int(t / 3600), int(t / 60) % 60, int(t) % 60, int(t * 10) % 10)

    def format(self, p, showTenths=None):
        showTenths = showTenths or (showTenths is None and self.showTenths)
        tenths = f".{p[3]}" if showTenths else ""
        
        if p[0]:
            return f"{p[0]}:{p[1]:02}:{p[2]:02}{tenths}"
        else:
            return f"{p[1]}:{p[2]:02}{tenths}"
        
    def __str__(self):
        return self.format(self.parts())

    
class Team(CountDownTimer):
    def __init__(self, name="team1", colour="red", timeInSeconds=40*60, remainingTimeouts=2):
        super().__init__(timeInSeconds)
        self.name = name
        self.colour = colour
        self.scoreboardColour = colour
        self.remainingTimeouts = remainingTimeouts

    def ajaxResponse(self, values={}):
        t = self.timeRemaining()
        result = {"name": self.name,
                  "colour": self.colour,
                  "remainingTimeouts": self.remainingTimeouts,
                  "active": not self.paused(),
                  "time": secondsToStr(t),
                  "seconds": t}
        result.update(values)
        return result

    
class CompetitionTimer:
    def __init__(self, timeInSeconds=40*60, intermissionTime=9*60, timeoutNumber=2, timeoutLength=120):
        self.teams = [Team(name="", timeInSeconds=timeInSeconds, colour="red"),
                      Team(name="", timeInSeconds=timeInSeconds, colour="yellow")]
        self.activeTeam = 0
        self.intermissionTime = intermissionTime
        self.timeoutNumber = timeoutNumber
        self.timeoutLength = timeoutLength

    def ajaxResponse(self, values={}):
        t1 = self.teams[0].ajaxResponse()
        t2 = self.teams[1].ajaxResponse()
        result = {"team1": t1,
                  "team2": t2,
                  "activeTeam": self.activeTeam + 1,
                  "active": not self.paused(),
                  "intermissionTime": secondsToStr(self.intermissionTime),
                  "timeoutNumber": self.timeoutNumber,
                  "timeoutLength": self.timeoutLength}
        result.update(values)
        return result

    def paused(self):
        return self.teams[0].paused() and self.teams[1].paused()

    def active(self):
        return not self.paused()

    def pause(self, curTime=None):
        self.teams[0].pause(curTime=curTime)
        self.teams[1].pause(curTime=curTime)
        return self.teams[0].paused() and self.teams[1].paused()

    def pauseTeam1(self, curTime=None):
        self.pause(curTime=curTime)
        self.activeTeam = 0
        return True

    def pauseTeam2(self, curTime=None):
        self.pause(curTime=curTime)
        self.activeTeam = 1
        return True

    def resume(self, curTime=None):
        self.teams[self.activeTeam].resume(curTime=curTime)
        return True

    def resumeTeam1(self, curTime=None):
        self.pause()
        self.activeTeam = 0
        self.teams[self.activeTeam].resume(curTime=curTime)
        return True

    def resumeTeam2(self, curTime=None):
        self.pause()
        self.activeTeam = 1
        self.teams[self.activeTeam].resume(curTime=curTime)
        return True

    def exchangeTeams(self, curTime=None):
        self.pause()
        self.activeTeam = (self.activeTeam + 1) % 2
        self.teams[self.activeTeam].resume(curTime=curTime)

        return True


class BreakTimes:
    def __init__(self, name="?", filterTime=0):
        self.times = []
        self.name = name
        self.filterTime = filterTime

    def canRecord(self):
        if self.filterTime > 0 and len(self.times) > 0:
            return (time.time() - self.times[-1][1]) >= self.filterTime

        return True

    def addTime(self, breakTime):
        if len(self.times) > 0:
            if self.filterTime > 0:
                if (breakTime[0] - self.times[-1][1]) < self.filterTime:
                    warning("breaktimers: sensor ignored: %s atTime=%s too soon: %s ft=%s",
                            self.name, breakTime, breakTime[0] - self.times[-1][1], self.filterTime)
                    return None

        info("breaktimers: sensor: %s time appended: %s", self.name, breakTime)
        self.times.append(breakTime)

        # bubble sort it into place. Generally nothing should ever move
        for idx in range(len(self.times) - 1, 0, -1):
            if self.times[idx][0] < self.times[idx-1][0]:
                self.times[idx], self.times[idx - 1] = self.times[idx - 1], self.times[idx]
        
        return len(self.times)

    def setFilterTime(self, filterTime=None):
        self.filterTime = filterTime if filterTime else 0
        
    def resetTimes(self, reset=True, filterTime=None):
        if reset:
            self.times = []

        self.filterTime = filterTime if filterTime else 0

    def getTimes(self):
        return self.times
