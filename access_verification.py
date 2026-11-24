"""
Implents access verification for http requests
"""
from functools import wraps

from aiohttp import web as aiohttp_web

from logger import info, warning
from http_utils import CLOCK_HDR

from clock_authenticator import ClockTokenAuthentication
import config

token_authenticator = None
users = None


def set_user_password(user, password):
    config.display.users.set_password(user, password)

def is_administrator(user):
    return config.display.users.is_administrator(user)

def verify_user(user, passwd):
    return config.display.users.verify(user, passwd)

def check_user_setup():
    if not config.display.users.has_users():
        config.display.users.add_user("button", "good", is_admin=False)
        info("added missing default user button:good")

    if not config.display.users.has_admin_user():
        config.display.users.add_user("skip", "callsTheShots", is_admin=True)
        info("added missing admin user skip:callsTheShots")

    config.display.save()


def verify_token(access_token, audience, verbose=False):
    if not access_token:
        warning("verify_token: bad token tkn=%s", access_token)

        return False

    my_sheet = config.display.sheets.my_sheet
    tkn = token_authenticator.verify(access_token,  my_sheet)
    if not tkn:
        warning("verify_token: unverifiable token=%s", access_token)

        return False

    tkn_audience = tkn["aud"]
    if audience == "user":
        verified = tkn["user"] in config.display.users
    elif audience == "pin":
        verified = tkn_audience in ["user", "pin", "peer"]
    elif audience in ["sensor", "config", "peer"]:
        verified = tkn_audience == audience
    elif audience == "admin":
        user = tkn["user"]
        verified = tkn_audience == "user" and is_administrator(user)
    else:
        verified = False

    if not verified:
        warning("verify_token: unverified tkn=%s audience=}%s", tkn, audience)

    return verified


def ajax_verify_token(audience):
    def ajax_verify_token_wrapper(func):
        @wraps(func)
        async def wrapped(request):
            access_token = request.headers.get(CLOCK_HDR, None)

            if access_token:
                my_sheet = config.display.sheets.my_sheet
                tkn = token_authenticator.verify(access_token,  my_sheet)
                if not tkn:
                    warning("security: %s verify failed tkn; ip=%s who=%s", audience, request.remote, func.__name__)
                    return aiohttp_web.HTTPUnauthorized()

                token_audience = tkn["aud"]
                if audience == "user":
                    verified = tkn["user"] in config.display.users
                elif audience == "pin":
                    verified = token_audience in ["user", "pin", "peer"]
                elif audience in ["sensor", "config", "peer"]:
                    verified = token_audience == audience
                elif audience == "admin":
                    user = tkn["user"]
                    verified = token_audience == "user" and is_administrator(user)
                else:
                    verified = False

                if verified:
                    request.access_token_audience = token_audience
                    return await func(request)

                warning("security: %s verify failed tkn; ip=%s", audience, request.remote)
            else:
                warning("security: %s verify failed no access token; ip=%s", audience, request.remote)

            return aiohttp_web.HTTPUnauthorized()

        return wrapped

    return ajax_verify_token_wrapper


def create_authenticator(user_set):
    global users, token_authenticator

    users = user_set
    token_authenticator = ClockTokenAuthentication(users)
    return token_authenticator


def get_authenticator():
    global token_authenticator

    return token_authenticator
