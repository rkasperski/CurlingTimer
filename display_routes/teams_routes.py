"""
Defines the endpoints that set and display teams names
"""

from aiohttp import web as aiohttp_web
from access_verification import ajax_verify_token
import config
import curling_clock_manager
from utils import to_int

routes = aiohttp_web.RouteTableDef()

def show_team_names(no_names_view, active_until=None, active_interval=None):
    manager = curling_clock_manager.manager
    timers = manager.timers

    if timers.competition.paused() \
           and timers.count_down.paused() \
           and (timers.competition.teams[0].name.strip() \
                or timers.competition.teams[1].name.strip()):
        manager.set_view(curling_clock_manager.manager.view_team_names, reset_idle=False)
        manager.reset_idle_time(active_until=active_until, active_interval=active_interval)
    elif no_names_view:
        manager.set_view(no_names_view)
    else:
        manager.set_view(curling_clock_manager.manager.view_blank_screen)


@routes.post('/teamnames/show/competition')
@ajax_verify_token("pin")
async def teamnames_show_competition_ajax(request):
    json = await request.json()

    active_until = to_int(json.get("until", None), None)
    how_long = to_int(json.get("howLong", None), None)

    show_team_names(curling_clock_manager.manager.view_competition_update, active_until, how_long)
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response(
        {"operation": "competition:names"}), content_type="application/json")


@routes.post('/teamnames/show/countdown')
@ajax_verify_token("pin")
async def teamnames_show_count_down_ajax(request):
    json = await request.json()

    active_until = to_int(json.get("until", None), None)
    how_long = to_int(json.get("howLong", None), None)

    show_team_names(curling_clock_manager.manager.view_count_down_update, active_until, how_long)
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response(
        {"operation": "countdown:names"}), content_type="application/json")


@routes.post('/teamnames/show')
@ajax_verify_token("pin")
async def teamnames_show_ajax(request):
    json = await request.json()
    active_until = to_int(json.get("until", None), None)
    how_long = to_int(json.get("howLong", None), None)
    show_team_names(None, active_until, how_long)
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response(
        {"operation": "team names show"}), content_type="application/json")


@routes.post('/teamnames/get')
@ajax_verify_token("pin")
async def teamnames_get_ajax(request):
    my_sheet = config.display.sheets.my_sheet
    teams = curling_clock_manager.manager.timers.competition.teams
    return aiohttp_web.json_response({"team1": teams[0].name,
                                      "team2": teams[1].name,
                                      "time1": teams[1].time_remaining(),
                                      "time2": teams[1].time_remaining(),
                                      "timeouts1": teams[0].remaining_timeouts,
                                      "timeouts2": teams[1].remaining_timeouts,
                                      "top_colour": my_sheet.top_colour,
                                      "bottom_colour": my_sheet.bottom_colour,
                                      "sheet": my_sheet.name,
                                      "ordinal": my_sheet.ordinal})


@routes.post('/teamnames/set')
@ajax_verify_token("pin")
async def teamnames_set_ajax(request):
    json = await request.json()

    colour = json.get("colour", None)

    my_sheet = config.display.sheets.my_sheet
    competition_timer = curling_clock_manager.manager.timers.competition
    if "team1" in json:
        competition_timer.teams[0].name = json["team1"]
        competition_timer.teams[0].colour = my_sheet.top_colour if colour is None or colour == "default" else colour

    if "team2" in json:
        competition_timer.teams[1].name = json["team2"]
        competition_timer.teams[1].colour = my_sheet.bottom_colour if colour is None or colour == "default" else colour

    return aiohttp_web.json_response({"team1": competition_timer.teams[0].name,
                                      "team2": competition_timer.teams[1].name,
                                      "sheet": my_sheet.name,
                                      "ordinal": my_sheet.ordinal}, content_type="application/json")
