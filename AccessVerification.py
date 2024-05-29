from Logger import info

from functools import wraps

from aiohttp import web as aiohttp_web
from passlib.hash import pbkdf2_sha256

from HTTP_Utils import CLOCK_HDR

from ClockAuthenticator import ClockTokenAuthentication
import Config

tokenAuthenticator = None
users = None


def stripPasswordHash(pwd):
    return pwd[6:] if pwd.startswith("Admin:$") else pwd


def setUserPassword(user, password, isAdmin=False):
    Config.display.users.modified = True
    Config.display.users[user] = ("Admin:" if isAdmin else "") + pbkdf2_sha256.hash(password)

    
def verifyUser(user, password):
    userPWDHash = Config.display.users.get(user, None)
    validUser = userPWDHash and ((userPWDHash == "" and password == "") or (pbkdf2_sha256.verify(password, stripPasswordHash(userPWDHash))))

    return validUser


def isAdministrator(user):
    userPWD = Config.display.users.get(user, None)

    return userPWD and userPWD.startswith("Admin:$")


def checkUserSetup():
    if len(Config.display.users) == 0:
        setUserPassword("button", "good", isAdmin=False)

    needsAdmin = True
    for user in Config.display.users.keys():
        if isAdministrator(user):
            needsAdmin = False
            break

    if needsAdmin:
        setUserPassword("skip", "callsTheShots", isAdmin=True)

    if Config.display.modified:
        Config.display.save()

        
def verifyToken(accessToken, audience):
    if not accessToken:
        return False
    
    mySheet = Config.display.sheets.mySheet
    tkn = tokenAuthenticator.verify(accessToken,  mySheet)
    if not tkn:
        return False

    tknAud = tkn["aud"]
    if audience == "user":
        verified = tkn["user"] in Config.display.users
    elif audience == "pin":
        verified = tknAud in ["user", "pin", "peer"]
    elif audience in ["sensor", "config", "peer"]:
        verified = tknAud == audience
    elif audience == "admin":
        user = tkn["user"]
        verified = tknAud == "user" and isAdministrator(user)
    else:
        verified = False
        
    return verified
    
        
def ajaxVerifyToken(audience):
    def ajaxVerifyToken_wrapper(func):
        @wraps(func)
        async def wrapped(request):
            accessToken = request.headers.get(CLOCK_HDR, None)
            
            if accessToken:
                mySheet = Config.display.sheets.mySheet
                tkn = tokenAuthenticator.verify(accessToken,  mySheet)
                if not tkn:
                    info("security: %s verify failed tkn", audience)
                    return aiohttp_web.HTTPUnauthorized()

                tknAud = tkn["aud"]
                if audience == "user":
                    verified = tkn["user"] in Config.display.users
                elif audience == "pin":
                    verified = tknAud in ["user", "pin", "peer"]
                elif audience in ["sensor", "config", "peer"]:
                    verified = tknAud == audience
                elif audience == "admin":
                    user = tkn["user"]
                    verified = tknAud == "user" and isAdministrator(user)
                else:
                    verified = False

                if verified:
                    request.accessTknAudience = tknAud
                    return await func(request)

                info("security: %s verify failed tkn", audience)
            else:
                info("security: %s verify failed no access token", audience)

            return aiohttp_web.HTTPUnauthorized()

        return wrapped

    return ajaxVerifyToken_wrapper


def createAuthenticator(userSet):
    global users, tokenAuthenticator
    
    users = userSet
    tokenAuthenticator = ClockTokenAuthentication(users)
    return tokenAuthenticator


def getAuthenticator():
    global tokenAuthenticator

    return tokenAuthenticator
