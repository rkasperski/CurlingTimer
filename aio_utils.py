import aiohttp_jinja2

from utils import my_ip_address, my_host_name
import config
import kapow
from access_verification import is_administrator
import access_verification
import http_utils as http
from hardware_clock import has_hardware_clock

get_colours_func = None


async def render_template(template, request, verbose=False):
    global get_colours_func

    context = {}
    my_sheet = config.display.sheets.my_sheet
    my_name = my_sheet.name if my_sheet else my_host_name()

    if get_colours_func:
        context["colours"] = get_colours_func()

    context["type"] = "display"
    context["setup"] = config.display.server.setup
    context["batteryAlert"] = config.display.rink.battery_alert
    context["clockServer"] = config.display.rink.clock_server
    context["hwClock"] = has_hardware_clock()
    context["numberOfSheets"] = len(config.display.sheets)
    context["welcomeMessage"] = config.display.defaults.welcome_message
    context["organization"] = config.display.organization.organization
    context["scheme"] = http.scheme
    context["port"] = http.port
    context["sheets"] = config.display.sheets
    context["drawServer"] = config.display.defaults.draw_server
    context["kapow"] = list(kapow.registered.keys())
    context["debug"] = request.query.get("debug", 0)
    access_token = request.headers.get(http.CLOCK_HDR, None)

    if access_token:
        my_sheet = config.display.sheets.my_sheet
        tkn = access_verification.token_authenticator.verify(access_token,  my_sheet)

        if tkn["aud"] == "user":
            user = tkn["user"]
            context["user"] = user
            context["isadmin"] = is_administrator(user)
            context["accessToken"] = request.access_token
            context["userlogin"] = True

    my_ip = my_ip_address()
    context["ip"] = request.query.get("ip", my_ip)
    context["sheet"] = request.query.get("sheet", my_name)

    response = await aiohttp_jinja2.render_template_async(template, request, context)
    return response


def register_get_colours(prm_get_colours_func):
    global get_colours_func

    get_colours_func = prm_get_colours_func
