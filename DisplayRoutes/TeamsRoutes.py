import time

from aiohttp import web as aiohttp_web
from AccessVerification import ajaxVerifyToken
import Config
import CurlingClockManager
from Utils import toInt

routes = aiohttp_web.RouteTableDef()


def getValidBoardColour(c):
    return "white" if c in [None, "default", "board"] or c not in Config.colours else c


def showTeamNames(active_until=None, active_interval=None):
    if CurlingClockManager.manager.timers.competition.paused() and CurlingClockManager.manager.timers.countDown.paused() and (CurlingClockManager.manager.timers.competition.teams[0].name.strip() or CurlingClockManager.manager.timers.competition.teams[0].name.strip()):
        CurlingClockManager.manager.setView(CurlingClockManager.manager.teamNames, reset_idle=False)
        CurlingClockManager.manager.resetIdleTime(activeUntil=active_until, activeInterval=active_interval)
    else:
        CurlingClockManager.manager.setView(CurlingClockManager.manager.competitionUpdate)

        
@routes.post('/teamnames/show')
@ajaxVerifyToken("pin")
async def teamnamesShowAjax(request):
    json = await request.json()

    activeUntil = toInt(json.get("until", None), None)
    howLong = toInt(json.get("howLong", None), None)

    showTeamNames(activeUntil, howLong)
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "competition:names"}), content_type="application/json")


@routes.post('/teamnames/get')
@ajaxVerifyToken("pin")
async def teamnamesGetAjax(request):
    mySheet = Config.display.sheets.mySheet
    teams = CurlingClockManager.manager.timers.competition.teams
    return aiohttp_web.json_response({"team1": teams[0].name,
                                      "team2": teams[1].name,
                                      "time1": teams[1].timeRemaining(),
                                      "time2": teams[1].timeRemaining(),
                                      "timeouts1": teams[0].remainingTimeouts,
                                      "timeouts2": teams[1].remainingTimeouts,
                                      "topColour": mySheet.topColour,
                                      "bottomColour": mySheet.bottomColour,
                                      "sheet": mySheet.name,
                                      "ordinal": mySheet.ordinal})


@routes.post('/teamnames/set')
@ajaxVerifyToken("pin")
async def teamnamesSetAjax(request):
    json = await request.json()

    colour = json.get("colour", None)

    mySheet = Config.display.sheets.mySheet
    competitionTimer = CurlingClockManager.manager.timers.competition
    if "team1" in json:
        competitionTimer.teams[0].name = json["team1"]
        competitionTimer.teams[0].colour = mySheet.topColour if colour is None or colour == "default" else colour

    if "team2" in json:
        competitionTimer.teams[1].name = json["team2"]
        competitionTimer.teams[1].colour = mySheet.bottomColour if colour is None or colour == "default" else colour

    return aiohttp_web.json_response({"team1": competitionTimer.teams[0].name,
                                      "team2": competitionTimer.teams[1].name,
                                      "sheet": mySheet.name,
                                      "ordinal": mySheet.ordinal}, content_type="application/json")
