"""
Implements the websockets interfaces used for break timer communication
"""
import time
import asyncio

from aiohttp import web as aiohttp_web

from logger import info
from access_verification import verify_token
from utils import my_host_name
import curling_clock_manager
from rock_throw import RockTimingEvents
from web_socket import WebSocketBase

routes = aiohttp_web.RouteTableDef()


# @routes.post('/breatkimer/display')
# @ajax_verify_token("pin")
# async def break_timer_display_times_ajax(request):
#     json = await request.json()

#     if json.get("clear", False):
#         curling_clock_manager.manager.break_time_display_clear()
#     else:
#         times = json.get("times", [])
#         for t, c in reversed(times):
#             curling_clock_manager.manager.set_break_time_display(float(t), c)

#     return aiohttp_web.json_response({"action": "display"})


class BreakTimer_monitor(WebSocketBase):
    def __init__(self, sensor, web_socket_display, host_name, access_token, verbose=0):
        super().__init__(sensor["name"], verbose=verbose)
        self.id = None
        self.sensor = sensor
        self.web_socket_display = web_socket_display
        self.break_timer_url = f'ws://{self.sensor["ip"]}/ws/gettimes'
        self.my_host_name = host_name
        self.access_token = access_token

    async def connect(self):
        info("BreakTimer_monitor: connect %s remote: %s", self.break_timer_url, self.remote)
        await super().connect(self.break_timer_url)

    async def onclose(self):
        info("BreakTimer_monitor: onclose %s %s; remote: %s", self.name, self.break_timer_url, self.remote)
        if self.web_socket_display:
            self.web_socket_display.disconnect_sensor(self.sensor)

    async def cmd_time(self, time):
        info("BreakTimer_monitor: %s received time %s; remote: %s", self.name, time, self.remote)
        if self.web_socket_display:
            curling_clock_manager.manager.reset_idle_time()
            self.web_socket_display.add_time(self.name, time)

    async def cmd_times(self, times):
        info("BreakTimer_monitor: %s revceived times; remote: %s", self.name, self.remote)
        if self.web_socket_display:
            self.web_socket_display.add_times(self.name, times)

    async def cmd_reset(self, data):
        info("BreakTimer_monitor: %s receieved reset; ignored; remote: %s", self.name, self.remote)

    async def cmd_registered(self, data):
        info("BreakTimer_monitor: %s received registered; data=%s remote: %s id=%s", self.name, data, self.remote, self.id)

    async def register(self):
        await self.send_msg("register", {"tkn": self.access_token,
                                         "id": self.my_host_name,
                                         "name": self.my_host_name,
                                         "data": True,
                                         "filterTime": 5})
        info("BreakTimer_monitor: %s send register remote: %s", self.my_host_name, self.remote)

    async def onconnect(self):
        info("BreakTimer_monitor: %s onconnect remote: %s", self.my_host_name, self.remote)

        await self.register()

    def disconnect(self):
        self.web_socket_display = None

