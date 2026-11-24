import asyncio
import time
import datetime
import os
import random
import re
import string
import sys

from aiohttp import web as aiohttp_web

from logger import warning, info, debug, error, \
    log_entries, clear_logs, \
    level_map as logger_level_map, \
    setLevel as logger_set_level , \
    getLevelName as logger_get_level_name
import http_utils as http
from iot_ssl import get_info_ssl_certificate, generate_ssl_certificate


from utils import MemUsage, mem_usage, YEAR_IN_SECONDS, head_tail, run_command
from access_verification import ajax_verify_token, verify_user, is_administrator, get_authenticator
from config import get_display_config
from identify import whoareyou, whoami, get_app, get_version
from clock_authenticator import pin_expire_time
import setup_app
from devices import get_device_monitor

has_hardware_clock = False # pylint: disable=invalid-name

routes = aiohttp_web.RouteTableDef()  # pylint: disable=invalid-name

hardware_config = None  # pylint: disable=invalid-name
system_stats = []  # pylint: disable=invalid-name
curling_clock_manager = None # pylint: disable=invalid-name

def register_hardware_config(hardware_config_parm):
    global hardware_config # pylint: disable=global-statement

    hardware_config = hardware_config_parm


def register_curling_clock_manager(prm_curling_clock_manager):
    global curling_clock_manager # pylint: disable=global-statement

    curling_clock_manager = prm_curling_clock_manager


def register_hardware_clock(prm_has_hardware_clock):
    global has_hardware_clock # pylint: disable=global-statement

    has_hardware_clock = prm_has_hardware_clock

async def delayed_restart(delay=5, reboot=False):
    await asyncio.sleep(delay)
    if reboot:
        os.system("sudo reboot")
    else:
        sys.exit()


async def collect_system_stats_task(_app):
    global system_stats # pylint: disable=global-statement, global-variable-not-assigned

    try:
        while 1:
            system_stats.append(mem_usage())
            # collect every 30 minutes
            await asyncio.sleep(60*30)
    except asyncio.CancelledError:
        return


async def start_tasks(app):
    app['system_stats_collector'] = asyncio.create_task(collect_system_stats_task(app))


async def stop_tasks(app):
    if 'system_stats_collector' in app:
        info("CommonRoutes: stop tasks - start")
        info("CommonRoutes: stop tasks - cancel")
        app['system_stats_collector'].cancel()
        info("CommonRoutes: stop tasks - done")


async def sensor_info_collector(sensor_list):
    sensor_servers_inspected = {"Unassigned"}
    break_sensor_info = []
    for sensor_ip, sensor_name in sensor_list:
        if sensor_ip in sensor_servers_inspected:
            continue

        sensor_servers_inspected.add(sensor_ip)

        sensor_identity = await whoareyou(sensor_ip, http.port)
        if sensor_identity:
            break_sensor_info.append([sensor_name, sensor_identity])

    return break_sensor_info


@routes.post('/shutdown')
@ajax_verify_token("admin")
async def shutdown_ajax(_request):
    info("app: shutting down...")
    os.system("sudo shutdown now")
    return aiohttp_web.json_response({"shutdown": 1})


@routes.get('/whoareyou')
async def who_am_i_ajax(_request):
    return aiohttp_web.json_response(whoami())


@routes.get('/epoch')
async def epoch_ajax(_request):
    return aiohttp_web.json_response({"epoch": time.time()})


async def wait_for_restart(wait=3):
    if wait:
        await asyncio.sleep(wait)

    sys.exit()


