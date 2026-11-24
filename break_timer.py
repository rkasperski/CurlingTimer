#!/usr/bin/env python
import os
import sys
import re
import asyncio
import signal
#import ssl
import traceback
import functools
from urllib.parse import urlparse, urlunparse, ParseResult

from aiohttp import web as aiohttp_web
from aiohttp import web_log as aiohttp_web_log
from aiohttp import log as aiohttp_log
from aiohttp.web import middleware as aiohttp_middleware
import aiohttp_cors
import aiohttp_jinja2
import jinja2
from jinja2 import pass_eval_context
from markupsafe import Markup, escape

from logger import error, info, debug, warning
# EYE uncomment when on modern linux
#import iot_ssl as iotssl
from utils import my_ip_address, drop_root_privileges, configure_wifi, \
    singleton as utils_singleton, my_host_name
from config import open as config_open
from identify import set_app as identify_set_app, \
    register_device_info as identify_register_device_info
from break_timer_sensors import create as break_timer_sensors_create
from break_timer_config import BreakTimerConfigSection

from auto_config_parser import AutoConfigParser

from access_verification import create_authenticator, check_user_setup

import setup_app

import http_utils as http
from common_routes import start_tasks as common_start_tasks, \
    stop_tasks as common_stop_tasks, \
    register_hardware_config , \
    routes as common_routes

from break_timer_routes import routes as http_break_timer_routes
from update_software_routes import routes as http_update_software_routes, register_purpose

who_me = utils_singleton('break-timer')

run_user = "pi"  # pylint: disable=invalid-name
run_group = "pi"  # pylint: disable=invalid-name

my_app = None  # pylint: disable=invalid-name
token_authenticator = None  # pylint: disable=invalid-name
display_config = None  # pylint: disable=invalid-name

http.HEADERS["user-agent"] = "Curling Timer/1.0"

break_timer_sensor_manager = None  # pylint: disable=invalid-name


async def start_background_tasks(app):
    await common_start_tasks(app)


async def cleanup_background_tasks(app):
    await common_stop_tasks(app)


@aiohttp_middleware
async def middleware(request, handler):
    peername = request.transport.get_extra_info('peername')

    if not request.url.path == "/status":
        debug("%s %s %s",
             request.method,
             request.url,
             peername)

    resp = await handler(request)

    if request.url.path.startswith("/static"):
        resp.headers["Cache-Control"] = "max-age=31536000, public"

    return resp

default_cross_origin_headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PATCH, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Origin, Content-Type, X-Auth-Token",
    }


def setup_secret_key(config):
    info("security: using existing secret key")
    try:
        token_authenticator.set_key(config.server.secret_key)
    except Exception:  # pylint: disable=broad-exception-caught
        config.server.secret_key = config.server.default_secret_key
        token_authenticator.set_key(config.server.secret_key)

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


async def http_redirector_html_get(request):
    parsed = urlparse(str(request.url))
    sp = parsed.netloc.split(":")

    if len(sp) == 1:
        sp.append("")

    sp[1] = str(http.port)

    newloc = urlunparse(ParseResult("https", ":".join(sp), parsed.path, parsed.params, parsed.query, parsed.fragment))
    return aiohttp_web.HTTPFound(location=newloc)


async def http_redirector_html_post(request):
    parsed = urlparse(str(request.url))
    sp = parsed.netloc.split(":")

    if len(sp) == 1:
        sp.append("")

    sp[1] = str(http.port)

    newloc = urlunparse(ParseResult("https", ":".join(sp), parsed.path, parsed.params, parsed.query, parsed.fragment))
    return aiohttp_web.HTTPFound(location=newloc)

async def shutdown(sig=None, loop=None):
    warning("shutting down ...")

    if break_timer_sensor_manager:
        break_timer_sensor_manager.off()

    exc_info = sys.exc_info()
    if any(exc_info):
        traceback.print_exc(file=sys.stderr)

    if sig:
        warning('caught %s', sig.name)

    current_task = asyncio.current_task()
    tasks = [task for task in asyncio.all_tasks() if task is not  current_task]

    list(map(lambda task: task.cancel(), tasks))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    warning('finished awaiting cancelled tasks, results: %s', results)
    loop.stop()


async def run_app(app_main, ssl_context):
    try:
        # main server
        runner_main = aiohttp_web.AppRunner(app_main,
                                           handle_signals=False,
                                           access_log_class=aiohttp_web_log.AccessLogger,
                                           access_log_format=aiohttp_web_log.AccessLogger.LOG_FORMAT,
                                           access_log=aiohttp_log.access_logger)
        await runner_main.setup()

        site_main = aiohttp_web.TCPSite(runner_main, None, http.port,
                                       shutdown_timeout=60,
                                       ssl_context=ssl_context,
                                       backlog=128)
        await site_main.start()

        warning('HTTP Server started %s on http://%s:%s',
                "https" if ssl_context else "http",
                "0.0.0.0",
                http.port)

        runner_redirector = None
        if ssl_context is not None:
            # redirector app
            app_redirector = aiohttp_web.Application()
            app_redirector.router.add_get('/{tail:.*}', http_redirector_html_get)
            app_redirector.router.add_post('/{tail:.*}', http_redirector_html_post)

            allow_cors(app_redirector)

            runner_redirector = aiohttp_web.AppRunner(app_redirector,
                                                     handle_signals=True,
                                                     access_log_class=aiohttp_web_log.AccessLogger,
                                                     access_log_format=aiohttp_web_log.AccessLogger.LOG_FORMAT,
                                                     access_log=aiohttp_log.access_logger)
            await runner_redirector.setup()
            site_redirector = aiohttp_web.TCPSite(runner_redirector, None, 80)
            await site_redirector.start()
            warning('HTTP Redirector started on http://%s:%s', "0.0.0.0", 80)

        drop_root_privileges(run_user, groups=[run_group, "adm"])
        try:
            while True:
                await asyncio.sleep(1)  # sleep forever by 1 hour intervals

        except KeyboardInterrupt:
            pass
        finally:
            await runner_main.cleanup()
            if runner_redirector:
                await runner_redirector.cleanup()

    except asyncio.CancelledError:
        pass

    except Exception:
        error("app: run task")
        raise
    finally:
        pass


