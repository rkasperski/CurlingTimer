import os
import tempfile
import shutil
import subprocess

from aiohttp import web as aiohttp_web
from aiohttp import MultipartReader as aiohttp_MultipartReader
from logger import error, warning, info
from access_verification import ajax_verify_token
import setup_app
from identify import get_version, get_build_date

routes = aiohttp_web.RouteTableDef()

what_am_i = "unknown"

def register_purpose(purpose):
    global what_am_i

    what_am_i = purpose


def list_updates():
    my_app = setup_app.get_app()
    update_path = my_app.update_dir
    updates = [f for f in os.listdir(update_path) if f.endswith(".tgz") and os.path.isfile(os.path.join(update_path, f))]
    return updates


@routes.post('/update/list')
@ajax_verify_token("admin")
async def update_list_ajax(_unused_request):
    return aiohttp_web.json_response({"updloaded": True,
                                      "updates": list_updates()})


@routes.post('/update/clean')
@ajax_verify_token("admin")
async def update_clean_ajax(request):
    json = await request.json()
    my_app = setup_app.get_app()

    file_name = json.get("file", None)

    if file_name is None:
        warning("update: clean; nothing to do")
        return aiohttp_web.json_response({"cleaned": False,
                                          "updates": list_updates(),
                                          "msg": "nothing to do"})

    file_name = file_name.strip()
    rm_file_name = os.path.basename(file_name)

    if rm_file_name != file_name or not file_name:
        warning("update: clean; bad file name %s", file_name)
        return aiohttp_web.json_response({"cleaned": False,
                                          "updates": list_updates(),
                                          "msg": "clean refused"})

    tgz_path_name = my_app.update(rm_file_name)
    sp = os.path.splitext(tgz_path_name)
    if sp[-1] != ".tgz":
        warning("update: clean; not a build %s", file_name)
        return aiohttp_web.json_response({"cleaned": False,
                                          "updates": list_updates(),
                                          "msg": "clean refused"})

    sum_path_name = sp[0] + ".sum.txt"
    if os.path.exists(sum_path_name):
        if os.path.isfile(sum_path_name):
            try:
                os.remove(sum_path_name)
            except OSError:
                warning("update: clean; failed to remove sum %s", file_name)

    if not os.path.exists(tgz_path_name):
        warning("update: clean; does not exist %s", tgz_path_name)
        return aiohttp_web.json_response({"cleaned": False,
                                          "updates": list_updates(),
                                          "msg": f"update already removed: {tgz_path_name}"})

    if os.path.exists(tgz_path_name):
        if os.path.isfile(tgz_path_name):
            try:
                os.remove(tgz_path_name)
            except OSError:
                warning("update: clean; failed to remove build %s", tgz_path_name)
                return aiohttp_web.json_response({"cleaned": False,
                                                  "updates": list_updates(),
                                                  "msg": f"remove of buid refused: {tgz_path_name}"})

    return aiohttp_web.json_response({"cleaned": True,
                                      "updates": list_updates(),
                                      "msg": f"update removed: {file_name}"})


@routes.post('/update/upload')
@ajax_verify_token("admin")
async def update_upload_ajax(request):
    reader = aiohttp_MultipartReader.from_response(request)
    file_name = None
    my_app = setup_app.get_app()
    file_uploaded = False
    partial_file_name = None

    info("Update: started upload")
    while True:
        part = await reader.next()
        if part is None:
            break

        try:
            part_name = part.name
            partial_file_name = part.filename
        except ValueError:
            content_disposition = part.headers.get("Content-Disposition", None)[11:]
            sp = content_disposition.split('"; ')
            for n, v in [t.split("=") for t in sp]:
                if v.startswith('"'):
                    v = v[1:]
                if v.endswith('"'):
                    v = v[0:-1]

                if n == "filename":
                    partial_file_name = v
                elif n == "name":
                    part_name = v  # not too sure about this one

        if part_name == "updateFileUpload":
            if not partial_file_name:
                continue

            info("Update: uploading file: %s", partial_file_name)
            ext = partial_file_name.rsplit(".", 1)[-1]
            if ext in ["tgz"]:
                file_uploaded = True
                file_name = my_app.update(partial_file_name)

                with open(file_name, "wb+") as f:
                    while not part.at_eof():
                        chunk = await part.read_chunk()

                        f.write(chunk)
            else:
                warning("Update: bad file extension: %s", partial_file_name)
                aiohttp_web.json_response({"updloaded": False,
                                           "msg": "bad file extension"})

    if not file_uploaded:
        error("Update: filed to upload file: %s", partial_file_name)
        aiohttp_web.json_response({"updloaded": False,
                                   "msg": f"failed to upload file {partial_file_name}"})

    info("Update: uploaded file: %s", partial_file_name)
    return aiohttp_web.json_response({"updloaded": True,
                                      "msg": "succesful"})


