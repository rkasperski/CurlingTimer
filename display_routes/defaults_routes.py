import asyncio
from aiohttp import web as aiohttp_web

from access_verification import ajax_verify_token, is_administrator, set_user_password, get_authenticator
from http_utils import CLOCK_HDR

import config
from utils import to_int
import curling_clock_manager
from configuration_manager import update_all_configs

routes = aiohttp_web.RouteTableDef()


@routes.post('/colours/show')
@ajax_verify_token("user")
async def colour_show_ajax(request):
    json = await request.json()

    red = to_int(json.get("red", 255))
    green = to_int(json.get("green", 255))
    blue = to_int(json.get("blue", 255))

    curling_clock_manager.manager.set_splash_colour(colour=(red, green, blue))
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_splash_colour)

    return aiohttp_web.json_response({"action": "colour"})


def usersToExternal():
    return [{"name": user, "admin": 1 if is_administrator(user) else 0} for user in config.display.users.keys()]


@routes.get('/ajax/defaults')
@ajax_verify_token("pin")
async def defaults_ajax_get(request):
    return aiohttp_web.json_response({**config.display.defaults.items()})


@routes.post('/ajax/defaults')
@ajax_verify_token("user")
async def defaults_ajax_post(request):
    json = await request.json()

    values = json.get("values", {})

    config.display.defaults.update(values.items())
    config.display.defaults.modified = True
    curling_clock_manager.manager.set_defaults_from_config()

    asyncio.ensure_future(update_all_configs())

    return aiohttp_web.json_response({"msg": "values saved"})


@routes.get('/ajax/users')
@ajax_verify_token("admin")
async def users_ajax_get(request):
    return aiohttp_web.json_response({"users": usersToExternal()})


@routes.post('/ajax/users')
@ajax_verify_token("admin")
async def users_ajax_post(request):
    json = await request.json()

    data = json["data"]
    msgs = []

    print(f"{data=}")
    for userData in data:
        print(f"{userData}")
        user = userData["user"]
        if (action := userData["action"]) == "delete":
            try:
                config.display.users.del_user(user)
                msgs.append(f"user:{user} deleted")

            except KeyError:
                msgs.append(f"user:{user} not deleted")
        elif action == "add":
            password = userData["password"]
            is_admin = userData.get("admin", False)

            config.display.users.add_user(user, password, is_admin=is_admin)
            msgs.append(f"user:{user} added")
        else:
            aiohttp_web.json_response({"msg": f"failed to perform {action=}"})

    asyncio.ensure_future(update_all_configs())

    return aiohttp_web.json_response({"msg": "\n".join(msgs)})


@routes.get('/ajax/user')
@ajax_verify_token("admin")
async def user_ajax_get(request):
    access_token = request.headers.get(CLOCK_HDR, None)
    user = "None"
    priviledge = "None"
    sheet = ""
    if access_token:
        my_sheet = config.display.sheets.my_sheet
        sheet = my_sheet.name
        authenticator = get_authenticator()
        tkn = authenticator.verify(access_token,  my_sheet)
        if tkn:
            if tkn["aud"] == 'user':
                user = tkn["user"]
                priviledge = "admin" if is_administrator(user) else "user"
            elif tkn["aud"] == 'pin':
                priviledge = "pin"
                user = tkn["pin"]

    return aiohttp_web.json_response({"user": user,
                                      "priviledge": priviledge,
                                      "sheet": sheet})


@routes.post('/ajax/password')
@ajax_verify_token("user")
async def ajax_password_post(request):
    access_token = request.headers.get(CLOCK_HDR, None)
    authenticator = get_authenticator()
    tkn = authenticator.verify(access_token)

    if not tkn:
        return aiohttp_web.json_response({"msg": "password changed failed"})

    data = await request.json()
    user = data["user"]
    password = data["password"]
    is_admin = is_administrator(user)

    if user != tkn["user"]:
        return aiohttp_web.json_response({"msg": "password changed failed"})

    if len(password) < 5:
        return aiohttp_web.json_response({"msg": "password changed failed"})

    set_user_password(user, password)
    asyncio.ensure_future(update_all_configs())

    return aiohttp_web.json_response({"msg": "password changed"})


@routes.get('/ajax/colours')
@ajax_verify_token("pin")
async def colours_ajax_get(request):
    return aiohttp_web.json_response({"colours": curling_clock_manager.manager.get_colours()})


@routes.post('/ajax/colours')
@ajax_verify_token("user")
async def colours_ajax_post(request):
    json = await request.json()

    curling_clock_manager.manager.set_colours({n: [int(rgb[0]), int(rgb[1]), int(rgb[2])] for n, rgb in json["colours"]})
    config.display.colours.add_colours(curling_clock_manager.manager.get_colours(), clear=True)
    asyncio.ensure_future(update_all_configs())

    return aiohttp_web.json_response({"msg": "colours saved"})
