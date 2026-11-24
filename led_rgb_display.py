import asyncio
import os

import argparse
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageFont

import hardware
from auto_config_parser import AutoConfigParser
from logger import error, warning, info, debug
from base_display import BaseDisplay
from fancy_text import BaseFont

sections = ["Hardware"]

display = None  # pylint: disable=invalid-name

class Font(BaseFont): # pylint: disable=too-few-public-methods
    def __init__(self, name, font, font_id, size):
        ss = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRTSUVWXYZ"

        bbox = font.getbbox(ss, anchor='ls')
        ascender = -bbox[1]
        descender = bbox[3]

        super().__init__(name, font, font_id, size, ascender, descender, ascender + descender)

    def get_size(self, text):
        bbox = self.font.getbbox(text, anchor='ls')
        return (bbox[2] - bbox[0], bbox[3] - bbox[1])

class Drawable:
    def __init__(self, canvas, owner):
        self.canvas = canvas
        self.owner = owner
        self.drawable = None
        smallest_dimension = min(owner.width, owner.height)
        self.width = owner.width
        self.height = owner.height
        self.visible_pixel_dimension = int(smallest_dimension / 16)
        self.visible_pixels = (int(self.width / self.visible_pixel_dimension),
                               int(self.height / self.visible_pixel_dimension))

    def start(self, clear=False):
        self.drawable = ImageDraw.Draw(self.canvas)
        self.drawable.fontmode = "1"

        if clear:
            self.clear()

        return self.drawable

    def clear(self):
        self.drawable.rectangle((0, 0, self.width, self.height), fill=self.owner.map_colour("black"))

    def end(self):
        self.drawable = None

    def show(self):
        if self.drawable:
            self.end()

        self.owner.show(self)

    def fill(self, colour):
        self.drawable.rectangle((0, 0, self.width, self.height), fill=self.owner.map_colour(colour))

    def draw_point(self, x, y, colour=None):
        pd = self.visible_pixel_dimension

        colour = self.owner.map_colour(colour) if colour else None
        self.drawable.rectangle((x, y, x + pd - 1, y + pd - 1), fill=colour)

    # pylint: disable=too-many-positional-arguments, too-many-arguments
    def draw_rect(self, x, y, width, height, fill_colour=None, border_colour=None, border_width=0):
        border_colour = self.owner.map_colour(border_colour) if border_colour else None
        fill_colour = self.owner.map_colour(fill_colour) if fill_colour else None
        self.drawable.rectangle((x, y, x + width, y + height),
                                width=border_width,
                                outline=border_colour,
                                fill=fill_colour)

    def draw_circle(self, x, y, radius=5, fill_colour=None, border_colour=None, border_width=0):
        border_colour = self.owner.map_colour(border_colour) if border_colour else None
        fill_colour = self.owner.map_colour(fill_colour) if fill_colour else None
        self.drawable.circle((x, y), radius, width=border_width, outline=border_colour, fill=fill_colour)

    def draw_polygon(self, pts, fill_colour=None, border_colour=None, border_width=0):
        border_colour = self.owner.map_colour(border_colour) if border_colour else None
        fill_colour = self.owner.map_colour(fill_colour) if fill_colour else None

        self.drawable.polygon(pts,  width=border_width, outline=border_colour, fill=fill_colour)

    def draw_text(self, font, x, y , text, colour):
        colour = self.owner.map_colour(colour)

        self.drawable.text((x, y), text, font=font.font, fill=colour, anchor="ls")


