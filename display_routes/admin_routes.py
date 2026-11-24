import datetime
import time
import asyncio

from aiohttp import web as aiohttp_web

from logger import warning, info, exception
from access_verification import ajax_verify_token
from config import get_display_config
from curling_clock_manager import get_manager
from timers import str_to_seconds
from hardware_clock import update_clock_time, set_hardware_clock
import http_utils as http
from utils import my_ip_address, generate_pin
from identify import whoareyou
from configuration_manager import update_all_configs
from common_routes import delayed_restart

routes = aiohttp_web.RouteTableDef()


@routes.post('/restart')
@ajax_verify_token("admin")
async def restart_ajax(_request):
    info("app: restart...")
    manager = get_manager()
    manager.set_scrolling_text("Restarting ...")
    manager.set_view(manager.view_display_text)
    asyncio.ensure_future(delayed_restart(delay=5))
    return aiohttp_web.json_response({"restart": 1})


@routes.post('/reboot')
@ajax_verify_token("admin")
async def reboot_ajax(_request):
    info("app: reboot...")
    manager = get_manager()
    manager.set_scrolling_text("Rebooting ...")
    manager.set_view(manager.view_display_scrolling_text)
    asyncio.ensure_future(delayed_restart(delay=5, reboot=True))
    return aiohttp_web.json_response({"reboot": 1})


@routes.post('/pin/get')
@ajax_verify_token("user")
async def get_pin_ajax(request):
    json = await request.json()
    expire_time = json["expireTime"]
    pin_sheet = json["sheet"]

    new_pin = generate_pin()

    config =  get_display_config()

    for sheet in config.sheets:
        if sheet.name == pin_sheet:
            sheet.pin = new_pin
            sheet.pin_expire_time = str(int(time.time() + str_to_seconds(expire_time)))

            config.sheets.modified = True
            asyncio.ensure_future(update_all_configs())

            return aiohttp_web.json_response({"pin": new_pin,
                                              "pinExpireTime": datetime.datetime.fromtimestamp(int(sheet.pin_expire_time)).strftime('%c')
                                              })

    return aiohttp_web.json_response({"pin": "Unassigned",
                                      "pinExpireTime": "badness"
                                      })


@routes.post('/pin/get/all')
@ajax_verify_token("user")
async def pin_get_all_ajax(request):
    json = await request.json()
    expire_time = json["expireTime"]

    new_pins = []
    config =  get_display_config()
    for sheet in config.sheets:
        if sheet.ip == "Unassigned":
            continue

        new_pin = generate_pin()
        sheet.pin = new_pin
        sheet.pin_expire_time = str(int(time.time() + str_to_seconds(expire_time)))

        new_pins.append({"sheet": sheet.name,
                         "ordinal": sheet.ordinal,
                         "pinExpireTime": datetime.datetime.fromtimestamp(int(sheet.pin_expire_time)).strftime('%c'),
                         "pin": new_pin})

    config.sheets.modified = True
    asyncio.ensure_future(update_all_configs())
    return aiohttp_web.json_response({"pins": new_pins})


@routes.post('/flash')
@ajax_verify_token("user")
async def flash_text_ajax(request):
    json = await request.json()
    manager = get_manager()
    
    if manager:
        manager.set_flash_text(json.get("text", my_ip_address()), json.get("colour", "red"))
        manager.set_view(manager.view_display_flash_text)

    return aiohttp_web.json_response({"operation": "flashtext"})


