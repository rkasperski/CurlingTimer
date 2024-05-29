import sys
import re
from collections import namedtuple
import datetime
import Logger

import csv
import openpyxl
import xlrd
import pdfminer.high_level
from pdfminer.layout import LAParams, LTRect, LTPage, LTLine
from dateutil.parser import parse as date_parser


class Draw:
    def __init__(self, name, time, date, show, colour, autoDelete, atStart):
        self.name = name
        self.time = time
        self.date = date
        self.show = show
        self.colour = colour
        self.autoDelete = autoDelete
        self.atStart = atStart
        self.sheets = []

    def dump(self):
        print(f'name={self.name} date={self.date} time={self.time} colour={self.colour} show={self.show} autoDelete={self.autoDelete} atStart={self.atStart}')
        for s in self.sheets:
            print(f"    {s['sheet']:4} {s['team1']:20} {s['team2']:20}")

    def asDict(self):
        return {"name": self.name,
                "time": self.time,
                "date": self.date,
                "show": self.show,
                "colour": self.colour,
                "autoDelete": self.autoDelete,
                "atStart": self.atStart,
                "sheets": self.sheets}
    

def pdfTextBlobsToDraws(txtList, startTime, autoDelete, colour, show, atStart, verbose):
    reSheet1 = re.compile("(?P<time>\d+:\d\d(\s*(am|pm))?)?\s*(?P<sheet>\d+)\s+(?P<team1>[\w./ '\-]*)\s+vs\s+(?P<team2>[\w./ '\-]*)", re.I)
    reSheet2 = re.compile("(?P<date>(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)(\.|,)?\s*\d+(\s*,?\s*\d\d+)?)\s+(?P<sheet>\d+)\s+(?P<team1>[\w./ '\-]*)\s+vs\s+(?P<team2>[\w./ '\-]*)", re.I)
    reSheet3 = re.compile("(?P<date>(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)(\.|,)?\s*\d+\s+)?((w|l)\s)?(?P<team1>[\w./ '\-]*) (?P<sheet>\d+) (?P<team2>[\w./ '\-]*)( (w|l))?$", re.I)
    reDate = re.compile("(?P<date>(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)(\.|,)?\s*\d+(\s*,?\s*\d\d+)?)", re.I)
    name = "Unknown"
    draws = []

    if verbose:
        print("====== step 2 A =======")
        
    for txt in txtList:
        if verbose:
            print("--- blob ---")
            print(txt.replace("\n", "\\n"))
            print("---")
            print(txt)
            print("--- blob ---")

        if txt.lower().startswith("date"):
            continue

        sp = txt.split("\n")

        if len(sp) == 1:
            if name == "Unknown" or "league" in txt.lower():
                name = txt
            continue

        draw = Draw(None, startTime, None, show, colour, autoDelete, atStart)

        for ts in sp:
            ts = ts.strip()
            m = reSheet1.match(ts)
            if verbose >= 1:
                print(f"S {ts=} {m=}")
                if m:
                    print(f"    {m.groupdict()=}")

            if m:
                if verbose:
                    print(f"    1: {m.groupdict()=}")

                if m["time"]:
                    draw.time = m["time"]

                draw.sheets.append({"sheet": m["sheet"], "team1": m["team1"].strip(), "team2": m["team2"].strip()})
                continue

            m = reSheet2.match(ts)
            if m:
                if verbose:
                    print(f"    2: {m.groupdict()=}")

                if m["date"]:
                    if draw.sheets:
                        draws.append(draw)
                        draw = Draw(None, startTime, None, show, colour, autoDelete, atStart)

                    draw.date = m["date"]

                draw.sheets.append({"sheet": m["sheet"], "team1": m["team1"].strip(), "team2": m["team2"].strip()})
                continue

            m = reSheet3.match(ts)
            if m:
                if verbose:
                    print(f"    3: {m.groupdict()=}")

                draw.sheets.append({"sheet": m["sheet"], "team1": m["team1"].strip(), "team2": m["team2"].strip()})
                if m["date"]:
                    draw.date = m["date"]
                continue

            m = reDate.match(ts)
            if m:
                if draw.sheets:
                    draws.append(draw)
                    draw = Draw(None, startTime, None, show, colour, autoDelete, atStart)
                    
                draw.date = m["date"].replace('.', '')

                if verbose >= 1:
                    print(f"    D: {m.groups()=}")

            if verbose:
                print(f"D {ts=} {m=}")

        draws.append(draw)

    for d in draws:
        d.name = name

    return draws


