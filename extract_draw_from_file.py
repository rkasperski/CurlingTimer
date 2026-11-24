import sys
import re
from collections import namedtuple
import datetime

import csv
import openpyxl
import xlrd
import pdfminer.high_level
from pdfminer.layout import LAParams, LTRect, LTPage, LTLine
from dateutil.parser import parse as date_parser
from logger import warning


class Draw:
    def __init__(self, name, time, date, show, colour, auto_delete, at_start):
        self.name = name
        self._time = time
        self.time_set = False
        self._date = date
        self.date_set = False
        self.show = show
        self.colour = colour
        self.auto_delete = auto_delete
        self.at_start = at_start
        self.sheets = []

    @property
    def time(self):
        return self._time

    @time.setter
    def time(self, value):
        self._time = value
        self.time_set = True
        
    @property
    def date(self):
        return self._date

    @date.setter
    def date(self, value):
        self._date = value
        self.date_set = True

    def dump(self, file=sys.stdout):
        print(f'name={self.name} date={self.date} time={self.time} colour={self.colour} show={self.show} autoDelete={self.auto_delete} atStart={self.at_start}', file=file)
        for s in self.sheets:
            print(f"    {s['sheet']:4} {s['team1']:20} {s['team2']:20}", file=file)

    def as_dict(self):
        return {"name": self.name,
                "time": self._time,
                "date": self._date,
                "show": self.show,
                "colour": self.colour,
                "autoDelete": self.auto_delete,
                "atStart": self.at_start,
                "sheets": self.sheets}
    

def pdf_text_blobs_to_draws(txt_list, start_time, auto_delete, colour, show, at_start, verbose):
    re_time_sheet_teams = re.compile(r"(?P<time>\d+:\d\d(\s*(am|pm))?)?\s*(?P<sheet>\d+)\s+(?P<team1>[\w./ '\-]*)\s+vs\s+(?P<team2>[\w./ '\-]*)( (w|l))?$", re.I)
    re_date_sheet_teams = re.compile(r"(?P<date>(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)(\.|,)?\s*\d+(\s*,?\s*\d\d+)?)\s+(?P<sheet>\d+)\s+(?P<team1>[\w./ '\-]*)\s+vs\s+(?P<team2>[\w./ '\-]*)( (w|l))?$", re.I)
    re_date_team_sheet_team = re.compile(r"(?P<date>(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)(\.|,)?\s*\d+\s+)?((w|l)\s)?(?P<team1>[\w./ '\-]*) (?P<sheet>\d+) (?P<team2>[\w./ '\-]*)( (w|l))?$", re.I)
    re_date = re.compile(r"(?P<date>(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)(\.|,)?\s*\d+(\s*,?\s*\d\d+)?)", re.I)
    name = "Unknown"
    draws = []

    if verbose:
        print("====== step 2 A =======")
        
    for txt in txt_list:
        if verbose:
            print("--- blob start ---")
            print(txt.replace("\n", "\\n"))
            print("---")
            print(txt)
            print("--- blob end ---")

        sp = txt.split("\n")
        if sp[0].lower().startswith("date"):
            del sp[0]

        if len(sp) == 1:
            if name == "Unknown" or "league" in txt.lower():
                name = txt
            continue

        draw = Draw(None, start_time, None, show, colour, auto_delete, at_start)

        for ts in sp:
            ts = ts.strip()
            if verbose >= 1:
                print(f"S {ts=}")
                
            if m := re_time_sheet_teams.match(ts):
                if verbose:
                    print(f"    1: {m.groupdict()=}")

                if m["time"]:
                    if draw.time_set:
                        first_draw = draw
                        draws.append(draw)

                        draw = Draw(None, start_time, None, show, colour, auto_delete, at_start)
                        if first_draw.date_set:
                            draw.date = first_draw.date

                    draw.time = m["time"]

                draw.sheets.append({"sheet": m["sheet"], "team1": m["team1"].strip(), "team2": m["team2"].strip()})
                continue

            if m := re_date_sheet_teams.match(ts):
                if verbose:
                    print(f"    2: {m.groupdict()=}")

                if m["date"]:
                    if draw.sheets:
                        draws.append(draw)
                        draw = Draw(None, start_time, None, show, colour, auto_delete, at_start)

                    draw.date = m["date"]

                draw.sheets.append({"sheet": m["sheet"], "team1": m["team1"].strip(), "team2": m["team2"].strip()})
                continue

            if m := re_date_team_sheet_team.match(ts):
                if verbose:
                    print(f"    3: {m.groupdict()=}")

                draw.sheets.append({"sheet": m["sheet"], "team1": m["team1"].strip(), "team2": m["team2"].strip()})
                if m["date"]:
                    draw.date = m["date"]
                continue

            if m := re_date.match(ts):
                if draw.sheets:
                    draws.append(draw)
                    draw = Draw(None, start_time, None, show, colour, auto_delete, at_start)
                    
                draw.date = m["date"].replace('.', '')

                if verbose >= 1:
                    print(f"    D: {m.groups()=}")

            if verbose:
                print(f"D {ts=} {m=}")

        draws.append(draw)

    for d in draws:
        d.name = name

    return draws


