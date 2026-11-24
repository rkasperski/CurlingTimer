import time
import asyncio
import re

from fancy_text import BaseFont, FancyText, FancyTextSegment

def never_idle():
    return False

class BaseDisplay:
    required_colours = (("red", (255, 0, 0)),
                        ("cyan", (0, 255, 255)),
                        ("yellow", (255, 255, 0)),
                        ("white", (255, 255, 255)),
                        ("black", (0, 0, 0)),
                        ("green", (0, 255, 0)),
                        ("pink", (255, 153, 153)),
                        ("orange", (255, 95, 31)),
                        ("blue", (120, 120, 255)),
                        ("purple", (255, 0, 255)),
                        )

    def __init__(self):
        self.set_colours()
        self.colour_cache = {}
        self.font_id = 0
        self.last_display = ""
        self.first_time = True
        self.splash_colour = None
        self.sequence_number = 0
        self.break_times = []

        self.scroll_delay = 0.0500
        self.scroll_amount = 1

        self.set_colours()
        self.colour_cache = {}
        self.is_idle = never_idle
        self.hardware_config = None

        self.pos = 1
        self.mirrored = False

        self.leading_one_adjust = (0, 0)
        self.colon_adjust = (0, 0)

        self.white = (255, 255, 255)
        self.soft_white = (180, 180, 180)
        self.width = 1024
        self.height = 720

        self.timer_font = None
        self.timer_font_offset = 0
        self.small_font = None
        self.two_line_font = None
        self.two_time_font = None
        self.clock_font = None
        self.seconds_font = None
        self.text_font = None
        self.timer_font_vertical_offset = 0
        self.two_time_display_vertical_offset = 0

    def get_colours(self):
        return list(self.colours.items())

    def set_colours(self, colours=None):
        self.colour_cache = {}

        self.colours = {}
        if colours is not None:
            for n, rgb in colours:
                self.colours[re.sub(r"\W*", "", n.lower())] = rgb

        for n, rgb in self.required_colours:
            if n not in self.colours:
                self.colours[n] = rgb

    def abort(self):
        self.sequence_number += 1

    def set_is_idle(self, is_idle):
        self.is_idle = is_idle

    def show(self, drawable):
        pass

    def two_time_display(self, display_time1 , colour1, display_time2, colour2):
        self.sequence_number += 1

        cur_display = f"{colour1}:{display_time1}:{colour2}:{display_time2}"

        if self.last_display == cur_display:
            return

        self.last_display = cur_display

        drawable = self.get_cleared_drawable()

        w1, h1 = self.two_time_font.get_size(display_time1)
        w2, h2 = self.two_time_font.get_size(display_time2)

        wmax = max(w1, w2)
        xoffset = int((self.width - wmax) / 2)
        xend = xoffset + wmax

        drawable.draw_text(self.two_time_font,
                           xend - w1,
                           self.height * 0.50 + self.two_time_display_vertical_offset,
                           display_time1, colour1)
        drawable.draw_text(self.two_time_font,
                           xend - w2,
                           self.height * 1 + self.two_time_display_vertical_offset,
                           display_time2, colour2)

        self.show(drawable)

    async def display_team_names(self, team1, colour1, team2, colour2, scroll_teams_separator=None):
        if scroll_teams_separator:
            separator_colour = self.map_colour("white") if colour1 != colour2 else self.map_colour("yellow")
            ft = FancyText(self.width,
                           FancyTextSegment(team1, self.text_font, self.map_colour(colour1)),
                           FancyTextSegment(f" {scroll_teams_separator} ", self.two_line_font, separator_colour),
                           FancyTextSegment(team2, self.text_font, self.map_colour(colour2)))
            return await self.display_scrolling_text(ft)

        return await self.two_line_text(team1, team2, colour1=colour1, colour2=colour2, centre=True)

    def set_splash_colour(self, colour="white"):
        self.sequence_number += 1
        self.splash_colour = self.colours.get(colour, (255, 255, 255)) if isinstance(colour, str) else colour

    def display_splash_colour(self, colour=None):
        if colour is None:
            colour = "white" if self.splash_colour is None else self.splash_colour

        colour = self.map_colour(colour)

        self.sequence_number += 1

        drawable = self.get_cleared_drawable()
        drawable.draw_rect(0, 0 , self.width, self.height, fill_colour=colour)
        self.show(drawable)

    def update_timer(self, display_time, colour, prefix, show_tenths=False):
        cur_display = prefix + display_time

        if self.last_display == cur_display:
            return

        self.last_display = cur_display

        font = self.timer_font

        drawable = self.get_cleared_drawable()

        if show_tenths:
            display_time, tenths = display_time.rsplit(".", 1)
            y = font.ascender
        else:
            y = font.ascender + int((self.height - font.ascender) / 2) + self.timer_font_vertical_offset

        adjustment = self.leading_one_adjust if display_time[0] == "1" else (0, 0)

        colon_adjustment = sum(self.colon_adjust) * display_time.count(":")

        width_display_time, _ = font.get_size(display_time)

        width_display_time -= sum(adjustment) + colon_adjustment
        pos = max(0, int((self.width - width_display_time) / 2)) - 1

        for c in display_time:
            if c == ":":
                adjustment = self.colon_adjust

            pos -= adjustment[0]

            drawable.draw_text(font, pos, y, c, colour)
            cwidth = self.timer_font.get_size(c)[0]
            pos += cwidth - adjustment[1]

            adjustment = (0, 0)

        if show_tenths:
            sz_seconds = self.seconds_font.get_size(tenths)

            drawable.draw_text(self.seconds_font, pos - sz_seconds[0] - int((cwidth - sz_seconds[0])/ 2), y +  self.seconds_font.ascender, tenths, colour)

        self.show(drawable)

    async def display_scrolling_text(self, my_text, colour="white", start_time=None, two_line_ok=False, display_time=0):
        canvas_width = self.width
        text_colour = self.map_colour(colour)

        if two_line_ok and isinstance(my_text, str):
            sp = my_text.split(" ")
            if len(sp) == 2:
                text_len0, text_height0 = self.two_line_font.get_size(sp[0])
                text_len1, text_height1 = self.two_line_font.get_size(sp[1])
                if text_len0 < canvas_width and text_len1 < canvas_width:
                    return await self.two_line_text(sp[0], sp[1], colour=text_colour, centre=True,
                                                    display_time=display_time, start_time=start_time)

        self.sequence_number += 1

        if isinstance(my_text, str):
            ft = FancyText(self.width, FancyTextSegment(my_text.strip(), self.text_font, text_colour))
        else:
            ft = my_text

        self.last_display = ft.signature()

        length_ft, height_ft = ft.get_size()

        y_offset = int((self.height - height_ft) / 2)

        cur_sequence_number = self.sequence_number
        if not start_time:
            start_time = time.monotonic()

        end_time = start_time + display_time

        drawable = self.get_cleared_drawable()
        if length_ft < canvas_width:
            ft.draw(drawable, (int((canvas_width - length_ft) / 2), y_offset))
            self.show(drawable)

            while cur_sequence_number == self.sequence_number and not self.is_idle():
                if display_time and time.monotonic() >= end_time:
                    return True

                await asyncio.sleep(0.005)

            return False

        scroll_length = length_ft + canvas_width
        scroll_count = 1

        while cur_sequence_number == self.sequence_number and not self.is_idle():
            next_time = start_time + self.scroll_delay * scroll_count

            cur_time = time.monotonic()
            if display_time and  cur_time > end_time:
                return True

            scroll_count += 1
            time_diff = int((time.monotonic() - start_time) * self.scroll_amount / self.scroll_delay) % scroll_length

            drawable.start(clear=True)
            ft.draw(drawable, (-time_diff + canvas_width, y_offset))
            self.show(drawable)

            while time.monotonic() < next_time and cur_sequence_number == self.sequence_number:
                await asyncio.sleep(0.005)

        return False

    async def display_flash_text(self, my_text, colour="white", delay=1.0, display_count=1000, length=5.0):
        self.sequence_number += 1

        my_text = my_text.rstrip()
        self.last_display = "ft:" + my_text

        cur_sequence_number = self.sequence_number
        displayed = None
        start_time = time.monotonic()

        while display_count > 0 and cur_sequence_number == self.sequence_number and not self.is_idle():
            cur_time = time.monotonic()

            showing = (int((cur_time - start_time) / delay) % 2) == 1
            if displayed != showing:
                displayed = showing

                if displayed:
                    display_count -= 1
                    self.display_text(my_text, colour, centre=True, sequence_update=False)
                else:
                    drawable = self.get_cleared_drawable()
                    self.show(drawable)

            await asyncio.sleep(0.05)        

    def blank(self):
        self.sequence_number += 1
        self.last_display = "blank:"
        drawable = self.get_cleared_drawable()
        self.show(drawable)
        return 0.25

    def find_font(self, text_list, font_list):
        for f in font_list:
            fits = True
            for l in text_list:
                text_len, text_height = f.get_size(l)
                if text_len > self.width:
                    fits = False

            if fits:
                return f

        return font_list[-1]

    def display_text(self, text, colour="white", centre=False, sequence_update=True):
        text = text.rstrip()
        if sequence_update:
            self.sequence_number += 1
            self.last_display = "dt:" + text

        text_colour = self.map_colour(colour)

        if '\n' in text:
            lines = text.split('\n', 1)
        else:
            lines = [text]

        display_font = self.find_font(lines, [self.timer_font, self.text_font, self.small_font])

        if display_font == self.small_font and len(lines) == 1:
            width = 0
            for i in range(len(text)):
                text_len, text_height = display_font.get_size(text[0: i])
                if text_len > self.width:
                    lines = [text[0:i - 1], text[i - 1:]]
                    break

        drawable = self.get_cleared_drawable()
        vpos = 0
        for text in lines:
            text_len, text_height = display_font.get_size(text)
            vpos += display_font.height
            if centre:
                hpos = int(max(0, (self.width - text_len) / 2))
            else:
                hpos = 0

            drawable.draw_text(display_font, hpos, vpos, text, text_colour)

        self.show(drawable)

    async def two_line_text(self, line1, line2, colour=None, colour1="white", colour2="white", centre=False, start_time=None, display_time=0, scroll=True):
        self.sequence_number += 1

        colour1 = (colour1 if colour1 else colour).lower()
        colour2 = (colour2 if colour2 else colour).lower()

        cur_display = "twoline:" + line1 + "\n" + line2 + "\n" + colour1 + "\n" + colour2

        self.last_display = cur_display

        line1 = line1.rstrip()
        line2 = line2.rstrip()

        c1 = self.map_colour(colour1)
        c2 = self.map_colour(colour2)

        pos = self.width
        two_line_font = self.two_line_font
        len1, height1 = two_line_font.get_size(line1)
        len2, height2 = two_line_font.get_size(line2)

        cur_sequence_number = self.sequence_number
        if not start_time:
            start_time = time.monotonic()

        end_time = start_time + display_time

        if (not scroll) or (len1 < pos and len2 < pos):
            drawable = self.get_cleared_drawable()
            centre1 = int((self.width - len1) / 2) if centre else 0
            centre2 = int((self.width - len2) / 2) if centre else 0
            drawable.draw_text(two_line_font, centre1, self.height * 0.38 , line1, c1)
            drawable.draw_text(two_line_font, centre2, self.height * 0.88, line2, c2)
            self.show(drawable)

            while cur_sequence_number == self.sequence_number and not self.is_idle():
                await asyncio.sleep(0.005)
                if display_time and time.monotonic() >= end_time:
                    return True

            return False

        pos = self.width
        scroll_count = 1
        scroll_length = max(len1, len2) + self.width

        drawable = self.get_drawable()
        while cur_sequence_number == self.sequence_number and not self.is_idle():
            next_time = start_time + self.scroll_delay * scroll_count
            cur_time = time.monotonic()

            if display_time and cur_time > end_time:
                return

            scroll_count += 1
            time_diff = int(scroll_count * self.scroll_amount) % scroll_length

            draw_x_pos = -time_diff + self.width

            drawable.start(clear=True)
            drawable.draw_text(two_line_font, draw_x_pos, self.height * 0.38, line1, c1)
            drawable.draw_text(two_line_font, draw_x_pos, self.height * 0.88, line2, c2)
            self.show(drawable)

            while time.monotonic() < next_time and cur_sequence_number == self.sequence_number:
                await asyncio.sleep(0.005)

    def break_time_set(self, t, c):
        if len(self.break_times) == 0:
            self.break_times = [[t, c]]
        else:
            self.break_times = [[t, c], self.break_times[0]]

    def break_time_clear(self):
        self.break_times = []

    async def break_time_display(self):
        try:
            self.sequence_number += 1

            cur_display = "breaktime:"

            if len(self.break_times) == 0:
                drawable = self.get_cleared_drawable()
                drawable.draw_text(self.two_line_font, int(self.width * 0.45), int(self.height * 0.5), "...", "white")
                self.show(drawable)
                cur_display += "..."
                self.last_display = cur_display
            else:
                strs = []
                for t, c in self.break_times[0: min(2, len(self.break_times))]:
                    if t < 1:
                        txt = "%.5f" % t
                        txt = txt[1:]
                    elif t < 10:
                        txt = "%.4f" % t
                    else:
                        txt = "%.3f" % t

                    strs.append((txt, c))

                strs.append(["", (0,0,0)])
                self.two_time_display(strs[0][0], strs[0][1], strs[1][0], strs[1][1])

            if self.last_display == cur_display:
                return 0.01

        except Exception as e:
            error("timerdisplay: displayBreakTimes exception=%s", e, exc_info=True)
            raise

        return 0.005

    def clock_update(self, show_tenths=False, colour="white"):
        self.sequence_number += 1

        cur_time = time.time()
        local_time = time.localtime(cur_time)
        tenths = (int(cur_time * 10) % 10) if show_tenths else 0
        display_time = time.strftime("%H:%M", local_time)

        cur_display = f"localTime:{local_time}.{tenths}"

        if self.last_display == cur_display:
            return 0.05

        self.last_display = cur_display

        colour = self.map_colour(colour)

        drawable = self.get_cleared_drawable()

        width = self.clock_font.get_size(display_time)[0] - len(display_time) + 1

        start_pos = (self.width - width) / 2 - 1

        drawable.draw_text(self.clock_font,
                          start_pos,
                          self.clock_font.height - self.clock_font.descender,
                          display_time, colour)

        seconds = ("0" + str(local_time.tm_sec))[-2:]
        if show_tenths:
            seconds += '.' + str(tenths)

        # sz_seconds = self.seconds_font.get_size(seconds)
        secs_place = max(0, start_pos) + self.clock_font.get_size(display_time[:-1])[0]

        drawable.draw_text(self.seconds_font,
                          secs_place,
                          self.clock_font.ascender + self.seconds_font.ascender,
                          seconds, colour)

        self.show(drawable)
        return 0.05

