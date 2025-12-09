from Logger import warning, info, exception
import datetime
import time
import asyncio

import HTTP_Utils

from aiohttp import web as aiohttp_web

from AccessVerification import ajaxVerifyToken
import Config
import CurlingClockManager
from Timers import strToSeconds
from HardwareClock import updateClockTime, setHardwareClock
import HTTP_Utils as httpUtils
from Utils import myIPAddress, generatePIN
from Identify import whoareyou
from ConfigurationManager import updateAllConfigs
from CommonRoutes import delayedRestart

routes = aiohttp_web.RouteTableDef()


@routes.post('/restart')
@ajaxVerifyToken("admin")
async def restartAjax(request):
    info("app: restart...")
    CurlingClockManager.manager.setScrollingText("Restarting ...")
    CurlingClockManager.manager.setView(CurlingClockManager.manager.displayText)
    asyncio.ensure_future(delayedRestart(delay=5))
    return aiohttp_web.json_response({"restart": 1})


@routes.post('/reboot')
@ajaxVerifyToken("admin")
async def rebootAjax(request):
    info("app: reboot...")
    CurlingClockManager.manager.setScrollingText("Rebooting ...")
    CurlingClockManager.manager.setView(CurlingClockManager.manager.displayScrollingText)
    asyncio.ensure_future(delayedRestart(delay=5, reboot=True))
    return aiohttp_web.json_response({"reboot": 1})


@routes.post('/pin/get')
@ajaxVerifyToken("user")
async def getPINAjax(request):
    json = await request.json()
    expireTime = json["expireTime"]
    pinSheet = json["sheet"]

    newPin = generatePIN()

    for sheet in Config.display.sheets:
        if sheet.name == pinSheet:
            sheet.pin = newPin
            sheet.pinExpireTime = str(int(time.time() + strToSeconds(expireTime)))

            Config.display.sheets.modified = True
            asyncio.ensure_future(updateAllConfigs())
            
            return aiohttp_web.json_response({"pin": newPin,
                                              "pinExpireTime": datetime.datetime.fromtimestamp(int(sheet.pinExpireTime)).strftime('%c')
                                              })

    return aiohttp_web.json_response({"pin": "Unassigned",
                                      "pinExpireTime": "badness"
                                      })


@routes.post('/pin/get/all')
@ajaxVerifyToken("user")
async def PINgetAllAjax(request):
    json = await request.json()
    expireTime = json["expireTime"]

    newPins = []
    for sheet in Config.display.sheets:
        if sheet.ip == "Unassigned":
            continue

        newPin = generatePIN()
        sheet.pin = newPin
        sheet.pinExpireTime = str(int(time.time() + strToSeconds(expireTime)))

        newPins.append({"sheet": sheet.name,
                        "ordinal": sheet.ordinal,
                        "pinExpireTime": datetime.datetime.fromtimestamp(int(sheet.pinExpireTime)).strftime('%c'),
                        "pin": newPin})

    Config.display.sheets.modified = True
    asyncio.ensure_future(updateAllConfigs())
    return aiohttp_web.json_response({"pins": newPins})


@routes.post('/flash')
@ajaxVerifyToken("user")
async def flashTextAjax(request):
    json = await request.json()
    if CurlingClockManager.manager:
        CurlingClockManager.manager.setFlashText(json.get("text", myIPAddress()), json.get("colour", "red"))
        CurlingClockManager.manager.setView(CurlingClockManager.manager.displayFlashText)

    return aiohttp_web.json_response({"operation": "flashtext"})