def bidirectional_contains(a, b):
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
        self.pg_no = src.pg_no
        self.bbox = src.bbox
        self.column = column

def normBox(box):
    return [round(d) for d in box]
        
def pdf_extract_text_blobs(fn, verbose=0):
    laparams = LAParams()
    laparams.line_margin = 0
    laparams.char_margin = 0.5
    laparams.boxes_flow = 0

    TxtLine = namedtuple('TxtLine', 'txt pg_no bbox')

    txt_list = []
    with open(fn, 'rb') as fp:
        pages = pdfminer.high_level.extract_pages(fp, laparams=laparams)

        for pg_no, p in enumerate(pages):
            for t in p:
                if not isinstance(t, (LTRect, LTPage, LTLine)):
                    txt = t.get_text().strip()
                    txt_list.append(TxtLine(txt, pg_no, normBox(t.bbox)))

    min_x = min(t.bbox[0] for t in txt_list)
    max_x = max(t.bbox[2] for t in txt_list)
    mid_point = (min_x + max_x) / 2

    if verbose >= 2:
        print("====== step 1 A =======")
    
        print(f"{min_x=}")
        print(f"{max_x=}")
        print(f"{mid_point=}")
        txt_list.sort(key=lambda t: (t.pg_no, -t.bbox[3], t.bbox[0]))
        print(">>> page, -bbox.top left <<<")
        print_top = None
        for t in txt_list:
            if print_top is not None and print_top != t.bbox[3]:
                print()

            print_top = t.bbox[3]
            print(t.pg_no, t.bbox, t.txt)

    def pos_to_column(t):
        return 1 if t.bbox[0] > mid_point else 0

    txt_list = [MyTxtLine(t, pos_to_column(t)) for t in txt_list]

    txt_list.sort(key=lambda t: (t.column, t.pg_no, -t.bbox[3], t.bbox[0]))

    if verbose >= 2:
        print("====== step 1 B =======")
        print(">>> page, col -bbox.top left <<<")
        for t in txt_list:
            print(t.pg_no, t.column, t.bbox, t.txt)

        print(f"{min_x=}")
        print(f"{max_x=}")

    bottom = txt_list[0].bbox[3]

    pc = txt_list[0]
    blk = [pc]
    blocks = [blk]
    
    # merge text on the same line
    for c in txt_list[1:]:
        if pc.pg_no == c.pg_no and bidirectional_contains(pc.bbox, c.bbox):
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
    
    horizontal_merge = []
    for blk in blocks:
        blk.sort(key=lambda t: t.bbox[0])
        c = TxtLine(' '.join(t.txt for t in blk),
                    blk[0].pg_no,
                    (min(t.bbox[0] for t in blk),
                     min(t.bbox[1] for t in blk),
                     max(t.bbox[2] for t in blk),
                     max(t.bbox[3] for t in blk)))
        horizontal_merge.append(c)

    txt_list = horizontal_merge

    if verbose >= 2:
        print("====== step 1 D =======")
        print("\n\n>>> horizontal merge <<<")
        for t in txt_list:
            print(t.bbox, t.txt)

    sum_diff = 0
    cnt_diff = 0
    bottom = txt_list[0].bbox[1]  # bottom of current item
    pg_no = txt_list[0].pg_no
    sum_line_height = txt_list[0].bbox[3] - txt_list[0].bbox[1]
    cnt_line_height = 1
    for txt in txt_list[1:]:
        if pg_no == txt.pg_no:
            sum_diff += bottom - txt.bbox[3]
            cnt_diff += 1
        else:
            pg_no = txt.pg_no

        bottom = txt.bbox[1]

        sum_line_height += txt.bbox[3] - txt.bbox[1]
        cnt_line_height += 1

    average_line_space = sum_diff / cnt_diff
    average_line_height = sum_line_height / cnt_line_height

    if verbose >= 2:
        print("====== step 1 E =======")
        print(f"{average_line_space=}")
        print(f"{average_line_height=}")

        for t in txt_list:
            print(t.pg_no, t.bbox, t.txt)

    vertical_merge = [txt_list[0]]
    # merge text on the consecutive lines
    for i in range(1, len(txt_list)):
        p = vertical_merge[-1]
        c = txt_list[i]

        txt = c.txt.strip()

        if txt:
            if p.pg_no == c.pg_no:
                if c.bbox[3] + average_line_height - 1 >= p.bbox[1] and p.bbox[2] > c.bbox[0]:
                    vertical_merge[-1] = TxtLine(p.txt + '\n' + txt, p.pg_no, [min(p.bbox[0], c.bbox[0]), min(p.bbox[1], c.bbox[1]), max(p.bbox[2], c.bbox[2]), max(p.bbox[3], c.bbox[3])])
                else:
                    vertical_merge.append(c)
            else:
                # assume that text runs together accross pages
                vertical_merge[-1] = TxtLine(p.txt + '\n' + txt, c.pg_no, [min(p.bbox[0], c.bbox[0]), c.bbox[1], max(p.bbox[2], c.bbox[2]), c.bbox[3]])

    txt_list = vertical_merge

    if verbose >= 2:
        print("====== step 1 F =======")
        for t in txt_list:
            print()
            print(t.pg_no, t.bbox)
            print("-")
            print(t.txt)

    # gather into groups
    # a group is any
    return [t.txt.strip() for t in txt_list]


