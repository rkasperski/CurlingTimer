from asyncio import get_event_loop as asyncio_get_event_loop, \
    ensure_future as asyncio_ensure_future, \
    sleep as asyncio_sleep
from json import loads as json_loads, dumps as json_dumps
from logging import basicConfig as logging_basicConfig, \
    getLogger as logging_getLogger, \
    INFO as logging_INFO, DEBUG as logging_DEBUG
from socket import inet_ntoa as socket_inet_ntoa, \
    inet_aton as socket_inet_aton
from sys import argv as sys_argv

from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceListener, ZeroconfServiceTypes
import zeroconf

from utils import my_ip_address, my_host_name
from logger import info, debug, error, \
    log_to_stdout as logger_log_to_stdout, \
    setLevel as logger_setLevel

zeroconf.DNS_TTL = 60

registered_services = []

global_zc = None

def get_zc():
    global global_zc

    if not global_zc:
        global_zc = Zeroconf()

    return global_zc


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

def json_decoder(bs):
    return json_loads(bs.decode("utf-8"))

class ServiceListener(ServiceListener):
    def __init__(self, service_type=None, decoder=None):
        self.service_type = service_type
        self.decoder = decoder if decoder else json_decoder
        self.found_services = {}

    def setDecoder(self, decoder):
        # decode takes one parameter which is a byte-array
        self.decoder = decoder

    def add_service(self, zc, service_type, name):
        self.add_gather(zc, service_type, name)

    def services(self):
        return self.found_services.values()

    def update_service(self, zc, type, name):
        pass

    def add_gather(self, zc, service_type, name):
        zc = get_zc()

        self.service_type = service_type
        service_info = zc.get_service_info(service_type, name)
        if service_info is None:
            info("zeroconf: gather: failed to get data for %s %s", service_type, name)
            return

        properties = service_info.properties
        if self.decoder:
            properties = {p.decode("utf-8") : self.decoder(v) for p, v in service_info.properties.items()}

        try:
            ip = socket_inet_ntoa(service_info.addresses[0])
        except TypeError:
            info("zeroconf: gather: failed to interpret ip %s %s %s", service_type, name, service_info)
            if "__ip" in properties:
                ip = properties["__ip"]
                info("zeroconf: gather: backup ip %s %s %s", service_type, name, ip)
            else:
                return

        sp = name.split(".", 1)
        info("zeroconf: add %s %s %s %s", service_type, name, ip, properties)
        if self.add(service_type, sp[0], ip, service_info.port, properties):
            self.found_services[name] = ServiceData(service_type, sp[0], ip, service_info.port, properties)

    def add(self, service_type, name, ip, port, properties):
        return True

    def remove_service(self, zc, service_type, name):
        info("zeroconf: remove %s %s - start", service_type, name)
        if self.remove(service_type, name):
            try:
                del self.found_services[name]
            except KeyError:
                pass
        info("zeroconf: remove %s %s - done", service_type, name)

    def remove(self, service_type, name):
        return True

    async def verify(self, delete_if_bad=True):
        zc = get_zc()

        services = list(self.items())
        for name, d in services:
            service_info = await zc.get_service_info(self.service_type, name)

            if service_info.address is None and service_info.port is None:
                if delete_if_bad:
                    if self.remove(self.service_type, name):
                        try:
                            del self.found_services[name]
                        except KeyError:
                            pass
                continue

            # ip = socket_inet_ntoa(service_info.address) if service_info.address else None
            self.verified(name, *d)

    def verified(self, name, ip, port, properties):
        debug("zeroconf: verified %s %s %s %s", service_type, name, ip, properties)

def json_encoder(s):
    return json_dumps(s).encode("utf-8")


def publish(service_type, port, properties={}, encoder=None):
    zc = get_zc()

    ip = my_ip_address()
    host_name = my_host_name()

    encoder = encoder if encoder else json_encoder

    name = f"{host_name}.{ip}.{service_type}"

    if "__ip" not in properties:
        properties["__ip"] = ip

    if encoder:
        properties = {p: encoder(v) for p, v in properties.items()}


    service_info = ServiceInfo(service_type,
                               name,
                               addresses=[socket_inet_aton(ip)], port=port,
                               properties=properties)

    info("zeroconf: publish %s %s %s %s", service_type, name, port, properties)
    registered_services.append(service_info)
    zc.register_service(service_info, ttl=30)

service_browsers = []
def monitor(service_type, listener=None, decoder=None):
    global service_browsers

    if listener is None:
        listener = ServiceListener(decoder=decoder)
    elif decoder:
        listener.setDecoder(decoder)

    browser = ServiceBrowser(get_zc(), service_type, listener=listener)
    service_browsers.append(browser)
    return listener

async def close():
    info("Zero Conf manager: stop tasks - start" )
    zc = get_zc()

    try:
        info("Zero Conf manager: stop tasks - stop browsers" )
        for service_browser in service_browsers:
            info("Zero Conf manager: stop tasks - cancel service browser %s", service_browser)
            service_browser.cancel()
            info("Zero Conf manager: stop tasks - await service browser %s", service_browser)
            await service_browser.task

        info("Zero Conf manager: stop tasks - unregister services" )
        info("Zero Conf manager: stop tasks - zc close" )
        await zc.close()
    except Exception as e:
        error("zero conf: shutdown error %s", e)

    info("Zero Conf manager: stop tasks - done" )

def test_main():
    logging_basicConfig(level=logging.DEBUG)
    logging_getLogger('zeroconf').setLevel(logging.INFO)
    logger_log_to_stdout()
    logger_setLevel(logging_INFO)

    if len(sys_argv) > 1:
        assert sys_argv[1:] == ['--debug']
        logging_getLogger('zeroconf').setLevel(logging_DEBUG)

    loop = asyncio_get_event_loop()

    zc = get_zc()

    async def list_service():
        await ZeroconfServiceTypes.find(zc, timeout=5.0)

    lister_service_task = asyncio_ensure_future(list_service())

    clock_displays_monitor = monitor("_clockdisplay._tcp.local.")
    break_timers_monitor = monitor("_breaktimer._tcp.local.")
    hardware_clocks_monitor = monitor("_hwclock._tcp.local.")

    async def check_services():
        while True:
            await asyncio_sleep(10)

            await clock_displays_monitor.verify()
            await break_timers_monitor.verify()
            await hardware_clocks_monitor.verify()

    clock_displays_publish = publish("_clockdisplay._tcp.local.", 80)
    break_timers_publish = publish("_breaktimer._tcp.local.", 80, {"sensors": ["sensora", "sensorb"]})
    hardware_clocks_publish = publish("_hwclock._tcp.local.", 8143)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        info("Unregistering...")
        loop.run_until_complete(close())
    finally:
        loop.close()

if __name__ == '__main__':
    test_main()
