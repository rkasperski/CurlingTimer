from time import monotonic as time_monotonic

from logger import info
from timers import BreakTimes

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
    def __init__(self, name, filter_time):
        super().__init__(name, filter_time)
        self.update_time = time_monotonic()

    def __repr__(self):
        return str([self.name, self.filter_time])

    async def reset_times(self, reset=True, filter_time=0):
        super().reset_times(reset=reset, filter_time=filter_time)

        info("breaksensor: reset_times:%s", self.name)
        self.update_time = time_monotonic()
        return True


class DisplayBreakTimeTracker(BreakTimes):
    def __init__(self):
        # times are filtered at sensors. want close times from two differenct
        # sensors to be displayed
        super().__init__(name="Display", filter_time=0)
        self.active_sensors = {}
        self.update_time = time_monotonic()

    def get_last_update_time(self):
        return self.update_time

    def set_active_sensors(self, sensors):
        self.active_sensors = {}
        for sensor in sensors:
            name = sensor["name"]
            self.active_sensors[name] = BreakSensor(name, sensor["colour"], sensor["name"], sensor["ip"], placement=sensor["placement"])

        self.update_time = time_monotonic()

    def get_active_sensors(self):
        return self.active_sensors.values()

    def sensor_colour(self, name):
        try:
            sensor = self.active_sensors[name]
            return sensor.colour
        except (KeyError, IndexError):
            return "white"

    def get_times(self):
        return super().get_times()

    def reset_sensor(self, name):
        self.times = [t for t in self.times if t[-1] != name]
        self.update_time = time_monotonic()

    def reset_times(self, reset=True):
        super().reset_times(reset=reset)
        self.update_time = time_monotonic()

    def add_time(self, name, new_break_time):
        try:
            info("breaksensor: receieved time: %s %s", name, new_break_time)
            new_break_time.append(name)
            super().add_time(new_break_time)
            self.update_time = time_monotonic()
        except KeyError:
            info("breaksensor: Sensor not found: %s", name)