# pylint: disable=too-few-public-methods
class SampleBase:
    def __init__(self, hardware_config_filename=None):
        if not hardware_config_filename:
            hardware_config_filename = "hardware.toml"

        hardware_config_file = AutoConfigParser(sections=sections, filename=hardware_config_filename)
        hardware_config = hardware.HardwareConfigSection(hardware_config_file)

        hardware_config_file.hardware = hardware_config

        self.hardware_config = hardware_config_file

        self.parser = argparse.ArgumentParser()
        self.matrix = None
        self.args = None

        self.parser.add_argument("-r", "--led-rows",
                                 action="store",
                                 help="Display rows. 16 for 16x32, 32 for 32x32. Default: 32",
                                 default=hardware_config.rows, type=int)
        self.parser.add_argument("--led-cols",
                                 action="store",
                                 help="Panel columns. Typically 32 or 64. (Default: 32)",
                                 default=hardware_config.cols, type=int)
        self.parser.add_argument("-c", "--led-chain",
                                 action="store",
                                 help="Daisy-chained boards. Default: 1.",
                                 default=hardware_config.chain, type=int)
        self.parser.add_argument("-P", "--led-parallel",
                                 action="store",
                                 help="For Plus-models or RPi2: parallel chains. 1..3. Default: 1",
                                 default=hardware_config.parallel, type=int)
        self.parser.add_argument("-p", "--led-pwm-bits",
                                 action="store",
                                 help="Bits used for PWM. Something between 1..11. Default: 11",
                                 default=hardware_config.pwm_bits, type=int)
        self.parser.add_argument("-b", "--led-brightness",
                                 action="store",
                                 help="Sets brightness level. Default: 100. Range: 1..100",
                                 default=hardware_config.brightness, type=int)
        self.parser.add_argument("-m", "--led-gpio-mapping",
                                 choices=['regular', 'adafruit-hat', 'adafruit-hat-pwm'],
                                 help="Hardware Mapping: regular, adafruit-hat, adafruit-hat-pwm",
                                 default=hardware_config.gpio_mapping, type=str)
        self.parser.add_argument("--led-scan-mode",
                                 action="store",
                                 choices=range(2), type=int,
                                 help="Progressive or interlaced scan. 0 Progressive, 1 Interlaced (default)",
                                 default=hardware_config.scan_mode)
        self.parser.add_argument("--led-pwm-lsb-nanoseconds",
                                 action="store",
                                 type=int,
                                 help="Base time-unit for the on-time in the lowest significant " \
                                      "bit in nanoseconds. Default: 130",
                                 default=hardware_config.pwm_lsb_nanoseconds)
        self.parser.add_argument("--led-show-refresh",
                                 action="store_true",
                                 help="Shows the current refresh rate of the LED panel",
                                 default=hardware_config.show_refresh)
        self.parser.add_argument("--led-slowdown-gpio",
                                 action="store",
                                 choices=range(5), type=int,
                                 help="Slow down writing to GPIO. Range: 1..100. Default: 1",
                                 default=hardware_config.slowdown_gpio)
        self.parser.add_argument("--led-no-hardware-pulse",
                                 action="store",
                                 help="Don't use hardware pin-pulse generation")
        self.parser.add_argument("--led-rgb-sequence",
                                 action="store",
                                 type=str,
                                 help="Switch if your matrix has led colors swapped. Default: RGB",
                                 default=hardware_config.rgb_sequence)
        self.parser.add_argument("--led-pixel-mapper",
                                 action="store", help="Apply pixel mappers. e.g \"Rotate:90\"",
                                 type=str,
                                 default=hardware_config.pixel_mapper)
        self.parser.add_argument("--led-row-addr-type",
                                 action="store",
                                 type=int, choices=[0, 1, 2],                                 
                                 help="0 = default; 1=AB-addressed panels;2=row direct",
                                 default=hardware_config.row_addr_type)
        self.parser.add_argument("--led-multiplexing",
                                 action="store",
                                 type=int,
                                 help="Multiplexing type: 0=direct; 1=strip; 2=checker; 3=spiral; " \
                                       "4=ZStripe; 5=ZnMirrorZStripe; " \
                                       "6=coreman; 7=Kaler2Scan; 8=ZStripeUneven (Default: 0)",
                                 default=hardware_config.multiplexing)
        self.parser.add_argument("--mirrored",
                                 action="store_true",
                                 help="mirror display",
                                 default=hardware_config.mirrored)

    def init_matrix(self):
        args = self.parse_args()

        options = RGBMatrixOptions()
        options.drop_privileges = 0

        if self.args.led_gpio_mapping is not None:
            options.hardware_mapping = args.led_gpio_mapping

        options.rows = args.led_rows
        options.cols = args.led_cols
        options.chain_length = args.led_chain
        options.parallel = args.led_parallel
        options.row_address_type = args.led_row_addr_type
        options.multiplexing = args.led_multiplexing
        options.pwm_bits = args.led_pwm_bits
        options.brightness = args.led_brightness
        options.pwm_lsb_nanoseconds = args.led_pwm_lsb_nanoseconds
        options.led_rgb_sequence = args.led_rgb_sequence
        options.pixel_mapper_config = args.led_pixel_mapper

        if args.led_show_refresh:
            options.show_refresh_rate = 1

        if args.led_slowdown_gpio is not None:
            options.gpio_slowdown = args.led_slowdown_gpio

        if self.args.led_no_hardware_pulse:
            options.disable_hardware_pulsing = True

        self.matrix = RGBMatrix(options=options)

        info(f"""{options.drop_privileges=}
{options.hardware_mapping=}
{options.rows=}
{options.cols=}
{options.chain_length=}
{options.parallel=}
{options.row_address_type=}
{options.multiplexing=}
{options.pwm_bits=}
{options.brightness=}
{options.pwm_lsb_nanoseconds=}
{options.led_rgb_sequence=}
{options.pixel_mapper_config=}
{options.show_refresh_rate=}
{options.gpio_slowdown=}
{options.disable_hardware_pulsing=}
""")
        return True


