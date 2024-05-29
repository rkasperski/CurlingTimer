import time
from zoneinfo import ZoneInfo
from AIO_Utils import renderTemplate

from aiohttp import web as aiohttp_web
from datetime import datetime

from AccessVerification import ajaxVerifyToken
import Config
import LED_RGB_Display
import CurlingClockManager
from Utils import myIPAddress
#import pytz
import CommonRoutes

routes = aiohttp_web.RouteTableDef()


@routes.post('/blank')
@ajaxVerifyToken("pin")
async def blankAjax(request):
    json = await request.json()

    blank = json.get("blank", True)

    if blank:
        CurlingClockManager.manager.forceIdle()
    else:
        CurlingClockManager.manager.resetIdleTime()
        
    return aiohttp_web.json_response({"blank": blank})


@routes.get('/')
async def altHtmlGet(request):
    return await renderTemplate('curlingtimer.html', request, {})


@routes.post('/text')
@ajaxVerifyToken("pin")
async def textAjax(request):
    LED_RGB_Display.display.resetIdleTime()
    json = await request.json()
    LED_RGB_Display.display.setScrollingText(json.get("text", "hello"), json.get("colour", "white"))
    CurlingClockManager.manager.setView(CurlingClockManager.manager.scrollingText)

    return aiohttp_web.json_response({"operation": "scrollingtext"})


@routes.post('/clock/status')
async def clockStatusAjax(request):
    # tz = pytz.timezone(Config.display.rink.timezone)
    tz = ZoneInfo(Config.display.rink.timezone)
    
    now = datetime.now(tz)
    secondsSinceMidnight = (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
    return aiohttp_web.json_response({"time": secondsSinceMidnight})


@routes.post('/clock/show')
@ajaxVerifyToken("pin")
async def clockShowAjax(request):
    LED_RGB_Display.display.resetIdleTime()
    CurlingClockManager.manager.setView(CurlingClockManager.manager.clockUpdate)
    return aiohttp_web.json_response({"time": time.time()})


@routes.post('/showip')
@ajaxVerifyToken("pin")
async def showIPAjax(request):
    LED_RGB_Display.display.resetIdleTime()
    LED_RGB_Display.display.setFlashText(myIPAddress())
    CurlingClockManager.manager.setView(CurlingClockManager.manager.flashText)

    return aiohttp_web.json_response({"show": 1})


@routes.post('/config')
@ajaxVerifyToken("config")
async def configAjax(request):
    json = await request.json()

    Config.display.fromString(json["config"])

    myIp = myIPAddress()

    Config.display.sheets.whoAmI(myIp)

    Config.display.sheets.modified = True

    if LED_RGB_Display.display:
        LED_RGB_Display.display.welcomeMessage = Config.display.defaults.welcomeMessage
        LED_RGB_Display.display.setScrollingText(LED_RGB_Display.display.welcomeMessage)

    return aiohttp_web.json_response({"time": time.time(),
                                      "configUpdate": True,
                                      "msg": "updated"})
