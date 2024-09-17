from aiohttp import web as aiohttp_web
from AccessVerification import ajaxVerifyToken
import Config
import CurlingClockManager
from Timers import strToSeconds

routes = aiohttp_web.RouteTableDef()


@routes.post('/competition/pause')
@ajaxVerifyToken("pin")
async def competitionPauseAjax(request):
    CurlingClockManager.manager.resetIdleTime()
    CurlingClockManager.manager.setView(CurlingClockManager.manager.competitionUpdate)
    CurlingClockManager.manager.timers.competition.pause()
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "pause"}))


@routes.post('/competition/show')
@ajaxVerifyToken("pin")
async def competitionShowAjax(request):
    CurlingClockManager.manager.resetIdleTime()
    CurlingClockManager.manager.setView(CurlingClockManager.manager.competitionUpdate)
    return aiohttp_web.json_response(CurlingClockManager.manager.ajaxResponse({"operation": "show"}))


@routes.post('/competition/resume')
@ajaxVerifyToken("pin")
async def competitionResumeAjax(request):
    CurlingClockManager.manager.resetIdleTime()
    CurlingClockManager.manager.setView(CurlingClockManager.manager.competitionUpdate)
    CurlingClockManager.manager.timers.competition.resume()
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "resume"}))


@routes.post('/competition/exchange')
@ajaxVerifyToken("pin")
async def competitionTeamExchangeAjax(request):
    CurlingClockManager.manager.resetIdleTime()
    CurlingClockManager.manager.setView(CurlingClockManager.manager.competitionUpdate)
    CurlingClockManager.manager.timers.competition.exchangeTeams()
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "flip"}))


@routes.post('/competition/team1/resume')
@ajaxVerifyToken("pin")
async def competitionTeam1ResumeAjax(request):
    CurlingClockManager.manager.resetIdleTime()
    CurlingClockManager.manager.setView(CurlingClockManager.manager.competitionUpdate)
    CurlingClockManager.manager.timers.competition.resumeTeam1()
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "start team 1"}))


@routes.post('/competition/team2/resume')
@ajaxVerifyToken("pin")
async def competitionTeam2ResumeAjax(request):
    CurlingClockManager.manager.resetIdleTime()
    CurlingClockManager.manager.setView(CurlingClockManager.manager.competitionUpdate)
    CurlingClockManager.manager.timers.competition.resumeTeam2()
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "start team 2"}))


@routes.post('/competition/team1/pause')
@ajaxVerifyToken("pin")
async def competitionTeam1PauseAjax(request):
    CurlingClockManager.manager.resetIdleTime()
    CurlingClockManager.manager.setView(CurlingClockManager.manager.competitionUpdate)
    CurlingClockManager.manager.timers.competition.pauseTeam1()
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "pause team 1"}))


@routes.post('/competition/team2/pause')
@ajaxVerifyToken("pin")
async def competitionTeam2PauseAjax(request):
    CurlingClockManager.manager.resetIdleTime()
    CurlingClockManager.manager.setView(CurlingClockManager.manager.competitionUpdate)
    CurlingClockManager.manager.timers.competition.pauseTeam2()
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.ajaxResponse({"operation": "pause team 2"}))


def gameSetup(teamTime, teamColour, team1Name, team2Name, intermissionTime):
    competitionTimer = CurlingClockManager.manager.timers.competition
    competitionTimer.timeoutNumber = int(Config.display.defaults.numberOfTimeouts)
    competitionTimer.timeoutLength = strToSeconds(Config.display.defaults.timeoutLength)

    mySheet = Config.display.sheets.mySheet

    teams = competitionTimer.teams
    teams[0].colour = mySheet.topColour if teamColour in ["board", "default"] else teamColour
    teams[0].name = team1Name
    teams[0].setTime(teamTime)
    teams[0].remainingTimeouts = competitionTimer.timeoutNumber

    teams[1].colour = mySheet.bottomColour if teamColour in ["board", "default"] else teamColour
    teams[1].name = team2Name
    teams[1].setTime(teamTime)
    teams[1].remainingTimeouts = competitionTimer.timeoutNumber

    if team1Name.strip() or team2Name.strip():
        CurlingClockManager.manager.setView(CurlingClockManager.manager.teamNames)
    else:
        CurlingClockManager.manager.setView(CurlingClockManager.manager.competitionUpdate)


@routes.post('/competition/setup')
@ajaxVerifyToken("pin")
async def competitionSetupAjax(request):
    CurlingClockManager.manager.abort()
    CurlingClockManager.manager.resetIdleTime()
    CurlingClockManager.manager.timers.competition.pause()

    json = await request.json()

    teamTime = strToSeconds(json["timeLimit"], default=38*60)
    intermissionTime = strToSeconds(json["intermissionLength"])
    teamColour = json.get("teamColour", "board")
    gameSetup(teamTime, teamColour, json["team1"], json["team2"], intermissionTime)

    return aiohttp_web.json_response(CurlingClockManager.manager.timers.competition.ajaxResponse({"timer": "competition"}))


@routes.post('/competition/status')
@ajaxVerifyToken("pin")
async def competitionStatusAjax(request):
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.competition.ajaxResponse({"operation": "status",
                                                                                                  "timer": "competition"}))


@routes.post('/competition/team1/status')
@ajaxVerifyToken("pin")
async def competitionTeam1StatusAjax(request):
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.competition.teams[0].ajaxResponse({"operation": "status",
                                                                                                           "timer": "competition"}))


