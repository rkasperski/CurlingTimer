import time
import asyncio

from logger import info, debug, error
from utils import my_ip_address
import http_utils as http
from identify import whoareyou
import config
from access_verification import get_authenticator
from devices import get_device_monitor


async def update_one_config(ip, config_str, force=False):
    display_config = config.display

    old_peer_version = None
    if not force:
        peer_data = await whoareyou(ip, http.port)
        if peer_data:
            peer_version = peer_data["configVersion"]
            if display_config.version() > peer_version:
                old_peer_version = peer_version

            info("update config peer test version=%s peer=%s ip=%s",  display_config.version(), peer_version, ip)

    rc = True
    if force or old_peer_version:
        tkn = get_authenticator().create(expires=int(time.time()) + 3600, audience="config")

        json_response = await http.post_url_json_response("updateOneConfig",
                                                          f'{http.scheme}://{ip}:{http.port}/config',
                                                          json_data={"config": config_str},
                                                          headers={http.CLOCK_HDR: tkn},
                                                          timeout=10)

        info("update config ip=%s version=%s force=%s old_peer_version=%s response=%s rc=%s",
             ip, display_config.version(), force, old_peer_version, json_response, rc)

        rc = json_response is not None

    return rc


async def update_all_configs(force=True):
    display_config = config.display

    if display_config.modified:
        display_config.save()

    all_current = True
    my_ip = my_ip_address()

    config_string = display_config.to_string(time.time())

    ip_list = [sheet.ip for sheet in display_config.sheets if sheet.ip not in ("Unassigned", my_ip)] + \
        [snsr["ip"] for snsr in get_device_monitor().get_sensors()]

    for ip in ip_list:
        all_current = all_current and await update_one_config(ip, config_string, force=force)

    return all_current


async def keep_configs_current_task(app):
    next_check_time = time.time()
    sensor_ips = set()

    config_update_delay = 10

    while True:
        try:
            await asyncio.sleep(config_update_delay)

            check_sensor_ips = {s["ip"] for s in get_device_monitor().get_sensors()}

            if time.time() > next_check_time or check_sensor_ips != sensor_ips:
                if await update_all_configs(force=False):
                    config_update_delay = min(3600, config_update_delay + 30)
                else:
                    config_update_delay = 10

                next_check_time = time.time() + config_update_delay

        except asyncio.CancelledError:
            return
        except Exception as e:
            error("had an unexpected exception: %s", str(s), exc_info=True)


async def start_tasks(app):
    info("ConfigurationManager: stop tasks - start")

    app['config_update'] = asyncio.create_task(keep_configs_current_task(app))


async def stop_tasks(app):
    if 'config_update' in app:
        debug("ConfigurationManager: stop tasks - cancel")
        app['config_update'].cancel()

        debug("ConfigurationManager: stop tasks - done")