@routes.post('/sslconfig/upload')
@ajax_verify_token("admin")
async def ssl_config_upload_ajax(request):
    if request.content_length > 5000000:
        # need failure response
        return aiohttp_web.HTTPRequestEntityTooLarge(location="/")

    reader = aiohttp_web.MultipartReader.from_response(request)
    while True:
        part = await reader.next()
        if part is None:
            break

        if not part.filename:
            break

        dir_path = get_app().config("ssl")

        fname = None
        text = await part.read()
        if part.filename.lower().endswith(".key"):
            fname = os.path.join(dir_path, "current.key")
        elif part.filename.lower().endswith(".crt"):
            fname = os.path.join(dir_path, "current.crt")

        if fname is None:
            return aiohttp_web.HTTPUnsupportedMediaType()

        with open(fname, "wb+") as f:
            f.write(text)

    ssl_info = get_info_ssl_certificate(dir_path, "current.crt")
    return aiohttp_web.json_response({"type": "uploaded",
                                      "info": ssl_info})


@routes.post('/sslconfig/generate')
@ajax_verify_token("admin")
async def ssl_config_generate_local_ajax(_request):
    hosts = []
    config = get_display_config()
    if config.organization.hosts:
        hosts = [s.strip() for s in config.organization.hosts.strip().split(",")]

    dir_path = setup_app.app.config("ssl/")
    key_path = os.path.join(dir_path, "current.key")
    cert_path = os.path.join(dir_path, "current.crt")

    my_hosts = [sheet.host_name for sheet in config.sheets]
    ip_list = [sheet.ip for sheet in config.sheets if sheet.ip and sheet.ip.lower() != "unassigned"]

    generate_ssl_certificate(certificate_file=cert_path,
                             key_file=key_path,
                             domain=config.organization.domain,
                             address=config.organization.address,
                             city=config.organization.city,
                             region=config.organization.region,
                             organization=config.organization.organization,
                             unit=config.organization.unit,
                             email=config.organization.email,
                             hosts=hosts + my_hosts,
                             ips=ip_list)

    ssl_info = get_info_ssl_certificate(dir_path, "current.crt")
    return aiohttp_web.json_response({"type": "generated",
                                      "info": ssl_info})


@routes.post('/sslconfig/info')
@ajax_verify_token("admin")
async def ssl_config_info_ajax(_request):
    dir_path = setup_app.app.config("ssl")

    ssl_info = get_info_ssl_certificate(dir_path, "current.crt")
    return aiohttp_web.json_response({"type": "info",
                                      "info": ssl_info})


@routes.get('/logout')
async def logout_html_get(_request):
    redirect_response = aiohttp_web.HTTPFound('/login')

    return redirect_response


re_date_time = re.compile(r"^(?:Log Time: *)?(?P<logtime>(?:\d+-\d+-\d+ *\d+:\d+:\d+(?:\.\d+)?)|(?:[a-zA-Z]{3} *\d* *\d+:\d+:\d))", re.I)


def split_date_time(lt):
    m = re_date_time.split(lt)

    if m[1:]:
        return m[1:]

    return [p.strip() for p in lt.split(":", 1)]


@routes.post('/secret/check')
async def secret_test_html_post(_request):
    config = get_display_config()

    source = string.ascii_letters + string.digits
    msg = ''.join((random.choice(source) for i in range(128)))
    msg_encoded = get_authenticator().encode(msg)

    offset = "HWCLOCK" if has_hardware_clock else "-"

    _, tail = head_tail("/var/run/ptpd2.status", head_lines=0, tail_lines=100)
    tail = [split_date_time(tl) for tl in tail]
    ptpd2_data = map_ptpd2_status_report(tail)

    offset = ptpd2_data.get("offset", offset)

    return aiohttp_web.json_response({"enc": msg_encoded,
                                      "msg": msg,
                                      "config": config.version(),
                                      "build":  get_version(),
                                      "offset": offset,
                                      "correction": ptpd2_data.get("correction", '-')})


