from Logger import error, info
import copy
import time
import asyncio

from Timers import BreakTimes
from Utils import myIPAddress
from HTTP_Utils import postUrlJSONResponse, CLOCK_HDR
import HTTP_Utils as httpUtils
import ZeroConfManager

tokenValidTime = 3600


class BreakSensor:
    __slots__ = ("name", "colour", "host", "ip", "placement")

    def __init__(self, name, colour, host, ip, placement=None):
        self.name = name
        self.colour = colour
        self.host = host
        self.ip = ip
        self.placement = placement

    def __repr__(self):
        return str([self.name, self.colour, self.host, self.ip, self.placement])

    
class BreakSensorTracker(BreakTimes):
    def __init__(self, name, filterTime):
        super().__init__(name, filterTime)
        self.updateTime = time.monotonic()
        
    def __repr__(self):
        return str([self.name, self.filterTime])

    async def resetTimes(self, reset=True, filterTime=0):
        super().resetTimes(reset=reset, filterTime=filterTime)

        info("breaksensor: resetTimes:%s", self.name)
        self.updateTime = time.monotonic()
        return True

    
class DisplayBreakTimeTracker(BreakTimes):
    def __init__(self):
        # times are filtered at sensors. want close times from two differenct
        # sensors to be displayed
        super().__init__(name="Display", filterTime=0)
        self.activeSensors = {}
        self.updateTime = time.monotonic()

    def getLastUpdateTime(self):
        return self.updateTime

    def setActiveSensors(self, sensors):
        self.activeSensors = {}
        for sensor in sensors:
            name = sensor["name"]
            self.activeSensors[name] = BreakSensor(name, sensor["colour"], sensor["name"], sensor["ip"], placement=sensor["placement"])
            
        self.updateTime = time.monotonic()

    def getActiveSensors(self):
        return self.activeSensors.values()

    def sensorColour(self, name):
        try:
            sensor = self.activeSensors[name]
            return sensor.colour
        except (KeyError, IndexError):
            return "white"

    def getTimes(self):
        return super().getTimes()

    def resetSensor(self, name):
        self.times = [t for t in self.times if t[-1] != name]
        self.updateTime = time.monotonic()

    def resetTimes(self, reset=True):
        super().resetTimes(reset=reset)
        self.updateTime = time.monotonic()

    def addTime(self, name, breakTime):
        try:
            info("breaksensor: receieved time: %s %s", name, breakTime)
            breakTime.append(name)
            super().addTime(breakTime)
            self.updateTime = time.monotonic()
        except KeyError:
            info("breaksensor: Sensor not found: %s", name)
            
