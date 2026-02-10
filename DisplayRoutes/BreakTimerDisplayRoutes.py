from Logger import info
import time
import asyncio
from aiohttp import web as aiohttp_web
from AccessVerification import ajaxVerifyToken, verifyToken
from Utils import myHostName
import Config
import CurlingClockManager
import RockThrow
from WebSocket import WebSocketBase

routes = aiohttp_web.RouteTableDef()


@routes.post('/breaktimer/display')
@ajaxVerifyToken("pin")
async def breakTimerDisplayTimesAjax(request):
    json = await request.json()

    if json.get("clear", False):
        CurlingClockManager.manager.clearBreakTimeDisplay()
    else:
        times = json.get("times", [])
        for t, c in reversed(times):
            CurlingClockManager.manager.setBreakTimeDisplay(float(t), c)
            
    return aiohttp_web.json_response({"action": "display"})


class BreakTimerMonitor(WebSocketBase):
    def __init__(self, sensor, webSocketDisplay, myHostName, accessToken, verbose=0):
        super().__init__(sensor["name"], verbose=verbose)
        self.id = None
        self.sensor = sensor
        self.webSocketDisplay = webSocketDisplay
        self.breakTimerUrl = f'ws://{self.sensor["ip"]}/ws/gettimes'
        self.myHostName = myHostName
        self.accessToken = accessToken

    async def connect(self):
        info("BreakTimerMonitor: connect %s remote: %s", self.breakTimerUrl, self.remote)
        await super().connect(self.breakTimerUrl)
        
    async def onclose(self):
        info("BreakTimerMonitor: onclose %s %s; remote: %s", self.name, self.breakTimerUrl, self.remote)
        if self.webSocketDisplay:
            self.webSocketDisplay.disconnectSensor(self.sensor)

    async def cmd_time(self, time):
        info("BreakTimerMonitor: %s received time %s; remote: %s", self.name, time, self.remote)
        if self.webSocketDisplay:
            CurlingClockManager.manager.resetIdleTime()
            self.webSocketDisplay.addTime(self.name, time)

    async def cmd_times(self, times):
        info("BreakTimerMonitor: %s revceived times; remote: %s", self.name, self.remote)
        if self.webSocketDisplay:
            self.webSocketDisplay.addTimes(self.name, times)

    async def cmd_reset(self, data):
        info("BreakTimerMonitor: %s receieved reset; ignored; remote: %s", self.name, self.remote)

    async def cmd_registered(self, data):
        info("BreakTimerMonitor: %s received registered; data=%s remote: %s id=%s", self.name, data, self.remote, self.id)

    async def register(self):
        await self.send_msg("register", {"tkn": self.accessToken,
                                         "id": self.myHostName,
                                         "name": self.myHostName,
                                         "data": True,
                                         "filterTime": 5})
        info("BreakTimerMonitor: %s send register remote: %s", self.myHostName, self.remote)

    async def onconnect(self):
        info("BreakTimerMonitor: %s onconnect remote: %s", self.myHostName, self.remote)

        await self.register()

    def disconnect(self):
        self.webSocketDisplay = None