async def secret_test_post(test_ip, name):
    response = await http.post_url_json_response("secretcheck",
                                                 f"{http.scheme}://{test_ip}:{http.port}/secret/check",
                                                 timeout=1,
                                                 json_data={})

    if not response:
        return [test_ip, name, "offline", "", "", "", ""]

    msg = get_authenticator().decode(response.get("enc", "bogus message"))

    return [test_ip,
            name,
            'shared' if msg != response['enc'] and msg == response.get("msg", msg) else "unknown",
            response.get("config", '-'),
            response.get("build", '-'),
            response.get("offset", '-'),
            response.get("correction", '-')]


async def log_file_post(test_ip, port, filename=None, nlines=5, timeout=None):
    tkn = get_authenticator().create(expires=int(time.time()) + 3600, audience="peer")

    data = {"nlines": nlines}
    if filename:
        data["filename"] = filename

    res = await http.post_url_json_response("logs",
                                            f"{http.scheme}://{test_ip}:{port}/logfile",
                                            timeout=timeout,
                                            json_data=data,
                                            headers={http.CLOCK_HDR: tkn})
    if res:
        return res

    return {"header": [], "tail": []}

@routes.post('/logfile')
@ajax_verify_token("peer")
async def log_file_html_post(request):
    json = await request.json()

    n_lines = json.get("nlines", 3)
    file_name = json.get("filename", "ptpd2.stats")

    path = None
    if file_name in ["ptpd2.stats", "ptpd2.log"]:
        path = "/var/log"
    elif file_name in ["ptpd2.status"]:
        path = "/run"

    if not path:
        return aiohttp_web.HTTPUnauthorized()

    head, tail = head_tail(os.path.join(path, file_name), head_lines=1, tail_lines=n_lines)

    header = None
    if len(head) != 0:
        if head[0].startswith("#"):
            header = head[0][2:].split(",")

    if header:
        tail = [l.split(",") for l in tail]
    else:
        header = ["Time", "Message"]
        tail = [split_date_time(l) for l in tail]

    return aiohttp_web.json_response({"tail": tail, "header": header})


@routes.get('/logfile')
@ajax_verify_token("user")
async def log_file_html_get(request):
    return await log_file_get(request)


@routes.get('/ptpd2')
@ajax_verify_token("user")
async def ptpd2_html_get_status(request):
    return await log_file_get(request, "ptpd2.status")

ptpd2_status_fields = {
    'Clock correction': 'correction',
    'Interface': 'interface',
    'Preset': 'preset',
    'Port state': 'state',
    'Sync mode': 'sync',
    'Offset from Master': 'offset',
    'Clock status': 'status',
    'Best master IP': 'master',
    'Mean Path Delay': 'delay',
    }


def map_ptpd2_status_report(data):
    res = {}
    for n, v in data:
        if n in ptpd2_status_fields:
            res[ptpd2_status_fields[n]] = v

    return res


def map_ptpd2_status(status):
    res = map_ptpd2_status_report(status['tail'])
    res['ip'] = status['ip']
    res['name'] = status['name']

    return res


async def log_file_get(request, filename=None):
    log_file_data = []
    if not filename:
        filename = request.rel_url.query.get("filename", "ptpd2.status")

    nlines = int(request.rel_url.query.get("nlines", 100))

    config = get_display_config()
    for sheet in config.sheets:
        if sheet.ip == "Unassigned":
            continue

        log_file = await log_file_post(sheet.ip, http.port, filename=filename, nlines=nlines)
        log_file_data.append({"ip": sheet.ip,
                              "name": sheet.name,
                              "header": log_file["header"],
                              "tail": log_file["tail"]})

    sensor_servers_inspected = {"Unassigned"}
    for sensor in get_device_monitor().get_sensors():
        sensor_ip = sensor["ip"]

        if sensor_ip in sensor_servers_inspected:
            continue

        sensor_servers_inspected.add(sensor_ip)
        log_file = await log_file_post(sensor_ip, http.port, filename=filename, nlines=nlines)
        log_file_data.append({"ip": sensor_ip,
                              "name": sensor["name"],
                              "header": log_file["header"],
                              "tail": log_file["tail"]})

    return log_file_data


