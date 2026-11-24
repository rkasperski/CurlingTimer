from aiohttp import web as aiohttp_web
from access_verification import ajax_verify_token
import config
import curling_clock_manager
from timers import str_to_seconds

routes = aiohttp_web.RouteTableDef()


@routes.post('/competition/pause')
@ajax_verify_token("pin")
async def competition_pause_ajax(request):
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_competition_update)
    curling_clock_manager.manager.timers.competition.pause()
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "pause"}))


@routes.post('/competition/show')
@ajax_verify_token("pin")
async def competition_show_ajax(request):
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_competition_update)
    return aiohttp_web.json_response(curling_clock_manager.manager.ajax_response({"operation": "show"}))


@routes.post('/competition/resume')
@ajax_verify_token("pin")
async def competition_resume_ajax(request):
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_competition_update)
    curling_clock_manager.manager.timers.competition.resume()
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "resume"}))


@routes.post('/competition/exchange')
@ajax_verify_token("pin")
async def competition_team_exchange_ajax(request):
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_competition_update)
    curling_clock_manager.manager.timers.competition.exchange_teams()
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "flip"}))


@routes.post('/competition/team1/resume')
@ajax_verify_token("pin")
async def competition_team1_resume_ajax(request):
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_competition_update)
    curling_clock_manager.manager.timers.competition.resume_team1()
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "start team 1"}))


@routes.post('/competition/team2/resume')
@ajax_verify_token("pin")
async def competition_team2_resume_ajax(request):
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_competition_update)
    curling_clock_manager.manager.timers.competition.resume_team2()
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "start team 2"}))


@routes.post('/competition/team1/pause')
@ajax_verify_token("pin")
async def competition_team1_pause_ajax(request):
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_competition_update)
    curling_clock_manager.manager.timers.competition.pause_team1()
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "pause team 1"}))


@routes.post('/competition/team2/pause')
@ajax_verify_token("pin")
async def competition_team2_pause_ajax(request):
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_competition_update)
    curling_clock_manager.manager.timers.competition.pause_team2()
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "pause team 2"}))


def game_setup(team_time, team_colour, team1_name, team2_name, intermission_time):
    competition_timer = curling_clock_manager.manager.timers.competition
    competition_timer.timeout_number = int(config.display.defaults.number_of_timeouts)
    competition_timer.timeout_length = str_to_seconds(config.display.defaults.timeout_length)

    my_sheet = config.display.sheets.my_sheet

    teams = competition_timer.teams
    teams[0].colour = my_sheet.top_colour if team_colour in ["board", "default"] else team_colour
    teams[0].name = team1_name
    teams[0].set_time(team_time)
    teams[0].remaining_timeouts = competition_timer.timeout_number

    teams[1].colour = my_sheet.bottom_colour if team_colour in ["board", "default"] else team_colour
    teams[1].name = team2_name
    teams[1].set_time(team_time)
    teams[1].remaining_timeouts = competition_timer.timeout_number

    print(f"{ teams[0].name=} {teams[0].remaining_timeouts=}")
    print(f"{ teams[1].name=} {teams[1].remaining_timeouts=}")

    if team1_name.strip() or team2_name.strip():
        curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_team_names)
    else:
        curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_competition_update)


@routes.post('/competition/setup')
@ajax_verify_token("pin")
async def competition_setup_ajax(request):
    curling_clock_manager.manager.abort()
    curling_clock_manager.manager.reset_idle_time()
    curling_clock_manager.manager.timers.competition.pause()

    json = await request.json()

    team_time = str_to_seconds(json["timeLimit"], default=38*60)
    intermission_time = str_to_seconds(json["intermissionLength"])
    team_colour = json.get("teamColour", "board")
    game_setup(team_time, team_colour, json["team1"], json["team2"], intermission_time)

    return aiohttp_web.json_response(curling_clock_manager.manager.timers.competition.ajax_response({"timer": "competition"}))


@routes.post('/competition/status')
@ajax_verify_token("pin")
async def competition_status_ajax(request):
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.competition.ajax_response({"operation": "status",
                                                                                                  "timer": "competition"}))


@routes.post('/competition/team1/status')
@ajax_verify_token("pin")
async def competition_team1Status_ajax(request):
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.competition.teams[0].ajax_response({"operation": "status",
                                                                                                           "timer": "competition"}))


@routes.post('/competition/team2/status')
@ajax_verify_token("pin")
async def competition_team2Status_ajax(request):
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.competition.teams[1].ajax_response({"operation": "status",
                                                                                                           "timer": "competition"}))