@routes.post('/timedate')
@ajax_verify_token("admin")
async def clock_set_html_post(request):
    start_time = time.time()
    data = await request.json()

    config =  get_display_config()
    try:
        if config.rink.clock_server.strip() != my_ip_address():
            return aiohttp_web.json_response({"msg": "trying to set time on a clock that doesn't have a hardware clock"})

        manager = get_manager()
        manager.abort()

        warning("timedate: request data=%s", data.items())

        permanent = data.get("permanent", True)

        new_time = data.get("time", None)
        if new_time:
            new_time = new_time.strip()

        new_time_zone = data.get("timeZone", None)
        if new_time_zone:
            new_time_zone = new_time_zone.strip()

        new_date = data.get("date", None)
        if new_date:
            new_date = new_date.strip()

        new_time_secs_since_midnight = None

        msg = "nothing asked"
        if new_time:
            sp = new_time.split(":")
            info("ClockSet: setting time %s: %s", new_time, sp)
            if len(sp) == 1:
                clock_time_hours, clock_time_minutes, clock_time_seconds = sp + [0, 0]
            elif len(sp) == 2:
                clock_time_hours, clock_time_minutes, clock_time_seconds = sp + [0,]
            else:
                clock_time_hours, clock_time_minutes, clock_time_seconds = sp[0:3]

            # adjust start time by  approximate amount do connection to match time. empirical hack
            new_time_secs_since_midnight = int(clock_time_hours) * 3600 + \
                int(clock_time_minutes) * 60 + int(clock_time_seconds) + 0.600

        if new_time_zone:
            if update_clock_time(new_time_zone=new_time_zone):
                config.rink.timezone = new_time_zone
                await update_all_configs()
                msg = "timezone set"
            else:
                return aiohttp_web.json_response({"msg": f"Failed to set time zone to '{new_time_zone}'"})

        diff_time = time.time() - start_time

        if new_time_secs_since_midnight or new_date:
            msg = update_clock_time(new_time_secs_from_midnight=new_time_secs_since_midnight + \
                                    diff_time if new_time_secs_since_midnight else None,
                                    new_date=new_date if new_date else None,
                                    new_time_zone=None)

        if permanent:
            set_hardware_clock()
            manager.set_scrolling_text("Restarting ...", "red")
            manager.set_view(manager.view_display_text)

            asyncio.ensure_future(delayed_restart(delay=5))
            msg = "Setting hardware clock"

    except Exception as e:
        msg = f"clock set badness {e}"
        exception("set timedate %s '%s'", msg, data, exc_info=True)

    return aiohttp_web.json_response({"msg": msg})


@routes.get('/ajax/sheets')
@ajax_verify_token("admin")
async def sheets_ajax_get(_request):
    config =  get_display_config()
    return aiohttp_web.json_response({"nSheets": len(config.sheets),
                                      "sheets": [s._asdict() for s in config.sheets],
                                      "clockServer": config.rink.clock_server,
                                      "clubName": config.rink.club_name,
                                      "drawServer": config.defaults.draw_server})


@routes.post('/ajax/sheets')
@ajax_verify_token("admin")
async def sheets_ajax_post(request):
    json = await request.json()

    config =  get_display_config()
    old_sheet_count = config.rink.number_of_sheets
    new_sheet_count = min(32, max(1, int(json["nSheets"])))

    config.sheets.set_count(new_sheet_count)

    sheets = json["sheets"]
    smallest = min(old_sheet_count, new_sheet_count)

    for upd_sheet, sheet in zip(sheets[0:smallest], config.sheets[0:smallest]):
        sheet.top_colour = upd_sheet["top"]
        sheet.bottom_colour = upd_sheet["bottom"]
        sheet.ip = upd_sheet["ip"]
        sheet.name = upd_sheet["name"]
        sheet.has_hardware_clock = "No"
        sheet.host_name = "Unassigned"

        if sheet.ip != "Unassigned":
            whoami = await whoareyou(sheet.ip, http.port)
            if whoami:
                sheet.has_hardware_clock = whoami.get("hwClock", "No")
                sheet.host_name = whoami.get("hostname", "Unassigned")

    if json["drawServer"].strip().lower() not in ["", "unassigned"]:
        config.defaults.draw_server = json["drawServer"].strip()
    else:
        # pick first non-rtc clock or last rtc clock if they all have clocks
        for s in config.sheets:
            if s.ip and s.ip.lower() != "unassigned":
                config.defaults.draw_server = s.ip

                if not s.has_hardware_clock:
                    break

    if json["clockServer"].strip().lower() not in ["", "unassigned"]:
        config.rink.clock_server = json["clockServer"].strip()
    else:
        # pick rtc clock
        for s in config.sheets:
            if s.ip and s.ip.lower() != "unassigned":
                if s.has_hardware_clock:
                    config.rink.clock_server = s.ip

    config.rink.club_name = json.get("clubName", "Just A Club")
    config.rink.modified = True

    config.server.setup = 4
    config.save()
    asyncio.ensure_future(update_all_configs())

    return aiohttp_web.json_response({"nSheets": len(config.sheets),
                                      "sheets":  [s._asdict() for s in config.sheets]})


@routes.get('/ajax/organization')
@ajax_verify_token("admin")
async def organization_ajax_get(_request):
    config =  get_display_config()
    
    return aiohttp_web.json_response({**config.organization.items()})


@routes.post('/ajax/organization')
@ajax_verify_token("admin")
async def organization_ajax_post(request):
    json = await request.json()

    values = json.get("data", {})

    config =  get_display_config()

    for n, v in values.items():
        config.organization.set(n, v)

    config.organization.modified = True
    asyncio.ensure_future(update_all_configs())

    return aiohttp_web.json_response({"msg": "values saved"})
