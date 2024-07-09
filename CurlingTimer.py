#!/usr/bin/env python
from Logger import error, info, debug
import os
import sys
import asyncio
import atexit
import signal
from urllib.parse import urlparse, urlunparse, ParseResult

import HardwareClock

from aiohttp import web as aiohttp_web
from aiohttp import web_log as aiohttp_web_log
from aiohttp import log as aiohttp_log
from aiohttp.web import middleware
import aiohttp_cors
import aiohttp_jinja2
import jinja2
from jinja2 import pass_eval_context
from markupsafe import Markup, escape
import ssl

import Config
import Identify
import LED_RGB_Display
import CurlingClockManager
import Utils
import AIO_Utils

from AccessVerification import createAuthenticator, checkUserSetup

import SetupApp
import functools

import HTTP_Utils as httpUtils
import CommonRoutes

HardwareClock.checkForHardwareClock()

runUser = "pi"
runGroup = "pi"

myApp = None
serverTask = None
serverActive = True
tokenAuthenticator = None
displayConfig = None

httpUtils.HEADERS["user-agent"] = "Curling Timer/1.0"

ledRGBDisplay = None
curlingClockManager = None

displayBreakTimeTracker = None


async def startBackgroundTasks(app):
    await CommonRoutes.startTasks(app)
    await curlingClockManager.startTasks(app)

    
async def cleanupBackgroundTasks(app):
    await curlingClockManager.stopTasks(app)
    await CommonRoutes.stopTasks(app)

    
@middleware
async def middleware(request, handler):
    peername = request.transport.get_extra_info('peername')

    if request.url.path.endswith("status"):
        debug("%s %s %s", request.method, request.url, peername)
    else:
        info("%s %s %s", request.method, request.url, peername)

    try:
        resp = await handler(request)
    except Exception as e:
        raise

    if request.url.path.startswith("/static"):
        sp = request.url.path.split("/")

        if sp[-1] not in ["utilscript.js"]:
            resp.headers["Cache-Control"] = "max-age=86400, public"

    return resp

defaultCrossOriginHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PATCH, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Origin, Content-Type, X-Auth-Token",
    }


def setupSecretKey(config):
    info("security: using existing secret key")
    try:
        tokenAuthenticator.setKey(config.server.secretKey)
    except Exception:
        config.server.secretKey = config.server.defaultSecretKey
        tokenAuthenticator.setKey(config.server.secretKey)
        
    info("security: secret key set")

def allow_cors(app):
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            max_age=86400,
        )
    })

    # Configure CORS on all routes.
    for route in list(app.router.routes()):
        cors.add(route)


@pass_eval_context
def nl2br(eval_ctx, value):
    result = escape(value).replace('\n', Markup('<br>\n'))
    if eval_ctx.autoescape:
        result = Markup(result)
    return result


async def httpRedirectorHtmlGet(request):
    parsed = urlparse(str(request.url))
    sp = parsed.netloc.split(":")

    if len(sp) == 1:
        sp.append("")

    sp[1] = str(httpUtils.port)

    newloc = urlunparse(ParseResult("https", ":".join(sp), parsed.path, parsed.params, parsed.query, parsed.fragment))
    return aiohttp_web.HTTPFound(location=newloc)


async def httpRedirectorHtmlPost(request):
    return aiohttp_web.HTTPMethodNotAllowed()


async def shutdown(sig, loop, app):
    global serverTask, serverActive, curlingClockManager

    serverActive = False
    
    print(f"shutting down sig={sig.name}...", file=sys.stderr)
    await curlingClockManager.stopTasks(app)

    serverTask.cancel()
    await serverTask

    tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]

    for task in tasks:
        print(task, file=sys.stderr)
        # task.cancel()
              
