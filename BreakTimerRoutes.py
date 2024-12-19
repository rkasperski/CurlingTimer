import time
import asyncio
from json import dumps
from aiohttp_jinja2 import render_template as renderTemplate
import HTTP_Utils
from Logger import info, debug

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
                           "debug": request.query.get("debug", 0),
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
@ajaxVerifyToken("user")
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
            info("BreakTimerWebSocket: sendTime: not verified; %s remote=%s id=%s", self.name, self.remote, self.id)
            await self.close("sendTime: not verified")
            return

        info("BreakTimerWebSocket: %s send time %s; remote=%s id=%s", self.name, timeData, self.remote, self.id)
        await self.send_msg("time", timeData)

    async def sendTimes(self):
        if not self.verified:
            info("BreakTimerWebSocket: sendTimes: not verified; %s remote=%s id=%s",  self.name, self.remote, self.id)
            await self.close("sendTimes: not verified")
            return

        times = breakTimerSensors.breakTimerSensorManager.getTimes()

        ln = len(times)
        if ln >= 5:
            td = [times[0:2], " ... " , times[-2:]]
        else:
            td = [times, "", ""]
            
        info("BreakTimerWebSocket: %s send times %s%s%s; remote=% sid=%s", self.name, *td, self.remote, self.id)
        
        await self.send_msg("times", times)

    async def sendReset(self):
        if not self.verified:
            await self.close("sendReset: not verified")
            return

        info("BreakTimerWebSocket: %s send reset; id=%s", self.name, self.id)
        await self.send_msg("reset")

    async def cmd_register(self, data):
        info("BreakTimerWebSocket: %s cmd register start %s; remote=%s id=%s", self.name, data, self.remote, self.id)
        accessToken = data.get("tkn")
        if not verifyToken(accessToken, "pin", verbose=True):
            info("verified; %s remote=%s id=%s",  self.name, self.remote, self.id)
            await self.close("cmd register: not verified")
            return

        self.verified = True
        id = data["id"]
        self.id = id
        #name = data["name"]
        name = self.remote
        filter_time = int(data.get("filterTime", 5))
        breakTimerSensors.breakTimerSensorManager.register(id, name, None, ws=self, filterTime=filter_time)
        await self.send_msg("registered", {"registered": True})
        if data.get("data", True):
            await self.sendTimes()
        info("BreakTimerWebSocket: %s cmd register end %s; remote=%s id=%s", self.name, data, self.remote, self.id)

    async def onclose(self):
        info("BreakTimerWebSocket: %s onclose url=%s; remote=%s, id=%s", self.name, self.url, self.remote, self.id)
        breakTimerSensors.breakTimerSensorManager.unregister(self.id)

    async def cmd_reset(self, data):
        if not self.verified:
            info("breakTimerSensors: reset register: not verified; %s remote=%s id=%s",  self.name, self.remote, self.id)
            await self.close("reset register: not verified")
            return

        filterTime = int(data.get("filterTime", 0))
        reset = int(data.get("reset", 1))

        info("BreakTimerWebSocket: %s cmd reset %s; remote=%s id=%s", self.name, data, self.remote, self.id)
        breakTimerSensors.breakTimerSensorManager.resetTimes(reset=reset, filterTime=filterTime)

    async def cmd_flash(self, data):
        if not self.verified:
            info("BreakTimerWebSocket: cmd flash: not verified; %s remote=%s id=%s",  self.name, self.remote, self.id)
            await self.close("cmd flash: not verified")
            return

        flashLaserDuration = int(data.get("flashtime", 10))

        info("BreakTimerWebSocket: %s cmd flash %s; remote=%s id=%s", self.name, data, self.remote, self.id)
        breakTimerSensors.breakTimerSensorManager.flashLaser(flashLaserDuration)

    async def cmd_state(self, data):
        if not self.verified:
            info("BreakTimerWebSocket: cmd state: not verified; %s remote=%s id=%s",  self.name, self.remote, self.id)
            await self.close("cmd state: not verified"); 
            return
        
        info("BreakTimerWebSocket: %s cmd state %s; remote=%s id=%s", self.name, data, self.remote, self.id)
        sensor = breakTimerSensors.breakTimerSensorManager.sensor
        return self.send_msg("state",  sensor.state())

    async def cmd_get(self, data):
        if not self.verified:
            info("BreakTimerWebSocket: cmd get: not verified; %s remote=%s id=%s",  self.name, self.remote, self.id)
            await self.close("cmd get: not verified")
            return

        times = breakTimerSensors.breakTimerSensorManager.getTimes()
        info("breaksensor: breakSensor %s ws get:  %s remote=%s id=%s", self.name, times, self.remote, self.id)
        self.send_msg("times", times)

    async def cmd_stop(self, data):
        if not self.verified:
            info("BreakTimerWebSocket: cmd stop: not verified; %s remote=%s id=%s",  self.name, self.remote, self.id)
            await self.close("cmd stop: not verified")
            return

        info("BreakTimerWebSocket: %s cmd stop %s; remote=%s id=%s", self.name, data, self.remote, self.id)
        sensor = breakTimerSensors.breakTimerSensorManager.sensor
        await self.close("close request")


@routes.get('/ws/gettimes')
async def websocket_handler(request):
    ws = BreakTimerWebSocket("app")
    if await ws.prepare(request):
        await ws.process()
