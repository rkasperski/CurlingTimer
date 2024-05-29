from Logger import info, error
import asyncio
import random
import time
import sys
import os

from Timers import BreakTimes
from HTTP_Utils import postUrlJSONResponse, CLOCK_HDR
import HTTP_Utils as httpUtils
import ZeroConfManager

cmd = "sudo /usr/bin/pigpiod -l"
rc = os.system(cmd)
print(f"starting '{cmd}': rc={rc}")
time.sleep(5)

import pigpio
pi = pigpio.pi()

tokenValidTime = 3600

breakTimerSensorManager = None
breakTimerSensor = None


class BreakTimerServer(BreakTimes):
    def __init__(self, tokenAuthenticator, sensorName):
        super().__init__(name=sensorName)

        self.listeners = {}
        self.tokenAuthenticator = tokenAuthenticator
        self.pendingSend = []
        self.monitor = None

    def isActive(self):
        return True

    def start(self):
        if (not self.monitor) or self.monitor.cancelled():
            self.monitor = asyncio.ensure_future(self.timeMonitor())
        
    def stop(self):
        if self.monitor:
            self.monitor.cancel()
            for sensor, tgtPort, ws in self.listeners.values():
                ws.close()

    async def timeMonitor(self):
        try:
            while True:
                await asyncio.sleep(0.050)

                self.recordingStateChangeNotification(self.canRecord())

                if len(self.pendingSend) == 0:
                    continue

                toSend = self.pendingSend.pop(0)

                await self.sendTime(toSend)
        except asyncio.CancelledError:
            self.monitor = None
        finally:
            self.monitor = None

    def register(self, id, sensor, tgtPort=None, filterTime=5, ws=None):
        self.setFilterTime(filterTime)
        
        if id not in self.listeners:
            info("breaksensor:register: sensor=%s id=%s tgtPort=%s", sensor, id, tgtPort)
            self.listeners[id] = (sensor, tgtPort, ws)

    def unregister(self, id):
        if id in self.listeners:
            info("breaksensor:unregister: tgt-ip=%s", id)
            del self.listeners[id]

    def resetTimes(self, reset=True, filterTime=5):
        super().resetTimes(reset=reset, filterTime=filterTime)
        for id, (sensor, tgtPort, ws) in self.listeners.items():
            asyncio.ensure_future(ws.sendReset())
    
    async def sendTime(self, breakTime):
        for id, (sensor, tgtPort, ws) in list(self.listeners.items()):
            response = await ws.sendTime(breakTime)

            info("breaksensor:sendTime: %s %s -> %s time=%s response=%s",
                 self.name, sensor, id, breakTime, response)

    def recordingStateChangeNotification(self, canRecord):
        if breakTimerSensor:
            breakTimerSensor.recordingStateChangeNotification(canRecord)

    def addTime(self, breakTime):
        if super().addTime(breakTime):
            self.pendingSend.append(breakTime)


