from Logger import warning, info, debug, error, logEntries, getEffectiveLevel, clearLogs, getLevelName
import Logger
import asyncio
import time
import datetime
import os
import random
import re
import string
import sys
import HTTP_Utils as httpUtils
from HTTP_Utils import CLOCK_HDR
import IOT_SSL

from aiohttp import web as aiohttp_web

from Utils import MemUsage, memUsage, yearInSeconds, headTail, runCommand
from AccessVerification import ajaxVerifyToken, verifyUser, isAdministrator, getAuthenticator
import AccessVerification
import Config
from Identify import whoareyou, whoami, getApp, versionNo
from ClockAuthenticator import pinExpireTime
import SetupApp
import Devices

hasHardwareClock = False

routes = aiohttp_web.RouteTableDef()

hardwareConfig = None
systemStats = []
curlingClockManager = None

def registerHardwareConfig(hardwareConfigParm):
    global hardwareConfig

    hardwareConfig = hardwareConfigParm


def registerCurlingClockManager(curlingClockManagerParm):
    global curlingClockManager

    curlingClockManager = curlingClockManagerParm

    
def registerHardwareClock(hasHardwareClockParm):
    global hasHardwareClock
    
    hasHardwareClock = hasHardwareClockParm
    
async def delayedRestart(delay=5, reboot=False):
    await asyncio.sleep(delay)
    if reboot:
        os.system("sudo reboot")
    else:
        sys.exit()

    
async def collectSystemStatsTask(app):
    global systemStats
    try:
        while 1:
            systemStats.append(memUsage())
            # collect every 30 minutes
            await asyncio.sleep(60*30)
    except asyncio.CancelledError:
        return

    
async def startTasks(app):
    app['system_stats_collector'] = asyncio.create_task(collectSystemStatsTask(app))

    
async def stopTasks(app):
    if 'system_stats_collector' in app:
        info("CommonRoutes: stop tasks - start")
        info("CommonRoutes: stop tasks - cancel")
        app['system_stats_collector'].cancel()
        info("CommonRoutes: stop tasks - done")

        
async def sensorInfoCollector(sensorList):
    sensorServersInspected = {"Unassigned"}
    breakSensorInfo = []
    for sensorIP, sensorName in sensorList:
        if sensorIP in sensorServersInspected:
            continue

        sensorServersInspected.add(sensorIP)

        whoami = await whoareyou(sensorIP, httpUtils.port)
        if whoami:
            breakSensorInfo.append([sensorName, whoami])

    return breakSensorInfo


@routes.post('/shutdown')
@ajaxVerifyToken("admin")
async def shutdownAjax(request):
    info("app: shutting down...")
    os.system("sudo shutdown now")
    return aiohttp_web.json_response({"shutdown": 1})


@routes.get('/whoareyou')
async def whoAmIAjax(request):
    return aiohttp_web.json_response(whoami())


@routes.get('/epoch')
async def epochAjax(request):
    return aiohttp_web.json_response({"epoch": time.time()})


async def waitForRestart(wait=3):
    if wait:
        await asyncio.sleep(wait)

    sys.exit()

    
@routes.post('/sslconfig/upload')
@ajaxVerifyToken("admin")
async def sslConfigUploadAjax(request):
    if request.content_length > 5000000:
        # need failure response
        return aiohttp_web.HTTPRequestEntityTooLarge(location="/")
    
    reader = aiohttp_web.MultipartReader.from_response(request)
    while True:
        part = await reader.next()
        if part is None:
            break

        if not part.filename:
            break

        dirPath = getApp().config("ssl")

        text = await part.read()
        if part.filename.lower().endswith(".key"):
            fname = os.path.join(dirPath, "current.key")
        elif part.filename.lower().endswith(".crt"):
            fname = os.path.join(dirPath, "current.crt")

        with open(fname, "wb+") as f:
            f.write(text)

    info = IOT_SSL.getInfoSSLCertificate(dirPath, "current.crt")
    return aiohttp_web.json_response({"type": "uploaded",
                                      "info": info})


