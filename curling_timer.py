#!/usr/bin/env python
import os
import sys
import asyncio
import signal
import time
from urllib.parse import urlparse, urlunparse, ParseResult
import ssl
import functools

from aiohttp import web as aiohttp_web
from aiohttp import web_log as aiohttp_web_log
from aiohttp import log as aiohttp_log
from aiohttp.web import middleware as aiohttp_middleware
import aiohttp_cors
import aiohttp_jinja2
from jinja2 import pass_eval_context as jinja2_pass_eval_context, FileSystemLoader as jinja2_FileSystemLoader
from markupsafe import Markup, escape

from hardware_clock import has_hardware_clock, update_clock_time, check_for_hardware_clock
from logger import error, info, debug
import config
from identify import set_app as identify_set_app, \
    register_device_info as identify_register_device_info, \
    get_version as identify_get_version, \
    get_build_date as identify_get_build_date
from curling_clock_manager import create as curlingclockmanager_create
from utils import my_host_name, configure_wifi, singleton, my_ip_address
from aio_utils import register_get_colours as aio_utils_register_get_colours

from access_verification import create_authenticator, check_user_setup

import setup_app
import http_utils as http
import common_routes

from display_routes.admin_routes import routes as http_admin_routes
from display_routes.display_routes import routes as http_display_routes
from display_routes.break_timer_display_routes import routes as http_break_timer_display_routes
from display_routes.index_routes import routes as http_index_routes
from display_routes.competition_timer_routes import routes as http_competition_timer_routes
from display_routes.count_down_timer_routes import routes as http_count_down_timer_routes
from display_routes.defaults_routes import routes as http_defaults_routes
from display_routes.draw_routes import routes as http_draw_routes
from display_routes.elapsed_timer_routes import routes as http_elapsed_timer_routes
from display_routes.teams_routes import routes as http_teams_routes
from update_software_routes import routes as http_update_software, register_purpose

check_for_hardware_clock()

run_user = "pi"
run_group = "pi"

my_app = None
server_task = None
server_active = True
token_authenticator = None

http.HEADERS["user-agent"] = "Curling Timer/1.0"

display_device = None
curling_clock_manager = None

async def start_background_tasks(app):
    await common_routes.start_tasks(app)
    await curling_clock_manager.start_tasks(app)


async def cleanup_background_tasks(app):
    await curling_clock_manager.stop_tasks(app)
    await common_routes.stop_tasks(app)


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
        resp.headers["Cache-Control"] = "max-age=86400, public"

    return resp

#default_cross_origin_headers = {
#    "Access-Control-Allow-Origin": "*",
#    "Access-Control-Allow-Methods": "GET, POST, PATCH, PUT, DELETE, OPTIONS",
#    "Access-Control-Allow-Headers": "Origin, Content-Type, X-Auth-Token",
#}

def setup_secret_key(prm_config):
    info("security: using existing secret key")
    try:
        token_authenticator.set_key(prm_config.server.secret_key)
    except Exception:  # pylint: disable=broad-exception-caught
        config.server.secret_key = prm_config.server.default_secret_key
        token_authenticator.set_key(prm_config.server.secret_key)

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


@jinja2_pass_eval_context
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

async def shutdown(sig, loop, app):
    global server_active # pylint: disable=global-statement

    server_active = False

    print(f"shutting down sig={sig.name}...", file=sys.stderr)
    await curling_clock_manager.stop_tasks(app)

    loop.stop()

    server_task.cancel()
    #await server_task

    current_task = asyncio.current_task()
    tasks = [task for task in asyncio.all_tasks() if task is not  current_task]

    for task in tasks:
        print(task, file=sys.stderr)
        task.cancel()

