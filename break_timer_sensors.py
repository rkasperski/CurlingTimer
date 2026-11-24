import asyncio
import time
import sys
import os
import http_utils as http_utils

from timers import BreakTimes
from logger import info, error, warning
from zero_configuration_manager import publish as zero_conf_manager_publish

cmd = "sudo /usr/bin/pigpiod -l"
rc = os.system(cmd)
warning("starting '%s': rc=%s", cmd, rc)
time.sleep(5)

import pigpio
pi = pigpio.pi()

break_timer_sensor_manager = None
break_timer_sensor = None


class BreakTimerServer(BreakTimes):
    def __init__(self, token_authenticator, sensor_name):
        super().__init__(name=sensor_name)

        self.listeners = {}
        self.token_authenticator = token_authenticator
        self.pending_send = []
        self.monitor = None

    def is_active(self):
        return True

    def start(self):
        if (not self.monitor) or self.monitor.cancelled():
            self.monitor = asyncio.ensure_future(self.time_monitor())

    def stop(self):
        if self.monitor:
            self.monitor.cancel()
            for _, _, ws in self.listeners.values():
                ws.close()

    async def time_monitor(self):
        try:
            while True:
                await asyncio.sleep(0.050)

                self.recording_state_change_notification(self.can_record())

                if len(self.pending_send) == 0:
                    continue

                to_send = self.pending_send.pop(0)

                await self.send_time(to_send)
        except asyncio.CancelledError:
            self.monitor = None
        finally:
            self.monitor = None

    def register(self, sensor_id, sensor, tgt_port=None, filter_time=5, ws=None):
        self.set_filter_time(filter_time)

        if sensor_id not in self.listeners:
            info("breaktimerserver: register: sensor=%s id=%s tgt_port=%s", sensor, sensor_id, tgt_port)
            self.listeners[sensor_id] = (sensor, tgt_port, ws)

    def unregister(self, sensor_id):
        if sensor_id in self.listeners:
            info("breaktimerserver:unregister: tgt-ip=%s", sensor_id)
            del self.listeners[sensor_id]

    def reset_times(self, reset=True, filter_time=5):
        super().reset_times(reset=reset, filter_time=filter_time)
        for _, (_, _, ws) in self.listeners.items():
            asyncio.ensure_future(ws.send_reset())

    async def send_time(self, break_time):
        for sensor_id, (sensor, _, ws) in list(self.listeners.items()):
            response = await ws.send_time(break_time)

            info("breaktimerserver:send_time: %s %s -> %s time=%s response=%s",
                 self.name, sensor, sensor_id, break_time, response)

    def recording_state_change_notification(self, can_record):
        if break_timer_sensor:
            break_timer_sensor.recording_state_change_notification(can_record)

    def add_time(self, break_time):
        if super().add_time(break_time):
            self.pending_send.append(break_time)


