#!/usr/bin/env python
from Logger import error, info, debug
import os
import sys
from Utils import dropRootPrivileges, myIPAddress
import re
import asyncio
import atexit
import base64
import signal
import traceback
from urllib.parse import urlparse, urlunparse, ParseResult

import IOT_SSL as iotssl

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
import BreakTimerSensors
import BreakTimerConfig
import Utils

from AutoConfigParser import AutoConfigParser

from AccessVerification import createAuthenticator, checkUserSetup

import SetupApp
import functools

import HTTP_Utils as httpUtils
import CommonRoutes

whoMe = Utils.singleton('break-timer')

runUser = "pi"
runGroup = "pi"

myApp = None
tokenAuthenticator = None

httpUtils.HEADERS["user-agent"] = "Curling Timer/1.0"

breakTimerSensorManager = None


async def start_background_tasks(app):
    await CommonRoutes.startTasks(app)

    
async def cleanup_background_tasks(app):
    await CommonRoutes.stopTasks(app)

    
@middleware
async def middleware(request, handler):
    peername = request.transport.get_extra_info('peername')

    debug("http: %s %s %s", request.method, request.url, peername)

    resp = await handler(request)

    if "/static/" in str(request.url):
        resp.headers["Cache-Control"] = "max-age=31536000, public"

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

        
_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')


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


async def shutdown(sig=None, loop=None):
    print("shutting down ...")

    if breakTimerSensorManager:
        breakTimerSensorManager.off()

    exc_info = sys.exc_info()
    if any(exc_info):
        traceback.print_exc(file=sys.stderr)

    if sig:
        print('caught {0}'.format(sig.name))

    tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
    list(map(lambda task: task.cancel(), tasks))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    print('finished awaiting cancelled tasks, results: {0}'.format(results))
    loop.stop()


async def runApp(appMain, ssl_context):
    try:
        # main server
        runnerMain = aiohttp_web.AppRunner(appMain,
                                           handle_signals=False,
                                           access_log_class=aiohttp_web_log.AccessLogger,
                                           access_log_format=aiohttp_web_log.AccessLogger.LOG_FORMAT,
                                           access_log=aiohttp_log.access_logger)
        await runnerMain.setup()
        
        siteMain = aiohttp_web.TCPSite(runnerMain, None, httpUtils.port,
                                       shutdown_timeout=60,
                                       ssl_context=ssl_context,
                                       backlog=128)
        await siteMain.start()

        print('HTTP Server started {} on http://{}:{}'.format("https" if ssl_context else "http", "0.0.0.0", httpUtils.port))

        runnerRedirector = None
        if ssl_context is not None:
            # redirector app
            appRedirector = aiohttp_web.Application()
            appRedirector.router.add_get('/{tail:.*}', httpRedirectorHtmlGet)
            appRedirector.router.add_post('/{tail:.*}', httpRedirectorHtmlPost)

            allow_cors(appRedirector)

            runnerRedirector = aiohttp_web.AppRunner(appRedirector,
                                                     handle_signals=True,
                                                     access_log_class=aiohttp_web_log.AccessLogger,
                                                     access_log_format=aiohttp_web_log.AccessLogger.LOG_FORMAT,
                                                     access_log=aiohttp_log.access_logger)
            await runnerRedirector.setup()
            siteRedirector = aiohttp_web.TCPSite(runnerRedirector, None, 80)
            await siteRedirector.start()
            print('HTTP Redirector started on http://{}:{}'.format("0.0.0.0", 80))

        dropRootPrivileges(runUser, groups=[runGroup, "adm"])
        try:
            while True:
                await asyncio.sleep(1)  # sleep forever by 1 hour intervals

        except KeyboardInterrupt:
            pass
        finally:
            await runnerMain.cleanup()
            if runnerRedirector:
                await runnerRedirector.cleanup()

    except asyncio.CancelledError:
        pass

    except Exception:
        error("app: run task")
        raise
    finally:
        pass

    