async def run_app(app_main, ssl_context):
    handle_signals = False
    try:
        # main server
        runner_main = aiohttp_web.AppRunner(app_main,
                                            handle_signals=handle_signals,
                                            access_log_class=aiohttp_web_log.AccessLogger,
                                            access_log_format=aiohttp_web_log.AccessLogger.LOG_FORMAT,
                                            access_log=aiohttp_log.access_logger)
        await runner_main.setup()
        site_main = aiohttp_web.TCPSite(runner_main, None, http.port,
                                        shutdown_timeout=60,
                                        ssl_context=ssl_context,
                                        backlog=128)
        await site_main.start()

        info("CurlingTimer: HTTP Server started %s on http://%s:%s",
             "https" if ssl_context else "http", "0.0.0.0",
             http.port)

        runner_redirector = None
        if ssl_context is not None:
            # redirector app
            app_redirector = aiohttp_web.Application()
            app_redirector.router.add_get('/{tail:.*}', http_redirector_html_get)
            app_redirector.router.add_post('/{tail:.*}', http_redirector_html_post)

            allow_cors(app_redirector)

            runner_redirector = aiohttp_web.AppRunner(app_redirector,
                                                      handle_signals=handle_signals,
                                                      access_log_class=aiohttp_web_log.AccessLogger,
                                                      access_log_format=aiohttp_web_log.AccessLogger.LOG_FORMAT,
                                                      access_log=aiohttp_log.access_logger)
            await runner_redirector.setup()
            site_redirector = aiohttp_web.TCPSite(runner_redirector, None, 80)
            await site_redirector.start()
            info("CurlingTimer: HTTP Redirector started on http://%s:%s", "0.0.0.0", 80)

        try:
            while server_active:
                await asyncio.sleep(1)  # sleep forever by 1 hour intervals

        except (asyncio.CancelledError, KeyboardInterrupt):
            info("curling timer: shutting down")
            return
        finally:
            info("curling timer: main cleaning up - start")
            await runner_main.cleanup()
            info("curling timer: main cleaning up - done")
            if runner_redirector:
                info("curling timer: redirector cleaning up - start")
                await runner_redirector.cleanup()
                info("curling timer: redirector cleaning up - done")

    except asyncio.CancelledError as e:
        info("curling timer: shutting down: %s", e)
        raise

    except Exception as e:
        error("app: run task %e", e, exc_info=True)
        raise
    finally:
        pass


def load_configuration(config_filename):
    return config.open(config_filename)

def check_colours(colours):
    for n, clr in colours:
        if n not in config.display.colours:
            config.display.colours.add_colour(n, clr)