def del_path(path):
    try:
        shutil.rmtree(path)
    except OSError as e:
        error("Update: failed to delete dir: error=%s; %s", e, path)
        return 1

    return 0


@routes.post('/update/unpack')
@ajax_verify_token("admin")
async def update_unpack_ajax(request):
    json = await request.json()
    my_app = setup_app.get_app()

    if my_app.user != "root":
        parent_dir = my_app.home_dir
    else:
        current_install_directory = my_app.app_dir
        parent_dir = os.path.dirname(current_install_directory)

    old_dir = os.path.join(parent_dir, f"{what_am_i}.old")
    install_dir = os.path.join(parent_dir, f"{what_am_i}")
    inactive_dir = os.path.join(parent_dir, f"{what_am_i}.new")
    unpack_dir = tempfile.mkdtemp()

    install_file = json.get("file")
    digest = json.get("digest")

    update_tar_file_name = my_app.update(install_file)

    if not install_file.startswith(what_am_i):
        error("Update: wrong build file %s: %s", what_am_i, install_file)
        return aiohttp_web.json_response({"rc": False,
                                          "msg": "wrong build file type. Try again"})

    cmd = f"sha512sum '{update_tar_file_name}'"
    run_test = subprocess.run(cmd, shell=True, capture_output=True, universal_newlines=True, check=False)
    rc = run_test.returncode
    info("Update: generate local digest: rc=%s; cmd=%s", rc, cmd)

    if rc != 0:
        error("Update: generate local digest failed: rc=%s; cmd=%s", rc, cmd)
        return aiohttp_web.json_response({"rc": False,
                                          "msg": "generate local digest failed"})

    local_digest = run_test.stdout.strip().replace("\t", " ").split(" ")[0]
    if digest != local_digest:
        error("Update: failed digest differ: rc=%s; cmd=%s\ndigest=%s\nlocal=%s", rc, cmd, digest, local_digest)
        return aiohttp_web.json_response({"rc": False,
                                          "msg": "digests differed"})

    info("Update: digests match")
    cmd = f"tar -xf '{update_tar_file_name}' --strip-components=1 -C '{unpack_dir}'"
    rc = os.system(cmd)
    info("Update: Unpack: rc=%s; cmd=%s", rc, cmd)
    if rc != 0:
        info("Update: cleaning up after failed unpack: %s", unpack_dir)
        del_path(unpack_dir)
        error("Update: failed Unpack: rc=%s; cmd=%s", rc, cmd)
        return aiohttp_web.json_response({"rc": False,
                                          "msg": "unpack failed"})

    if os.path.exists(inactive_dir):
        info("Update: cleaning old update directory: %s", inactive_dir)
        rc = del_path(inactive_dir)
        if rc != 0:
            error("Update: failed to delete existing inactive installion: rc=%s; path=%s", rc, inactive_dir)
            return aiohttp_web.json_response({"rc": False,
                                              "msg": "failed to delete existing inactive installion"})

    info("Update: cleaning unpack directory to update directory")
    try:
        shutil.move(unpack_dir, inactive_dir)
    except OSError as e:
        error("Update: failed to move unpacked dir to new install dir: error=%s; %s ==> %s ", e
              , unpack_dir, inactive_dir)
        return aiohttp_web.json_response({"rc": False,
                                          "msg": f"failed to move unpack dir to new dir: {str(e)}"})

    if os.path.exists(old_dir):
        info("Update: cleaning old installation directory: %s", old_dir)
        rc = del_path(old_dir)
        if rc != 0:
            error("Update: failed to delete existing old installion: rc=%s; path=%s", rc, old_dir)
            return aiohttp_web.json_response({"rc": False,
                                              "msg": "failed to delete existing old installion"})

    info("Update: moving current active installation to old installation %s ==> %s", install_dir, old_dir)
    try:
        shutil.move(install_dir, old_dir)
    except OSError as e:
        error("Update: failed to move active install dir to old install dir: error=%s; %s ==> %s ",
              e, install_dir, old_dir)
        return aiohttp_web.json_response({"rc": False,
                                          "msg": f"failed to move active install dir to old dir: {str(e)}"})

    info("Update: moving new installation to current active installation %s ==> %s", inactive_dir, install_dir)
    try:
        shutil.move(inactive_dir, install_dir)
    except OSError as e:
        error("Update: failed to move new install to active install: error=%s; %s ==> %s ",
              e, inactive_dir, install_dir)
        return aiohttp_web.json_response({"rc": False,
                                          "msg": f"failed to move new install dir to active install dir: {str(e)}"})

    version = get_version(install_dir)
    build_date = get_build_date(install_dir)

    info("Update file: %s version:%s built on:%s is installed", install_file, version, build_date)

    return aiohttp_web.json_response({"rc": True,
                                      "version": version,
                                      "builddate": build_date,
                                      "msg": f"version: {version} date:{build_date} verified and unpacked"})