def read_pdf(file_name, start_time, auto_delete, colour, show, at_start, verbose=0):
    if verbose:
        print("====== step 1 =======")
    
    blobs = pdf_extract_text_blobs(file_name, verbose)
    if verbose:
        print("====== step 2 =======")
    
    return pdf_text_blobs_to_draws(blobs, start_time, auto_delete, colour, show, at_start, verbose=verbose)

re_xls_date = re.compile(r"(?P<date>((jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\.?\s*\d+,\s*\d\d\d*)|(\d\d\d\d-\d\d-\d\d))", re.I)
re_time = re.compile(r"(?P<time>\d+:\d\d\s*(am|pm)?)",re.I)


def gather_excel_draw(wb_sheet, r, c, name, start_time, auto_delete, colour, show, at_start, verbose):
    row = wb_sheet[r]

    data = Draw(name, start_time, row[c].value.replace(".", " ").replace("  ", " "), show, colour, auto_delete, at_start)

    v1 = row[c + 1].value
    v2 = row[c + 2].value
    if v2 is None or (isinstance(v2, str) and v2.strip() == ""):
        if isinstance(v1, str) and v1.strip() != "":
            data.name = str(v1)

        r += 1

    sheet_no = 0
    while r < len(wb_sheet):
        sheet_no += 1
        row = wb_sheet[r]
        r += 1

        if verbose >= 2:
            print("---")
            for cell in row:
                print(cell, cell.value, isinstance(cell.value, str))

        v0 = row[c].value
        v1 = row[c + 1].value
        v2 = row[c + 2].value
        v1s = str(row[c + 1].value).strip()
        v2s = str(row[c + 2].value).strip()

        #print(f"{v0=}:{type(v0)} {v1=}:{type(v1)}:{v1s} {v2=}:{type(v2)}:{v2s}")
        if (not v2) and (v0 is not None and isinstance(v0, str) and v1s):
            #print("set {v0}='{v1s}'")
            v0l = v0.lower().replace('-', ' ').replace(' ', '')

            if v1s:
                if v0l in ['start', "starttime", "time"]:
                    data.time = v1s
                elif v0l in ["delete", "autodelete"]:
                    data.auto_delete = v1s
                elif v0l in ["colour", "color"]:
                    data.colour = v1s
                elif v0l in ["show", "showbefore"]:
                    data.show = v1s
                elif v0l in ["clock", "startclock", "atstart"]:
                    data.at_start = v1s

                continue

        if v1 is None or (isinstance(v1, str) and v1.strip() == ""):
            break

        if v2 is None or (isinstance(v2, str) and v2.strip() == ""):
            continue

        if len(row) < c + 3:
            continue

        if isinstance(v0, float):
            tv = 86400 * v0
            data.time = f"{int(tv / 3600)}:{int((tv % 3600) / 60):02}"
            
        elif isinstance(v0, str) and v0.strip():
            m = re_time.match(v0)
            if m:
                data.time = v0
        elif isinstance(v0, datetime.time):
            data.time = str(v0)

        sv = row[c + 1].value
        offset = 0
        sn = sheet_no
        if isinstance(sv, (int, float)) or (isinstance(sv, str) and sv.isdigit()):
            sn = int(sv)
            offset = 1

        if row[c + 2 + offset].value == "vs":
            t2 = row[c + offset + 3]
        else:
            t2 = row[c + offset + 2]

        data.sheets.append({"sheet": sn, "team1": row[c + offset + 1].value.strip(), "team2": t2.value.strip()})

    return (r, data)


