from Logger import info, error, debug
import asyncio
import os
import time
import csv

import filehash
import tempfile
import tinydb
import aiohttp
from dateutil.parser import parse as date_parser

import SetupApp
from HTTP_Utils import postUrlJSONResponse, CLOCK_HDR
import Config
import HTTP_Utils as httpUtils
import AccessVerification
from Utils import cleanFiles, secondsToStr, strToSeconds
from ExtractDrawFromFile import extractDrawsFromFile

dbHasher = filehash.FileHash('sha1')
drawDB = None

tokenValidTime = 3600


def toInt(s, default=None):
    try:
        return int(s)
    except (ValueError, TypeError):
        return s

    
class DrawManager:
    def __init__(self, fileName='draw.json', path=None):
        self.fileName = fileName
        myApp = SetupApp.getApp()
        self.fullPath = os.path.join(path, fileName) if path else myApp.data(self.fileName)

        self.hash = 0
        self.hashIsDirty = False

        self.drawsShown = set()
        self.drawsStarted = set()
        self._db = tinydb.TinyDB(self.fullPath)
        self.hashDrawDB = 0

    def dbFix(self):
        if self._db is not None:
            if os.path.isfile(self.fullPath):
                t = time.localtime(time.time())
                lclTime = time.strftime("%Y-%m-%d %H:%M:%S", t)
                badPath = self.fullPath + f".bad.{lclTime}"
                try:
                    os.rename(self.fullPath, badPath)
                    info("draw: db fix: move %s -> %s", self.fullPath, badPath)
                except Exception:
                    error("draw: db fix: bad move %s -> %s", self.fullPath, badPath)
                    self._db = None
                    error("draw: db fix: stop using draw db", exc_info=True)
                    return

            self._db = tinydb.TinyDB(self.fullPath)
            error("draw: db fix: creating empty draw db %s", self.fullPath)

    def dbSearch(self, *args, **kwargs):
        if self._db is None:
            return []
        
        try:
            return self._db.search(*args, **kwargs)
        except Exception:
            error("draw: db search: bad db")
            self.dbFix()
            return []

    def dbInsert(self, *args, **kwargs):
        if self._db is None:
            return None
        
        try:
            return self._db.insert(*args, **kwargs)
        except Exception:
            error("draw: db insert: bad db")
            self.dbFix()
            return None
        
    def dbUpdate(self, *args, **kwargs):
        if self._db is None:
            return None
        
        try:
            return self._db.update(*args, **kwargs)
        except Exception:
            error("draw: db update: bad db")
            self.dbFix()
            return None
        
    def dbRemove(self, *args, **kwargs):
        if self._db is None:
            return None
        
        try:
            return self._db.remove(*args, **kwargs)
        except Exception:
            error("draw: db remove: bad db")
            self.dbFix()
            return None
        
    def dbContains(self, *args, **kwargs):
        if self._db is None:
            return None
    
        try:
            return self._db.contains(*args, **kwargs)
        except Exception:
            error("draw: db contains: bad db")
        
    def dbGet(self, *args, **kwargs):
        if self._db is None:
            return None
    
        try:
            return self._db.get(*args, **kwargs)
        except Exception:
            error("draw: db get: bad db")
            self.dbFix()
            return None
        
    def dbAll(self):
        if self._db is None:
            return []
    
        try:
            return self._db.all()
        except Exception:
            error("draw: db all: bad db")
            self.dbFix()
            return []
        
    def addDraw(self, draw, drawName=None):
        if isinstance(draw, dict):
            e = draw
        else:
            e = draw.asDict()

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

        if drawName:
            e["name"] = drawName

        msg = self.normalizeSheetNumbers(e)
        self.hashIsDirty = True
        
        entry = tinydb.Query()
        docsToDelete = self.dbSearch((entry.date == e["date"]) & ((entry.name == e["name"]) | (entry.time == e["time"])))

        if docsToDelete:
            for dd in docsToDelete:
                self.deleteDraw(dd.doc_id)
                self.drawsShown.discard(dd.doc_id)
                self.drawsStarted.discard(dd.doc_id)
                
        id = self.dbInsert(e)
        return (self.getDrawById(id), msg)

    def updateDraw(self, id, e):
        self.normalizeSheetNumbers(e)
        self.dbUpdate(e, doc_ids=[id])
        self.drawsShown.discard(id)
        self.drawsStarted.discard(id)
        self.hashIsDirty = True
        return self.getDrawById(id)
        
    async def uploadAjax(self, request, verbose=False):
        reader = aiohttp.MultipartReader.from_response(request)
        fileName = None
        startTime = None
        autoDelete = "no"
        colour = "white"
        show = "no"
        atStart = "no"
        drawName = None

        msgs = []
        while True:
            part = await reader.next()
            if part is None:
                break

            text = await part.read()

            pn = part.name
            if verbose:
                print(f"{part.name=}")
                
            if pn == "defaultTime":
                startTime = text.decode("utf-8")
            elif pn == "defaultAutoDelete":
                autoDelete = text.decode("utf-8")
            elif pn == "defaultColour":
                colour = text.decode("utf-8")
            elif pn == "defaultShowDraw":
                show = text.decode("utf-8")
            elif pn == "defaultAtStart":
                atStart = text.decode("utf-8")
            elif pn == "drawName":
                tmp = text.decode("utf-8").strip()
                if tmp:
                    drawName = tmp
            elif pn == "excelFileUpload":
                if not part.filename:
                    continue
            
                ext = part.filename.rsplit(".", 1)[-1]
                if ext in ["csv", "xlsx", "xls", "pdf"]:
                    fileName = tempfile.mkstemp(suffix=f'_curlingtimer_schedule.{ext}', prefix='tmp', dir='/tmp')[1]

                    with open(fileName, "wb+") as f:
                        f.write(text)

        if verbose:
            print(f"{ext=} {startTime=} {autoDelete=} {colour=} {show=} {atStart=}")
            
        if fileName:
            if verbose:
                print(f"Extract {fileName=}")
                
            draws = extractDrawsFromFile(fileName, ext, startTime, autoDelete, colour, show, atStart)

            for draw in draws:
                await asyncio.sleep(0.001)
                draw, msg = self.addDraw(draw, drawName=drawName)
                if verbose:
                    print(f"add draw {draw}\n\t{msg}")
                    
                if msg:
                    msgs.append(msg)
                    
                if not draw:
                    continue

                msgs.append(f"added; {draw['name']} {draw['date']} {draw['time']}")

            msgs.sort()

            cleanFiles(fileName)

        return msgs

    def getHash(self):
        if self.hashIsDirty:
            self.hashIsDirty = False
            self.hashDrawDB = dbHasher.hash_file(self.fullPath)

        return self.hashDrawDB

    def getAllDraws(self):
        return self.dbAll()

    def getDrawById(self, id):
        if self.dbContains(doc_id=id):
            res = self.dbGet(doc_id=id)
            res["id"] = id
            return res
        else:
            return None

    def normalizeSheetNumbers(self, draw):
        if draw.get("normalized", False):
            return None

        msg = None
        sheets = draw["sheets"]
        nSheets = len(Config.display.sheets)
        
        norm = [{"team1": "", "team2": "", "sheet": i + 1} for i in range(nSheets)]

        nValid = sum(["sheet" in s and (isinstance(s["sheet"], int) or s["sheet"].isdigit()) and 1 <= int(s["sheet"]) <= nSheets for s in sheets])
        
        if nValid == len(sheets):
            for sheet in sheets:
                norm[toInt(sheet["sheet"], 1) - 1] = sheet
        else:
            for sheetNo, sheet in enumerate(sheets):
                sheet["sheet"] = sheetNo + 1
                try:
                    norm[sheetNo] = sheet
                except IndexError:
                    msg = "Too many sheets in draw"

        draw["sheets"] = norm
        draw["normalized"] = 1
        return msg

    def deleteDraw(self, id):
        if self.dbContains(doc_id=id):
            self.dbRemove(doc_ids=[id])
            self.hashIsDirty = True
            return True

        return False

    def writeCSV(self, fileName, draws=None):
        if draws is None:
            draws = self.getAllDraws()

        msg = None
        with open(fileName, "w", newline='') as csvFile:
            worksheet = csv.writer(csvFile)
            for draw in draws:
                msg = self.normalizeSheetNumbers(draw)
            
                worksheet.writerow([draw.get("date", "unknown"), draw.get("name", "unknown")])

                time = draw.get("time", "unknown")
                for s in draw["sheets"]:
                    worksheet.writerow([time, s["sheet"], s.get("team1", "team1"), s.get("team2", "team2")])
                    time = None

                worksheet.writerow(["show", draw.get("show", str(15))])
                worksheet.writerow(["colour", draw.get("colour", "white")])
                worksheet.writerow(["autoDelete", draw.get("autoDelete", str(48*60))])
                worksheet.writerow(["atStart", draw.get("atStart", "120")])
                worksheet.writerow([])

        return msg

    async def blankSheets(self, sheets):
        activeBlankTasks = []
        for sheet in sheets:
            sheetNo = toInt(sheet["sheet"], 1000000) - 1
            if sheetNo >= 0 and sheetNo < len(Config.display.sheets):
                sheetDisplay = Config.display.sheets[sheetNo]

                if sheetDisplay.ip == "Unassigned":
                    continue

                tkn = AccessVerification.tokenAuthenticator.create(expires=int(time.time()) + tokenValidTime, audience="peer")
                activeBlankTasks.append(postUrlJSONResponse("blankSheets",
                                                            f'{httpUtils.scheme}://{ sheetDisplay.ip}:{httpUtils.port}/blank',
                                                            jsonData={},
                                                            headers={CLOCK_HDR: tkn},
                                                            retries=3))
                info("Draw: blank %s", sheetDisplay.ip)
                

        await asyncio.wait(activeBlankTasks)
                
    async def startCountDownSheets(self, sheets, secsSinceDrawStart):
        gameTime = secondsToStr(max(0, strToSeconds(Config.display.defaults.gameTime) - secsSinceDrawStart))

        activeSetupTasks = []
        for sheet in sheets:
            sheetNo = toInt(sheet["sheet"], 1000000) - 1
            if sheetNo >= 0 and sheetNo < len(Config.display.sheets):
                sheetDisplay = Config.display.sheets[sheetNo]

                if sheetDisplay.ip == "Unassigned":
                    continue

                if sheet["team1"] or sheet["team2"]:
                    tkn = AccessVerification.tokenAuthenticator.create(expires=int(time.time()) + tokenValidTime, audience="peer")

                    activeSetupTasks.append(postUrlJSONResponse("draw/countdown/set",
                                                                f'{httpUtils.scheme}://{sheetDisplay.ip}:{ httpUtils.port}/countdown/set',
                                                                jsonData={"gameTime": gameTime,
                                                                          "finishedMessageColour": Config.display.defaults.finishedMessageColour,
                                                                          "finishedMessage": Config.display.defaults.finishedMessage,
                                                                          "lastEndMessage": Config.display.defaults.lastEndMessage,
                                                                          "lastEndMessageColour": Config.display.defaults.lastEndMessageColour
                                                                          },
                                                                headers={CLOCK_HDR: tkn},
                                                                retries=3))
                info("Draw: counttdaown set %s gameTime=%s",
                     sheetDisplay.ip,
                     gameTime)
                    

        await asyncio.wait(activeSetupTasks)

        activeStartTasks = []
        for sheet in sheets:
            sheetNo = toInt(sheet["sheet"], 1000000) - 1
            if sheetNo >= 0 and sheetNo < len(Config.display.sheets):
                sheetDisplay = Config.display.sheets[sheetNo]

                if sheetDisplay.ip == "Unassigned":
                    continue

                if sheet["team1"] or sheet["team2"]:
                    tkn = AccessVerification.tokenAuthenticator.create(expires=int(time.time()) + tokenValidTime, audience="peer")
                    activeStartTasks.append(postUrlJSONResponse("draw/countdown/start",
                                                                f'{httpUtils.scheme}://{sheetDisplay.ip}:{httpUtils.port}/countdown/start',
                                                                jsonData={},
                                                                headers={CLOCK_HDR: tkn},
                                                                retries=3))
                info("Draw: counttdown start %s", sheetDisplay.ip)
                
        await asyncio.wait(activeStartTasks)

    async def showTeams(self, colour, teamNamesBySheet, howLong=None, until=None):
        activeSetupTasks = []
        for sheet in teamNamesBySheet:
            sheetNo = toInt(sheet["sheet"], 1000000) - 1
            if sheetNo >= 0 and sheetNo < len(Config.display.sheets):
                sheetDisplay = Config.display.sheets[sheetNo]

                if sheetDisplay.ip == "Unassigned":
                    continue

                if sheet["team1"] or sheet["team2"]:
                    tkn = AccessVerification.tokenAuthenticator.create(expires=int(time.time()) + tokenValidTime, audience="peer")

                    activeSetupTasks.append(postUrlJSONResponse("draw/showTeams/set",
                                                                f'{httpUtils.scheme}://{sheetDisplay.ip}:{httpUtils.port}/teamnames/set',
                                                                jsonData={"team1": sheet["team1"],
                                                                          "team2": sheet["team2"],
                                                                          "colour": colour,
                                                                          },
                                                                headers={CLOCK_HDR: tkn},
                                                                retries=3))
                    info("Draw: show teams set %s '%s' '%s'", sheetDisplay.ip,  sheet["team1"],  sheet["team2"])

        await asyncio.wait(activeSetupTasks)

        activeStartTasks = []
        for sheet in teamNamesBySheet:
            sheetNo = toInt(sheet["sheet"], 1000000) - 1
            if sheetNo >= 0 and sheetNo < len(Config.display.sheets):
                sheetDisplay = Config.display.sheets[sheetNo]

                if sheetDisplay.ip == "Unassigned":
                    continue

                if sheet["team1"] or sheet["team2"]:
                    tkn = AccessVerification.tokenAuthenticator.create(expires=int(time.time()) + tokenValidTime, audience="peer")
                    activeStartTasks.append(postUrlJSONResponse("draw/showTeams/show",
                                                                f'{httpUtils.scheme}://{sheetDisplay.ip}:{httpUtils.port}/teamnames/show',
                                                                jsonData={"howLong": howLong,
                                                                          "until": until},
                                                                headers={CLOCK_HDR: tkn},
                                                                retries=3))
                    info("Draw: show teams show %s howLong=%s until=%s", sheetDisplay.ip,  howLong,  until)

        await asyncio.wait(activeStartTasks)

    def cleanAutoDeletes(self):
        deleteSet = set()
        drawsStarted = set()
        drawsShown = set()
        lclTime = int(time.time())
        
        for d in self.dbAll():
            docTime = time.mktime(time.strptime(d["date"] + ' ' + d["time"], "%Y-%m-%d %H:%M"))
            autoDelete = toInt(d.get("autoDelete", 14), 14)
                    
            secsSinceDraw = lclTime - docTime
            if isinstance(autoDelete, int) and secsSinceDraw > autoDelete * 24 * 60 * 60:
                deleteSet.add(d.doc_id)
            else:
                if d.doc_id in self.drawsStarted:
                    drawsStarted.add(d.doc_id)
                if d.doc_id in self.drawsShown:
                    drawsShown.add(d.doc_id)

        self.drawsStarted = drawsStarted
        self.drawsShown = drawsShown
        if deleteSet:
            self.dbRemove(doc_ids=list(deleteSet))
            self.hashIsDirty = True
        
    async def drawShowTask(self, app):
        lastDeleteCheckHour = None
        while True:
            try:
                await asyncio.sleep(1)

                entry = tinydb.Query()

                lclTime = int(time.time())
                localTime = time.localtime(lclTime)
                today = time.strftime("%Y-%m-%d", localTime)
                yesterday = time.strftime("%Y-%m-%d", time.localtime(lclTime - 24*60*60))
                tomorrow = time.strftime("%Y-%m-%d", time.localtime(lclTime + 24*60*60))
                
                if lastDeleteCheckHour != localTime.tm_hour:
                    lastDeleteCheckHour = localTime.tm_hour
                    self.cleanAutoDeletes()

                testDraws = self.dbSearch((entry.date == today) | (entry.date == yesterday) | (entry.date == tomorrow))
                for draw in testDraws:
                    show = toInt(draw.get("show", 0), 0) * 60
                    atStart = toInt(draw.get("atStart", "blank"))

                    drawTime = time.mktime(time.strptime(draw["date"] + ' ' + draw["time"], "%Y-%m-%d %H:%M"))
                    
                    secsToDrawStart = drawTime - lclTime

                    debug("Draw: check show=% atStart=%s drawTime=%s secsToDraw=%s",
                          show,
                          atStart,
                          drawTime,
                          secsToDrawStart)

                    if secsToDrawStart > 0:
                        if draw.doc_id not in self.drawsShown:
                            if show and secsToDrawStart < show:
                                info("Draw: check show teams drawTime=%s",
                                     drawTime)
                                     
                                await self.showTeams(draw["colour"], draw["sheets"], until=drawTime)
                                self.drawsShown.add(draw.doc_id)
                    elif secsToDrawStart <= 0:
                        if draw.doc_id not in self.drawsStarted:
                            self.drawsStarted.add(draw.doc_id)
                            if atStart == "countdown":
                                activeUntil = drawTime + strToSeconds(Config.display.defaults.gameTime) + strToSeconds(Config.display.defaults.blankTime)
                                info("Draw: countdown test activeUntil=%s lclTime=%s", activeUntil, lclTime)
                                if activeUntil > lclTime:
                                    info("Draw: countdown start secsToDrawStart=%s", -secsToDrawStart)
                                    await self.startCountDownSheets(draw["sheets"], -secsToDrawStart)
                            elif isinstance(atStart, int):
                                activeUntil = drawTime + atStart * 60
                                info("Draw: showTeams test activeUntil=%s lclTime=%s", activeUntil, lclTime)
                                if activeUntil > lclTime:
                                    info("Draw: showTeams activeUntil=%s", activeUntil)
                                    await self.showTeams(draw["colour"], draw["sheets"], until=activeUntil)
                            else:
                                blankAftr = drawTime + strToSeconds(Config.display.defaults.gameTime) + strToSeconds(Config.display.defaults.blankTime)
                                info("Draw: blank test blankAfter=%s lclTime=%s", blankUntil, lclTime)
                                if blankAfter > lclTime:
                                    info("Draw: blank")
                                    await self.blankSheets(draw["sheets"])
                                
            except asyncio.CancelledError:
                return
            except Exception as e:
                error("draw: show task %s", e, stack_info=True)

    async def startTasks(self, app):
        info("DrawManager: tasks - start")

        app['draw_monitor'] = asyncio.create_task(self.drawShowTask(app))

    async def stopTasks(self, app):
        if 'draw_monitor' in app:
            info("DrawManager: stop tasks - cancel")
            app['draw_monitor'].cancel()

            info("DrawManager: stop tasks - done")

            
def createDrawManager():
    global drawDB

    drawDB = DrawManager()
    return drawDB
