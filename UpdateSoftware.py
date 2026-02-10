from Logger import error, warning, info
import os
import tempfile
import shutil
import subprocess

from aiohttp import web as aiohttp_web
from aiohttp import MultipartReader as aiohttp_MultipartReader
from AccessVerification import ajaxVerifyToken
import SetupApp
from Identify import versionNo, buildDate, getVersion, getBuildDate

routes = aiohttp_web.RouteTableDef()

what_am_i = "unknown"

def register_purpose(purpose):
    global what_am_i
    
    what_am_i = purpose


def listUpdates():
    myApp = SetupApp.getApp()
    updatePath = myApp.updateDir
    updates = [f for f in os.listdir(updatePath) if f.endswith(".tgz") and os.path.isfile(os.path.join(updatePath, f))]
    return updates


@routes.post('/update/list')
@ajaxVerifyToken("admin")
async def updateListAjax(request):
    return aiohttp_web.json_response({"updloaded": True,
                                      "updates": listUpdates()})


@routes.post('/update/clean')
@ajaxVerifyToken("admin")
async def updateCleanAjax(request):
    json = await request.json()
    myApp = SetupApp.getApp()

    fileName = json.get("file", None)

    if fileName is None:
        warning("update: clean; nothing to do")
        return aiohttp_web.json_response({"cleaned": False,
                                          "updates": listUpdates(),
                                          "msg": "nothing to do"})

    fileName = fileName.strip()
    rmFileName = os.path.basename(fileName)

    if rmFileName != fileName or not fileName:
        warning(f"update: clean; bad file name {fileName}")
        return aiohttp_web.json_response({"cleaned": False,
                                          "updates": listUpdates(),
                                          "msg": "clean refused"})

    tgzPathName = myApp.update(rmFileName)
    sp = os.path.splitext(tgzPathName)
    if sp[-1] != ".tgz":
        warning(f"update: clean; not a build {fileName}")
        return aiohttp_web.json_response({"cleaned": False,
                                          "updates": listUpdates(),
                                          "msg": "clean refused"})

    sumPathName = sp[0] + ".sum.txt"
    if os.path.exists(sumPathName):
        if os.path.isfile(sumPathName):
            try:
                os.remove(sumPathName)
            except OSError:
                warning(f"update: clean; failed to remove sum {fileName}")
            
    if not os.path.exists(tgzPathName):
        warning(f"update: clean; does not exist {fileName}")
        return aiohttp_web.json_response({"cleaned": False,
                                          "updates": listUpdates(),
                                          "msg": f"update already removed: {fileName}"})

    if os.path.exists(tgzPathName):
        if os.path.isfile(tgzPathName):
            try:
                os.remove(tgzPathName)
            except OSError:
                warning(f"update: clean; failed to remove build {fileName}")
                return aiohttp_web.json_response({"cleaned": False,
                                                  "updates": listUpdates(),
                                                  "msg": f"remove of buid refused: {fileName}"})
            
    return aiohttp_web.json_response({"cleaned": True,
                                      "updates": listUpdates(),
                                      "msg": f"update removed: {fileName}"})


@routes.post('/update/upload')
@ajaxVerifyToken("admin")
async def updateUploadAjax(request):
    reader = aiohttp_MultipartReader.from_response(request)
    fileName = None
    myApp = SetupApp.getApp()
    fileUploaded = False
    pfilename = None
    pname = None

    info("Update: started upload")
    while True:
        part = await reader.next()
        if part is None:
            break

        try:
            pname = part.name
            pfilename = part.filename
        except ValueError:
            contentDisposition = part.headers.get("Content-Disposition", None)[11:]
            sp = contentDisposition.split('"; ')
            for n, v in [t.split("=") for t in sp]:
                if v.startswith('"'):
                    v = v[1:]
                if v.endswith('"'):
                    v = v[0:-1]

                if n == "filename":
                    pfilename = v
                elif n == "name":
                    pname = v  # not too sure about this one

        print(f"{pname=} {pfilename=}")
        if pname == "updateFileUpload":
            if not pfilename:
                continue
            
            info("Update: uploading file: %s", pfilename)
            ext = pfilename.rsplit(".", 1)[-1]
            if ext in ["tgz"]:
                fileUploaded = True
                fileName = myApp.update(pfilename)

                with open(fileName, "wb+") as f:
                    while not part.at_eof():
                        chunk = await part.read_chunk()

                        f.write(chunk)
            else:
                warning("Update: bad file extension: %s", pfilename)
                aiohttp_web.json_response({"updloaded": False,
                                           "msg": "bad file extension"})
                
    if not fileUploaded:
        error("Update: filed to upload file: %s", pfilename)
        aiohttp_web.json_response({"updloaded": False,
                                   "msg": f"failed to upload file {pfilename}"})
        
    info("Update: uploaded file: %s", pfilename)
    return aiohttp_web.json_response({"updloaded": True,
                                      "msg": "succesful"})