def inspect_excel_sheet(wb_sheet, draws, start_time, auto_delete, colour, show, at_start, verbose):
    name = "Unknown"

    first_row = list(filter(lambda s: s.value, wb_sheet[0]))
    name = ' - '.join([v.value for v in first_row])

    r = 0
    next_row = 0
    while next_row < len(wb_sheet):
        r = next_row
        next_row += 1

        row = wb_sheet[r]

        if verbose >= 2:
            print("===")
            for cell in row:
                print(cell, cell.value, isinstance(cell.value, str))

        for c, v in enumerate(row):
            if isinstance(v.value, str):
                if re_xls_date.match(v.value):
                    if verbose:
                        print("found start date:", v.value)
                    nr, draw = gather_excel_draw(wb_sheet, r, c, name, start_time, auto_delete, colour, show, at_start, verbose=verbose)
                    draws.append(draw)

                    next_row = max(next_row, nr)


ExcelValue = namedtuple('ExcelValue', 'value')


def read_csv(file_name, start_time, auto_delete, colour, show, at_start, verbose=0):
    draws = []
    with open(file_name) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')

        rows = []
        for row in csv_reader:
            rows.append([ExcelValue(v) for v in row])

    inspect_excel_sheet(rows, draws, start_time, auto_delete, colour, show, at_start, verbose=verbose, )

    return draws


def read_xls(file_name, start_time, auto_delete, colour, show, at_start, verbose=0):
    wb = xlrd.open_workbook(file_name)

    draws = []

    for wix in range(0, wb.nsheets):
        wb_sheet = wb.sheet_by_index(wix)

        rows = []
        for r in range(wb_sheet.nrows):
            rows.append(wb_sheet[r])

        inspect_excel_sheet(rows, draws, start_time, auto_delete, colour, show,  at_start, verbose=verbose)

    return draws