async def runApp(appMain, ssl_context):
    handleSignals = False
    try:
        # main server
        runnerMain = aiohttp_web.AppRunner(appMain,
                                           handle_signals=handleSignals,
                                           access_log_class=aiohttp_web_log.AccessLogger,
                                           access_log_format=aiohttp_web_log.AccessLogger.LOG_FORMAT,
                                           access_log=aiohttp_log.access_logger)
        await runnerMain.setup()
        siteMain = aiohttp_web.TCPSite(runnerMain, None, httpUtils.port,
                                       shutdown_timeout=60,
                                       ssl_context=ssl_context,
                                       backlog=128)
        await siteMain.start()

        info("CurlingTimer: HTTP Server started %s on http://%s:%s", "https" if ssl_context else "http", "0.0.0.0", httpUtils.port)

        runnerRedirector = None
        if ssl_context is not None:
            # redirector app
            appRedirector = aiohttp_web.Application()
            appRedirector.router.add_get('/{tail:.*}', httpRedirectorHtmlGet)
            appRedirector.router.add_post('/{tail:.*}', httpRedirectorHtmlPost)

            allow_cors(appRedirector)

            runnerRedirector = aiohttp_web.AppRunner(appRedirector,
                                                     handle_signals=handleSignals,
                                                     access_log_class=aiohttp_web_log.AccessLogger,
                                                     access_log_format=aiohttp_web_log.AccessLogger.LOG_FORMAT,
                                                     access_log=aiohttp_log.access_logger)
            await runnerRedirector.setup()
            siteRedirector = aiohttp_web.TCPSite(runnerRedirector, None, 80)
            await siteRedirector.start()
            info("CurlingTimer: HTTP Redirector started on http://%s:%s", "0.0.0.0", 80)

        try:
            while True:
                await asyncio.sleep(1)  # sleep forever by 1 hour intervals

        except (asyncio.CancelledError, KeyboardInterrupt):
            info("curling timer: shutting down")
            return
        finally:
            info("curling timer: main cleaning up - start")
            await runnerMain.cleanup()
            info("curling timer: main cleaning up - done")
            if runnerRedirector:
                info("curling timer: redirector cleaning up - start")
                await runnerRedirector.cleanup()
                info("curling timer: redirector cleaning up - done")

    except asyncio.CancelledError:
        info("curling timer: shutting down")
        pass
    
    except Exception as e:
        error("app: run task %e", e, exc_info=True)
        raise
    finally:
        info("curling timer: shutting down - all done")
        pass

    

    displayConfig = Config.open(fileName=configFn)
    return displayConfig


def loadConfiguration(configFn):
    displayConfig = Config.open(fileName=configFn)
    return displayConfig


async def mainLoopTask(loop, app):
    global serverActive, curlingClockManager

    while serverActive:
        await asyncio.sleep(0.1)

        
def gatherDisplayInfo(info):
    info["application"] = "DisplayTimer"
    info["idle"] = str(ledRGBDisplay.getIdleTime()) + " " + ledRGBDisplay.getIdleResetter()
    info["hwClock"] = "Yes" if HardwareClock.hasHardwareClock else "No"
    info["drawServer"] = Config.display.defaults.drawServer
    info["display"] = "Yes"
    mySheet = Config.display.sheets.mySheet
    info["name"] = mySheet.name if mySheet else Utils.myHostName()
    if Config.display.server.setup != 4:
        info["setup"] = Config.display.server.setup