def delPath(path):
    try:
        shutil.rmtree(path)
    except OSError as e:
        error("Update: failed to delete dir: error=%s; %s", e, path)
        return 1
    
    return 0


@routes.post('/update/unpack')
@ajaxVerifyToken("admin")
async def updateUnpackAjax(request):
    json = await request.json()
    myApp = SetupApp.getApp()

    if myApp.user != "root":
        parentDir = myApp.homeDir
    else:
        currentInstallDirectory = myApp.appDir
        parentDir = os.path.dirname(currentInstallDirectory)
        
    oldDir = os.path.join(parentDir, f"{what_am_i}.old")
    installDir = os.path.join(parentDir, f"{what_am_i}")
    inactiveDir = os.path.join(parentDir, f"{what_am_i}.new")
    unpackDir = tempfile.mkdtemp()

    installFile = json.get("file")
    digest = json.get("digest")

    updateTarFileName = myApp.update(installFile)

    if not installFile.startswith(what_am_i):
        error("Update: wrong build file %s: %s", what_am_i, installFile)
        return aiohttp_web.json_response({"rc": False,
                                          "msg": "wrong build file type. Try again"})
        
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

    info("Update: digests match")
    cmd = f"tar -xf '{updateTarFileName}' --strip-components=1 -C '{unpackDir}'"
    rc = os.system(cmd)
    info("Update: Unpack: rc=%s; cmd=%s", rc, cmd)
    if rc != 0:
        info("Update: cleaning up after failed unpack: %s", unpackDir)
        delPath(unpackDir)
        error("Update: failed Unpack: rc=%s; cmd=%s", rc, cmd)
        return aiohttp_web.json_response({"rc": False,
                                          "msg": "unpack failed"})

    if os.path.exists(inactiveDir):
        info("Update: cleaning old update directory: %s", inactiveDir)
        rc = delPath(inactiveDir)
        if rc != 0:
            error("Update: failed to delete existing inactive installion: rc=%s; path=%s", rc, inactiveDir)
            return aiohttp_web.json_response({"rc": False,
                                              "msg": "failed to delete existing inactive installion"})

    info("Update: cleaning unpack directory to update directory")
    try:
        shutil.move(unpackDir, inactiveDir)
    except OSError as e:
        error("Update: failed to move unpacked dir to new install dir: error=%s; %s ==> %s ", e, unpackDir, inactiveDir)
        return aiohttp_web.json_response({"rc": False,
                                          "msg": f"failed to move unpack dir to new dir: {str(e)}"})

    if os.path.exists(oldDir):
        info("Update: cleaning old installation directory: %s", oldDir)
        rc = delPath(oldDir)
        if rc != 0:
            error("Update: failed to delete existing old installion: rc=%s; path=%s", rc, oldDir)
            return aiohttp_web.json_response({"rc": False,
                                              "msg": "failed to delete existing old installion"})

    info("Update: moving current active installation to old installation %s ==> %s", installDir, oldDir)
    try:
        shutil.move(installDir, oldDir)
    except OSError as e:
        error("Update: failed to move active install dir to old install dir: error=%s; %s ==> %s ", e, installDir, oldDir)
        return aiohttp_web.json_response({"rc": False,
                                          "msg": f"failed to move active install dir to old dir: {str(e)}"})
       
    info("Update: moving new installation to current active installation %s ==> %s", inactiveDir, installDir)
    try:
        shutil.move(inactiveDir, installDir)
    except OSError as e:
        error("Update: failed to move new install to active install: error=%s; %s ==> %s ", e, inactiveDir, installDir)
        return aiohttp_web.json_response({"rc": False,
                                          "msg": f"failed to move new install dir to active install dir: {str(e)}"})

    version = getVersion(installDir)
    builddate = getBuildDate(installDir)

    info("Update file: %s version:%s built on:%s is installed", installFile, version, builddate)

    return aiohttp_web.json_response({"rc": True,
                                      "version": version,
                                      "builddate": builddate,
                                      "msg": f"version: {version} date:{builddate} verified and unpacked"})
