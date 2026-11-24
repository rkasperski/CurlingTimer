import tempfile
from aiohttp import web as aiohttp_web
import jsonschema
from access_verification import ajax_verify_token
from logger import error
import draws
from utils import clean_files

routes = aiohttp_web.RouteTableDef()

draw_json_schema = {
    "type": "object",
    "properties": {
        "time": {"regex": r"\d\d:\d\d"},
        "date": {"regex": r"\d\d\d\d-\d\d-\d\d"},
        "name": {"type": "string"},
        "colour": {"type": "string"},
        "show": {"regex": r"(no|none|blank\d+)"},
        "autoDelete": {"regex": r"(No|None|\d+)"},
        "atStart": {"regex": r"(no|none|countdown|blank|\d+)"},
        "sheets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "team1": {"type": "string"},
                    "team2": {"type": "string"}
                },
                "required": [
                    "team1",
                    "team2"
                ]
            }
        }
    },
    "required": [
        "sheets",
        "date",
        "show",
        "colour",
        "time",
        "name"
    ]
}


def draw_to_response(draw, response=None, sheets=True):
    if not response:
        response = {}

    response.update({"time": draw["time"],
                     "date": draw["date"],
                     "show": draw.get("show", "blank"),
                     "autoDelete": draw.get("autoDelete", "No"),
                     "atStart": draw.get("atStart", "blank"),
                     "name": draw["name"]})

    if sheets:
        response["sheets"] = draw["sheets"]

    return response


@routes.get('/draw/schedule.csv')
@ajax_verify_token("user")
async def draw_schedule_html_get(request):
    clean_files('/tmp/*_curlingtimer_schedule.xlsx')
    fname = tempfile.mkstemp(suffix='_curlingtimer_schedule.xlsx', prefix='tmp', dir='/tmp')[1]
    draws.draw_db.write_csv(fname)
    response = aiohttp_web.FileResponse(fname)
    # cleanFiles(fname)
    return response


@routes.post('/draw/upload')
@ajax_verify_token("user")
async def draw_upload_ajax(request):
    if request.content_length > 5000000:
        # need failure response
        return aiohttp_web.json_response({"rc": False,
                                          "hash": draws.draw_db.get_hash(),
                                          "msg": "draw upload is too large"})

    msgs = await draws.draw_db.upload_ajax(request)
    return aiohttp_web.json_response({"found": False,
                                      "hash": draws.draw_db.get_hash(),
                                      "msg": msgs})


@routes.post('/draw/get')
@ajax_verify_token("pin")
async def draw_get_ajax(request):
    json = await request.json()

    draw_id = int(json.get("id", 0))

    draw = draws.draw_db.get_draw_by_id(draw_id)
    if draw:
        return aiohttp_web.json_response({"found": True,
                                          "hash": draws.draw_db.get_hash(),
                                          "draw": draw})

    return aiohttp_web.json_response({"found": False})


@routes.post('/draw/hash')
@ajax_verify_token("pin")
async def draw_hash_ajax(request):
    return aiohttp_web.json_response({"hash": draws.draw_db.get_hash()})


@routes.get('/draw/list')
@ajax_verify_token("pin")
async def draw_get_list_ajax1(request):
    return aiohttp_web.json_response({"found": True,
                                      "hash": draws.draw_db.get_hash(),
                                      "draws": [ {**d, "id": d.doc_id} for d in draws.draw_db.get_all_draws()]})


@routes.post('/draw/add')
@ajax_verify_token("user")
async def draw_add_ajax(request):
    json = await request.json()

    try:
        jsonschema.validate(json, draw_json_schema)
        draw, msg = draws.draw_db.add_draw(json)

        return aiohttp_web.json_response(draw_to_response(json, {"added": True,
                                                                 "hash": draws.draw_db.get_hash(),
                                                                 "draw": draw,
                                                                 "msg": msg,
                                                                 "id": draw["id"]}))
    except jsonschema.exceptions.ValidationError:
        error("draws: invalid data received")

        return aiohttp_web.json_response({"added": False})


@routes.post('/draw/set')
@ajax_verify_token("user")
async def draw_set_ajax(request):
    json = await request.json()

    try:
        draw_id = json["id"]
        update_draw = json["draw"]

        utime = update_draw.get("time", None)
        if utime and len(utime) > 2 and utime[1] == ':':
            update_draw["time"] = '0' + utime

        jsonschema.validate(update_draw, draw_json_schema)

        draw = draws.draw_db.update_draw(draw_id, update_draw)

        return aiohttp_web.json_response(draw_to_response(draw, {"set": True,
                                                                 "hash": draws.draw_db.get_hash(),
                                                                 "draw": draw,
                                                                 "msg": "updated",
                                                                 "id": draw_id}))
    except jsonschema.exceptions.ValidationError:
        error("draws: invalid data received:")
        return aiohttp_web.json_response({"set": False})


@routes.post('/draw/delete')
@ajax_verify_token("user")
async def draw_delete_ajax(request):
    json = await request.json()

    draw_id = json.get("id", None)
    if draw_id:
        draws = [draw_id, ]
    else:
        draws = json.get("draws", [])

    msg = []
    for draw_id in draws:
        deleted = draws.draw_db.delete_draw(draw_id)
        msg.append([draw_id, deleted])

    return aiohttp_web.json_response({"deleted": msg,
                                      "hash": draws.draw_db.get_hash()})