# Main function - allow only a single instance
def main():
    global myApp, serverTask
    global displayConfig
    global ledRGBDisplay, curlingClockManager, startTime
    global displayBreakTimeTracker
    global tokenAuthenticator

    info("startup: begin")

    if HardwareClock.hasHardwareClock:
        HardwareClock.updateClockTime()

    Utils.ConfigureWifi()
    
    myApp = SetupApp.AppSetup("curling-timer", user=runUser, group=runGroup, configOnExternalMedia=True, dataOnExternalMedia=True)
    SetupApp.setApp(myApp)

    Identify.setApp(myApp)
    Identify.registerDeviceInfo(gatherDisplayInfo)

    myApp.copyFiles(("display.toml", "config.toml"), myApp.app("defaults"), myApp.config())

    info("startup: load configs")
    configFn = myApp.config("config.toml")
    displayConfig = loadConfiguration(configFn)

    Utils.singleton(f'curling-timer-{displayConfig.server.serverPort}')
    
    if displayConfig.sheets.mySheet is not None:
        Utils.checkAndSetHostName(displayConfig.sheets.mySheet.name.replace(" ", "").lower(),
                                  displayConfig.organization.domain,
                                  myApp.configDir)

    tokenAuthenticator = createAuthenticator(displayConfig.users)
    
    info("startup: init display")
    hardwareConfigFN = myApp.config("display.toml")
    ledRGBDisplay = LED_RGB_Display.create([], hardwareConfigFN=hardwareConfigFN, fontPath=[myApp.app("fonts")])
    args = ledRGBDisplay.parseArgs()

    if args.port:
        displayConfig.server.serverPort = int(args.port)
        
    CommonRoutes.registerHardwareConfig(ledRGBDisplay.hardwareConfig)
    CommonRoutes.registerHardwareClock(HardwareClock.hasHardwareClock)
    ledRGBDisplay.setColours(displayConfig.colours.getColours())

    info("startup: start display")
    ledRGBDisplay.process()

    ssl_context = None
  
    httpUtils.port = int(displayConfig.server.serverPort)
    httpUtils.scheme = displayConfig.server.serverScheme

    if httpUtils.scheme == "https":
        info("startup: start ssl")
        sslCertificate = myApp.config("ssl/current.crt")
        sslKey = myApp.config("ssl/current.key")

        if not os.path.exists(sslCertificate) or not os.path.exists(sslKey):
            import IOT_SSL as iotssl
            iotssl.generateSSLCertificate(Utils.myIPAddress(),
                                          certificateFile=sslCertificate,
                                          keyFile=sslKey,
                                          country=displayConfig.organization.country,
                                          region=displayConfig.organization.reigon,
                                          city=displayConfig.organization.city,
                                          organization=displayConfig.organization.organization,
                                          unit=displayConfig.organization.unit)

        info("ssl: SSL certificate=%s key=%s", sslCertificate, sslKey)
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.check_hostname = False
        ssl_context.load_cert_chain(sslCertificate, sslKey)

    info("startup: setup middleware")
    app = aiohttp_web.Application(middlewares=[middleware])

    setupSecretKey(displayConfig)

    info("startup: setup static")
    app.router.add_static('/static/css', path=myApp.app('static/css'), name='css')
    app.router.add_static('/static/js/', path=myApp.app('static/js/'), name='js')
    app.router.add_static('/static/', path=myApp.app('static'), name='static')

    info("startup: setup templates")
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(myApp.app('templates')), enable_async=True, filters={"nl2br": nl2br})
    info("startup: setup common routes")

    # setup_routes_common(app)

    info("startup: setup display routes")
    app.add_routes(CommonRoutes.routes)
    from UpdateSoftware import routes as httpUpdateSoftware
    app.add_routes(httpUpdateSoftware)
    
    AIO_Utils.registerGetColours(ledRGBDisplay.getColours)
    
    from DisplayRoutes.AdminRoutes import routes as httpAdminRoutes
    from DisplayRoutes.DisplayRoutes import routes as httpDisplayRoutes
    from DisplayRoutes.BreakTimerDisplayRoutes import routes as httpBreakTimerDisplayRoutes
    from DisplayRoutes.IndexRoutes import routes as httpIndexRoutes
    from DisplayRoutes.CompetitionTimerRoutes import routes as httpCompetitionTimerRoutes
    from DisplayRoutes.CountdownTimerRoutes import routes as httpCountdownTimerRoutes
    from DisplayRoutes.DefaultsRoutes import routes as httpDefaultsRoutes
    from DisplayRoutes.DrawRoutes import routes as httpDrawRoutes
    from DisplayRoutes.ElapsedTimerRoutes import routes as httpElapsedTimerRoutes
    from DisplayRoutes.TeamsRoutes import routes as httpTeamsRoutes
    
    app.add_routes(httpAdminRoutes)
    app.add_routes(httpDisplayRoutes)
    app.add_routes(httpBreakTimerDisplayRoutes)
    app.add_routes(httpIndexRoutes)
    app.add_routes(httpCompetitionTimerRoutes)
    app.add_routes(httpCountdownTimerRoutes)
    app.add_routes(httpDefaultsRoutes)
    app.add_routes(httpDrawRoutes)
    app.add_routes(httpElapsedTimerRoutes)
    app.add_routes(httpIndexRoutes)
    app.add_routes(httpTeamsRoutes)
       
    info("startup: create display manager")
    curlingClockManager = CurlingClockManager.create(ledRGBDisplay, displayConfig,
                                                     port=httpUtils.port,
                                                     tokenAuthenticator=tokenAuthenticator,
                                                     isIdle=ledRGBDisplay.isIdle,
                                                     user=runUser,
                                                     group=runGroup)

    CommonRoutes.registerCurlingClockManager(curlingClockManager)
    info("startup: start clock trackers")

    allow_cors(app)

    info("startup: background tasks")
    app.on_startup.append(startBackgroundTasks)
    app.on_cleanup.append(cleanupBackgroundTasks)

    info("startup: complete")
    checkUserSetup()

    loop = asyncio.get_event_loop()
    
    loop.add_signal_handler(signal.SIGINT, functools.partial(asyncio.ensure_future, shutdown(signal.SIGINT, loop, app)))
    loop.add_signal_handler(signal.SIGTERM, functools.partial(asyncio.ensure_future, shutdown(signal.SIGTERM, loop, app)))
    loop.add_signal_handler(signal.SIGQUIT, functools.partial(asyncio.ensure_future, shutdown(signal.SIGQUIT, loop, app)))

    serverTask = loop.create_task(runApp(app, ssl_context))
    loop.run_until_complete(mainLoopTask(loop, app))
    info("curling timer: reached the end")
    

if __name__ == "__main__":
    main()
