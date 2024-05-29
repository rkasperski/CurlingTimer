from aiohttp import web as aiohttp_web
from AccessVerification import ajaxVerifyToken
import Config
import LED_RGB_Display
import CurlingClockManager

routes = aiohttp_web.RouteTableDef()


@routes.post('/countdown/show')
@ajaxVerifyToken("pin")
async def countDownShowAjax(request):
    LED_RGB_Display.display.resetIdleTime()
    CurlingClockManager.manager.setView(CurlingClockManager.manager.countDownUpdate)
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "countdown:show"}))


@routes.post('/countdown/lastend')
@ajaxVerifyToken("pin")
async def countDownLastEndAjax(request):
    LED_RGB_Display.display.resetIdleTime()
    CurlingClockManager.manager.timers.countDown.pause()
    CurlingClockManager.manager.setView(CurlingClockManager.manager.countDownLastEnd)
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "countdown:last end"}))


@routes.post('/countdown/pause')
@ajaxVerifyToken("pin")
async def countDownPauseAjax(request):
    LED_RGB_Display.display.resetIdleTime()
    CurlingClockManager.manager.setView(CurlingClockManager.manager.countDownUpdate)
    CurlingClockManager.manager.timers.countDown.pause()
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "countdown:pause"}))


@routes.post('/countdown/resume')
@ajaxVerifyToken("pin")
async def countDownResumeAjax(request):
    LED_RGB_Display.display.resetIdleTime()
    CurlingClockManager.manager.setView(CurlingClockManager.manager.countDownUpdate)
    CurlingClockManager.manager.timers.countDown.resume()
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "countdown:resume"}))


@routes.post('/countdown/start')
@ajaxVerifyToken("pin")
async def countDownStartAjax(request):
    LED_RGB_Display.display.resetIdleTime()
    CurlingClockManager.manager.setView(CurlingClockManager.manager.countDownUpdate)
    CurlingClockManager.manager.timers.countDown.resume()

    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "countdown:start",
                                                                                      "timer": "countdown"}))


@routes.post('/countdown/status')
@ajaxVerifyToken("pin")
async def countDownStatusAjax(request):
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.countDown.ajaxResponse({"operation": "status",
                                                                                                "timer": "countdown"}))


@routes.post('/countdown/set')
@ajaxVerifyToken("pin")
async def countDownSetAjax(request):
    LED_RGB_Display.display.resetIdleTime()

    CurlingClockManager.manager.timers.countDown.pause()
    json = await request.json()
    CurlingClockManager.manager.timers.countDown.setTime(json["gameTime"])
    finishedMessageColour = json.get("finishedMessageColour", "green")
    lastEndMessageColour = json.get("lastEndMessageColour", "red")
    teamColour = json.get("teamColour", "default")
    timers = CurlingClockManager.manager.timers

    try:
        timers.countDown.setFinishedMessage(json["finishedMessage"],
                                            finishedMessageColour,
                                            Config.display.defaults.finishedMessageDisplayTime)
        timers.countDown.setLastEndMessage(json["lastEndMessage"], lastEndMessageColour)

        mySheet = Config.display.sheets.mySheet
        timers.competition.teams[0].name = json["team1"]
        timers.competition.teams[0].colour = mySheet.topColour if teamColour in ["board", "default"] else teamColour

        timers.competition.teams[1].name = json["team2"]
        timers.competition.teams[1].colour = mySheet.bottomColour if teamColour in ["board", "default"] else teamColour

        if json["team1"].strip() or json["team2"].strip():
            CurlingClockManager.manager.setView(CurlingClockManager.manager.teamNamesCountDown)
        else:
            CurlingClockManager.manager.setView(CurlingClockManager.manager.countDownUpdate)

    except KeyError:
        CurlingClockManager.manager.setView(CurlingClockManager.manager.countDownUpdate)

    return aiohttp_web.json_response(timers.ajaxResponse({"operation": "countdown:set"}))
