import aiohttp_jinja2
from aiohttp import web as aiohttp_web

from Utils import myIPAddress, myHostName
import Config
import Kapow
from AccessVerification import isAdministrator
import AccessVerification
import HTTP_Utils
import HardwareClock

getColours = None


async def renderTemplate(template, request, iContext={}, verbose=False):
    context = {}
    mySheet = Config.display.sheets.mySheet
    myName = mySheet.name if mySheet else myHostName()

    if getColours:
        context["colours"] = getColours()

    context["type"] = "display"
    context["setup"] = Config.display.server.setup
    context["batteryAlert"] = Config.display.rink.batteryAlert
    context["clockServer"] = Config.display.rink.clockServer
    context["hwClock"] = HardwareClock.hasHardwareClock
    context["numberOfSheets"] = len(Config.display.sheets)
    context["welcomeMessage"] = Config.display.defaults.welcomeMessage
    context["organization"] = Config.display.organization.organization
    context["scheme"] = HTTP_Utils.scheme
    context["port"] = HTTP_Utils.port
    context["sheets"] = Config.display.sheets
    context["drawServer"] = Config.display.defaults.drawServer
    context["kapow"] = list(Kapow.registered.keys())
    accessToken = request.headers.get(HTTP_Utils.CLOCK_HDR, None)
            
    if accessToken:
        mySheet = Config.display.sheets.mySheet
        tkn = AccessVerification.tokenAuthenticator.verify(accessToken,  mySheet)

        if tkn["aud"] == "user":
            user = tkn["user"]
            context["user"] = user
            context["isadmin"] = isAdministrator(user)
            context["accessToken"] = request.accessTkn
            context["userlogin"] = True
        
    myIp = myIPAddress()
    context["ip"] = myIp if request is None else request.query.get("ip", myIp)
    context["sheet"] = myName if request is None else request.query.get("sheet", myName)

    response = await aiohttp_jinja2.render_template_async(template, request, context)
    return response


def registerGetColours(getColoursFunc):
    global getColours

    getColours = getColoursFunc
