import asyncio
import os
import time
import csv

import tempfile
import tinydb
import aiohttp
from dateutil.parser import parse as date_parser
import filehash

from logger import info, error, debug
from setup_app import get_app
import http_utils as http
import config
from access_verification import get_authenticator
from utils import clean_files, seconds_to_str, str_to_seconds
from extract_draw_from_file import extract_draws_from_file

db_hasher = filehash.FileHash('sha1')
draw_db = None

token_valid_time = 3600


def to_int(s, default=None):
    try:
        return int(s)
    except (ValueError, TypeError):
        return s


class DrawManager:
    def __init__(self, file_name='draw.json', path=None):
        self.file_name = file_name
        my_app = get_app()
        self.full_path = os.path.join(path, file_name) if path else my_app.data(self.file_name)

        self.hash = 0
        self.hash_is_dirty = False

        self.draws_shown = set()
        self.draws_started = set()
        self._db = tinydb.TinyDB(self.full_path)
        self.hash_draw_db = 0

    def db_fix(self):
        if self._db is not None:
            if os.path.isfile(self.full_path):
                t = time.localtime(time.time())
                local_time = time.strftime("%Y-%m-%d %H:%M:%S", t)
                bad_path = self.full_path + f".bad.{local_time}"
                try:
                    os.rename(self.full_path, bad_path)
                    info("draw: db fix: move %s -> %s", self.full_path, bad_path)
                except Exception:
                    error("draw: db fix: bad move %s -> %s", self.full_path, bad_path)
                    self._db = None
                    error("draw: db fix: stop using draw db", exc_info=True)
                    return

            self._db = tinydb.TinyDB(self.full_path)
            error("draw: db fix: creating empty draw db %s", self.full_path)

    def db_search(self, *args, **kwargs):
        if self._db is None:
            return []

        try:
            return self._db.search(*args, **kwargs)
        except Exception:
            error("draw: db search: bad db args=%s kwargs=%s", args, kwargs)
            self.db_fix()
            return []

    def db_insert(self, *args, **kwargs):
        if self._db is None:
            return None

        try:
            return self._db.insert(*args, **kwargs)
        except Exception:
            error("draw: db insert: bad db args=%s kwargs=%s", args, kwargs)
            self.db_fix()
            return None

    def db_update(self, *args, **kwargs):
        if self._db is None:
            return None

        try:
            return self._db.update(*args, **kwargs)
        except Exception:
            error("draw: db update: bad db args=%s kwargs=%s", args, kwargs)
            self.db_fix()
            return None

    def db_remove(self, *args, **kwargs):
        if self._db is None:
            return None

        try:
            return self._db.remove(*args, **kwargs)
        except Exception:
            error("draw: db remove: bad db args=%s kwargs=%s", args, kwargs)
            self.db_fix()
            return None

    def db_contains(self, *args, **kwargs):
        if self._db is None:
            return None

        try:
            return self._db.contains(*args, **kwargs)
        except Exception:
            error("draw: db contains: bad db args=%s kwargs=%s", args, kwargs)

    def db_get(self, *args, **kwargs):
        if self._db is None:
            return None

        try:
            return self._db.get(*args, **kwargs)
        except Exception:
            error("draw: db get: bad db args=%s kwargs=%s", args, kwargs)
            self.db_fix()
            return None

    def db_all(self):
        if self._db is None:
            return []

        try:
            return self._db.all()
        except Exception:
            error("draw: db all: bad db args=%s kwargs=%s", args, kwargs)
            self.db_fix()
            return []

    def add_draw(self, draw, draw_name=None):
        if isinstance(draw, dict):
            e = draw
        else:
            e = draw.as_dict()

        msg = None

        try:
            t = date_parser(e['time'])
            e["time"] = t.strftime("%-H:%M")
            ds = e['date']
            if len(e.get("sheets")) == 0:
                if e.get('date', None) == "none" or e.get('time', None):
                    return (None, "didn't add; bad time")

                return (None, "didn't add; empty draw", e)
            if ds and ds.strip() and len(e.get("sheets")):
                d = date_parser(e['date'])
                e["date"] = d.strftime("%Y-%m-%d")
            else:
                e["date"] = "unknown"

        except TypeError as err:
            error("draw: add: %s exception: %s", e, err)
            return (None, f"didn't add; parsing error;  {e.get('name', None)} d={e.get('date', None)} r={e.get('time', None)}", e)

        if draw_name:
            e["name"] = draw_name

        msg = self.normalize_sheet_numbers(e)
        self.hash_is_dirty = True

        entry = tinydb.Query()
        draws_to_delete = self.db_search((entry.date == e["date"]) & (entry.name == e["name"]) & (entry.time == e["time"]))

        if draws_to_delete:
            for dd in draws_to_delete:
                self.delete_draw(dd.doc_id)
                self.draws_shown.discard(dd.doc_id)
                self.draws_started.discard(dd.doc_id)

        draw_id = self.db_insert(e)
        return (self.get_draw_by_id(draw_id), msg)

    def update_draw(self, draw_id, e):
        self.normalize_sheet_numbers(e)
        self.db_update(e, doc_ids=[draw_id])
        self.draws_shown.discard(draw_id)
        self.draws_started.discard(draw_id)
        self.hash_is_dirty = True
        return self.get_draw_by_id(draw_id)

    async def upload_ajax(self, request, verbose=0):
        reader = aiohttp.MultipartReader.from_response(request)
        file_name = None
        start_time = None
        auto_delete = "no"
        colour = "white"
        show = "no"
        at_start = "no"
        draw_name = None

        msgs = []
        while True:
            part = await reader.next()
            if part is None:
                break

            text = await part.read()

            pn = part.name

            if pn == "defaultTime":
                start_time = text.decode("utf-8")
            elif pn == "defaultAutoDelete":
                auto_delete = text.decode("utf-8")
            elif pn == "defaultColour":
                colour = text.decode("utf-8")
            elif pn == "defaultShowDraw":
                show = text.decode("utf-8")
            elif pn == "defaultAtStart":
                at_start = text.decode("utf-8")
            elif pn == "draw_name":
                tmp = text.decode("utf-8").strip()
                if tmp:
                    draw_name = tmp
            elif pn == "excelFileUpload":
                if not part.filename:
                    continue

                ext = part.filename.rsplit(".", 1)[-1]
                if ext in ["csv", "xlsx", "xls", "pdf"]:
                    file_name = tempfile.mkstemp(suffix=f'_curlingtimer_schedule.{ext}', prefix='tmp', dir='/tmp')[1]

                    with open(file_name, "wb+") as f:
                        f.write(text)

        debug("ext=%s start_time=%s auto_delete=%s colour=%s show=%s at_start=%s", 
              ext, start_time, auto_delete, colour, show, at_start)

        if file_name:
            debug("Extract file_name=%s", file_name)

            draws = extract_draws_from_file(file_name, ext, start_time, auto_delete, colour, show, at_start)

            for draw in draws:
                await asyncio.sleep(0.001)
                draw, msg = self.add_draw(draw, draw_name=draw_name)
                debug("add draw draw=%s msg=%s", draw, msg)

                if msg:
                    msgs.append(msg)

                if not draw:
                    continue

                msgs.append(f"added; {draw['name']} {draw['date']} {draw['time']}")

            msgs.sort()

            clean_files(file_name)

        return msgs

    def get_hash(self):
        if self.hash_is_dirty:
            self.hash_is_dirty = False
            self.hash_draw_db = db_hasher.hash_file(self.full_path)

        return self.hash_draw_db

    def get_all_draws(self):
        return self.db_all()

    def get_draw_by_id(self, draw_id):
        if self.db_contains(doc_id=draw_id):
            res = self.db_get(doc_id=draw_id)
            res["id"] = draw_id
            return res

        return None

    def normalize_sheet_numbers(self, draw):
        if draw.get("normalized", False):
            return None

        msg = None
        sheets = draw["sheets"]
        number_of_sheets = len(config.display.sheets)

        norm = [{"team1": "", "team2": "", "sheet": i + 1} for i in range(number_of_sheets)]

        not_valid = sum(["sheet" in s and (isinstance(s["sheet"], int) or s["sheet"].isdigit()) and 1 <= int(s["sheet"]) <= number_of_sheets for s in sheets])

        if not_valid == len(sheets):
            for sheet in sheets:
                norm[to_int(sheet["sheet"], 1) - 1] = sheet
        else:
            for sheet_no, sheet in enumerate(sheets):
                sheet["sheet"] = sheet_no + 1
                try:
                    norm[sheet_no] = sheet
                except IndexError:
                    msg = "Too many sheets in draw"

        draw["sheets"] = norm
        draw["normalized"] = 1
        return msg

    def delete_draw(self, draw_id):
        if self.db_contains(doc_id=draw_id):
            self.db_remove(doc_ids=[draw_id])
            self.hash_is_dirty = True
            return True

        return False

    def write_csv(self, file_name, draws=None):
        if draws is None:
            draws = self.get_all_draws()

        msg = None
        with open(file_name, "w", encoding="utf-8", newline='') as csv_file:
            worksheet = csv.writer(csv_file)
            for draw in draws:
                msg = self.normalize_sheet_numbers(draw)

                worksheet.writerow([draw.get("date", "unknown"), draw.get("name", "unknown")])

                draw_time = draw.get("time", "unknown")
                for s in draw["sheets"]:
                    worksheet.writerow([draw_time, s["sheet"], s.get("team1", "team1"), s.get("team2", "team2")])
                    draw_time = None

                worksheet.writerow(["show", draw.get("show", str(15))])
                worksheet.writerow(["colour", draw.get("colour", "white")])
                worksheet.writerow(["autoDelete", draw.get("autoDelete", str(48*60))])
                worksheet.writerow(["atStart", draw.get("atStart", "120")])
                worksheet.writerow([])

        return msg

    async def blank_sheets(self, sheets):
        active_blank_tasks = []
        for sheet in sheets:
            sheet_number = to_int(sheet["sheet"], 1000000) - 1
            if 0 <= sheet_number < len(config.display.sheets):
                sheet_display = config.display.sheets[sheet_number]

                if sheet_display.ip == "Unassigned":
                    continue

                tkn = get_authenticator().create(expires=int(time.time()) + token_valid_time, audience="peer")
                post_task = asyncio.create_task(
                    http.post_url_json_response("blankSheets",
                                                f'{http.scheme}://{ sheet_display.ip}:{http.port}/blank',
                                                json_data={},
                                                headers={http.CLOCK_HDR: tkn},
                                                retries=3))
                active_blank_tasks.append(post_task)
                info("Draw: blank %s", sheet_display.ip)


        await asyncio.wait(active_blank_tasks)

    async def start_count_down_sheets(self, sheets, secs_since_draw_start):
        game_time = seconds_to_str(max(0, str_to_seconds(config.display.defaults.game_time) - secs_since_draw_start))

        active_setup_tasks = []
        for sheet in sheets:
            sheet_number = to_int(sheet["sheet"], 1000000) - 1
            if 0 <= sheet_number < len(config.display.sheets):
                sheet_display = config.display.sheets[sheet_number]

                if sheet_display.ip == "Unassigned":
                    continue

                if sheet["team1"] or sheet["team2"]:
                    tkn = get_authenticator().create(expires=int(time.time()) + token_valid_time, audience="peer")

                    post_task = asyncio.create_task(
                        http.post_url_json_response(
                            "draw/countdown/set",
                            f'{http.scheme}://{sheet_display.ip}:{http.port}/countdown/set',
                            json_data={"gameTime": game_time,
                                       "finishedMessageColour": config.display.defaults.finished_message_colour,
                                       "finishedMessage": config.display.defaults.finished_message,
                                       "lastEndMessage": config.display.defaults.last_end_message,
                                       "lastEndMessageColour": config.display.defaults.last_end_message_colour
                                       },
                            headers={http.CLOCK_HDR: tkn},
                            retries=3))
                    active_setup_tasks.append(post_task)

                    info("Draw: counttdown set %s game_time=%s",
                         sheet_display.ip,
                         game_time)


        await asyncio.wait(active_setup_tasks)

        active_start_tasks = []
        for sheet in sheets:
            sheet_number = to_int(sheet["sheet"], 1000000) - 1
            if 0 <= sheet_number < len(config.display.sheets):
                sheet_display = config.display.sheets[sheet_number]

                if sheet_display.ip == "Unassigned":
                    continue

                if sheet["team1"] or sheet["team2"]:
                    tkn = get_authenticator().create(expires=int(time.time()) + token_valid_time, audience="peer")
                    post_task = asyncio.create_task(
                        http.post_url_json_response("draw/countdown/start",
                                                    f'{http.scheme}://{sheet_display.ip}:{http.port}/countdown/start',
                                                    json_data={},
                                                    headers={http.CLOCK_HDR: tkn},
                                                    retries=3))
                    active_start_tasks.append(post_task)
                    info("Draw: counttdown start %s", sheet_display.ip)

        await asyncio.wait(active_start_tasks)

    async def show_teams(self, colour, team_names_by_sheet, how_long=None, until=None):
        active_setup_tasks = []
        for sheet in team_names_by_sheet:
            sheet_number = to_int(sheet["sheet"], 1000000) - 1
            if 0 <= sheet_number < len(config.display.sheets):
                sheet_display = config.display.sheets[sheet_number]

                if sheet_display.ip == "Unassigned":
                    continue

                if sheet["team1"] or sheet["team2"]:
                    tkn = get_authenticator().create(expires=int(time.time()) + token_valid_time, audience="peer")

                    post_task = asyncio.create_task(
                        http.post_url_json_response("draw/showTeams/set",
                                                    f'{http.scheme}://{sheet_display.ip}:{http.port}/teamnames/set',
                                                    json_data={"team1": sheet["team1"],
                                                               "team2": sheet["team2"],
                                                               "colour": colour,
                                                               },
                                                    headers={http.CLOCK_HDR: tkn},
                                                    retries=3))
                    active_setup_tasks.append(post_task)
                    info("Draw: show teams set %s '%s' '%s'", sheet_display.ip,  sheet["team1"],  sheet["team2"])

        await asyncio.wait(active_setup_tasks)

        active_start_tasks = []
        for sheet in team_names_by_sheet:
            sheet_number = to_int(sheet["sheet"], 1000000) - 1
            if 0 <= sheet_number < len(config.display.sheets):
                sheet_display = config.display.sheets[sheet_number]

                if sheet_display.ip == "Unassigned":
                    continue

                if sheet["team1"] or sheet["team2"]:
                    tkn = get_authenticator().create(expires=int(time.time()) + token_valid_time, audience="peer")
                    post_task = asyncio.create_task(
                        http.post_url_json_response("draw/showTeams/show",
                                                    f'{http.scheme}://{sheet_display.ip}:{http.port}/teamnames/show',
                                                    json_data={"howLong": how_long,
                                                               "until": until},
                                                    headers={http.CLOCK_HDR: tkn},
                                                    retries=3))
                    active_start_tasks.append(post_task)
                    info("Draw: show teams show %s how_long=%s until=%s", sheet_display.ip,  how_long,  until)

        await asyncio.wait(active_start_tasks)

    def clean_auto_deletes(self):
        delete_set = set()
        draws_started = set()
        draws_shown = set()
        local_time = int(time.time())

        for d in self.db_all():
            draw_time = time.mktime(time.strptime(d["date"] + ' ' + d["time"], "%Y-%m-%d %H:%M"))
            auto_delete = to_int(d.get("autoDelete", 14), 14)

            secs_since_draw = local_time - draw_time
            if isinstance(auto_delete, int) and secs_since_draw > auto_delete * 24 * 60 * 60:
                delete_set.add(d.doc_id)
            else:
                if d.doc_id in self.draws_started:
                    draws_started.add(d.doc_id)
                if d.doc_id in self.draws_shown:
                    draws_shown.add(d.doc_id)

        self.draws_started = draws_started
        self.draws_shown = draws_shown
        if delete_set:
            self.db_remove(doc_ids=list(delete_set))
            self.hash_is_dirty = True

    async def draw_show_task(self, app):
        last_delete_check_hour = None
        while True:
            try:
                await asyncio.sleep(1)

                entry = tinydb.Query()

                local_time = int(time.time())
                local_time_tz = time.localtime(local_time)
                today = time.strftime("%Y-%m-%d", local_time_tz)
                yesterday = time.strftime("%Y-%m-%d", time.localtime(local_time - 24*60*60))
                tomorrow = time.strftime("%Y-%m-%d", time.localtime(local_time + 24*60*60))

                if last_delete_check_hour != local_time_tz.tm_hour:
                    last_delete_check_hour = local_time_tz.tm_hour
                    self.clean_auto_deletes()

                test_draws = self.db_search((entry.date == today) | (entry.date == yesterday) | (entry.date == tomorrow))
                for draw in test_draws:
                    show = to_int(draw.get("show", 0), 0) * 60
                    at_start = to_int(draw.get("atStart", "blank"))

                    draw_time = time.mktime(time.strptime(draw["date"] + ' ' + draw["time"], "%Y-%m-%d %H:%M"))

                    secs_to_draw_start = draw_time - local_time
                    if abs(secs_to_draw_start) > 8 * 3600:
                        continue

                    debug("Draw: %s check show=%s at_start=%s %s %s draw_time=%s secs_to_draw=%s",
                          draw["name"],
                          show,
                          at_start,
                          draw["date"],
                          draw["time"],
                          draw_time,
                          secs_to_draw_start)

                    if secs_to_draw_start > 0:
                        if draw.doc_id not in self.draws_shown:
                            if show and secs_to_draw_start < show:
                                info("Draw: check show teams draw_time=%s",
                                     draw_time)

                                await self.show_teams(draw["colour"], draw["sheets"], until=draw_time)
                                self.draws_shown.add(draw.doc_id)
                    elif secs_to_draw_start <= 0:
                        if draw.doc_id not in self.draws_started:
                            self.draws_started.add(draw.doc_id)
                            if at_start == "countdown":
                                active_until = draw_time + str_to_seconds(config.display.defaults.game_time) + str_to_seconds(config.display.defaults.blank_time)
                                info("Draw: countdown test active_until=%s local_time=%s", active_until, local_time)
                                if active_until > local_time:
                                    info("Draw: countdown start secs_to_draw_start=%s", -secs_to_draw_start)
                                    await self.start_count_down_sheets(draw["sheets"], -secs_to_draw_start)
                            elif isinstance(at_start, int):
                                active_until = draw_time + at_start * 60
                                info("Draw: show_teams test active_until=%s local_time=%s", active_until, local_time)
                                if active_until > local_time:
                                    info("Draw: showTeams active_until=%s", active_until)
                                    await self.show_teams(draw["colour"], draw["sheets"], until=active_until)
                            else:
                                blank_after = draw_time + str_to_seconds(config.display.defaults.game_time) + str_to_seconds(config.display.defaults.blank_time)
                                info("Draw: blank test blank_after=%s local_time=%s", blank_after, local_time)
                                if blank_after > local_time:
                                    info("Draw: blank")
                                    await self.blank_sheets(draw["sheets"])

            except asyncio.CancelledError:
                return
            except Exception as e:
                error("draw: show task %s", e, exc_info=True)
                raise

    async def start_tasks(self, app):
        info("DrawManager: tasks - start")

        app['draw_monitor'] = asyncio.create_task(self.draw_show_task(app))

    async def stop_tasks(self, app):
        if 'draw_monitor' in app:
            info("DrawManager: stop tasks - cancel")
            app['draw_monitor'].cancel()

            info("DrawManager: stop tasks - done")


def create_draw_manager():
    global draw_db

    draw_db = DrawManager()
    return draw_db