class BreakTimeDisplayWebSocket(WebSocketBase):
    def __init__(self, name, verbose=False):
        super().__init__(name, verbose=verbose)
        self.id = None
        self.active_sensors = {}
        self.active_sensor_count = 0
        self.verified = False
        self.rock_throw = None
        self.update_time = 0
        self.current_events = None
        self.times_by_sensor = {}

    def call_on_view_change(self, new_view):
        if new_view != curling_clock_manager.manager.view_break_time_update:
            info("BreakTimerDisplayWebSocket: %s view change", self.id)
            asyncio.create_task(self.send_msg("endsession", {"msg": "view change"}))

    def add_time(self, sensor, tm):
        if self.rock_throw:
            tm.append(sensor)
            evnt = self.rock_throw.check_for_event(tm)

            if evnt:
                self.current_events = [evnt]
                self.update_time = time.monotonic()

            return evnt

        return None

    def show_initial_times(self):
        if not self.rock_throw:
            return

        self.rock_throw.clear()
        curling_clock_manager.manager.break_time_clear()

        times_list = []

        for times in self.times_by_sensor.values():
            times_list += times

        times_list.sort()

        events = []
        for tm in times_list:
            evnt = self.rock_throw.check_for_event(tm)
            if evnt:
                events.append(evnt)

        if events:
            self.current_events = events
            self.update_time = time.monotonic()

        return None

    def add_times(self, sensor, sensor_times):
        sensor_times = [list(tm) + [sensor] for tm in sensor_times]

        self.times_by_sensor[sensor] = sensor_times

        if len(self.times_by_sensor) == self.active_sensor_count:
            self.show_initial_times()

    async def cmd_register(self, data):
        access_token = data.get("tkn")
        if not verify_token(access_token, "pin", verbose=True):
            info("BreakTimerDisplay: register: %s failed bad tkn %s; %s", self.remote, access_token, self.id, )
            await self.close("register: bad token")
            return

        info("BreakTimeDisplayWebSocket: register received; start %s: %s; %s", self.remote, data, self.id)

        self.verified = True
        self.id = data["id"]
        sensors = data["sensors"]
        circumference = 0.910
        sensor_to_placement_map = {sensor["name"]: sensor["placement"] for sensor in sensors}
        placement_to_colour_map = {sensor["placement"]: sensor["colour"] for sensor in sensors}

        self.rock_throw = RockTimingEvents(sensor_to_placement_map,
                                           placement_to_colour_map,
                                           circumference_in_meters=circumference)

        self.active_sensor_count = len(sensors)
        self.times_by_sensor = {}

        # filter_time = int(data.get("filterTime", 5))
        await self.send_msg("registered", {"registered": True})

        host_name = my_host_name()
        for sensor in sensors:
            bt = BreakTimer_monitor(sensor, self, host_name, access_token)
            self.active_sensors[bt.name] = bt
            asyncio.ensure_future(bt.connect())

            info("BreakTimerDisplay: register end %s: %s", self.id, data)

        curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_break_time_update)
        info("BreakTimeDisplayWebSocket: register received; done %s: %s; %s",self.remote, data, self.id)

    async def disconnect_sensor(self, sensor):
        bt = BreakTimer_monitor(sensor, self, host_name, access_token)

        del self.active_sensors[bt.name]

        # self.close_sensors()
        self.close()

    async def close_sensors(self):
        for bt in self.active_sensors.values():
            bt.disconnect()

        for bt in self.active_sensors.values():
            await bt.close()

        self.active_sensors = {}

    async def onclose(self):
        info("BreakTimeDisplayWebSocket: onclose; start %s; %s", self.remote, self.id)
        await self.close_sensors()

        curling_clock_manager.manager.register_rock_throw_listener(None)
        info("BreakTimeDisplayWebSocket: onclose; done %s; %s", self.remote, self.id)

    async def cmd_stop(self, data):
        info("BreakTimeDisplayWebSocket: stop received; %s; %s", self.remote, self.id)
        await self.close()

    def get_last_update_time(self):
        return self.update_time

    def get_events(self):
        return self.current_events

    def clear_events(self):
        self.current_events = None
        self.update_time = 0

    async def cmd_reset(self, data):
        info("BreakTimeDisplayWebSocket: reset received; start %s; %s", self.remote, self.id)
        if not self.verified:
            info("BreakTimerDisplayWebSocket: reset %s: not verified; %s", self.remote, self.id)
            await self.close()
            return

        if self.rock_throw:
            self.rock_throw.clear()
            curling_clock_manager.manager.break_time_clear()

        info("BreakTimeDisplayWebSocket: reset received; end %s", self.id)


@routes.get('/ws/breaktimerdisplay')
async def websocket_handler(request):
    ws = BreakTimeDisplayWebSocket("display", verbose=0)

    curling_clock_manager.manager.register_rock_throw_listener(ws)

    rc = None
    if await ws.prepare(request):
        curling_clock_manager.manager.set_call_on_view_change(ws.call_on_view_change)

        rc = await ws.process()
        await ws.close_sensors()
        curling_clock_manager.manager.clear_set_call_on_view_change(ws.call_on_view_change)

    curling_clock_manager.manager.register_rock_throw_listener(None)

    return rc