class BreakTimeDisplayWebSocket(WebSocketBase):
    def __init__(self, name, verbose=False):
        super().__init__(name, verbose=verbose)
        self.id = None
        self.activeSensors = {}
        self.activeSensorCount = 0
        self.verified = False
        self.rockThrow = None
        self.updateTime = 0
        self.currentEvents = None
        self.timesBySensor = {}

    def callOnViewChange(self, newView):
        if newView != CurlingClockManager.manager.breakTime:
            info("BreakTimerDisplayWebSocket: %s view change", self.id)
            asyncio.create_task(self.send_msg("endsession", {"msg": "view change"}))

    def addTime(self, sensor, tm):
        if self.rockThrow:
            tm.append(sensor)
            evnt = self.rockThrow.check_for_event(tm)

            if evnt:
                self.currentEvents = [evnt]
                self.updateTime = time.monotonic()

            return evnt

        return None

    def showInitialTimes(self):
        if not self.rockThrow:
            return

        self.rockThrow.clear()
        CurlingClockManager.manager.breakTimeClear()

        timesList = []

        for times in self.timesBySensor.values():
            timesList += times

        timesList.sort()

        events = []
        for tm in timesList:
            evnt = self.rockThrow.check_for_event(tm)
            if evnt:
                events.append(evnt)

        if events:
            self.currentEvents = events
            self.updateTime = time.monotonic()

        return None

    def addTimes(self, sensor, sensorTimes):
        sensorTimes = [list(tm) + [sensor] for tm in sensorTimes]

        self.timesBySensor[sensor] = sensorTimes

        if len(self.timesBySensor) == self.activeSensorCount:
            self.showInitialTimes()

    async def cmd_register(self, data):
        accessToken = data.get("tkn")
        if not verifyToken(accessToken, "pin", verbose=True):
            info("BreakTimerDisplay: register: %s failed bad tkn %s; %s", self.remote, accessToken, self.id, )
            await self.close("register: bad token")
            return

        info("BreakTimeDisplayWebSocket: register received; start %s: %s; %s", self.remote, data, self.id)

        self.verified = True
        id = data["id"]
        style = data.get("style", "raw")
        self.id = id
        sensors = data["sensors"]
        circumference = 0.910
        slidePathLength = 6.401
        sensorToPlacementMap = {sensor["name"]: sensor["placement"] for sensor in sensors}
        placementToColourMap = {sensor["placement"]: sensor["colour"] for sensor in sensors}

        self.rockThrow = RockThrow.RockTimingEvents(sensorToPlacementMap,
                                                    placementToColourMap,
                                                    circumferenceInM=circumference)
        
        self.activeSensorCount = len(sensors)
        self.timesBySensor = {}

        filterTime = int(data.get("filterTime", 5))
        await self.send_msg("registered", {"registered": True})

        hostName = myHostName()
        for sensor in sensors:
            bt = BreakTimerMonitor(sensor, self, hostName, accessToken)
            self.activeSensors[bt.name] = bt
            asyncio.ensure_future(bt.connect())

            info("BreakTimerDisplay: register end %s: %s", self.id, data)

        CurlingClockManager.manager.setView(CurlingClockManager.manager.breakTime)
        info("BreakTimeDisplayWebSocket: register received; done %s: %s; %s",self.remote, data, self.id)

    async def disconnectSensor(self, sensor):
        bt = BreakTimerMonitor(sensor, self, hostName, accessToken)

        del self.activeSensors[bt.name]

        # self.closeSensors()
        self.close()

    async def closeSensors(self):
        for bt in self.activeSensors.values():
            bt.disconnect()

        for bt in self.activeSensors.values():
            await bt.close()

        self.activeSensors = {}
         
    async def onclose(self):
        info("BreakTimeDisplayWebSocket: onclose; start %s; %s", self.remote, self.id)
        await self.closeSensors()

        CurlingClockManager.manager.registerRockThrowListener(None)    
        info("BreakTimeDisplayWebSocket: onclose; done %s; %s", self.remote, self.id)

    async def cmd_stop(self, data):
        info("BreakTimeDisplayWebSocket: stop received; %s; %s", self.remote, self.id)
        await self.close()

    def getLastUpdateTime(self):
        return self.updateTime

    def getEvents(self):
        return self.currentEvents

    def clearEvents(self):
        self.currentEvents = None
        self.updateTime = 0

    async def cmd_reset(self, data):
        info("BreakTimeDisplayWebSocket: reset received; start %s; %s", self.remote, self.id)
        if not self.verified:
            info("BreakTimerDisplayWebSocket: reset %s: not verified; %s", self.remote, self.id)
            await self.close()
            return

        if self.rockThrow:
            self.rockThrow.clear()
            CurlingClockManager.manager.breakTimeClear()

        info("BreakTimeDisplayWebSocket: reset received; end %s", self.id)


@routes.get('/ws/breaktimerdisplay')
async def websocket_handler(request):
    ws = BreakTimeDisplayWebSocket("display", verbose=0)

    CurlingClockManager.manager.registerRockThrowListener(ws)

    rc = None
    if await ws.prepare(request):
        CurlingClockManager.manager.setCallOnViewChange(ws.callOnViewChange)

        rc = await ws.process()
        await ws.closeSensors()
        CurlingClockManager.manager.unsetCallOnViewChange(ws.callOnViewChange)

    CurlingClockManager.manager.registerRockThrowListener(None)

    return rc