@routes.post('/sslconfig/generate')
@ajaxVerifyToken("admin")
async def sslConfigGenerateLocalAjax(request):
    hosts = []
    if Config.display.organization.hosts:
        hosts = [s.strip() for s in Config.display.organization.hosts.strip().split(",")]
        
    dirPath = SetupApp.app.config("ssl")
    keyPath = os.path.join(dirPath, "current.key")
    certPath = os.path.join(dirPath, "current.crt")

    IOT_SSL.generateSSLCertificate(certificateFile=certPath,
                                   keyFile=keyPath,
                                   domain=Config.display.organization.domain,
                                   address=Config.display.organization.address,
                                   city=Config.display.organization.city,
                                   region=Config.display.organization.region,
                                   organization=Config.display.organization.organization,
                                   unit=Config.display.organization.unit,
                                   email=Config.display.organization.email,
                                   hosts=hosts)
                                
    info = IOT_SSL.getInfoSSLCertificate(dirPath, "current.crt")
    return aiohttp_web.json_response({"type": "generated",
                                      "info": info})


@routes.post('/sslconfig/info')
@ajaxVerifyToken("admin")
async def sslConfigInfoAjax(request):
    dirPath = SetupApp.app.config("ssl")

    info = IOT_SSL.getInfoSSLCertificate(dirPath, "current.crt")
    return aiohttp_web.json_response({"type": "info",
                                      "info": info})


@routes.get('/logout')
async def logoutHtmlGet(request):
    redirect_response = aiohttp_web.HTTPFound('/login')

    return redirect_response


reDateTime = re.compile(r"^(?:Log Time: *)?(?P<logtime>(?:\d+-\d+-\d+ *\d+:\d+:\d+(?:\.\d+)?)|(?:[a-zA-Z]{3} *\d* *\d+:\d+:\d))", re.I)


def splitDateTime(lt):
    m = reDateTime.split(lt)

    if m[1:]:
        return m[1:]

    return [p.strip() for p in lt.split(":", 1)]


@routes.post('/secret/check')
async def secretTestHtmlPost(request):
    config = Config.display
    
    source = string.ascii_letters + string.digits
    msg = ''.join((random.choice(source) for i in range(128)))
    msgEncoded = AccessVerification.tokenAuthenticator.encode(msg)

    offset = "HWCLOCK" if hasHardwareClock else "-"
    
    head, tail = headTail("/var/run/ptpd2.status", headLines=0, tailLines=100)
    tail = [splitDateTime(tl) for tl in tail]
    ptpd2Data = mapPTPD2StatusReport(tail)

    if "offset" in ptpd2Data:
        offset = ptpd2Data["offset"]

    return aiohttp_web.json_response({"enc": msgEncoded,
                                      "msg": msg,
                                      "config": config.version(),
                                      "build":  versionNo,
                                      "offset": offset,
                                      "correction": ptpd2Data.get("correction", '-')})


async def secretTestPost(testIp, name):
    response = await httpUtils.postUrlJSONResponse("secretcheck",
                                                   f"{httpUtils.scheme}://{testIp}:{httpUtils.port}/secret/check",
                                                   timeout=1,
                                                   jsonData={})

    if not response:
        return [testIp, name, "offline", "", "", "", ""]

    msg = AccessVerification.tokenAuthenticator.decode(response.get("enc", "bogus message"))
    
    return [testIp,
            name,
            'shared' if msg != response['enc'] and msg == response.get("msg", msg) else "unknown",
            response.get("config", '-'),
            response.get("build", '-'),
            response.get("offset", '-'),
            response.get("correction", '-')]


async def logFilePost(testIp, port, filename=None, nlines=5, timeout=None):
    tkn = AccessVerification.tokenAuthenticator.create(expires=int(time.time()) + 3600, audience="peer")
    
    data = {"nlines": nlines}
    if filename:
        data["filename"] = filename

    res = await httpUtils.postUrlJSONResponse("logs",
                                              f"{httpUtils.scheme}://{testIp}:{port}/logfile",
                                              timeout=timeout,
                                              jsonData=data,
                                              headers={CLOCK_HDR: tkn})
    if res:
        return res

    return {"header": [], "tail": []}

@routes.post('/logfile')
@ajaxVerifyToken("peer")
async def logFileHtmlPost(request):
    json = await request.json()

    nLines = json.get("nlines", 3)
    fileName = json.get("filename", "ptpd2.stats")

    path = None
    if fileName in ["ptpd2.stats", "ptpd2.log"]:
        path = "/var/log"
    elif fileName in ["ptpd2.status"]:
        path = "/run"

    if not path:
        return aiohttp_web.HTTPUnauthorized()
    
    head, tail = headTail(os.path.join(path, fileName), headLines=1, tailLines=nLines)

    header = None
    if len(head):
        if head[0].startswith("#"):
            header = head[0][2:].split(",")
            
    if header:
        tail = [l.split(",") for l in tail]
    else:
        header = ["Time", "Message"]
        tail = [splitDateTime(l) for l in tail]

    return aiohttp_web.json_response({"tail": tail, "header": header})


