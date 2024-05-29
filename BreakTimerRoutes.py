from Logger import info, debug
import time
import asyncio
from aiohttp_jinja2 import render_template as renderTemplate
import HTTP_Utils
from json import loads, dumps

from aiohttp import web as aiohttp_web
from WebSocket import WebSocketBase

from AccessVerification import ajaxVerifyToken, verifyToken
import Config
import BreakTimerSensors as breakTimerSensors
import CommonRoutes
from Utils import myHostName, myIPAddress


routes = aiohttp_web.RouteTableDef()
# These deal with the retrieval of break times from the sensors


@routes.get('/')
async def breakSensorIndexHtmlGet(request):
    return renderTemplate('breaktimer.html',
                          request,
                          {"setup": Config.display.server.setup,
                           "name": myHostName(),
                           "type": "timer",
                           "ip":  myIPAddress(),
                           "scheme": HTTP_Utils.scheme,
                           "port": HTTP_Utils.port,
                           })


@routes.post('/restart')
@ajaxVerifyToken("admin")
async def restartAjax(request):
    info("app: restart...")
    asyncio.ensure_future(CommonRoutes.delayedRestart(delay=5))
    return aiohttp_web.json_response({"restart": 1})


@routes.post('/reboot')
@ajaxVerifyToken("admin")
async def rebootAjax(request):
    info("app: reboot...")
    asyncio.ensure_future(CommonRoutes.delayedRestart(delay=5, reboot=True))
    return aiohttp_web.json_response({"reboot": 1})


@routes.post('/status')
@ajaxVerifyToken("admin")
async def statusAjax(request):
    return aiohttp_web.json_response({"msg": "still here"})


@routes.post('/sensor/flash')
@ajaxVerifyToken("pin")
async def breakLaserFlashAjax(request):
    json = await request.json()

    flashLaserDuration = int(json.get("flashtime", 10))

    breakTimerSensors.breakTimerSensorManager.flashLaser(flashLaserDuration)

    return aiohttp_web.json_response({"flashing": "yes"})


@routes.post('/sensor/state')
@ajaxVerifyToken("sensor")
async def breakSensorStateAjax(request):
    sensor = breakTimerSensors.breakTimerSensorManager.sensor
    return aiohttp_web.json_response({"state": sensor.state()})


@routes.post('/config')
@ajaxVerifyToken("config")
async def configAjax(request):
    json = await request.json()

    Config.display.fromString(json["config"])

    return aiohttp_web.json_response({"time": time.time(),
                                      "configUpdate": True,
                                      "msg": "updated"})


def packageCmd(cmd, data):
    return dumps({"cmd": cmd,
                  "data": data})
    

class BreakTimerWebSocket(WebSocketBase):
    def __init__(self, name):
        super().__init__(name)
        self.id = None
        self.verified = False

    async def sendTime(self, timeData):
        if not self.verified:
            await self.close()
            return
        
        await self.send_msg("time", timeData)
        
    async def sendTimes(self):
        if not self.verified:
            await self.close()
            return
        
        await self.send_msg("times", breakTimerSensors.breakTimerSensorManager.getTimes())
        
    async def sendReset(self):
        if not self.verified:
            await self.close()
            return
        
        await self.send_msg("reset")
        
    async def cmd_register(self, data):
        accessToken = data.get("tkn")
        if not verifyToken(accessToken, "pin"):
            await self.close()
            return

        self.verified = True
        id = data["id"]
        self.id = id
        name = data["name"]
        filterTime = int(data.get("filterTime", 5))
        breakTimerSensors.breakTimerSensorManager.register(id, name, None, ws=self, filterTime=filterTime)
        await self.send_msg("registered", {"registered": True})
        if data.get("data", True):
            await self.sendTimes()
        
    async def closed(self):
        if not self.verified:
            await self.close()

        breakTimerSensors.breakTimerSensorManager.unregister(self.id)
        
    async def cmd_reset(self, data):
        if not self.verified:
            await self.close()
            return
        
        filterTime = int(data.get("filterTime", 0))
        reset = int(data.get("reset", 1))

        breakTimerSensors.breakTimerSensorManager.resetTimes(reset=reset, filterTime=filterTime)

    async def cmd_flash(self, data):
        if not self.verified:
            await self.close()
            return
        
        flashLaserDuration = int(data.get("flashtime", 10))

        breakTimerSensors.breakTimerSensorManager.flashLaser(flashLaserDuration)

    async def cmd_state(self, data):
        if not self.verified:
            await self.close()
            return
        
        sensor = breakTimerSensors.breakTimerSensorManager.sensor
        return self.send_msg("state",  sensor.state())

    async def cmd_get(self, data):
        if not self.verified:
            await self.close()
            return
        
        times = breakTimerSensors.breakTimerSensorManager.getTimes()
        debug("breaksensor: breakSensor ws get:  %s", times)
        self.send_msg("times", times)

    async def cmd_stop(self, data):
        if not self.verified:
            await self.close()
            return
        
        await self.close()

        
@routes.get('/ws/gettimes')
async def websocket_handler(request):
    ws = BreakTimerWebSocket("app")
    await ws.prepare(request)
    await ws.process()
