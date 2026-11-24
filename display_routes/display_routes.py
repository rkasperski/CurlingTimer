import time
from zoneinfo import ZoneInfo

from datetime import datetime
from aiohttp import web as aiohttp_web

from aio_utils import render_template
from access_verification import ajax_verify_token
import config
import curling_clock_manager
from utils import my_ip_address
from logger import info

routes = aiohttp_web.RouteTableDef()


@routes.post('/blank')
@ajax_verify_token("pin")
async def blank_ajax(request):
    json = await request.json()

    blank = json.get("blank", True)

    if blank:
        curling_clock_manager.manager.force_idle()
    else:
        curling_clock_manager.manager.reset_idle_time()

    return aiohttp_web.json_response({"blank": blank})


@routes.get('/')
async def alt_html_get(request):
    return await render_template('curlingtimer.html', request, {})


@routes.post('/text')
@ajax_verify_token("pin")
async def text_ajax(request):
    json = await request.json()
    curling_clock_manager.manager.set_scrolling_text(json.get("text", "hello"), json.get("colour", "white"))
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_display_scrolling_text)

    return aiohttp_web.json_response({"operation": "scrollingtext"})


@routes.post('/clock/status')
async def clock_status_ajax(request):
    # tz = pytz.timezone(config.display.rink.timezone)
    tz = ZoneInfo(config.display.rink.timezone)

    now = datetime.now(tz)
    seconds_since_midnight = (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
    return aiohttp_web.json_response({"time": seconds_since_midnight})


@routes.post('/clock/show')
@ajax_verify_token("pin")
async def clock_show_ajax(request):
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_clock_update)
    return aiohttp_web.json_response({"time": time.time()})


@routes.post('/showip')
@ajax_verify_token("pin")
async def show_ip_ajax(request):
    curling_clock_manager.manager.set_flash_text(my_ip_address())
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_display_flash_text)

    return aiohttp_web.json_response({"show": 1})


@routes.post('/config')
@ajax_verify_token("config")
async def config_ajax(request):
    json = await request.json()

    peer_name = request.transport.get_extra_info('peername')
    info("received new config from: %s", peer_name)
    config.display.from_string(json["config"])
    # config.display.sheets.modified = True

    if curling_clock_manager.manager:
        curling_clock_manager.manager.set_defaults_from_config()

    return aiohttp_web.json_response({"time": time.time(),
                                      "configUpdate": True,
                                      "msg": "updated"})