@routes.post('/ptpd/restart')
@ajax_verify_token("admin")
async def ptpd_restart_html_post(_request):
    rc, output = run_command("sudo systemctl restart ptpd")
    warning("startup: restarting ptpd rc=%s\noutput=%s", rc, output)

    return aiohttp_web.json_response({"rc": rc, "msg": output})


@routes.get('/adminlogs')
@ajax_verify_token("admin")
async def admin_logs_html_get(_request):
    level = logger_get_level_name()
    return aiohttp_web.json_response({"headers": ("Time", "Level", "Who", "Message", "Traceback"),
                                      "data": list(log_entries),
                                      "level": level})


@routes.get('/debuglevel')
@ajax_verify_token("admin")
async def debug_level_ajax_get(_request):
    level = logger_get_level_name()
    return aiohttp_web.json_response({"level": level})


map_state = {"PTP_SLAVE": "secondary",
            "PTP_MASTER": "primary"}


@routes.get('/ajax/ptp/status')
@ajax_verify_token("user")
async def log_file_ajax_pyp_status(request):
    log_file_data = await log_file_get(request, "ptpd2.status")

    mapped_data = [map_ptpd2_status(lt) for lt in log_file_data]

    headers = ("Name", "IP", "State", "Time Server", "Offset", "Status", "Correction", "Sync")

    selected_fields = [[e["name"],
                        e["ip"],
                        map_state.get(e.get("state", ""), ""),
                        e.get("master", ""),
                        e.get("offset", ""),
                        e.get("status", ""),
                        e.get("correction", ""),
                        e.get("sync", "")] for e in mapped_data]
    return aiohttp_web.json_response({"headers": headers, "data": selected_fields})


@routes.get('/adminversion')
@ajax_verify_token("admin")
async def version_ajax_get(_request):
    sheet_info = []

    config = get_display_config()
    for sheet in config.sheets:
        if sheet.ip == "Unassigned":
            continue

        sheet_identity = await whoareyou(sheet.ip, http.port)
        if sheet_identity:
            epoch = float(sheet_identity["epochTimestamp"])
            try:
                start_time = float(sheet_identity["_startTime"])
            except KeyError:
                start_time = float(sheet_identity["epochTimestamp"])

            data = list(sheet_identity.items())
            data.append(("epochDiff",  epoch - start_time))
            data.sort()
            sheet_info.append({"name": sheet.name, "data": data})

    sensor_servers_inspected = {"Unassigned"}
    break_sensor_data = []
    for sensor in get_device_monitor().get_sensors():
        sensor_ip = sensor["ip"]
        if sensor_ip in sensor_servers_inspected:
            continue

        sensor_servers_inspected.add(sensor_ip)

        sensor_identity = await whoareyou(sensor_ip, http.port)
        if sensor_identity:
            epoch = float(sensor_identity["epochTimestamp"])
            try:
                start_time = float(sensor_identity["_startTime"])
            except KeyError:
                start_time = float(sensor_identity["epochTimestamp"])

            data = list(sensor_identity.items())
            data.append(("epochDiff",  epoch - start_time))
            data.sort()
            break_sensor_data.append({"name": sensor["name"], "data": data})

    return aiohttp_web.json_response({"sheets": sheet_info, "sensors": break_sensor_data})


@routes.get('/adminmemory')
@ajax_verify_token("admin")
async def memor_ajax_get(_request):
    global system_stats  # pylint: disable=global-statement, global-variable-not-assigned

    return aiohttp_web.json_response({"data": [mem_usage()] + list(reversed(system_stats)),
                                      "headers": MemUsage._fields})


@routes.get('/adminptpdstatus')
@ajax_verify_token("admin")
async def admin_ptpd_status_ajax_get(request):
    log_file_data = await log_file_get(request, "ptpd2.status")
    return aiohttp_web.json_response({"data": log_file_data})