def gather_display_info(whoami_info):
    whoami_info["application"] = "DisplayTimer"
    whoami_info["idle"] = str(curling_clock_manager.get_idle_time()) + " " + curling_clock_manager.get_idle_resetter()
    whoami_info["hwClock"] = "Yes" if has_hardware_clock() else "No"
    whoami_info["drawServer"] = config.display.defaults.draw_server
    whoami_info["clockServer"] = config.display.rink.clock_server
    whoami_info["clubName"] = config.display.rink.club_name
    whoami_info["batteryAlert"] = config.display.rink.battery_alert
    whoami_info["display"] = "Yes"
    my_sheet = config.display.sheets.my_sheet
    whoami_info["name"] = my_sheet.name if my_sheet else my_host_name()
    if config.display.server.setup != 4:
        whoami_info["setup"] = config.display.server.setup

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
    global my_app                # pylint: disable=global-statement
    global server_task           # pylint: disable=global-statement
    global display_device        # pylint: disable=global-statement
    global curling_clock_manager # pylint: disable=global-statement
    global token_authenticator   # pylint: disable=global-statement

    info("python: %s", sys.version)
    show_on_tv = len(sys.argv) > 1 and sys.argv[1] == "TV"

    if show_on_tv:
        sys.argv.pop(1)

    info("startup: begin")

    if has_hardware_clock():
        update_clock_time()

    configure_wifi()

    my_app = setup_app.AppSetup("curling-timer",
                                user=run_user,
                                group=run_group,
                                config_on_external_media=True,
                                data_on_external_media=True,
                                update_on_external_media=True)
    setup_app.set_app(my_app)

    identify_set_app(my_app)
    identify_register_device_info(gather_display_info)

    my_app.copy_files(("display.toml", "config.toml"), my_app.app("defaults"), my_app.config())

    info("startup: load configs version=%s; builddate=%s", identify_get_version(), identify_get_build_date())
    config_filename = my_app.config("config.toml")
    display_config = load_configuration(config_filename)

    singleton(f'curling-timer-{display_config.server.server_port}')

    token_authenticator = create_authenticator(display_config.users)

    info("startup: init display")
    hardware_config_filename = my_app.config("display.toml")
    if show_on_tv:
        import tv_display as display_server
    else:
        import led_rgb_display as display_server

    display_device = display_server.create([],
                                           hardware_config_filename=hardware_config_filename,
                                           font_path=[my_app.app("fonts")])
    args = display_device.parse_args()

    if args.port:
        display_config.server.server_port = int(args.port)

    common_routes.register_hardware_config(display_device.hardware_config)
    common_routes.register_hardware_clock(has_hardware_clock())

    info("startup: start display")
    display_device.start_display()

    ssl_context = None

    http.port = int(display_config.server.server_port)
    http.scheme = display_config.server.server_scheme
    display_config.server.server_schemer = 5

    if http.scheme == "https":
        info("startup: start ssl")
        ssl_certificate = my_app.config("ssl/current.crt")
        ssl_key = my_app.config("ssl/current.key")

        if not os.path.exists(ssl_certificate) or not os.path.exists(ssl_key):
            import iot_ssl as iotssl
            iotssl.generate_ssl_certificate(my_ip_address(),
                                            certificate_file=ssl_certificate,
                                            key_file=ssl_key,
                                            country=display_config.organization.country,
                                            region=display_config.organization.reigon,
                                            city=display_config.organization.city,
                                            organization=display_config.organization.organization,
                                            unit=display_config.organization.unit)

        info("ssl: SSL certificate=%s key=%s", ssl_certificate, ssl_key)
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.check_hostname = False
        ssl_context.load_cert_chain(ssl_certificate, ssl_key)

    info("startup: setup middleware")
    app = aiohttp_web.Application(middlewares=[middleware])

    setup_secret_key(display_config)

    info("startup: setup static")
    app.router.add_static('/static/css', path=my_app.app('static/css'), name='css')
    app.router.add_static('/static/js/', path=my_app.app('static/js/'), name='js')
    app.router.add_static('/static/', path=my_app.app('static'), name='static')

    info("startup: setup templates")
    aiohttp_jinja2.setup(app,
                         loader=jinja2_FileSystemLoader(my_app.app('templates')),
                         enable_async=True,
                         filters={"nl2br": nl2br})
    info("startup: setup common routes")

    # setup_routes_common(app)

    info("startup: setup display routes")
    app.add_routes(common_routes.routes)
    register_purpose("CurlingTimer")

    app.add_routes(http_update_software)

    aio_utils_register_get_colours(display_device.get_colours)

    app.add_routes(http_admin_routes)
    app.add_routes(http_display_routes)
    app.add_routes(http_break_timer_display_routes)
    app.add_routes(http_index_routes)
    app.add_routes(http_competition_timer_routes)
    app.add_routes(http_count_down_timer_routes)
    app.add_routes(http_defaults_routes)
    app.add_routes(http_draw_routes)
    app.add_routes(http_elapsed_timer_routes)
    app.add_routes(http_teams_routes)

    info("startup: create display manager")

    my_app.dump()
    curling_clock_manager = curlingclockmanager_create(display_device, display_config,
                                                       port=http.port,
                                                       token_authenticator=token_authenticator,
                                                       user=run_user,
                                                       group=run_group)

    display_device.set_is_idle(curling_clock_manager.is_idle)

    curling_clock_manager.set_colours(display_config.colours.get_colours())

    common_routes.register_curling_clock_manager(curling_clock_manager)
    info("startup: start clock trackers")

    allow_cors(app)

    info("startup: background tasks")
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)

    info("startup: complete")
    check_user_setup()
    check_colours(display_device.required_colours)

    loop = display_device.run()
    loop.set_exception_handler(global_exception_handler)

    loop.add_signal_handler(signal.SIGINT, functools.partial(asyncio.ensure_future,
                                                             shutdown(signal.SIGINT, loop, app)))
    loop.add_signal_handler(signal.SIGTERM, functools.partial(asyncio.ensure_future,
                                                              shutdown(signal.SIGTERM, loop, app)))
    loop.add_signal_handler(signal.SIGQUIT, functools.partial(asyncio.ensure_future,
                                                              shutdown(signal.SIGQUIT, loop, app)))

    server_task = loop.create_task(run_app(app, ssl_context))

    loop.run_forever()

    info("curling timer: reached the end")


if __name__ == "__main__":
    main()