def loadConfiguration(configFn):
    global displayConfig

    displayConfig = Config.open(fileName=configFn)

    if len(displayConfig.users) == 0:
        print("bad config read")
        sys.exit()

        
def gatherBreakTimerInfo(info):
    info["application"] = "BreakTimer"
    info["breaktimer"] = "Yes"
    sensor = breakTimerSensorManager.sensor
    info["sensors"] = sensor.name
    info["name"] = Utils.myHostName()

    
# Main function - allow only a single instance
def main():
    global myApp
    global startTime
    global breakTimerListener
    global breakTimerSensorManager
    global tokenAuthenticator

    info("startup: begin")

    Utils.ConfigureWifi()
    
    myApp = SetupApp.AppSetup("break-sensor",
                              user=runUser,
                              group=runGroup,
                              configOnExternalMedia=True,
                              dataOnExternalMedia=True,
                              externalPath=f"/media/{runUser}/curling-timer")
    SetupApp.setApp(myApp)

    Identify.setApp(myApp)
    Identify.registerDeviceInfo(gatherBreakTimerInfo)

    myApp.copyFiles(("sensors.toml", "config.toml"), myApp.app("defaults"), myApp.config())

    info("startup: load configs")
    configFn = myApp.config("config.toml")
    loadConfiguration(configFn)

    tokenAuthenticator = createAuthenticator(displayConfig.users)

    info("startup: init display")
    hardwareConfigFN = myApp.config("sensors.toml")
    hardwareConfig = AutoConfigParser(filename=hardwareConfigFN, sections=["sensor",])
    sensorSection = BreakTimerConfig.BreakTimerConfigSection(hardwareConfig)
    hardwareConfig.hardware = sensorSection
    CommonRoutes.registerHardwareConfig(hardwareConfig)

    info("startup: show ready led")

    ssl_context = None

    httpUtils.port = int(displayConfig.server.serverPort)
    httpUtils.scheme = displayConfig.server.serverScheme

    if httpUtils.scheme == "https":
        info("startup: start ssl")

        sslCertificate = myApp.config("ssl/current.crt")
        sslKey = myApp.config("ssl/current.key")

        if not os.path.exists(sslCertificate) or not os.path.exists(sslKey):
            iotssl.generateSSLCertificate(myIPAddress(),
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
    app.router.add_static('/static/webfonts/', path=myApp.app('static/webfonts'), name='webfonts')
    app.router.add_static('/static/', path=myApp.app('static'), name='static')

    info("startup: setup templates")
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(myApp.app('templates')), filters={"nl2br": nl2br})
    info("startup: setup common routes")

    # setup_routes_common(app)

    app.add_routes(CommonRoutes.routes)

    from UpdateSoftware import routes as httpUpdateSoftware
    app.add_routes(httpUpdateSoftware)

    info("startup: start break timer sensors")
    breakTimerSensorManager = BreakTimerSensors.create(sensorSection, tokenAuthenticator, port=httpUtils.port)

    info("startup: start break timer routes")
    import BreakTimerRoutes as httpBreakTimerRoutes
    app.add_routes(httpBreakTimerRoutes.routes)

    allow_cors(app)

    info("startup: background tasks")
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)

    info("startup: complete")
    checkUserSetup()
    loop = asyncio.get_event_loop()

    loop.add_signal_handler(signal.SIGTERM,
                            functools.partial(asyncio.ensure_future, shutdown(signal.SIGTERM, loop)))
    loop.add_signal_handler(signal.SIGQUIT,
                            functools.partial(asyncio.ensure_future, shutdown(signal.SIGQUIT, loop)))
    loop.add_signal_handler(signal.SIGINT,
                            functools.partial(asyncio.ensure_future, shutdown(signal.SIGINT, loop)))

    loop.run_until_complete(runApp(app, ssl_context))

    
if __name__ == "__main__":
    main()
