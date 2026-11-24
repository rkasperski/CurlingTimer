from logger import info
import zero_configuration_manager

device_monitor = None

class DeviceMonitor:
    def __init__(self):
        info("zeroconf: monitor clock devices")

        self.display_listener = zero_configuration_manager.monitor("_clockdisplay._tcp.local.")
        self.breaktimer_listener = zero_configuration_manager.monitor("_breaktimer._tcp.local.")

    def get_sensors(self):
        sensors = [{"name": snsr.name,
                    "ip": snsr.ip,
                    "port": snsr.port,
                    "type": "sensor"} for snsr in self.breaktimer_listener.services()]
        sensors.sort(key=lambda p: p["name"])
        return sensors

    def get_displays(self):
        displays = [{"name": dsp.name,
                     "ip": dsp.ip,
                     "port": dsp.port,
                     "type": "display"} for dsp in self.display_listener.services()]
        displays.sort(key=lambda p: p["name"])
        return displays

device_monitor = DeviceMonitor()

def get_device_monitor():
    return device_monitor
