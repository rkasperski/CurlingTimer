import tempfile
from Logger import error
from AccessVerification import ajaxVerifyToken
from aiohttp import web as aiohttp_web
import jsonschema
import Draws
from Utils import cleanFiles

routes = aiohttp_web.RouteTableDef()

drawJSONSchema = {
    "type": "object",
    "properties": {
        "time": {"regex": "\d\d:\d\d"},
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


def drawToResponse(draw, response=None, sheets=True):
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
@ajaxVerifyToken("user")
async def drawScheduleHtmlGet(request):
    cleanFiles('/tmp/*_curlingtimer_schedule.xlsx')
    fname = tempfile.mkstemp(suffix='_curlingtimer_schedule.xlsx', prefix='tmp', dir='/tmp')[1]
    Draws.drawDB.writeCSV(fname)
    response = aiohttp_web.FileResponse(fname)
    # cleanFiles(fname)
    return response


@routes.post('/draw/upload')
@ajaxVerifyToken("user")
async def drawUploadAjax(request):
    if request.content_length > 5000000:
        # need failure response
        return aiohttp_web.json_response({"rc": False,
                                          "hash": Draws.drawDB.getHash(),
                                          "msg": "draw upload is too large"})

    msgs = await Draws.drawDB.uploadAjax(request)
    return aiohttp_web.json_response({"found": False,
                                      "hash": Draws.drawDB.getHash(),
                                      "msg": msgs})


@routes.post('/draw/get')
@ajaxVerifyToken("pin")
async def drawGetAjax(request):
    json = await request.json()

    id = int(json.get("id", 0))

    draw = Draws.drawDB.getDrawById(id)
    if draw:
        return aiohttp_web.json_response({"found": True,
                                          "hash": Draws.drawDB.getHash(),
                                          "draw": draw})
    else:
        return aiohttp_web.json_response({"found": False})

    
@routes.post('/draw/hash')
@ajaxVerifyToken("pin")
async def drawHashAjax(request):
    return aiohttp_web.json_response({"hash": Draws.drawDB.getHash()})


@routes.post('/draw/getlist')
@ajaxVerifyToken("pin")
async def drawGetListAjax(request):
    return aiohttp_web.json_response({"found": True,
                                      "hash": Draws.drawDB.getHash(),
                                      "draws": [drawToResponse(d, {"id": d.doc_id}, sheets=False)
                                                for d in Draws.drawDB.getAllDraws()]})


@routes.post('/draw/add')
@ajaxVerifyToken("user")
async def drawAddAjax(request):
    json = await request.json()

    try:
        jsonschema.validate(json, drawJSONSchema)
        draw, msg = Draws.drawDB.addDraw(json)

        return aiohttp_web.json_response(drawToResponse(json, {"added": True,
                                                               "hash": Draws.drawDB.getHash(),
                                                               "draw": draw,
                                                               "msg": msg,
                                                               "id": draw["id"]}))
    except jsonschema.exceptions.ValidationError:
        error("draws: invalid data received")

        return aiohttp_web.json_response({"added": False})

    
@routes.post('/draw/set')
@ajaxVerifyToken("user")
async def drawSetAjax(request):
    json = await request.json()

    try:
        id = json["id"]
        updateDraw = json["draw"]
        jsonschema.validate(updateDraw, drawJSONSchema)
        draw = Draws.drawDB.updateDraw(id, updateDraw)

        return aiohttp_web.json_response(drawToResponse(draw, {"set": True,
                                                               "hash": Draws.drawDB.getHash(),
                                                               "draw": draw,
                                                               "id": draw["id"]}))
    except jsonschema.exceptions.ValidationError:
        error("draws: invalid data received:")
        return aiohttp_web.json_response({"set": False})

    
@routes.post('/draw/delete')
@ajaxVerifyToken("user")
async def drawDeleteAjax(request):
    json = await request.json()

    id = json.get("id", None)
    if id:
        draws = [id, ]
    else:
        draws = json.get("draws", [])

    msg = []
    for id in draws:
        deleted = Draws.drawDB.deleteDraw(id)
        msg.append([id, deleted])

    return aiohttp_web.json_response({"deleted": msg,
                                      "hash": Draws.drawDB.getHash()})