@routes.get('/logfile')
@ajaxVerifyToken("user")
async def logFileHtmlGet(request):
    return await logFileGet(request)


@routes.get('/ptpd2')
@ajaxVerifyToken("user")
async def ptpd2HtmlGet(request):
    return await logFileGet(request, "ptpd2.status")

ptpd2StatusFields = {
    'Clock correction': 'correction',
    'Interface': 'interface',
    'Preset': 'preset',
    'Port state': 'state',
    'Sync mode': 'sync',
    'Offset from Master': 'offset',
    'Clock status': 'status',
    'Best master IP': 'master',
    'Mean Path Delay': 'delay',
    }


def mapPTPD2StatusReport(data):
    res = {}
    for n, v in data:
        if n in ptpd2StatusFields:
            res[ptpd2StatusFields[n]] = v
            
    return res


def mapPTPD2Status(status):
    res = mapPTPD2StatusReport(status['tail'])
    res['ip'] = status['ip']
    res['name'] = status['name']
    
    return res


async def logFileGet(request, filename=None, nLines=None):
    logFileData = []
    if not filename:
        filename = request.rel_url.query.get("filename", "ptpd2.status")

    nlines = int(request.rel_url.query.get("nlines", 100))
    
    for sheet in Config.display.sheets:
        if sheet.ip == "Unassigned":
            continue

        logFile = await logFilePost(sheet.ip, httpUtils.port, filename=filename, nlines=nlines)
        logFileData.append({"ip": sheet.ip, "name": sheet.name, "header": logFile["header"], "tail": logFile["tail"]})

    sensorServersInspected = {"Unassigned"}
    for sensor in Devices.deviceMonitor.getSensors():
        sensorIP = sensor["ip"]
    
        if sensorIP in sensorServersInspected:
            continue

        sensorServersInspected.add(sensorIP)
        logFile = await logFilePost(sensorIP, httpUtils.port, filename=filename, nlines=nlines)
        logFileData.append({"ip": sensorIP, "name": sensor["name"], "header": logFile["header"], "tail": logFile["tail"]})

    return logFileData


@routes.post('/ptpd/restart')
@ajaxVerifyToken("admin")
async def ptpdRestartHtmlPost(request):
    rc, output = runCommand("sudo systemctl restart ptpd")
    warning("startup: restarting ptpd rc=%s\noutput=%s", rc, output)

    return aiohttp_web.json_response({"rc": rc, "msg": output})


@routes.get('/adminlogs')
@ajaxVerifyToken("admin")
async def adminlogsHtmlGet(request):
    level = getLevelName()
    return aiohttp_web.json_response({"headers": ("Time", "Level", "Who", "Message", "Traceback"),
                                      "data": list(logEntries),
                                      "level": level})


@routes.get('/debuglevel')
@ajaxVerifyToken("admin")
async def debugLevelAjaxGet(request):
    level = getLeveNamel()
    return aiohttp_web.json_response({"level": level})


mapState = {"PTP_SLAVE": "secondary",
            "PTP_MASTER": "primary"}


@routes.get('/ajax/ptp/status')
@ajaxVerifyToken("user")
async def logFileAjaxPTPStatus(request):
    logFileData = await logFileGet(request, "ptpd2.status")

    mappedData = [mapPTPD2Status(lt) for lt in logFileData]

    headers = ("Name", "IP", "State", "Time Server", "Offset", "Status", "Correction", "Sync")

    selectedFields = [[e["name"],
                       e["ip"],
                       mapState.get(e.get("state", ""), ""),
                       e.get("master", ""),
                       e.get("offset", ""),
                       e.get("status", ""),
                       e.get("correction", ""),
                       e.get("sync", "")] for e in mappedData]
    return aiohttp_web.json_response({"headers": headers, "data": selectedFields})