def bidirectionalContains(a, b):
    # a is contained by b
    if a[1] >= b[1] and a[3] <= b[3]:
        return 1

    # b is contained by a
    if b[1] >= a[1] and b[3] <= a[3]:
        return 1

    return 0


class MyTxtLine:
    def __init__(self, src, column):
        self.txt = src.txt
        self.pgNo = src.pgNo
        self.bbox = src.bbox
        self.column = column

        
def extractTextBlobsFromPDF(fn, verbose=0):
    laparams = LAParams()
    laparams.line_margin = 0
    laparams.char_margin = 1
    laparams.boxes_flow = 0

    TxtLine = namedtuple('TxtLine', 'txt pgNo bbox')

    txtList = []
    with open(fn, 'rb') as fp:
        pages = pdfminer.high_level.extract_pages(fp, laparams=laparams)

        for pgNo, p in enumerate(pages):
            for t in p:
                if not isinstance(t, (LTRect, LTPage, LTLine)):
                    txt = t.get_text().strip()
                    txtList.append(TxtLine(txt, pgNo, t.bbox))

    minX = min([t.bbox[0] for t in txtList])
    maxX = max([t.bbox[2] for t in txtList])
    midPoint = (minX + maxX) / 2

    if verbose >= 2:
        print("====== step 1 A =======")
    
        print(f"{minX=}")
        print(f"{maxX=}")
        print(f"{midPoint=}")
        txtList.sort(key=lambda t: (t.pgNo, -t.bbox[1], t.bbox[0]))
        print(">>> page, -bbox.top left <<<")
        for t in txtList:
            print(t.pgNo, t.bbox, t.txt)

    def posToColumn(t):
        return 1 if t.bbox[0] > midPoint else 0

    txtList = [MyTxtLine(t, posToColumn(t)) for t in txtList]

    txtList.sort(key=lambda t: (t.column, t.pgNo, -t.bbox[1], t.bbox[0]))

    if verbose >= 2:
        print("====== step 1 B =======")
        print(">>> page, col -bbox.top left <<<")
        for t in txtList:
            print(t.pgNo, t.column, t.bbox, t.txt)

        print(f"{minX=}")
        print(f"{maxX=}")

    bottom = txtList[0].bbox[3]

    pc = txtList[0]
    blk = [pc]
    blocks = [blk]
    
    # merge text on the same line
    for c in txtList[1:]:
        if pc.pgNo == c.pgNo and bidirectionalContains(pc.bbox, c.bbox):
            blk.append(c)
        else:
            blk = [c]
            blocks.append(blk)

        pc = c

    if verbose >= 2:
        print("====== step 1 C =======")
        print("\n\n>>> block collections <<<")
        for i, b in enumerate(blocks):
            print(f">> {i=} <<")
            for t in b:
                print(t.bbox, t.txt)
            print()
    
    hMerge = []
    for blk in blocks:
        blk.sort(key=lambda t: t.bbox[0])
        c = TxtLine(' '.join([t.txt for t in blk]),
                    blk[0].pgNo,
                    (min([t.bbox[0] for t in blk]),
                     min([t.bbox[1] for t in blk]),
                     max([t.bbox[2] for t in blk]),
                     max([t.bbox[3] for t in blk])))
        hMerge.append(c)

    txtList = hMerge

    if verbose >= 2:
        print("====== step 1 D =======")
        print("\n\n>>> horizontal merge <<<")
        for t in txtList:
            print(t.bbox, t.txt)

    sumDiff = 0
    cntDiff = 0
    bottom = txtList[0].bbox[1]  # bottom of current item
    pgNo = txtList[0].pgNo
    sumLineHeight = txtList[0].bbox[3] - txtList[0].bbox[1]
    cntLineHeight = 1
    for txt in txtList[1:]:
        if pgNo == txt.pgNo:
            sumDiff += bottom - txt.bbox[3]
            cntDiff += 1
        else:
            pgNo = txt.pgNo

        bottom = txt.bbox[1]

        sumLineHeight += txt.bbox[3] - txt.bbox[1]
        cntLineHeight += 1

    averageLineSpace = sumDiff / cntDiff
    averageLineHeight = sumLineHeight / cntLineHeight

    if verbose >= 2:
        print("====== step 1 E =======")
        print(f"{averageLineSpace=}")
        print(f"{averageLineHeight=}")

        for t in txtList:
            print(t.pgNo, t.bbox, t.txt)

    vMerge = [txtList[0]]
    # merge text on the consecutive lines
    for i in range(1, len(txtList)):
        p = vMerge[-1]
        c = txtList[i]

        txt = c.txt.strip()

        if txt:
            if p.pgNo == c.pgNo:
                if c.bbox[3] + averageLineHeight - 1 >= p.bbox[1] and p.bbox[2] > c.bbox[0]:
                    vMerge[-1] = TxtLine(p.txt + '\n' + txt, p.pgNo, [min(p.bbox[0], c.bbox[0]), min(p.bbox[1], c.bbox[1]), max(p.bbox[2], c.bbox[2]), max(p.bbox[3], c.bbox[3])])
                else:
                    vMerge.append(c)
            else:
                # assume that text runs together accross pages
                vMerge[-1] = TxtLine(p.txt + '\n' + txt, c.pgNo, [min(p.bbox[0], c.bbox[0]), c.bbox[1], max(p.bbox[2], c.bbox[2]), c.bbox[3]])

    txtList = vMerge

    if verbose >= 2:
        print("====== step 1 E =======")
        for t in txtList:
            print()
            print(t.pgNo, t.bbox)
            print("-")
            print(t.txt)

    # gather into groups
    # a group is any
    return [t.txt.strip() for t in txtList]