@routes.get('/adminptpdstats')
@ajax_verify_token("user")
async def admin_ptpd_stats_ajax_get(request):
    log_file_data = await log_file_get(request, filename="ptpd2.stats")
    return aiohttp_web.json_response({"data": log_file_data})


@routes.get('/adminptpdlogs')
@ajax_verify_token("user")
async def admin_ptpd_logs_ajax_get(request):
    log_file_data = await log_file_get(request, filename="ptpd2.log")
    return aiohttp_web.json_response({"data": log_file_data})


@routes.get('/adminptpdoffset')
@ajax_verify_token("user")
async def admin_ptpd_offset_ajax_get(request):
    log_file_data = await log_file_get(request, "ptpd2.status")

    mapped_data = [map_ptpd2_status(lt) for lt in log_file_data]
    data = [[e.get("name", ""),
             e.get("ip", ""),
             map_state.get(e.get("state", ""), ""),
             e.get("master", ""),
             e.get("offset", ""),
             e.get("status", ""),
             e.get("correction", ""),
             e.get("sync", "")] for e in mapped_data]

    headers = ["Name", "IP", "State", "Primary", "Offset", "Status", "Correction", "Sync"]

    return aiohttp_web.json_response({"headers": headers,
                                      "data": data})


@routes.get('/ajax/time')
@ajax_verify_token("admin")
async def time_ajax_get(_request):
    now = datetime.datetime.now()
    config = get_display_config()
    return aiohttp_web.json_response({"time": now.strftime("%X"),
                                      "date": now.strftime("%Y-%m-%d"),
                                      "tz": str(now.astimezone().tzinfo),
                                      "timezone": config.rink.timezone})


@routes.post('/ajax/login')
async def login_ajax_post(request):
    data = await request.json()
    user = data["user"]
    password = data["password"]

    debug("security: checking user")
    if verify_user(user, password):
        tkn = get_authenticator().create(user=user,
                                         expires=int(time.time()) + YEAR_IN_SECONDS,
                                         audience="user")
        return aiohttp_web.json_response({"msg": "login succeeded",
                                          "rc": True,
                                          "user": user,
                                          "admin":  is_administrator(user),
                                          "accessToken": tkn})

    config = get_display_config()
    warning("security: User: %s passwd: %s does not match %s",
            user, password,  config.users.get(user, None))

    return aiohttp_web.json_response({"msg": "login failed",
                                      "accessToken": None,
                                      "rc": False})


@routes.post('/ajax/login/pin')
async def login_pin_ajax_post(request):
    data = await request.json()

    pin = data.get("pin", "not a pin").upper()
    debug("security: checking pin")
    config = get_display_config()
    my_sheet = config.sheets.my_sheet
    msg = ""
    if pin == my_sheet.pin:
        expire_time = pin_expire_time(my_sheet)
        if expire_time:
            tkn = get_authenticator().create(pin=pin, expires=expire_time, user=pin, audience="pin")
            debug("security: pin: %s succeeded", pin)
            return aiohttp_web.json_response({"msg": "login succeeded",
                                              "rc": True,
                                              "pin": pin,
                                              "admin": False,
                                              "id": my_sheet.ordinal,
                                              "accessToken": tkn})

        msg = "pin has expired"
    else:
        msg = "pin is either not current or it belongs to a different sheet"

    warning("security: pin: %s failed", pin)

    return aiohttp_web.json_response({"msg": msg,
                                      "rc": False,
                                      "accessToken": None})


@routes.post('/ajax/log/level')
@ajax_verify_token("admin")
async def log_level_ajax_post(request):
    json = await request.json()

    level = json.get("level", None).lower()
    level_name = "debug"
    if level in logger_level_map:
        level_name = level
    elif level.isdigit():
        if int(level):
            level_name = "debug"
        else:
            level_name = "warning"

    logger_set_level(logger_level_map[level_name])
    level = logger_get_level_name()
    error("Logger: set level to %s: %s", level_name, level)

    return aiohttp_web.json_response({"level": level})