@routes.post('/competition/team2/status')
@ajaxVerifyToken("pin")
async def competitionTeam2StatusAjax(request):
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.competition.teams[1].ajaxResponse({"operation": "status",
                                                                                                           "timer": "competition"}))


@routes.post('/timeout/status')
@ajaxVerifyToken("pin")
async def timeoutStatusAjax(request):
    timer = CurlingClockManager.manager.timers.timeout
    return aiohttp_web.json_response(timer.ajaxResponse({"operation": "status",
                                                         "team": timer.teamId,
                                                         "timer": "timeout"}))


@routes.post('/intermission/status')
@ajaxVerifyToken("pin")
async def intermissionStatusAjax(request):
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.intermission.ajaxResponse({"operation": "status",
                                                                                                   "timer": "intermission"}))


@routes.post('/competition/intermission/start')
@ajaxVerifyToken("pin")
async def competitionIntermissionStartPost(request):
    CurlingClockManager.manager.timers.competition.pause()
    CurlingClockManager.manager.abort()

    data = await request.json()

    seconds = strToSeconds(data.get("intermissionLength", Config.display.defaults.intermissionLength))

    CurlingClockManager.manager.timers.intermission.setTime(seconds)
    CurlingClockManager.manager.timers.intermission.resume()
    CurlingClockManager.manager.setView(CurlingClockManager.manager.intermissionUpdate)
    return aiohttp_web.json_response(CurlingClockManager.manager.timers.intermission.ajaxResponse({"operation": "start",
                                                                                                   "timer": "intermission"}))


@routes.post('/competition/intermission/cancel')
@ajaxVerifyToken("pin")
async def intermissionCancelAjax(request):
    CurlingClockManager.manager.timers.intermission.pause()
    CurlingClockManager.manager.setView(CurlingClockManager.manager.competitionUpdate)
    return aiohttp_web.json_response({"operation": "start"})


@routes.post('/competition/timeout/start')
@ajaxVerifyToken("pin")
async def competitionTimeoutStartAjax(request):
    CurlingClockManager.manager.timers.competition.pause()
    CurlingClockManager.manager.abort()

    data = await request.json()
    mySheet = Config.display.sheets.mySheet

    timer = CurlingClockManager.manager.timers.timeout
    timer.teamId = data.get("team", "team1")
    if timer.teamId == "team1":
        timer.team = CurlingClockManager.manager.timers.competition.teams[0]
        timer.colour = mySheet.topColour
    else:
        timer.team = CurlingClockManager.manager.timers.competition.teams[1]
        timer.colour = mySheet.bottomColour

    timer.setTime(Config.display.defaults.timeoutLength)

    timer.resume()

    CurlingClockManager.manager.setView(CurlingClockManager.manager.timeoutUpdate)

    return aiohttp_web.json_response(timer.ajaxResponse({"operation": "start"}))


@routes.post('/competition/timeout/done')
@ajaxVerifyToken("pin")
async def competitionTimeoutDoneAjax(request):
    CurlingClockManager.manager.resetIdleTime()

    timer = CurlingClockManager.manager.timers.timeout
    timer.team.remainingTimeouts -= 1
    timer.pause()
    
    if timer.teamId == "team1":
        CurlingClockManager.manager.timers.competition.resumeTeam1()
        team = CurlingClockManager.manager.timers.competition.teams[0]
    elif timer.teamId == "team2":
        CurlingClockManager.manager.timers.competition.resumeTeam2()
        team = CurlingClockManager.manager.timers.competition.teams[1]
        
    CurlingClockManager.manager.setView(CurlingClockManager.manager.competitionUpdate)
    return aiohttp_web.json_response(team.ajaxResponse({"operation": "done"}))


@routes.post('/competition/timeout/cancel')
@ajaxVerifyToken("pin")
async def competitionTimeoutCancelAjax(request):
    CurlingClockManager.manager.resetIdleTime()
    CurlingClockManager.manager.timers.timeout.pause()
    CurlingClockManager.manager.setView(CurlingClockManager.manager.competitionUpdate)
    return aiohttp_web.json_response({"operation": "cancel"})


@routes.post('/competition/betweenendtimer')
@ajaxVerifyToken("pin")
async def competitionTBetweenEndTimerAjax(request):
    CurlingClockManager.manager.timers.competition.pause()
    CurlingClockManager.manager.abort()

    data = await request.json()
    betweenEndTime = int(data.get("betweenEndTime", Config.display.defaults.betweenEndTime))

    CurlingClockManager.manager.intermission.setTime(betweenEndTime)
    CurlingClockManager.manager.timers.intermission.setState("intermission")
    CurlingClockManager.manager.setView(CurlingClockManager.manager.intermissionUpdate)
    CurlingClockManager.manager.timers.timeout.resume()
    CurlingClockManager.manager.setView(CurlingClockManager.manager.betweenEndTimerUpdate)

    return aiohttp_web.json_response({"operation": "start"})


@routes.post('/competition/settime')
@ajaxVerifyToken("pin")
async def competitionSetTimeAjax(request):
    json = await request.json()
    team = json.get("team", None)
    teamTime = json.get("time", None)

    if team is not None and teamTime is not None:
        if team == "team1":
            CurlingClockManager.manager.timers.competition.teams[0].setTime(teamTime)
        else:
            CurlingClockManager.manager.timers.competition.teams[1].setTime(teamTime)
            
        return aiohttp_web.json_response(CurlingClockManager.manager.timers.competition.ajaxResponse())

    return aiohttp_web.json_response({"rc": "fail"})