class ClockTimerDisplaySingleton(SampleBase, BaseDisplay):
    def __init__(self, args, display_string=None, hardware_config_filename=None, font_path=["fonts"]):
        BaseDisplay.__init__(self)
        SampleBase.__init__(self, hardware_config_filename=hardware_config_filename)

        self.font_path = [font_path] if isinstance(font_path, str) else font_path

        # self.parser.set_defaults(led_rows=16, led_cols=32)

        self.parser.add_argument("--twoline-font", action="store", type=str,
                                 help="the twoline font", default="EncodeSansSemiCondensed-Light.ttf:15")
        self.parser.add_argument("--twotime-font", action="store", type=str,
                                 help="the twotime font - should be monospaced",
                                 default="IBMPlexSansCondensed-Light.ttf:21")
        self.parser.add_argument("--timer-font", action="store", type=str,
                                 help="the timer font", default="RobotoCondensed-Light.ttf:26")
        self.parser.add_argument("--small-font", action="store", type=str,
                                 help="the small font", default="RobotoCondensed-Light.ttf:10")
        self.parser.add_argument("--clock-font", action="store", type=str,
                                 help="the clock font", default="RobotoCondensed-Light.ttf:26")
        self.parser.add_argument("--seconds-font", action="store", type=str,
                                 help="the clock seconds font", default="RobotoCondensed-Light.ttf:14")
        self.parser.add_argument("--text-font", action="store", type=str,
                                 help="the text font", default="Lato-Light.ttf:32")

        self.parser.add_argument("--start-message", help="message to display at the start", type=str, default=None)
        self.parser.add_argument("--port", help="start in given port", type=str, default=None)

        self.mirrored = False
        self.leading_one_adjust = (3, 2)
        self.colon_adjust = (2, 1)
        self.offscreen_canvas = None

    def parse_args(self):
        if not self.args:
            self.args = self.parser.parse_args()

        return self.args

    def start_display(self):
        if self.init_matrix():
            self.offscreen_canvas = self.matrix.CreateFrameCanvas()

            self.width = self.offscreen_canvas.width
            self.height = self.offscreen_canvas.height

            self.timer_font = self.load_font("Timer", self.args.timer_font, font_path_list=self.font_path)
            self.small_font = self.load_font("Small", self.args.small_font, font_path_list=self.font_path)
            self.two_line_font = self.load_font("TwoLine", self.args.twoline_font, font_path_list=self.font_path)
            self.two_time_font = self.load_font("TwoTime", self.args.twotime_font, font_path_list=self.font_path)
            self.clock_font = self.load_font("Clock", self.args.clock_font, font_path_list=self.font_path)
            self.seconds_font = self.load_font("Seconds", self.args.seconds_font, font_path_list=self.font_path)
            self.text_font = self.load_font("Text", self.args.text_font, font_path_list=self.font_path)

            self.offscreen_canvas = self.matrix.CreateFrameCanvas()

            self.pos = 1
            self.mirrored = self.args.mirrored
            if self.mirrored:
                self.width = int(self.width / 2)

        self.canvas = Image.new("RGB", (self.width, self.height))

    def load_font(self, name, font_filename, default=True, font_path_list=[]):
        self.font_id += 1

        sp = font_filename.split(":")
        font_filename = sp[0]
        size = 12

        if len(sp) > 1:
            size = int(sp[1])

        for path in font_path_list:
            if os.path.exists(font_filename):
                font_path = font_filename
            else:
                font_path = os.path.join(path, font_filename)

            if os.path.exists(font_path):
                debug("pillow: %s loading font: %s(%d) size=%d", name, font_path, self.font_id, size)
                if font_path.lower().endswith(".ttf"):
                    font = ImageFont.truetype(font_path, size=size)
                else:
                    font = ImageFont.load(font_path)

                f = Font(name, font, self.font_id, size)
                info("pillow: %s loaded font: %s(%d) size=%d ascender=%s descender=%s height=%s", name, font_path, self.font_id, f.size, f.ascender, f.descender, f.height)
                return f

        error("pillow: %s font not found: %s", name, font_path)

        if default:
            warning("pillow: %s loading default font for: %s", name, font_filename)
            return Font(name, ImageFont.load_default(), self.font_id, 12)

        return None

    def get_drawable(self):
        return Drawable(self.canvas, self)

    def get_cleared_drawable(self):
        drawable = Drawable(self.canvas, self)

        drawable.start(clear=True)

        return drawable

    def show(self, drawable):
        self.offscreen_canvas.SetImage(self.canvas)

        if self.mirrored:
            self.offscreen_canvas.SetImage(self.canvas, self.width)

        self.offscreen_canvas = self.matrix.SwapOnVSync(self.offscreen_canvas)

    def map_colour(self, c):
        if isinstance(c, list):
            return c

        if isinstance(c, str):
            try:
                return self.colour_cache[c]
            except KeyError:
                rgb = self.colours.get(c.lower(), (255, 255, 255))
                self.colour_cache[c] = rgb
                return rgb
        else:
            return c

    def run(self):
        loop = asyncio.get_event_loop()
        return loop


def create(args, display_string=None, hardware_config_filename=None, font_path=["fonts"]):
    global display

    if not display:
        display = ClockTimerDisplaySingleton(args,
                                             display_string=display_string,
                                             hardware_config_filename=hardware_config_filename,
                                             font_path=font_path)

    return display

