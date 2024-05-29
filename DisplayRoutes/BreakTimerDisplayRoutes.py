from Logger import info
import time
import asyncio
from aiohttp import web as aiohttp_web
from AccessVerification import ajaxVerifyToken, verifyToken
from Utils import myHostName
import Config
import LED_RGB_Display
import CurlingClockManager
import RockThrow
from WebSocket import WebSocketBase

routes = aiohttp_web.RouteTableDef()


@routes.post('/breaktimer/display')
@ajaxVerifyToken("pin")
async def breakTimerDisplayTimesAjax(request):
    json = await request.json()

    if json.get("clear", False):
        LED_RGB_Display.display.clearBreakTimeDisplay()
    else:
        times = json.get("times", [])
        for t, c in reversed(times):
            LED_RGB_Display.display.setBreakTimeDisplay(float(t), c)
            
    return aiohttp_web.json_response({"action": "display"})


class BreakTimerMonitor(WebSocketBase):
    def __init__(self, sensor, webSocketDisplay):
        super().__init__(sensor["name"])
        self.id = None
        self.sensor = sensor
        self.webSocketDisplay = webSocketDisplay

    async def connect(self):
        await super().connect(f'ws://{self.sensor["ip"]}/ws/gettimes')
        
    async def close(self):
        await super().close()
        self.webSocketDisplay = None

    async def cmd_time(self, time):
        LED_RGB_Display.display.resetIdleTime()
        name = self.sensor["name"]
        self.webSocketDisplay.addTime(name, time)        

    async def cmd_times(self, times):
        pass
    
    async def cmd_reset(self, data):
        pass

    async def cmd_registered(self, data):
        pass

    async def register(self, name, accessToken):
        await self.send_msg("register", {"tkn": accessToken,
                                         "id": name,
                                         "name": name,
                                         "data": False,
                                         "filterTime": 5})

class BreakTimeDisplayWebSocket(WebSocketBase):
    def __init__(self, name):
        super().__init__(name)
        self.id = None
        self.activeSensors = []
        self.verified = False
        self.rockThrow = None
        self.updateTime = 0
        self.currentEvent = None

    async def event(self, event, data=None):
        if not self.verified:
            self.close()

        await self.send_msg("event", {"type": event, "data": data})

    async def close(self):
        await super().close()
        for bt in self.activeSensors:
            await bt.close()

    def addTime(self, sensor, tm):
        if self.rockThrow:
            tm.append(sensor)
            evnt = self.rockThrow.checkForEvent(tm)

            if evnt:
                self.currentEvent = evnt
                self.updateTime = time.monotonic()

            return evnt

        return None

    async def cmd_register(self, data):
        accessToken = data.get("tkn")
        if not verifyToken(accessToken, "pin"):
            self.close()
            
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
                                                    mode=style,
                                                    circumference=circumference,
                                                    slidePathLength=slidePathLength)
        
        self.pendingSensors = len(sensors)

        for sensor in sensors:
            bt = BreakTimerMonitor(sensor, self)
            asyncio.ensure_future(bt.connect())
            self.activeSensors.append(bt)

        hostName = myHostName()
        await asyncio.sleep(0.500)
        for bt in self.activeSensors:
            await bt.register(hostName, accessToken)
        
        filterTime = int(data.get("filterTime", 5))
        await self.send_msg("registered", {"registered": True})

        CurlingClockManager.manager.setView(CurlingClockManager.manager.breakTime)
         
    async def closed(self):
        CurlingClockManager.manager.registerRockThrowListener(None)    
        
    async def cmd_stop(self, data):
        await self.close()

    def getLastUpdateTime(self):
        return self.updateTime

    def getEvent(self):
        return self.currentEvent

    async def cmd_reset(self, data):
        if self.rockThrow:
            self.rockThrow.clear()

@routes.get('/ws/breaktimerdisplay')
async def websocket_handler(request):
    ws = BreakTimeDisplayWebSocket("display")
    
    await ws.prepare(request)
    CurlingClockManager.manager.registerRockThrowListener(ws)    
    await ws.process()