@routes.post('/timedate')
@ajaxVerifyToken("admin")
async def clockSetHtmlPost(request):
    startTime = time.time()
    data = await request.json()
    
    try:
        if Config.display.rink.clockServer.strip() != myIPAddress():
            return aiohttp_web.json_response({"msg": "trying to set time on a clock that doesn't have a hardware clock"})
        
        CurlingClockManager.manager.abort()
    
        warning("timedate: request data=%s", data.items())

        permanent = data.get("permanent", True)
    
        newTime = data.get("time", None)
        if newTime:
            newTime = newTime.strip()
        
        newTimeZone = data.get("timeZone", None)
        if newTimeZone:
            newTimeZone = newTimeZone.strip()
        
        newDate = data.get("date", None)
        if newDate:
            newDate = newDate.strip()

        newTimeSecsSinceMidnight = None

        msg = "nothing asked"
        if newTime:
            sp = newTime.split(":")
            info("ClockSet: setting time %s: %s", newTime, sp)
            if len(sp) == 1:
                clockTimeHours, clockTimeMinutes, clockTimeSeconds = sp + [0, 0]
            elif len(sp) == 2:
                clockTimeHours, clockTimeMinutes, clockTimeSeconds = sp + [0,]
            else:
                clockTimeHours, clockTimeMinutes, clockTimeSeconds = sp[0:3]
                
            # adjust start time by  approximate amount do connection to match time. empirical hack
            newTimeSecsSinceMidnight = int(clockTimeHours) * 3600 + int(clockTimeMinutes) * 60 + int(clockTimeSeconds) + 0.600
            
        if newTimeZone:
            if updateClockTime(newTimeZone=newTimeZone):
                Config.display.rink.timezone = newTimeZone
                await updateAllConfigs(True)
                msg = "timezone set"
            else:
                return aiohttp_web.json_response({"msg": f"Failed to set time zone to '{newTimeZone}'"})
            
        diffTime = time.time() - startTime

        if newTimeSecsSinceMidnight or newDate:
            msg = updateClockTime(newTimeSecsFromMidnight=newTimeSecsSinceMidnight + diffTime if newTimeSecsSinceMidnight else None,
                                  newDate=newDate if newDate else None,
                                  newTimeZone=None)

        if permanent:
            setHardwareClock()
            CurlingClockManager.manager.setScrollingText("Restarting ...", "red")
            CurlingClockManager.manager.setView(CurlingClockManager.manager.displayText)
            
            asyncio.ensure_future(delayedRestart(delay=5))
            msg = "Setting hardware clock"

    except Exception as e:
        msg = f"clock set badness {e}"
        exception("set timedate %s '%s'", msg, data, exc_info=True)
            
    return aiohttp_web.json_response({"msg": msg})


@routes.get('/ajax/sheets')
@ajaxVerifyToken("admin")
async def sheetsAjaxGet(request):
    return aiohttp_web.json_response({"nSheets": len(Config.display.sheets),
                                      "sheets": [s._asdict() for s in Config.display.sheets],
                                      "clockServer": Config.display.rink.clockServer,
                                      "clubName": Config.display.rink.clubName,
                                      "drawServer": Config.display.defaults.drawServer})


@routes.post('/ajax/sheets')
@ajaxVerifyToken("admin")
async def sheetsAjaxPost(request):
    json = await request.json()

    oldSheetCount = Config.display.rink.numberOfSheets
    newSheetCount = min(32, max(1, int(json["nSheets"])))

    Config.display.sheets.setCount(newSheetCount)

    sheets = json["sheets"]
    smallest = min(oldSheetCount, newSheetCount)
    
    for updSheet, sheet in zip(sheets[0:smallest], Config.display.sheets[0:smallest]):
        sheet.topColour = updSheet["top"]
        sheet.bottomColour = updSheet["bottom"]
        sheet.ip = updSheet["ip"]
        sheet.name = updSheet["name"]
        sheet.hasHardwareClock = "No"
        sheet.hostName = "Unassigned"

        if sheet.ip != "Unassigned":
            whoami = await whoareyou(sheet.ip, httpUtils.port)
            if whoami:
                sheet.hasHardwareClock = whoami.get("hwClock", "No")
                sheet.hostName = whoami.get("hostname", "Unassigned")
    
    if json["drawServer"].strip().lower() not in ["", "unassigned"]:
        Config.display.defaults.drawServer = json["drawServer"].strip()
    else:
        # pick first non-rtc clock or last rtc clock if they all have clocks
        for s in Config.display.sheets:
            if s.ip and s.ip.lower() != "unassigned":
                Config.display.defaults.drawServer = s.ip

                if not s.hasHardwareClock:
                    break

    if json["clockServer"].strip().lower() not in ["", "unassigned"]:
        Config.display.rink.clockServer = json["clockServer"].strip()
    else:
        # pick rtc clock
        for s in Config.display.sheets:
            if s.ip and s.ip.lower() != "unassigned":
                if s.hasHardwareClock:
                    Config.display.rink.clockServer = s.ip

    Config.display.rink.clubName = json.get("clubName", "Just A Club")
    Config.display.rink.modified = True

    Config.display.server.setup = 4
    Config.display.save()
    asyncio.ensure_future(updateAllConfigs())

    return aiohttp_web.json_response({"nSheets": len(Config.display.sheets),
                                      "sheets":  [s._asdict() for s in Config.display.sheets]})


@routes.get('/ajax/organization')
@ajaxVerifyToken("admin")
async def organizationAjaxGet(request):
    return aiohttp_web.json_response({**Config.display.organization.items()})


@routes.post('/ajax/organization')
@ajaxVerifyToken("admin")
async def organizationAjaxPost(request):
    json = await request.json()

    values = json.get("data", {})

    for n, v in values.items():
        Config.display.organization.set(n, v)

    Config.display.organization.modified = True
    asyncio.ensure_future(updateAllConfigs())

    return aiohttp_web.json_response({"msg": "values saved"})
