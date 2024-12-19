import time
import asyncio

from Logger import info, debug
from Utils import myIPAddress, traceback
import HTTP_Utils as httpUtils
from HTTP_Utils import postUrlJSONResponse, scheme, CLOCK_HDR
from Identify import whoareyou
import Config
import AccessVerification
import Devices


async def updateOneConfig(ip, configStr):
    tkn = AccessVerification.tokenAuthenticator.create(expires=int(time.time()) + 3600, audience="config")

    jsonResponse = await postUrlJSONResponse("updateOneConfig",
                                             f'{scheme}://{ip}:{httpUtils.port}/config',
                                             jsonData={"config": configStr},
                                             headers={CLOCK_HDR: tkn},
                                             timeout=10)

    info("config: send update ip=%s result='%s'", ip, jsonResponse) 
    return jsonResponse


async def updateAllConfigs(save=True, force=True, ipList=None):
    info("config: config save=%s", save)
    if save:
        Config.display.save()

    allCurrent = True
    myIp = myIPAddress()

    config = Config.display
    configString = None

    if ipList is None:
        ipList = [sheet.ip for sheet in config.sheets if sheet.ip != "Unassigned" and sheet.ip != myIp] + [snsr["ip"] for snsr in Devices.deviceMonitor.getSensors()]

    for ip in ipList:
        needUpdate = force
        if not force:
            peerData = await whoareyou(ip, httpUtils.port)
            if peerData:
                needUpdate = config.version() > peerData["configVersion"]

        if needUpdate:
            if configString is None:
                configString = config.toString(time.time())

            if not await updateOneConfig(ip, configString):
                allCurrent = False

    return allCurrent


async def keepConfigsCurrentTask(app):
    nextCheckTime = time.time()
    sensorIPs = set()

    configUpdateDelay = 0

    while True:
        try:
            await asyncio.sleep(10)
            
            checkSensorIPs = set([s["ip"] for s in Devices.deviceMonitor.getSensors()])
            if checkSensorIPs != sensorIPs:
                await updateAllConfigs(save=False, force=False, ipList=list(checkSensorIPs))
                sensorIPs = checkSensorIPs

            if time.time() > nextCheckTime:
                await updateAllConfigs(save=False, force=False)
                configUpdateDelay = min(3600, configUpdateDelay + 30)

                nextCheckTime = time.time() + configUpdateDelay

        except asyncio.CancelledError:
            return
        except Exception as e:
            traceback(str(e))


async def startTasks(app):
    info("ConfigurationManager: stop tasks - start")

    app['config_update'] = asyncio.create_task(keepConfigsCurrentTask(app))


async def stopTasks(app):
    if 'config_update' in app:
        debug("ConfigurationManager: stop tasks - cancel")
        app['config_update'].cancel()

        debug("ConfigurationManager: stop tasks - done")