@routes.get('/adminversion')
@ajaxVerifyToken("admin")
async def versionAjaxGet(request):
    sheetInfo = []

    for sheet in Config.display.sheets:
        if sheet.ip == "Unassigned":
            continue

        whoami = await whoareyou(sheet.ip, httpUtils.port)
        if whoami:
            epoch = float(whoami["epochTimestamp"])
            try:
                startTime = float(whoami["_startTime"])
            except KeyError:
                startTime = float(whoami["epochTimestamp"])

            data = list(whoami.items())
            data.append(("epochDiff",  epoch - startTime))
            data.sort()
            sheetInfo.append({"name": sheet.name, "data": data})

    sensorServersInspected = {"Unassigned"}
    breakSensorData = []
    for sensor in Devices.deviceMonitor.getSensors():
        sensorIP = sensor["ip"]
        if sensorIP in sensorServersInspected:
            continue

        sensorServersInspected.add(sensorIP)
        
        whoami = await whoareyou(sensorIP, httpUtils.port)
        if whoami:
            epoch = float(whoami["epochTimestamp"])
            try:
                startTime = float(whoami["_startTime"])
            except KeyError:
                startTime = float(whoami["epochTimestamp"])

            data = list(whoami.items())
            data.append(("epochDiff",  epoch - startTime))
            data.sort()
            breakSensorData.append({"name": sensor["name"], "data": data})

    return aiohttp_web.json_response({"sheets": sheetInfo, "sensors": breakSensorData})


@routes.get('/adminmemory')
@ajaxVerifyToken("admin")
async def memorAjaxGet(request):
    global systemStats
    return aiohttp_web.json_response({"data": [memUsage()] + list(reversed(systemStats)),
                                      "headers": MemUsage._fields})


@routes.get('/adminptpdstatus')
@ajaxVerifyToken("admin")
async def adminPTPDStatusAjaxGet(request):
    logFileData = await logFileGet(request, "ptpd2.status")
    return aiohttp_web.json_response({"data": logFileData})


@routes.get('/adminptpdstats')
@ajaxVerifyToken("user")
async def adminPTPDStatsAjaxGet(request):
    logFileData = await logFileGet(request, filename="ptpd2.stats")
    return aiohttp_web.json_response({"data": logFileData})


@routes.get('/adminptpdlogs')
@ajaxVerifyToken("user")
async def adminPTPDLogsAjaxGet(request):
    logFileData = await logFileGet(request, filename="ptpd2.log")
    return aiohttp_web.json_response({"data": logFileData})


@routes.get('/adminptpdoffset')
@ajaxVerifyToken("user")
async def adminPTPDOffsetAjaxGet(request):
    logFileData = await logFileGet(request, "ptpd2.status")
    
    mappedData = [mapPTPD2Status(lt) for lt in logFileData]
    data = [[e.get("name", ""),
             e.get("ip", ""),
             mapState.get(e.get("state", ""), ""),
             e.get("master", ""),
             e.get("offset", ""),
             e.get("status", ""),
             e.get("correction", ""),
             e.get("sync", "")] for e in mappedData]
             
    headers = ["Name", "IP", "State", "Primary", "Offset", "Status", "Correction", "Sync"]
    
    return aiohttp_web.json_response({"headers": headers,
                                      "data": data})


@routes.get('/ajax/time')
@ajaxVerifyToken("admin")
async def timeAjaxGet(request):
    now = datetime.datetime.now()
    return aiohttp_web.json_response({"time": now.strftime("%X"),
                                      "date": now.strftime("%Y-%m-%d"),
                                      "tz": str(now.astimezone().tzinfo),
                                      "timezone": Config.display.rink.timezone})


@routes.post('/ajax/login')
async def loginAjaxPost(request):
    data = await request.json()
    user = data["user"]
    password = data["password"]

    debug("security: checking user")
    if verifyUser(user, password):
        tkn = AccessVerification.tokenAuthenticator.create(user=user, expires=int(time.time()) + yearInSeconds, audience="user")
        return aiohttp_web.json_response({"msg": "login succeeded",
                                          "rc": True,
                                          "user": user,
                                          "admin":  isAdministrator(user),
                                          "accessToken": tkn})
    
    warning("security: User: %s passwd: %s does not match %s",
            user, password,  Config.display.users.get(user, None))

    return aiohttp_web.json_response({"msg": "login failed",
                                      "accessToken": None,
                                      "rc": False})


@routes.post('/ajax/login/pin')
async def loginPinAjaxPost(request):
    data = await request.json()

    pin = data.get("pin", "not a pin").upper()
    debug("security: checking pin")
    mySheet = Config.display.sheets.mySheet
    msg = ""
    if pin == mySheet.pin:
        expireTime = pinExpireTime(mySheet)
        if expireTime:
            tkn = AccessVerification.tokenAuthenticator.create(pin=pin, expires=expireTime, user=pin, audience="pin")
            debug("security: pin: %s succeeded", pin)
            return aiohttp_web.json_response({"msg": "login succeeded",
                                              "rc": True,
                                              "pin": pin,
                                              "admin": False,
                                              "accessToken": tkn})

        else:
            msg = "pin has expired"
    else:
        msg = "pin is either not current or it belongs to a different sheet"

    warning("security: pin: %s failed", pin)

    return aiohttp_web.json_response({"msg": msg,
                                      "rc": False,
                                      "accessToken": None})


