from aiohttp import web as aiohttp_web
from AccessVerification import ajaxVerifyToken
import LED_RGB_Display
import CurlingClockManager

routes = aiohttp_web.RouteTableDef()


@routes.post('/settime')
@ajaxVerifyToken("admin")
async def setTimeAjax(request):
    LED_RGB_Display.display.resetIdleTime()
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "set time"}))


@routes.post('/status')
@ajaxVerifyToken("pin")
async def statusPostAjax(request):
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "status"}))


# Eye is this used???
@routes.get('/status')
@ajaxVerifyToken("user")
async def statusGetAjax(request):
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "status"}))


@routes.post('/kapow')
@ajaxVerifyToken("pin")
async def kapowAjax(request):
    LED_RGB_Display.display.resetIdleTime()
    json = await request.json()
    kpw = json.get("kapow", "rain")

    CurlingClockManager.manager.setKapow(kpw)

    return aiohttp_web.json_response({"operation": "kapow"})
