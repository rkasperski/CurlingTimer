import asyncio
import json
import logging
import socket
import sys
import os

from Utils import myIPAddress, myHostName
import Logger

from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceListener, ServiceStateChange, ZeroconfServiceTypes
import zeroconf

zeroconf.DNS_TTL = 60

registeredServices = []

zc = None

def getZc():
    global zc

    if not zc:
        zc = Zeroconf()

    return zc


class ServiceData:
    __slots__ = ("service", "name", "ip", "port", "properties")

    def __init__(self, service, name, ip, port, properties):
        self.service = service
        self.name = name
        self.ip = ip
        self.port = port
        self.properties = properties

    def __repr__(self):
        return str([self.service, self.name, self.ip, self.port, self.properties])

def jsonDecoder(bs):
    return json.loads(bs.decode("utf-8"))

class ServiceListener(ServiceListener):
    def __init__(self, service_type=None, decoder=None):
        self.service_type = service_type
        self.decoder = decoder if decoder else jsonDecoder
        self.found_services = {}

    def setDecoder(self, decoder):
        # decode takes one parameter which is a byte-array
        self.decoder = decoder

    def add_service(self,zc, service_type, name):
        self.add_gather(zc, service_type, name)

    def services(self):
        return self.found_services.values()

    def update_service(self, zc, type, name):
        pass

    def add_gather(self, zc, service_type, name):
        zc = getZc()

        self.service_type = service_type
        info = zc.get_service_info(service_type, name)
        if info is None:
            Logger.info("zeroconf: gather: failed to get data for %s %s", service_type, name)
            return

        properties = info.properties
        if self.decoder:
            properties = {p.decode("utf-8") : self.decoder(v) for p, v in info.properties.items()}

        try:
            ip = socket.inet_ntoa(info.addresses[0])
        except TypeError:
            Logger.info("zeroconf: gather: failed to interpret ip %s %s %s", service_type, name, info)
            if "__ip" in properties:
                ip = properties["__ip"]
                Logger.info("zeroconf: gather: backup ip %s %s %s", service_type, name, ip)
            else:
                return

        sp = name.split(".", 1)
        Logger.info("zeroconf: add %s %s %s %s", service_type, name, ip, properties)
        if self.add(service_type, sp[0], ip, info.port, properties):
            self.found_services[name] = ServiceData(service_type, sp[0], ip, info.port, properties)

    def add(self, service_type, name, ip, port, properties):
        return True

    def remove_service(self, zc, service_type, name):
        Logger.info("zeroconf: remove %s %s - start", service_type, name)
        if self.remove(service_type, name):
            try:
                del self.found_services[name]
            except KeyError:
                pass
        Logger.info("zeroconf: remove %s %s - done", service_type, name)

    def remove(self, service_type, name):
        return True

    async def verify(self, deleteIfBad=True):
        zc = getZc()

        services = list(self.items())
        for name, d in services:
            info = await zc.get_service_info(self.service_type, name)

            if info.address is None and info.port is None:
                if deleteIfBad:
                    if self.remove(self.service_type, name):
                        try:
                            del self.found_services[name]
                        except KeyError:
                            pass
                continue

            ip = socket.inet_ntoa(info.address) if info.address else None
            self.verified(name, *d)

    def verified(self, name, ip, port, properties):
        Logger.debug("zeroconf: verified %s %s %s %s", service_type, name, ip, properties)

def jsonEncoder(s):
    return json.dumps(s).encode("utf-8")


def publish(service_type, port, properties={}, encoder=None):
    zc = getZc()

    ip = myIPAddress()
    hostName = myHostName()

    encoder = encode if encoder else jsonEncoder

    name = "{0}.{1}.{2}".format(hostName, ip, service_type)

    if "__ip" not in properties:
        properties["__ip"] = ip

    if encoder:
        properties = {p: encoder(v) for p, v in properties.items()}


    info = ServiceInfo(service_type,
                       name,
                       addresses=[socket.inet_aton(ip)], port=port,
                       properties=properties)

    Logger.info("zeroconf: publish %s %s %s %s", service_type, name, port, properties)
    registeredServices.append(info)
    zc.register_service(info, ttl=30)

serviceBrowsers = []
def monitor(service_type, listener=None, decoder=None):
    global serviceBrowsers
    
    if listener is None:
        listener = ServiceListener(decoder=decoder)
    elif decoder:
        listener.setDecoder(decoder)

    browser = ServiceBrowser(getZc(), service_type, listener=listener)
    serviceBrowsers.append(browser)
    return listener

async def close():
    Logger.info("Zero Conf manager: stop tasks - start" )
    zc = getZc()
    
    try:
        Logger.info("Zero Conf manager: stop tasks - stop browsers" )
        for serviceBrowser in serviceBrowsers:
            Logger.info("Zero Conf manager: stop tasks - cancel service browser %s", serviceBrowser)
            serviceBrowser.cancel()
            Logger.info("Zero Conf manager: stop tasks - await service browser %s", serviceBrowser)
            await serviceBrowser.task
            
        Logger.info("Zero Conf manager: stop tasks - unregister services" )
        Logger.info("Zero Conf manager: stop tasks - zc close" )
        await zc.close()
    except Exception as e:
         Logger.error("zero conf: shutdown error %s", e)

    Logger.info("Zero Conf manager: stop tasks - done" )

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    if len(sys.argv) > 1:
        assert sys.argv[1:] == ['--debug']
        logging.getLogger('zeroconf').setLevel(logging.DEBUG)

    loop = asyncio.get_event_loop()

    zc = getZc()

    async def list_service():
        los = await ZeroconfServiceTypes.find(zc,timeout=5.0)

    ll = asyncio.ensure_future(list_service())

    clockDisplays = monitor("_clockdisplay._tcp.local.")
    breakTimers = monitor("_breaktimer._tcp.local.")
    hardwareClocks = monitor("_hwclock._tcp.local.")

    async def checkServices():
        while True:
            await asyncio.sleep(10)

            await breakTimers.verify()
            await clockDisplays.verify()
            await hardwareClocks.verify()

    clockdisplays = publish("_clockdisplay._tcp.local.", 80)
    breaktimers = publish("_breaktimer._tcp.local.", 80, {"sensors": ["sensora", "sensorb"]})
    hwclocks = publish("_hwclock._tcp.local.", 8143)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("Unregistering...")
        loop.run_until_complete(close())
    finally:
        loop.close()
