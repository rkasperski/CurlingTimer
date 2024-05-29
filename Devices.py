from Logger import info
import ZeroConfManager


class DeviceMonitor:
    def __init__(self):
        info("zeroconf: monitor clock devices")

        self.displayListener = ZeroConfManager.monitor("_clockdisplay._tcp.local.")
        self.breaktimerListener = ZeroConfManager.monitor("_breaktimer._tcp.local.")

    def getSensors(self):
        sensors = [{"name": snsr.name,
                    "ip": snsr.ip,
                    "port": snsr.port,
                    "type": "sensor"} for snsr in self.breaktimerListener.services()]
        sensors.sort(key=lambda p: p["name"])
        return sensors
        
    def getDisplays(self):
        displays = [{"name": dsp.name,
                     "ip": dsp.ip,
                     "port": dsp.port,
                     "type": "display"} for dsp in self.displayListener.services()]
        displays.sort(key=lambda p: p["name"])
        return displays

    
deviceMonitor = DeviceMonitor()