def readPDF(fileName, startTime, autoDelete, colour, show, atStart, verbose=0):
    if verbose:
        print("====== step 1 =======")
    
    blobs = extractTextBlobsFromPDF(fileName, verbose)
    if verbose:
        print("====== step 2 =======")
    
    return pdfTextBlobsToDraws(blobs, startTime, autoDelete, colour, show, atStart, verbose=verbose)

reXLSDate = re.compile("(?P<date>((jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\.?\s*\d+,\s*\d\d\d*)|(\d\d\d\d-\d\d-\d\d))", re.I)
reTime = re.compile("(?P<time>\d+:\d\d\s*(am|pm)?)",re.I)


def gatherExcelDraw(wb_sheet, r, c, name, startTime, autoDelete, colour, show, atStart, verbose):
    row = wb_sheet[r]

    data = Draw(name, startTime, row[c].value.replace(".", " ").replace("  ", " "), show, colour, autoDelete, atStart)

    v1 = row[c + 1].value
    v2 = row[c + 2].value
    if v2 is None or (isinstance(v2, str) and v2.strip() == ""):
        if isinstance(v1, str) and v1.strip() != "":
            data.name = str(v1)

        r += 1

    sheetNo = 0
    while r < len(wb_sheet):
        sheetNo += 1
        row = wb_sheet[r]
        r += 1

        v0 = row[c].value
        v1 = row[c + 1].value
        v2 = row[c + 2].value

        if (not v2) and v0 is not None and isinstance(v0, str) and v1 is not None:
            v0l = v0.lower().replace('-', ' ').replace(' ', '')

            if (not isinstance(v1, str)) or v1:
                if v0l in ['start', "starttime", "time"]:
                    data.time = v1
                elif v0l in ["delete", "autodelete"]:
                    data.autoDelete = v1
                elif v0l in ["colour", "color"]:
                    data.colour = v1
                elif v0l in ["show", "showbefore"]:
                    data.show = v1
                elif v0l in ["clock", "startclock", "atstart"]:
                    data.atStart = v1

                continue

        if v2 is None or (isinstance(v2, str) and v2.strip() == ""):
            break

        if isinstance(v0, float):
            tv = 86400 * v0
            data.time = f"{int(tv / 3600)}:{int((tv % 3600) / 60):02}"
            
        elif isinstance(v0, str) and v0.strip():
            m = reTime.match(v0)
            if m:
                data.time = v0
        elif isinstance(v0, datetime.time):
            data.time = str(v0)

        sv = row[c + 1].value
        offset = 0
        sn = sheetNo
        if isinstance(sv, (int, float)) or (isinstance(sv, str) and sv.isdigit()):
            sn = int(sv)
            offset = 1

        if row[c + 2 + offset].value == "vs":
            t2 = row[c + offset + 3]
        else:
            t2 = row[c + offset + 2]

        data.sheets.append({"sheet": sn, "team1": row[c + 2].value.strip(), "team2": t2.value.strip()})

    return (r, data)