@routes.post('/ajax/log/clear')
@ajax_verify_token("admin")
async def log_clear_ajax_post(_request):
    clear_logs()
    level = logger_get_level_name()
    return aiohttp_web.json_response({"level": level})


@routes.post('/ajax/secret/set')
async def set_secret_key_ajax_post(request):
    config = get_display_config()
    if config.server.setup != 0 and not config.server.is_default_secret_key():
        access_token = request.headers.get(http.CLOCK_HDR, None)
        authenticator = get_authenticator()
        tkn = authenticator.verify(access_token)

        if not tkn:
            return aiohttp_web.json_response({"msg": "set secret failed; not permitted", "rc": False})

        if not is_administrator(tkn["user"]):
            return aiohttp_web.json_response({"msg": "set secret failed; not permitted", "rc": False})

    data = await request.json()
    secret_key = data.get("secret", None)
    info("security: generating new secret key")
    encrypted_key = get_authenticator().generate_key_from_passphrase(secret_key)

    if not encrypted_key:
        info("security: secret key improperly generated; ignored")
        return aiohttp_web.json_response({"msg": "set secret failed; encryption", "rc": False})

    info("security: secret key generated")
    config.server.secret_key = encrypted_key

    if curling_clock_manager:
        config.server.setup = 1
    else:
        # running a break timer so record as being fully setup
        config.server.setup = 4

    config.save()

    if curling_clock_manager:
        curling_clock_manager.view_display_scrolling_text("restarting", 300*60)

    asyncio.ensure_future(wait_for_restart())

    return aiohttp_web.json_response({"msg": "set secret key succeeded; restarting ...", "rc": True})


@routes.get('/ajax/hardware')
@ajax_verify_token("admin")
async def hardware_ajax_get(_request):
    global hardware_config  # pylint: disable=global-statement, global-variable-not-assigned

    return aiohttp_web.json_response({**hardware_config.hardware.items()} if hardware_config else {})


@routes.post('/ajax/hardware')
@ajax_verify_token("admin")
async def hardware_ajax_post(request):
    global hardware_config # pylint: disable=global-statement, global-variable-not-assigned

    json = await request.json()

    settings = json.get("settings", {})

    hardware_config.hardware.update(settings.items())
    hardware_config.save()

    return aiohttp_web.json_response({"msg": "settings saved"})


@routes.get('/ajax/clock/state')
@ajax_verify_token("user")
async def secret_clock_state_html_get(_request):
    secret_test_data = []
    config = get_display_config()
    for sheet in config.sheets:
        if sheet.ip == "Unassigned":
            continue

        matched = await secret_test_post(sheet.ip, sheet.name)
        secret_test_data.append(matched)

    sensor_servers_inspected = {"Unassigned"}
    for sensor in get_device_monitor().get_sensors():
        sensor_ip = sensor["ip"]
        if sensor_ip in sensor_servers_inspected:
            continue

        sensor_servers_inspected.add(sensor_ip)
        matched = await secret_test_post(sensor_ip, sensor["name"])
        secret_test_data.append(matched)

    return aiohttp_web.json_response({"data": secret_test_data,
                                      "headers": ["IP", "Name", "Secret", "Config", "Build", "Offset", "correction"]})

@routes.get('/ajax/devices')
@ajax_verify_token("pin")
async def devices_ajax_get(request):
    monitor = get_device_monitor()

    sensors = monitor.get_sensors()
    displays = monitor.get_displays()
    sheets = curling_clock_manager.get_sheets() if curling_clock_manager else []

    sheets = [{"ip": sheet.ip,
               "name": sheet.name,
               "type": "display",
               "port": http.port} for sheet in sheets if sheet.ip != "Unassigned"]

    if request.access_token_audience == "pin":
        displays = []

    return aiohttp_web.json_response({"displays": displays,
                                      "sensors":  sensors,
                                      "sheets" : sheets})