def load_configuration(config_filename):
    global display_config  # pylint: disable=global-statement

    display_config = config_open(config_filename)

    if len(display_config.users) == 0:
        error("bad config read")
        sys.exit()


def gather_break_timer_info(prm_info):
    prm_info["application"] = "BreakTimer"
    prm_info["breaktimer"] = "Yes"
    sensor = break_timer_sensor_manager.sensor
    prm_info["sensors"] = sensor.name
    prm_info["name"] = my_host_name()

def global_exception_handler(_loop, context):
    # context["message"] usually contains the error summary
    message = context.get("message")
    exception = context.get("exception")
    task = context.get("task")

    if exception:
        error("Uncaught exception: %s in task %s", exception, task, exc_info=exception)
    else:
        error("Asyncio error message: %s in task %s", message, task)


# Main function - allow only a single instance
# pylint: disable=too-many-statements
def main():
    global my_app  # pylint: disable=global-statement
    global break_timer_sensor_manager # pylint: disable=global-statement
    global token_authenticator # pylint: disable=global-statement

    info("startup: begin")

    configure_wifi()

    my_app = setup_app.AppSetup("break-sensor",
                                user=run_user,
                                group=run_group,
                                config_on_external_media=True,
                                data_on_external_media=True,
                                external_path=f"/media/{run_user}/curling-timer")
    setup_app.set_app(my_app)

    identify_set_app(my_app)
    identify_register_device_info(gather_break_timer_info)

    my_app.copy_files(("sensors.toml", "config.toml"), my_app.app("defaults"), my_app.config())

    info("startup: load configs")
    config_filename = my_app.config("config.toml")
    load_configuration(config_filename)

    token_authenticator = create_authenticator(display_config.users)

    info("startup: init display")
    hardware_config_filename = my_app.config("sensors.toml")
    hardware_config = AutoConfigParser(filename=hardware_config_filename, sections=["sensor",])
    sensor_section = BreakTimerConfigSection(hardware_config)
    hardware_config.hardware = sensor_section
    register_hardware_config(hardware_config)

    info("startup: show ready led")

    ssl_context = None

    # EYE uncomment when on modern linux
    # if http.scheme == "https":
    #     info("startup: start ssl")

    #     ssl_certificate = my_app.config("ssl/current.crt")
    #     ssl_key = my_app.config("ssl/current.key")

    #     if not os.path.exists(ssl_certificate) or not os.path.exists(ssl_key):
    #         iotssl.generate_ssl_certificate(my_ip_address(),
    #                                         certificate_file=ssl_certificate,
    #                                         key_file=ssl_key,
    #                                         country=display_config.organization.country,
    #                                         region=display_config.organization.reigon,
    #                                         city=display_config.organization.city,
    #                                         organization=display_config.organization.organization,
    #                                         unit=display_config.organization.unit)

    #     info("ssl: SSL certificate=%s key=%s", ssl_certificate, ssl_key)
    #     # EYE: uncomment when on modern linux
    #     #ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    #     ssl_context.check_hostname = False
    #     ssl_context.load_cert_chain(ssl_certificate, ssl_key)

    info("startup: setup middleware")
    app = aiohttp_web.Application(middlewares=[middleware])

    setup_secret_key(display_config)

    info("startup: setup static")
    app.router.add_static('/static/css', path=my_app.app('static/css'), name='css')
    app.router.add_static('/static/js/', path=my_app.app('static/js/'), name='js')
    app.router.add_static('/static/', path=my_app.app('static'), name='static')

    info("startup: setup templates")
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(my_app.app('templates')), filters={"nl2br": nl2br})
    info("startup: setup common routes")

    app.add_routes(common_routes)

    register_purpose("BreakTimer")
    app.add_routes(http_update_software_routes)

    info("startup: start break timer sensors")
    break_timer_sensor_manager = break_timer_sensors_create(sensor_section, token_authenticator, port=http.port)

    info("startup: start break timer routes")
    app.add_routes(http_break_timer_routes)

    allow_cors(app)

    info("startup: background tasks")
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)

    info("startup: complete")
    check_user_setup()
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(global_exception_handler)

    loop.add_signal_handler(signal.SIGTERM,
                            functools.partial(asyncio.ensure_future, shutdown(signal.SIGTERM, loop)))
    loop.add_signal_handler(signal.SIGQUIT,
                            functools.partial(asyncio.ensure_future, shutdown(signal.SIGQUIT, loop)))
    loop.add_signal_handler(signal.SIGINT,
                            functools.partial(asyncio.ensure_future, shutdown(signal.SIGINT, loop)))

    loop.run_until_complete(run_app(app, ssl_context))


if __name__ == "__main__":
    main()
 
