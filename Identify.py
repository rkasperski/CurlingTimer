import time
import uuid
import os

from Utils import myIPAddress, myHostName
import HTTP_Utils as httpUtils
from HTTP_Utils import getUrlJSONResponse
import Config

gatherDeviceInfo = None
myApp = None


def setApp(app):
    global myApp

    myApp = app

    
def getApp():
    return myApp

    
async def whoareyou(testIp, port, timeout=None):
    return await getUrlJSONResponse("whoareyou",
                                    f"{httpUtils.scheme}://{testIp}:{port}/whoareyou",
                                    timeout=timeout)


async def getEpoch(testIp, port, timeout=None):
    return await getUrlJSONResponse("getEpoch",
                                    f"{httpUtils.scheme}://{testIp}:{port}/epoch",
                                    timeout=timeout)


def getBuildDate(path=None):
    if not path:
        path = myApp.app("info")
    elif not path.endswith("info"):
        path = os.path.join(path, "info")

    path = os.path.join(path, "builddate")
    
    try:
        with open(path) as fp:
            date = fp.readline().strip()
    except OSError:
        date = "unknown"

    return date


def getVersion(path=None):
    if not path:
        path = myApp.app("info")
    elif not path.endswith("info"):
        path = os.path.join(path, "info")

    path = os.path.join(path, "version.txt")
    
    try:
        with open(path) as f:
            version = f.readline().strip()
    except OSError:
        version = "0.0"

    return version


def whoami():
    config = Config.display
    name = myHostName()

    lclTime = time.time()
    localTime = time.localtime(lclTime)
    mlsec = str(lclTime).split('.')[1][:3]
    displayTime = time.strftime("%H:%M:%S.", localTime) + mlsec

    attributes = {
        "macId": ("%x" % uuid.getnode()),
        "whoAmI": name,
        "ip": myIPAddress(),
        "port": httpUtils.port,
        "epochTimestamp": time.time(),
        "time": displayTime,
        "configVersion": config.version(),
        "buildVersion": getVersion(),
        "buildDate": getBuildDate(),
        "hostname": myHostName(),
        "configDate": config.modificationDate(),
        }

    gatherDeviceInfo(attributes)

    return attributes


def registerDeviceInfo(deviceInfo):
    global gatherDeviceInfo

    gatherDeviceInfo = deviceInfo
