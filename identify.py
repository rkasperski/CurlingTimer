"""
Implements methods that tell about the hardware capabiities of the current device.
"""
from time import time as time_time, \
    localtime as time_localtime, \
    strftime as time_strftime

from uuid import getnode as uuid_getnode
from os import path as os_path

from logger import error

from utils import my_ip_address, my_host_name
import http_utils as http
import config
from version import version as version_version, build_date as version_build_date

gather_device_info = None
my_app = None


def set_app(app):
    global my_app

    my_app = app


def get_app():
    return my_app


async def whoareyou(test_ip, port, timeout=None):
    return await http.get_url_json_response("whoareyou",
                                            f"{http.scheme}://{test_ip}:{port}/whoareyou",
                                            timeout=timeout)


async def get_epoch(test_ip, port, timeout=None):
    return await http.get_url_json_response("getEpoch",
                                       f"{http.scheme}://{test_ip}:{port}/epoch",
                                       timeout=timeout)


def get_info_path(path):
    print(f"AA {path=}")
    if not path:
        path = my_app.app()

    print(f"AB {path=}")
    if not os_path.exists(path):
        return None

    if path.endswith("info"):
        return path

    tpath = os_path.join(path, "info")
    print(f"AC {tpath=}")
    if os_path.exists(tpath):
        return tpath

    tpath = os_path.join(path, "_internal", "info")
    print(f"AD {tpath=}")
    if os_path.exists(tpath):
        return tpath

    return None

def get_build_date(path=None):
    bd_path = get_info_path(path)
    if not bd_path:
        error("Identify: failed to find build date file: <not specified>")
        return "unknown"

    bd_path = os_path.join(bd_path, "build_date.txt")

    try:
        with open(bd_path, "r", encoding="utf-8") as fp:
            date = fp.readline().strip()
    except OSError:
        error("Identify: failed to find build date file: %s", bd_path)
        date = "unknown"

    return date


def get_version(path=None):
    v_path = get_info_path(path)
    if not v_path:
        error("Identify: failed to find version file: <not specified>")
        return "unknown"

    v_path = os_path.join(v_path, "version.txt")
    try:
        with open(v_path, "r", encoding="utf-8") as f:
            version = f.readline().strip()
    except OSError:
        error("Identify: failed to find version file: %s", v_path)
        version = "0.0"

    return version


def whoami():
    name = my_host_name()

    lcl_time = time_time()
    local_time = time_localtime(lcl_time)
    mlsec = str(lcl_time).split('.')[1][:3]
    display_time = time_strftime("%H:%M:%S.", local_time) + mlsec

    config_display = config.display

    attributes = {
        "macId": (f"{uuid_getnode():x}"),
        "whoAmI": name,
        "ip": my_ip_address(),
        "port": http.port,
        "epochTimestamp": time_time(),
        "time": display_time,
        "configVersion": config_display.version(),
        "buildVersion": version_version,
        "buildDate": version_build_date,
        "hostname": my_host_name(),
        "configDate": config_display.modification_date(),
        }

    gather_device_info(attributes)

    return attributes


def register_device_info(device_info_func):
    global gather_device_info

    gather_device_info = device_info_func
