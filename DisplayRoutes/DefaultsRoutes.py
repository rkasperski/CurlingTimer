import asyncio
from aiohttp import web as aiohttp_web

from AccessVerification import ajaxVerifyToken, isAdministrator, setUserPassword, getAuthenticator
from HTTP_Utils import CLOCK_HDR

import Config
from Utils import toInt
import CurlingClockManager
from ConfigurationManager import updateAllConfigs

routes = aiohttp_web.RouteTableDef()


@routes.post('/colours/show')
@ajaxVerifyToken("user")
async def colourShowAjax(request):
    json = await request.json()

    red = toInt(json.get("red", 255))
    green = toInt(json.get("green", 255))
    blue = toInt(json.get("blue", 255))

    CurlingClockManager.manager.setSplashColour(colour=(red, green, blue))
    CurlingClockManager.manager.setView(CurlingClockManager.manager.splashColour)
    
    return aiohttp_web.json_response({"action": "colour"})


def usersToExternal():
    return [{"name": user, "admin": 1 if isAdministrator(user) else 0} for user in Config.display.users.keys()]


@routes.get('/ajax/defaults')
@ajaxVerifyToken("user")
async def defaultsAjaxGet(request):
    return aiohttp_web.json_response({**Config.display.defaults.items()})


@routes.post('/ajax/defaults')
@ajaxVerifyToken("user")
async def defaultsAjaxPost(request):
    json = await request.json()

    values = json.get("values", {})

    for n, v in values.items():
        Config.display.defaults.set(n, v)

    Config.display.defaults.modified = True
    CurlingClockManager.manager.setDefaultsFromConfig()

    asyncio.ensure_future(updateAllConfigs())

    return aiohttp_web.json_response({"msg": "values saved"})


@routes.get('/ajax/users')
@ajaxVerifyToken("admin")
async def usersAjaxGet(request):
    return aiohttp_web.json_response({"users": usersToExternal()})


@routes.post('/ajax/users')
@ajaxVerifyToken("admin")
async def usersAjaxPostt(request):
    json = await request.json()

    data = json["data"]
    msgs = []
    
    for userData in data:
        user = userData["user"]
        if userData["action"] != "add":
            try:
                Config.display.users.delUser(user)
                msgs.append(f"user:{user} deleted")

            except KeyError:
                msgs.append(f"user:{user} not deleted")
        else:
            password = userData["password"]
            isAdmin = userData.get("admin", False)

            setUserPassword(user, password, isAdmin=isAdmin)
            msgs.append(f"user:{user} added")

    asyncio.ensure_future(updateAllConfigs())

    return aiohttp_web.json_response({"msg": "\n".join(msgs)})


@routes.get('/ajax/user')
@ajaxVerifyToken("admin")
async def userAjaxGet(request):
    accessToken = request.headers.get(CLOCK_HDR, None)
    user = "None"
    priviledge = "None"
    sheet = ""
    if accessToken:
        mySheet = Config.display.sheets.mySheet
        sheet = mySheet.name
        authenticator = getAuthenticator()
        tkn = authenticator.verify(accessToken,  mySheet)
        if tkn:
            if tkn["aud"] == 'user':
                user = tkn["user"]
                priviledge = "admin" if isAdministrator(user) else "user"
            elif tkn["aud"] == 'pin':
                priviledge = "pin"
                user = tkn["pin"]
    
    return aiohttp_web.json_response({"user": user,
                                      "priviledge": priviledge,
                                      "sheet": sheet})


@routes.post('/ajax/password')
@ajaxVerifyToken("admin")
async def ajaxPasswordPost(request):
    accessToken = request.headers.get(CLOCK_HDR, None)
    authenticator = getAuthenticator()
    tkn = authenticator.verify(accessToken)

    if not tkn:
        return aiohttp_web.json_response({"msg": "password changed failed"})

    data = await request.json()
    user = data["user"]
    password = data["password"]
    isAdmin = isAdministrator(user)

    if user != tkn["user"]:
        return aiohttp_web.json_response({"msg": "password changed failed"})

    if len(password) < 5:
        return aiohttp_web.json_response({"msg": "password changed failed"})

    setUserPassword(user, password, isAdmin=isAdmin)
    asyncio.ensure_future(updateAllConfigs())

    return aiohttp_web.json_response({"msg": "password changed"})


@routes.get('/ajax/colours')
@ajaxVerifyToken("pin")
async def hardwareAjaxGet(request):
    return aiohttp_web.json_response({"colours": CurlingClockManager.manager.getColours()})


@routes.post('/ajax/colours')
@ajaxVerifyToken("user")
async def hardwareAjaxPost(request):
    json = await request.json()

    CurlingClockManager.manager.setColours({n: [int(rgb[0]), int(rgb[1]), int(rgb[2])] for n, rgb in json["colours"]})
    Config.display.colours.addColours(CurlingClockManager.manager.getColours(), clear=True)
    asyncio.ensure_future(updateAllConfigs())
    
    return aiohttp_web.json_response({"msg": "colours saved"})
