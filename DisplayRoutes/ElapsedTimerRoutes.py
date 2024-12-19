from aiohttp import web as aiohttp_web
from AccessVerification import ajaxVerifyToken
import CurlingClockManager

routes = aiohttp_web.RouteTableDef()


@routes.post('/elapsed/set')
@ajaxVerifyToken("pin")
async def elapsedSetAjax(request):
    CurlingClockManager.manager.timers.elapsedTime.pause()
    json = await request.json()
    CurlingClockManager.manager.timers.elapsedTime.setInitialTime(json["time"])

    CurlingClockManager.manager.setView(CurlingClockManager.manager.elapsedTimeUpdate)
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "elapsedtime:set"}))


@routes.post('/elapsed/status')
@ajaxVerifyToken("pin")
async def elapsedStatusAjax(request):
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.elapsedTime.ajaxResponse({"operation": "status",
                                                                                                  "timer": "elapsed"}))


@routes.post('/elapsed/show')
@ajaxVerifyToken("pin")
async def elapsedShowAjax(request):
    CurlingClockManager.manager.setView(CurlingClockManager.manager.elapsedTimeUpdate)

    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "elapsedtime:show"}))


@routes.post('/elapsed/pause')
@ajaxVerifyToken("pin")
async def elapsedPauseAjax(request):
    CurlingClockManager.manager.setView(CurlingClockManager.manager.elapsedTimeUpdate)
    CurlingClockManager.manager.timers.elapsedTime.pause()
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "elapsedtime:pause"}))


@routes.post('/elapsed/resume')
@ajaxVerifyToken("pin")
async def elapsedResumeAjax(request):
    CurlingClockManager.manager.setView(CurlingClockManager.manager.elapsedTimeUpdate)
    CurlingClockManager.manager.timers.elapsedTime.resume()
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "elapsedtime:start"}))


@routes.post('/elapsed/start')
@ajaxVerifyToken("pin")
async def elapsedStartAjax(request):
    CurlingClockManager.manager.setView(CurlingClockManager.manager.elapsedTimeUpdate)
    CurlingClockManager.manager.timers.elapsedTime.resume()
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "elapsedtime:start"}))