@routes.post('/ajax/log/level')
@ajaxVerifyToken("admin")
async def logLevelAjaxPost(request):
    json = await request.json()

    level = json.get("level", None).lower()
    levelName = "debug"
    if level in Logger.levelMap:
        levelName = level
    elif level.isdigit():
        if int(level):
            levelName = "debug"
        else:
            levelName = "warning"

    Logger.setLevel(Logger.levelMap[levelName])
    level = getLevelName()
    error("Logger: set level to %s: %s", levelName, level)
    
    return aiohttp_web.json_response({"level": level})


@routes.post('/ajax/log/clear')
@ajaxVerifyToken("admin")
async def lofClearAjaxPost(request):
    clearLogs()
    level = getLevelName()
    return aiohttp_web.json_response({"level": level})


@routes.post('/ajax/secret/set')
async def setSecretKeyAjaxPost(request):
    if Config.display.server.setup != 0 and not Config.display.server.isDefaultSecretKey():
        accessToken = request.headers.get(CLOCK_HDR, None)
        authenticator = getAuthenticator()
        tkn = authenticator.verify(accessToken)

        if not tkn:
            return aiohttp_web.json_response({"msg": "set secret failed; not permitted", "rc": False})

        if not isAdministrator(tkn["user"]):
            return aiohttp_web.json_response({"msg": "set secret failed; not permitted", "rc": False})

    data = await request.json()
    secretKey = data.get("secret", None)
    info("security: generating new secret key")
    encryptedKey = AccessVerification.tokenAuthenticator.generateKeyFromPassphrase(secretKey)

    if not encryptedKey:
        info("security: secret key improperly generated; ignored")
        return aiohttp_web.json_response({"msg": "set secret failed; encryption", "rc": False})

    info("security: secret key generated")
    Config.display.server.secretKey = encryptedKey

    if curlingClockManager:
        Config.display.server.setup = 1
    else:
        # running a break timer so record as being fully setup
        Config.display.server.setup = 4
        
    Config.display.save()

    if curlingClockManager:
        curlingClockManager.displayScrollingText("restarting", 300*60)
        
    asyncio.ensure_future(waitForRestart())

    return aiohttp_web.json_response({"msg": "set secret key succeeded; restarting ...", "rc": True})

    
@routes.get('/ajax/hardware')
@ajaxVerifyToken("admin")
async def hardwareAjaxGet(request):
    global hardwareConfig
    return aiohttp_web.json_response({**hardwareConfig.hardware.items()})


@routes.post('/ajax/hardware')
@ajaxVerifyToken("admin")
async def hardwareAjaxPost(request):
    global hardwareConfig
    json = await request.json()

    settings = json.get("settings", {})

    for n, v in settings.items():
        hardwareConfig.hardware.set(n, v)

    hardwareConfig.save()

    return aiohttp_web.json_response({"msg": "settings saved"})


@routes.get('/ajax/clock/state')
@ajaxVerifyToken("user")
async def secretClockStateHtmlGet(request, filename=None):
    secretTestData = []
    for sheet in Config.display.sheets:
        if sheet.ip == "Unassigned":
            continue
            
        matched = await secretTestPost(sheet.ip, sheet.name)
        secretTestData.append(matched)

    sensorServersInspected = {"Unassigned"}
    for sensor in Devices.deviceMonitor.getSensors():
        sensorIP = sensor["ip"]
        if sensorIP in sensorServersInspected:
            continue
        
        sensorServersInspected.add(sensorIP)
        matched = await secretTestPost(sensorIP, sensor["name"])
        secretTestData.append(matched)

    return aiohttp_web.json_response({"data": secretTestData,
                                      "headers": ["IP", "Name", "Secret", "Config", "Build", "Offset", "correction"]})

@routes.get('/ajax/devices')
@ajaxVerifyToken("pin")
async def devicesAjaxGet(request):
    sensors = Devices.deviceMonitor.getSensors()
    displays = Devices.deviceMonitor.getDisplays()
    
    if request.accessTknAudience == "pin":
        displays = []

    return aiohttp_web.json_response({"displays": displays,
                                      "sensors":  sensors})