class BreakTimerSensor(BreakTimerServer):
    def __init__(self, token_authenticator, name="sensor", laser_pin=24, sensor_pin=19, indicator_pin=21,
                 laser_on_flash_ms=500, laser_off_flash_ms=500, recording_pin=None):
        super().__init__(token_authenticator, name)
        self.sensor_enabled = False
        self.sensor_pin = sensor_pin
        self.indicator_pin = indicator_pin
        self.laser_pin = laser_pin
        self.recording_pin = recording_pin
        self.start_flash_time = 0
        self.end_flash_time = 0
        self.is_flashing = False
        self.checking = False
        self.start_time = 0
        self.start_tick = 0
        self.pre_start_flash_time = 0
        self.post_end_flash_time = 0
        self.laser_on_flash_ms = laser_on_flash_ms
        self.laser_off_flash_ms = laser_off_flash_ms

        try:
            pi.set_mode(sensor_pin, pigpio.INPUT)
            pi.set_pull_up_down(sensor_pin, pigpio.PUD_DOWN)
            info("breaktimer: using pigpio sensor %s plugged in", name)
            pi.callback(sensor_pin, pigpio.EITHER_EDGE, self.pigpio_callback)
            level = pi.read(sensor_pin)
        except AttributeError:
            error("breaktimer: probably need to run pigpiod")
            sys.exit()

        pi.set_mode(laser_pin, pigpio.OUTPUT)
        pi.write(laser_pin, 0)

        pi.write(laser_pin, 1)

        if indicator_pin:
            pi.set_mode(indicator_pin, pigpio.OUTPUT)
            pi.write(indicator_pin, level)

        if recording_pin:
            pi.set_mode(recording_pin, pigpio.OUTPUT)
            pi.write(recording_pin, 0)

        info("breaktimer: initialized breaktimer %s sensor sensor=%s, indicator=%s laser=%s",
             name, sensor_pin, indicator_pin, laser_pin)

        asyncio.ensure_future(self.enable())        

    async def enable(self, wait_time=0.300):
        await asyncio.sleep(wait_time)

        self.sensor_enabled = True

    def recording_state_change_notification(self, can_record):
        if self.recording_pin:
            pi.write(self.recording_pin, 1 if can_record else 0)

    def pigpio_callback(self, pio, level, tick):
        # do adjustment to get close time of day
        cur_time = time.time() - pigpio.tickDiff(tick, pi.get_current_tick()) / 1000000

        if level:
            if self.indicator_pin:
                pi.write(self.indicator_pin, 1)

            # interval_time = cur_time - self.start_time
            interval_time = pigpio.tickDiff(self.start_tick, tick) / 1000000
            if self.is_flashing:
                flash_inner_time = self.end_flash_time - self.start_flash_time
                flash_outer_time = self.post_end_flash_time - self.pre_start_flash_time
                diff_time = interval_time - flash_outer_time
                r = (self.start_time, cur_time,  diff_time)
                info("""flashing: %s diff=%.5f
detect=%.5f, %.5f, %.5f
flash_inner=%.5f, %.5f, %.5f
flash_outer=%.5f, %.5f, %.5f
startDelay=%.5f
endDelay=%.5f""",
                     self.name, diff_time,
                     interval_time, flash_inner_time, flash_outer_time,
                     flash_inner_time, self.start_flash_time, self.end_flash_time,
                     flash_outer_time, self.pre_start_flash_time, self.post_end_flash_time,
                     self.start_flash_time - self.pre_start_flash_time,
                     self.post_end_flash_time - self.end_flash_time)
            else:
                r = (self.start_time, self.start_time + interval_time, interval_time)
                info("breaksensor: %s %s", self.name, r)

            if self.sensor_enabled:
                self.add_time(r)
        else:
            self.start_tick = tick
            self.start_time = cur_time
            if self.indicator_pin:
                pi.write(self.indicator_pin, 0)

        return

    def state(self):
        return pi.read(self.sensor_pin)

    def off(self):
        pi.write(self.laser_pin, 0)

    async def flash(self, duration):
        self.is_flashing = True
        on_time_secs = self.laser_on_flash_ms / 1000.0
        off_time_secs = self.laser_off_flash_ms / 1000.0
        await asyncio.sleep(on_time_secs)

        flash_end_time = time.time() + duration
        while time.time() <= flash_end_time:
            self.pre_start_flash_time = time.time()
            pi.write(self.laser_pin, 0)
            self.start_flash_time = time.time()

            await asyncio.sleep(off_time_secs)

            self.end_flash_time = time.time()
            pi.write(self.laser_pin, 1)
            self.post_end_flash_time = time.time()

            await asyncio.sleep(on_time_secs / 2)
            diff = self.end_flash_time - self.start_flash_time
            self.add_time((self.start_flash_time, self.end_flash_time, diff))
            info("flash: %s %s", self.name, (self.start_flash_time, self.end_flash_time, diff))
            await asyncio.sleep(on_time_secs / 2)

        pi.write(self.laser_pin, 1)

        self.is_flashing = False


class BreakTimerSensorManager():
    def __init__(self, sensor):
        self.sensor = sensor
        sensor.start()

    def publish(self, port=None):
        zero_conf_manager_publish("_breaktimer._tcp.local.", port if port else http_utils.port)

    def flash_laser(self, flash_duration=10):
        try:
            asyncio.ensure_future(self.sensor.flash(flash_duration))
        except (KeyError, ValueError):
            return "error"

    def off(self):
        self.sensor.off()

    def get_times(self):
        try:
            return self.sensor.get_times()
        except KeyError:
            return (-1, 0, [])

    def reset_times(self, reset=True, filter_time=5):
        try:
            self.sensor.reset_times(reset=reset, filter_time=filter_time)
            info("breaksensor: Sensor reset: %s reset=%s filter=%s",
                 self.sensor.name, reset, filter_time)
            return True
        except KeyError:
            info("breaksensor: Sensor reset: doesn't exist: %s", self.sensor.name)
            return False

    def register(self, sensor_id, sensor, tgt_port=None, ws=None, filter_time=None):
        try:
            if filter_time is None:
                filter_time = 5

            self.sensor.register(sensor_id, sensor, tgt_port, ws=ws, filter_time=filter_time)
            info("breaksensor: Sensor Register: %s %s ==> %s:%s",
                 self.sensor.name, sensor, sensor_id, tgt_port)
        except KeyError:
            info("breaksensor: Sensor Register: doesn't exist: %s %s ==> %s:%s",
                 self.sensor.name, sensor, sensor_id, tgt_port)

    def unregister(self, tgt_ip):
        try:
            self.sensor.unregister(tgt_ip)
            info("breaksensor: Sensor Unregister: %s %s",
                 self.sensor.name, tgt_ip)
        except KeyError:
            info("breaksensor: Sensor Unregister: doesn't exist: %s %s",
                 self.sensor.name, tgt_ip)


def create(config, token_authenticator, port=None):
    global break_timer_sensor, break_timer_sensor_manager

    break_timer_sensor = BreakTimerSensor(token_authenticator,
                                          name=config.name,
                                          laser_pin=config.laser_pin,
                                          sensor_pin=config.sensor_pin,
                                          recording_pin=config.recording_pin,
                                          indicator_pin=config.indicator_pin,
                                          laser_on_flash_ms=config.laser_on_flash_ms,
                                          laser_off_flash_ms=config.laser_off_flash_ms)

    break_timer_sensor_manager = BreakTimerSensorManager(break_timer_sensor)

    break_timer_sensor_manager.publish(port)
    return break_timer_sensor_manager
