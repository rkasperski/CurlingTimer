from time import time as time_time
import asyncio
from json import dumps
from aiohttp_jinja2 import render_template as render_template

from aiohttp import web as aiohttp_web
import http_utils as http
from web_socket import WebSocketBase

from logger import info
from access_verification import ajax_verify_token, verify_token
import config
import break_timer_sensors 
from common_routes import delayed_restart
from utils import my_host_name, my_ip_address


routes = aiohttp_web.RouteTableDef()
# These deal with the retrieval of break times from the sensors


@routes.get('/')
async def break_sensor_index_html_get(request):
    return render_template('breaktimer.html',
                           request,
                           {"setup": config.display.server.setup,
                            "name": my_host_name(),
                            "type": "timer",
                            "ip":  my_ip_address(),
                            "scheme": http.scheme,
                            "port": http.port,
                            "debug": request.query.get("debug", 0),
                            })


@routes.post('/restart')
@ajax_verify_token("admin")
async def restart_ajax(request):
    info("app: restart...")
    asyncio.ensure_future(delayed_restart(delay=5))
    return aiohttp_web.json_response({"restart": 1})


@routes.post('/reboot')
@ajax_verify_token("admin")
async def reboot_ajax(request):
    info("app: reboot...")
    asyncio.ensure_future(delayed_restart(delay=5, reboot=True))
    return aiohttp_web.json_response({"reboot": 1})


@routes.post('/status')
@ajax_verify_token("user")
async def status_ajax(request):
    return aiohttp_web.json_response({"msg": "still here"})


@routes.post('/sensor/flash')
@ajax_verify_token("pin")
async def break_laser_flash_ajax(request):
    json = await request.json()

    flash_laser_duration = int(json.get("flashtime", 10))

    break_timer_sensors.break_timer_sensor_manager.flash_laser(flash_laser_duration)

    return aiohttp_web.json_response({"flashing": "yes"})


@routes.post('/sensor/state')
@ajax_verify_token("sensor")
async def break_sensor_state_ajax(request):
    sensor = break_timer_sensors.break_timer_sensor_manager.sensor
    return aiohttp_web.json_response({"state": sensor.state()})


@routes.post('/config')
@ajax_verify_token("config")
async def config_ajax(request):
    json = await request.json()

    config.display.from_string(json["config"])

    return aiohttp_web.json_response({"time": time_time(),
                                      "configUpdate": True,
                                      "msg": "updated"})


# EYE unused
#def package_cmd(cmd, data):
#    return dumps({"cmd": cmd,
#                  "data": data})