@routes.post('/timeout/status')
@ajax_verify_token("pin")
async def timeout_status_ajax(request):
    timer = curling_clock_manager.manager.timers.timeout
    return aiohttp_web.json_response(timer.ajax_response({"operation": "status",
                                                         "team": timer.team_id,
                                                         "timer": "timeout"}))


@routes.post('/intermission/status')
@ajax_verify_token("pin")
async def intermission_status_ajax(request):
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.intermission.ajax_response({"operation": "status",
                                                                                                   "timer": "intermission"}))


@routes.post('/competition/intermission/start')
@ajax_verify_token("pin")
async def competitionIntermission_startPost(request):
    curling_clock_manager.manager.timers.competition.pause()
    curling_clock_manager.manager.abort()

    data = await request.json()

    seconds = str_to_seconds(data.get("intermissionLength", config.display.defaults.intermission_length))

    curling_clock_manager.manager.timers.intermission.set_time(seconds)
    curling_clock_manager.manager.timers.intermission.resume()
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_intermission_update)

    return aiohttp_web.json_response(curling_clock_manager.manager.timers.intermission.ajax_response({"operation": "start",
                                                                                                   "timer": "intermission"}))


@routes.post('/competition/intermission/cancel')
@ajax_verify_token("pin")
async def intermissionCancel_ajax(request):
    curling_clock_manager.manager.timers.intermission.pause()
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_competition_update)

    return aiohttp_web.json_response({"operation": "start"})


@routes.post('/competition/timeout/start')
@ajax_verify_token("pin")
async def competition_timeout_start_ajax(request):
    curling_clock_manager.manager.timers.competition.pause()
    curling_clock_manager.manager.abort()

    data = await request.json()
    my_sheet = config.display.sheets.my_sheet

    timer = curling_clock_manager.manager.timers.timeout
    timer.team_id = data.get("team", "team1")
    if timer.team_id == "team1":
        timer.team = curling_clock_manager.manager.timers.competition.teams[0]
        timer.colour = my_sheet.top_colour
    else:
        timer.team = curling_clock_manager.manager.timers.competition.teams[1]
        timer.colour = my_sheet.bottom_colour

    timer.set_time(config.display.defaults.timeout_length)

    timer.resume()

    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_timeout_update)

    return aiohttp_web.json_response(timer.ajax_response({"operation": "start"}))


@routes.post('/competition/timeout/done')
@ajax_verify_token("pin")
async def competition_timeoutDone_ajax(request):
    timer = curling_clock_manager.manager.timers.timeout
    timer.team.remaining_timeouts -= 1
    timer.pause()

    if timer.team_id == "team1":
        curling_clock_manager.manager.timers.competition.resume_team1()
        team = curling_clock_manager.manager.timers.competition.teams[0]
    elif timer.team_id == "team2":
        curling_clock_manager.manager.timers.competition.resume_team2()
        team = curling_clock_manager.manager.timers.competition.teams[1]

    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_competition_update)
    return aiohttp_web.json_response(team.ajax_response({"operation": "done"}))


@routes.post('/competition/timeout/cancel')
@ajax_verify_token("pin")
async def competition_timeoutCancel_ajax(request):

    curling_clock_manager.manager.timers.timeout.pause()
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_competition_update)
    return aiohttp_web.json_response({"operation": "cancel"})


@routes.post('/competition/betweenendtimer')
@ajax_verify_token("pin")
async def competition_BetweenEndTimer_ajax(request):
    curling_clock_manager.manager.timers.competition.pause()
    curling_clock_manager.manager.abort()

    data = await request.json()
    between_end_time = int(data.get("betweenEndTime", config.display.defaults.between_end_time))

    curling_clock_manager.manager.timers.intermission.set_time(between_end_time)
    curling_clock_manager.manager.timers.intermission.set_intermission("intermission")
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_intermission_update)
    curling_clock_manager.manager.timers.timeout.resume()
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_between_end_timer_update)

    return aiohttp_web.json_response({"operation": "start"})


@routes.post('/competition/settime')
@ajax_verify_token("pin")
async def competition_set_time_ajax(request):
    json = await request.json()
    team = json.get("team", None)
    team_time = json.get("time", None)

    if team is not None and team_time is not None:
        if team == "team1":
            curling_clock_manager.manager.timers.competition.teams[0].set_time(team_time)
        else:
            curling_clock_manager.manager.timers.competition.teams[1].set_time(team_time)

        return aiohttp_web.json_response(curling_clock_manager.manager.timers.competition.ajax_response())

    return aiohttp_web.json_response({"rc": "fail"})
