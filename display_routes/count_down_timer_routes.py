from aiohttp import web as aiohttp_web
from access_verification import ajax_verify_token
import config
import curling_clock_manager

routes = aiohttp_web.RouteTableDef()

@routes.post('/countdown/show')
@ajax_verify_token("pin")
async def count_down_show_ajax(_request):
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_count_down_update)
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "countdown:show"}))


@routes.post('/countdown/lastend')
@ajax_verify_token("pin")
async def count_down_last_end_ajax(_request):
    curling_clock_manager.manager.timers.count_down.pause()
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_count_down_last_end)
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "countdown:last end"}))


@routes.post('/countdown/pause')
@ajax_verify_token("pin")
async def count_down_pause_ajax(_request):
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_count_down_update)
    curling_clock_manager.manager.timers.count_down.pause()
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "countdown:pause"}))


@routes.post('/countdown/resume')
@ajax_verify_token("pin")
async def count_down_resume_ajax(_request):
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_count_down_update)
    curling_clock_manager.manager.timers.count_down.resume()
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "countdown:resume"}))


@routes.post('/countdown/start')
@ajax_verify_token("pin")
async def count_down_start_ajax(_request):
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_count_down_update)
    curling_clock_manager.manager.timers.count_down.resume()

    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "countdown:start",
                                                                                      "timer": "countdown"}))


@routes.post('/countdown/status')
@ajax_verify_token("pin")
async def count_down_status_ajax(_request):
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.count_down.ajax_response({"operation": "status",
                                                                                                "timer": "countdown"}))


@routes.post('/countdown/set')
@ajax_verify_token("pin")
async def count_down_set_ajax(request):
    curling_clock_manager.manager.timers.count_down.pause()
    json = await request.json()
    curling_clock_manager.manager.timers.count_down.set_time(json["gameTime"])
    finished_message_colour = json.get("finishedMessageColour", "green")
    last_end_message_colour = json.get("lastEndMessageColour", "red")
    team_colour = json.get("teamColour", "default")
    timers = curling_clock_manager.manager.timers

    try:
        timers.count_down.set_finished_message(json["finishedMessage"],
                                               finished_message_colour,
                                               config.display.defaults.finished_message_display_time)
        timers.count_down.set_last_end_message(json["lastEndMessage"],
                                               last_end_message_colour,
                                               config.display.defaults.last_end_message_display_time)

        my_sheet = config.display.sheets.my_sheet
        timers.competition.teams[0].name = json["team1"]
        timers.competition.teams[0].colour = my_sheet.top_colour if team_colour in ["board", "default"] else team_colour

        timers.competition.teams[1].name = json["team2"]
        timers.competition.teams[1].colour = my_sheet.bottom_colour if team_colour in ["board", "default"] else team_colour

        if json["team1"].strip() or json["team2"].strip():
            curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_team_names_count_down)
        else:
            curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_count_down_update)
    except KeyError:
        curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_count_down_update)

    return aiohttp_web.json_response(timers.ajax_response({"operation": "countdown:set"}))
