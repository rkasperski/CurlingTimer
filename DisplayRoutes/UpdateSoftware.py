from Logger import warning, info, error, debug
import os
import tempfile
import shutil
import subprocess

from aiohttp import web as aiohttp_web
from aiohttp import MultipartReader as aiohttp_MultipartReader
from AccessVerification import ajaxVerifyToken, verifyAccess
import SetupApp
from pprint import pprint
from Identify import getVersion, getBuildDate
import CurlingClockManager

routes = aiohttp_web.RouteTableDef()

def listUpdates():
    myApp = SetupApp.getApp()
    updatePath = myApp.data("updates")
    updates = [f for f in os.listdir(updatePath) if f.endswith(".tgz") and os.path.isfile(os.path.join(updatePath, f))]
    return updates

@routes.post('/update/list')
@ajaxVerifyToken("admin")
async def updateListAjax(request):
    return aiohttp_web.json_response({"updloaed": True,
                                      "updates": listUpdates()})

def delPath(path):
    shutil.rmtree(path)

    return True

@routes.post('/update/unpack')
@ajaxVerifyToken("admin")
async def updateUnpackAjax(request):
    json = await request.json()
    myApp = SetupApp.getApp()
    
    cwd = os.getcwd()
    inactiveDir = os.path.join(os.path.dirname(cwd), "CurlingTimer.new")
    unpackDir = tempfile.mkdtemp()

    installFile = json.get("file")
    digest =  json.get("digest")

    updateTarFileName = myApp.data(os.path.join("updates", installFile))

    cmd = f"sha512sum '{updateTarFileName}'"    
    runTest = subprocess.run(cmd, shell=True, capture_output=True, universal_newlines=True)
    rc = runTest.returncode
    info("Update: generate local digest: rc=%s; cmd=%s", rc, cmd)

    if rc != 0:
        error("Update: generate local digest failed: rc=%s; cmd=%s", rc, cmd)
        return aiohttp_web.json_response({"rc": False,
                                          "msg": "generate local digest failed"})

    localDigest = runTest.stdout.strip().replace("\t", " ").split(" ")[0]
    if digest != localDigest:
        error("Update: failed digest differ: rc=%s; cmd=%s\ndigest=%s\nlocal=%s", rc, cmd, digest, localDigest)
        return aiohttp_web.json_response({"rc": False,
                                          "msg": "digests differed"})

    cmd = f"tar -xf '{updateTarFileName}' --strip-components=1 -C '{unpackDir}'"
    rc = os.system(cmd)
    info("Update: Unpack: rc=%s; cmd=%s", rc, cmd)
    if rc != 0:
        delPath(unpackDir)
        error("Update: failed Unpack: rc=%s; cmd=%s", rc, cmd)
        return aiohttp_web.json_response({"rc": False,
                                          "msg": "unpack failed"})

    if os.path.exists(inactiveDir):
        rc = delPath(inactiveDir)
        if rc != 0:
            error("Update: failed to delete existing inactive installion: rc=%s; path=%s", rc, inactiveDir)
            return aiohttp_web.json_response({"rc": False,
                                              "msg": "failed to delete existing inactive installion"})

    shutil.move(unpackDir, inactiveDir)

    version = getVersion(inactiveDir)
    builddate = getBuildDate(inactiveDir)
    return aiohttp_web.json_response({"rc": True,
                                      "msg": "version {version} {buildDate} unpacked, verified and ready to activate"})

@routes.get('/update/activate')
@ajaxVerifyToken("admin")
async def uploadActivateAjax(request):
    json = await request.json()

    cwd = os.getcwd()
    parentDir = os.path.dirname(cwd)
    oldDir = os.path.join(parentDir, "CurlingTimer.old")
    inactiveDir = os.path.join(parentDir, "CurlingTimer.new")
    installDir = os.path.join(parentDir, "CurlingTimer")
    
    if os.path.exists(oldDir):
        rc = delPath(oldDir)
        if rc != 0:
            error("Activate: failed to delete existing old installion: rc=%s; path=%s", rc, oldDir)
            return aiohttp_web.json_response({"rc": False,
                                              "msg": "failed to delete existing old installion"})

    shutil.move(installDir, oldDir)
    shutil.move(inactiveDir, installDir)
    
    version = getVersion(installDir)
    buildDate = getBuildDate(installDir)
    
    info("Activate: moved installation into place version=%s builddate=%s dir=%s", version, buildDate, installDir)
    return aiohttp_web.json_response({"rc": True,
                                      "msg": f"version {version} {buildDate} will run on restart"})
    
