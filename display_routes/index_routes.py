from aiohttp import web as aiohttp_web
from access_verification import ajax_verify_token
import curling_clock_manager

routes = aiohttp_web.RouteTableDef()


@routes.post('/settime')
@ajax_verify_token("admin")
async def set_time_ajax(_request):
    curling_clock_manager.manager.reset_idle_time()
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "set time"}))


@routes.post('/status')
@ajax_verify_token("pin")
async def status_post_ajax(_request):
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "status"}))


# Eye is this used???
@routes.get('/status')
@ajax_verify_token("user")
async def status_get_ajax(_request):
    return aiohttp_web.json_response(curling_clock_manager.manager.timers.ajax_response({"operation": "status"}))


@routes.post('/kapow')
@ajax_verify_token("pin")
async def kapow_ajax(request):
    curling_clock_manager.manager.reset_idle_time()
    json = await request.json()
    kpw = json.get("kapow", "rain")

    curling_clock_manager.manager.set_kapow(kpw)

    return aiohttp_web.json_response({"operation": "kapow"})