def read_xlsx(file_name, start_time, auto_delete, colour, show, at_start, verbose=0):
    wb = openpyxl.load_workbook(file_name)

    draws = []

    for wb_sheet in wb.worksheets:
        rows = []
        for r in wb_sheet:
            rows.append(r)

        inspect_excel_sheet(rows, draws, start_time, auto_delete, colour, show, at_start, verbose=verbose)

    return draws


def extract_draws_from_file(file_name, ext, start_time=None, auto_delete=2880, colour="white", show="15", at_start="yes", default_year=None, verbose=0):
    if ext == "csv":
        draws = read_csv(file_name, start_time, auto_delete, colour, show, at_start, verbose=verbose)
    elif ext in ["xlsx"]:
        draws = read_xlsx(file_name, start_time, auto_delete, colour, show, at_start, verbose=verbose)
    elif ext in ["xls"]:
        draws =  read_xls(file_name, start_time, auto_delete, colour, show, at_start, verbose=verbose)
    elif ext == "pdf":
        draws = read_pdf(file_name, start_time, auto_delete, colour, show, at_start, verbose=verbose)
    else:
        return []

    if verbose > 1:
        print(">>> before date normalization <<<")
        for draw in draws:
            draw.dump()

    rDraws = []
    # normalize times and dates
    for draw in draws:
        #print(draw.date, draw.time, len(draw.sheets))

        if draw.date is None and draw.time is None and len(draw.sheets) == 0:
            continue

        try:
            if ', ' not in draw.date:
                draw.date = ", ".join(draw.date.rsplit(",", 1))
            d = date_parser(draw.date, default=default_year)
            #print(f"{d=} {draw.date=} {default_year=}")
        except TypeError:
            warning("ExtractDrawFromFile: name=%s date=%s time=%s colour=%s show=%s auto_delete=%s at_start=%s",
                    draw.name, draw.date, draw.time, draw.colour, draw.show, draw.auto_delete, draw.at_start)
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

        rDraws.append(draw)

    return rDraws


def main():
    import os
    import argparse
    import filecmp

    parser = argparse.ArgumentParser()

    parser.add_argument("-t", "--test", action="store_true",
                        help="run in test mode. The default year is 2025")

    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity level")

    parser.add_argument("-q", "--quiet", action="count", default=0, help="only show mismatches")

    parser.add_argument("file", nargs="+")

    args = parser.parse_args();

    verbose = args.verbose
    quiet = args.quiet
    test_mode = args.test

    default_year = datetime.datetime(2025, 1, 1) if test_mode else None

    print("in test mode the default year is 2025")

    for fn in args.file:
        ext = fn.rsplit(".")[-1]

        if ext in ["test", "verified"]:
            continue

        if verbose:
            print()
            print()
            print()
            print(f">>> {fn} <<<")

        if test_mode:
            draws = extract_draws_from_file(fn, ext, verbose=verbose, default_year=default_year)
            draws.sort(key=lambda d: d.date if d.date else "")
            test_filename = f"{fn}.test"
            with open(test_filename, "w") as f:
                for draw in draws:
                    draw.dump(f)

            result_filename = f"{fn}.verified"

            if os.path.exists(result_filename):
                is_the_same = filecmp.cmp(result_filename, test_filename)
                if quiet:
                    if not is_the_same:
                        print(f"{fn}: {'matches' if is_the_same else 'differs'}")
                else:
                     print(f"{fn}: {'matches' if is_the_same else 'differs'}")

                if is_the_same:
                    os.remove(test_filename)
            else:
                print(f"{fn}: missing verified version")
        else:
            print()
            print()
            print(f"=== {fn} ===")

            draws = extract_draws_from_file(fn, fn.rsplit(".")[-1], verbose=verbose)
            draws.sort(key=lambda d: d.date if d.date else "")
            for draw in draws:
                draw.dump()


if __name__ == "__main__":
    main()