class BreakTimerWebSocket(WebSocketBase):
    def __init__(self, name):
        super().__init__(name)
        self.id = None
        self.verified = False

    async def send_time(self, time_data):
        if not self.verified:
            info("BreakTimerWebSocket: sendTime: not verified; %s remote=%s id=%s", self.name, self.remote, self.id)
            await self.close("sendTime: not verified")
            return

        info("BreakTimerWebSocket: %s send time %s; remote=%s id=%s", self.name, time_data, self.remote, self.id)
        await self.send_msg("time", time_data)

    async def send_times(self):
        if not self.verified:
            info("BreakTimerWebSocket: sendTimes: not verified; %s remote=%s id=%s",  self.name, self.remote, self.id)
            await self.close("sendTimes: not verified")
            return

        times = break_timer_sensors.break_timer_sensor_manager.get_times()

        ln = len(times)
        if ln >= 5:
            td = [times[0:2], " ... " , times[-2:]]
        else:
            td = [times, "", ""]

        info("BreakTimerWebSocket: %s send times %s%s%s; remote=% sid=%s", self.name, *td, self.remote, self.id)

        await self.send_msg("times", times)

    async def send_reset(self):
        if not self.verified:
            await self.close("sendReset: not verified")
            return

        info("BreakTimerWebSocket: %s send reset; id=%s", self.name, self.id)
        await self.send_msg("reset")

    async def cmd_register(self, data):
        access_token = data.get("tkn")
        if not verify_token(access_token, "pin", verbose=True):
            info("BreakTimerWebSocket: %s cmd register unverified; %s remote=%s",  self.name, data, self.remote)
            await self.close("cmd register: not verified")
            return

        self.id = data["id"]
        info("BreakTimerWebSocket: %s cmd register start %s; remote=%s id=%s", self.name, data, self.remote, self.id)
        self.verified = True
        name = self.remote
        filter_time = int(data.get("filterTime", 5))
        break_timer_sensors.break_timer_sensor_manager.register(self.id, name, None, ws=self, filter_time=filter_time)
        await self.send_msg("registered", {"registered": True})
        if data.get("data", True):
            await self.send_times()
        info("BreakTimerWebSocket: %s cmd register end %s; remote=%s id=%s", self.name, data, self.remote, self.id)

    async def onclose(self):
        info("BreakTimerWebSocket: %s onclose url=%s; remote=%s, id=%s", self.name, self.url, self.remote, self.id)
        break_timer_sensors.break_timer_sensor_manager.unregister(self.id)

    async def cmd_reset(self, data):
        if not self.verified:
            info("breakTimerSensors: reset register: not verified; %s remote=%s id=%s",  self.name, self.remote, self.id)
            await self.close("reset register: not verified")
            return

        filter_time = int(data.get("filterTime", 0))
        reset = int(data.get("reset", 1))

        info("BreakTimerWebSocket: %s cmd reset %s; remote=%s id=%s", self.name, data, self.remote, self.id)
        break_timer_sensors.break_timer_sensor_manager.reset_times(reset=reset, filter_time=filter_time)

    async def cmd_flash(self, data):
        if not self.verified:
            info("BreakTimerWebSocket: cmd flash: not verified; %s remote=%s id=%s",  self.name, self.remote, self.id)
            await self.close("cmd flash: not verified")
            return

        flash_laser_duration = int(data.get("flashtime", 10))

        info("BreakTimerWebSocket: %s cmd flash %s; remote=%s id=%s", self.name, data, self.remote, self.id)
        break_timer_sensors.break_timer_sensor_manager.flash_laser(flash_laser_duration)

    async def cmd_state(self, data):
        if not self.verified:
            info("BreakTimerWebSocket: cmd state: not verified; %s remote=%s id=%s",  self.name, self.remote, self.id)
            await self.close("cmd state: not verified")
            return

        info("BreakTimerWebSocket: %s cmd state %s; remote=%s id=%s", self.name, data, self.remote, self.id)
        sensor = break_timer_sensors.break_timer_sensor_manager.sensor
        return self.send_msg("state",  sensor.state())

    async def cmd_get(self, data):
        if not self.verified:
            info("BreakTimerWebSocket: cmd get: not verified; %s remote=%s id=%s",  self.name, self.remote, self.id)
            await self.close("cmd get: not verified")
            return

        times = break_timer_sensors.break_timer_sensor_manager.get_times()
        info("breaksensor: breakSensor %s ws get:  %s remote=%s id=%s", self.name, times, self.remote, self.id)
        self.send_msg("times", times)

    async def cmd_stop(self, data):
        if not self.verified:
            info("BreakTimerWebSocket: cmd stop: not verified; %s remote=%s id=%s",  self.name, self.remote, self.id)
            await self.close("cmd stop: not verified")
            return

        info("BreakTimerWebSocket: %s cmd stop %s; remote=%s id=%s", self.name, data, self.remote, self.id)
        sensor = break_timer_sensors.break_timer_sensor_manager.sensor
        await self.close("close request")


@routes.get('/ws/gettimes')
async def websocket_handler(request):
    ws = BreakTimerWebSocket("app")
    if await ws.prepare(request):
        await ws.process()