class BreakTimerSensor(BreakTimerServer):
    def __init__(self, tokenAuthenticator, name="sensor", laserPin=24, sensorPin=19, indicatorPin=21, laserOnFlashMS=500, laserOffFlashMS=500, recordingPin=None):
        super().__init__(tokenAuthenticator, name)
        self.sensorEnabled = False
        self.sensorPin = sensorPin
        self.indicatorPin = indicatorPin
        self.laserPin = laserPin
        self.recordingPin = recordingPin
        self.startFlashTime = 0
        self.endFlashTime = 0
        self.isFlashing = False
        self.checking = False
        self.startTime = 0
        self.startTick = 0
        self.preStartFlashTime = 0
        self.postEndFlashTime = 0
        self.laserOnFlashMS = laserOnFlashMS
        self.laserOffFlashMS = laserOffFlashMS

        try:
            pi.set_mode(sensorPin, pigpio.INPUT)
            pi.set_pull_up_down(sensorPin, pigpio.PUD_DOWN)
            info("breaktimer: using pigpio sensor %s plugged in", name)
            pi.callback(sensorPin, pigpio.EITHER_EDGE, self.pigpio_callback)
            level = pi.read(sensorPin)
        except AttributeError:
            error("breaktimer: probably need to run pigpiod")
            sys.exit()

        pi.set_mode(laserPin, pigpio.OUTPUT)
        pi.write(laserPin, 0)

        pi.write(laserPin, 1)

        if indicatorPin:
            pi.set_mode(indicatorPin, pigpio.OUTPUT)
            pi.write(indicatorPin, level)

        if recordingPin:
            pi.set_mode(recordingPin, pigpio.OUTPUT)
            pi.write(recordingPin, 0)
            
        info("breaktimer: initialized breaktimer %s sensor sensor=%s, indicator=%s laser=%s",
             name, sensorPin, indicatorPin, laserPin)

        asyncio.ensure_future(self.enable())        

    async def enable(self, waitTime=0.300):
        await asyncio.sleep(waitTime)

        self.sensorEnabled = True

    def recordingStateChangeNotification(self, canRecord):
        if self.recordingPin:
            pi.write(self.recordingPin, 1 if canRecord else 0)

    def pigpio_callback(self, pio, level, tick):
        # do adjustment to get close time of day
        curTime = time.time() - pigpio.tickDiff(tick, pi.get_current_tick()) / 1000000
        
        if level:
            if self.indicatorPin:
                pi.write(self.indicatorPin, 1)

            # intervalTime = curTime - self.startTime
            intervalTime = pigpio.tickDiff(self.startTick, tick) / 1000000
            if self.isFlashing:
                flashInnerTime = self.endFlashTime - self.startFlashTime
                flashOuterTime = self.postEndFlashTime - self.preStartFlashTime
                diffTime = intervalTime - flashOuterTime
                r = (self.startTime, curTime,  diffTime)
                info("""flashing: %s diff=%.5f
detect=%.5f, %.5f, %.5f
flashInner=%.5f, %.5f, %.5f
flashOuter=%.5f, %.5f, %.5f
startDelay=%.5f
endDelay=%.5f""",
                     self.name, diffTime,
                     intervalTime, flashInnerTime, flashOuterTime,
                     flashInnerTime, self.startFlashTime, self.endFlashTime,
                     flashOuterTime, self.preStartFlashTime, self.postEndFlashTime,
                     self.startFlashTime - self.preStartFlashTime,
                     self.postEndFlashTime - self.endFlashTime)
            else:
                r = (self.startTime, self.startTime + intervalTime, intervalTime)
                info("breaksensor: %s %s", self.name, r)

            if self.sensorEnabled:
                self.addTime(r)
        else:
            self.startTick = tick
            self.startTime = curTime
            if self.indicatorPin:
                pi.write(self.indicatorPin, 0)

        return

    def state(self):
        return pi.read(self.sensorPin)

    def off(self):
        pi.write(self.laserPin, 0)
        
    async def flash(self, duration):
        self.isFlashing = True
        onTimeSecs = self.laserOnFlashMS / 1000.0
        offTimeSecs = self.laserOffFlashMS / 1000.0
        await asyncio.sleep(onTimeSecs)

        flashEndTime = time.time() + duration
        while time.time() <= flashEndTime:
            self.preStartFlashTime = time.time()
            pi.write(self.laserPin, 0)
            self.startFlashTime = time.time()

            await asyncio.sleep(offTimeSecs)

            self.endFlashTime = time.time()
            pi.write(self.laserPin, 1)
            self.postEndFlashTime = time.time()

            await asyncio.sleep(onTimeSecs / 2)
            diff = self.endFlashTime - self.startFlashTime
            self.addTime((self.startFlashTime, self.endFlashTime, diff))
            info("flash: %s %s", self.name, (self.startFlashTime, self.endFlashTime, diff))
            await asyncio.sleep(onTimeSecs / 2)

        pi.write(self.laserPin, 1)

        self.flashOnLength = 0
        self.isFlashing = False

        
class BreakTimerSensorManager():
    def __init__(self, sensor):
        self.sensor = sensor
        sensor.start()

    def publish(self, port=None):
        ZeroConfManager.publish("_breaktimer._tcp.local.", port if port else httpUtils.port)

    def flashLaser(self, flashDuration=10):
        try:
            asyncio.ensure_future(self.sensor.flash(flashDuration))
        except (KeyError, ValueError):
            return "error"

    def off(self):
        self.sensor.off()

    def getTimes(self):
        try:
            return self.sensor.getTimes()
        except KeyError:
            return (-1, 0, [])

    def resetTimes(self, reset=True, filterTime=5):
        try:
            self.sensor.resetTimes(reset=reset, filterTime=filterTime)
            info("breaksensor: Sensor reset: %s reset=%s filter=%s",
                 self.sensor.name, reset, filterTime)
            return True
        except KeyError:
            info("breaksensor: Sensor reset: doesn't exist: %s", self.sensor.name)
            return False

    def register(self, id, sensor, tgtPort=None, ws=None, filterTime=None):
        try:
            if filterTime is None:
                filterTime = 5
                
            self.sensor.register(id, sensor, tgtPort, ws=ws, filterTime=filterTime)
            info("breaksensor: Sensor Register: %s %s ==> %s:%s",
                 self.sensor.name, sensor, id, tgtPort)
        except KeyError:
            info("breaksensor: Sensor Register: doesn't exist: %%s %s ==> %s:%s",
                 self.sensor.name, sensor, id, tgtPort)
            pass

    def unregister(self, tgtIP):
        try:
            self.sensor.unregister(tgtIP)
            info("breaksensor: Sensor Unregister: %s %s",
                 self.sensor.name, tgtIP)
        except KeyError:
            info("breaksensor: Sensor Unregister: doesn't exist: %s %s",
                 self.sensor.name, tgtIP)
            pass


def create(config, tokenAuthenticator, port=None):
    global breakTimerSensor, breakTimerSensorManager

    breakTimerSensor = BreakTimerSensor(tokenAuthenticator,
                                        name=config.name,
                                        laserPin=config.laserPin,
                                        sensorPin=config.sensorPin,
                                        recordingPin=config.recordingPin,
                                        indicatorPin=config.indicatorPin,
                                        laserOnFlashMS=config.laserOnFlashMS,
                                        laserOffFlashMS=config.laserOffFlashMS)

    breakTimerSensorManager = BreakTimerSensorManager(breakTimerSensor)

    breakTimerSensorManager.publish(port)
    return breakTimerSensorManager