def inspectExcelSheet(wb_sheet, draws, startTime, autoDelete, colour, show, atStart, verbose):
    name = "Unknown"

    firstRow = list(filter(lambda s: s.value, wb_sheet[0]))
    name = ' - '.join([v.value for v in firstRow])

    r = 0
    nextR = 0
    while nextR < len(wb_sheet):
        r = nextR
        nextR += 1

        row = wb_sheet[r]

        for c, v in enumerate(row):
            if isinstance(v.value, str):
                if reXLSDate.match(v.value):
                    if verbose:
                        print("found start date:", v.value)
                    nr, draw = gatherExcelDraw(wb_sheet, r, c, name, startTime, autoDelete, colour, show, atStart, verbose=verbose)
                    draws.append(draw)

                    nextR = max(nextR, nr)


ExcelValue = namedtuple('ExcelValue', 'value')


def readCSV(fileName, startTime, autoDelete, colour, show, atStart, verbose=0):
    draws = []
    with open(fileName) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')

        rows = []
        for row in csv_reader:
            rows.append([ExcelValue(v) for v in row])

    inspectExcelSheet(rows, draws, startTime, autoDelete, colour, show, atStart, verbose=verbose, )

    return draws


def readXLS(fileName, startTime, autoDelete, colour, show, atStart, verbose=0):
    wb = xlrd.open_workbook(fileName)

    draws = []

    for wix in range(0, wb.nsheets):
        wb_sheet = wb.sheet_by_index(wix)

        rows = []
        for r in range(wb_sheet.nrows):
            rows.append(wb_sheet[r])

        inspectExcelSheet(rows, draws, startTime, autoDelete, colour, show,  atStart, verbose=verbose)

    return draws


def readXLSX(fileName, startTime, autoDelete, colour, show, atStart, verbose=0):
    wb = openpyxl.load_workbook(fileName)

    draws = []

    for wb_sheet in wb.worksheets:
        rows = []
        for r in wb_sheet:
            rows.append(r)

        inspectExcelSheet(rows, draws, startTime, autoDelete, colour, show, atStart, verbose=verbose)

    return draws


def extractDrawsFromFile(fileName, ext, startTime=None, autoDelete=2880, colour="white", show="15", atStart="yes", verbose=0):
    if ext == "csv":
        draws = readCSV(fileName, startTime, autoDelete, colour, show, atStart, verbose=verbose)
    elif ext in ["xlsx"]:
        draws = readXLSX(fileName, startTime, autoDelete, colour, show, atStart, verbose=verbose)
    elif ext in ["xls"]:
        draws =  readXLS(fileName, startTime, autoDelete, colour, show, atStart, verbose=verbose)
    elif ext == "pdf":
        draws = readPDF(fileName, startTime, autoDelete, colour, show, atStart, verbose=verbose)
    else:
        return []

    if verbose > 1:
        print(">>> before date normalization <<<")
        for draw in draws:
            draw.dump()
            
    # normalize times and dates
    for draw in draws:
        try:
            d = date_parser(draw.date)
        except TypeError:
            Logger.warning("ExtractDrawFromFile: name=%s date=%s time=%s colour=%s show=%s autoDelete=%s atStart=%s",
                           draw.name, draw.date, draw.time, draw.colour, draw.show, draw.autoDelete, draw.atStart)
            if verbose:
                draw.dump()
            continue
            
        nd = d.strftime("%Y-%m-%d")
        draw.date = nd

        ts = draw.time
        if ts:
            t = date_parser(ts)
            nt = t.strftime("%-H:%M")
            draw.time = nt

    return draws


if __name__ == "__main__":
    args = sys.argv[1:]

    verbose = 0
    while args[0] == "-v":
        verbose += 1
        args.pop(0)

    for fn in args:
        print()
        print()
        print(f"=== {fn} ===")
        draws = extractDrawsFromFile(fn, fn.rsplit(".")[-1], verbose=verbose)

        draws.sort(key=lambda d: d.date if d.date else "")
        for draw in draws:
            draw.dump()
