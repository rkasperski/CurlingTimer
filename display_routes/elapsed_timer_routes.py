from aiohttp import web as aiohttp_web
from access_verification import ajax_verify_token
import curling_clock_manager

routes = aiohttp_web.RouteTableDef()


@routes.post('/elapsed/set')
@ajax_verify_token("pin")
async def elapsed_set_ajax(request):
    curling_clock_manager.manager.timers.elapsed_time.pause()
    json = await request.json()
    curling_clock_manager.manager.timers.elapsed_time.set_initial_time(json["time"])

    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_elapsed_time_update)
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "elapsedtime:set"}))


@routes.post('/elapsed/status')
@ajax_verify_token("pin")
async def elapsed_status_ajax(request):
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.elapsed_time.ajax_response({"operation": "status",
                                                                                                    "timer": "elapsed"}))


@routes.post('/elapsed/show')
@ajax_verify_token("pin")
async def elapsed_show_ajax(request):
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_elapsed_time_update)

    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "elapsedtime:show"}))


@routes.post('/elapsed/pause')
@ajax_verify_token("pin")
async def elapsed_pause_ajax(request):
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_elapsed_time_update)
    curling_clock_manager.manager.timers.elapsed_time.pause()
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "elapsedtime:pause"}))


@routes.post('/elapsed/resume')
@ajax_verify_token("pin")
async def elapsed_resume_ajax(request):
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_elapsed_time_update)
    curling_clock_manager.manager.timers.elapsed_time.resume()
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "elapsedtime:start"}))


@routes.post('/elapsed/start')
@ajax_verify_token("pin")
async def elapsed_start_ajax(request):
    curling_clock_manager.manager.set_view(curling_clock_manager.manager.view_elapsed_time_update
                                        )
    curling_clock_manager.manager.timers.elapsed_time.resume()
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "elapsedtime:start"}))
