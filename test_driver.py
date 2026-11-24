import functools
import sys
import asyncio

import logging
from PySide6.QtCore import qInstallMessageHandler # Or PySide6 / PyQt5

logging.basicConfig(level=logging.DEBUG)

def qt_message_handler(mode, context, message):
    # This intercepts the "Painter not active" text
    if "Painter not active" in message:
        # Raising an exception here forces Python to show you the call stack
        raise RuntimeError(f"Qt Error Intercepted: {message} at line {context.line} in {context.file}")

# Install the handler early in your script execution
qInstallMessageHandler(qt_message_handler)

from Kapow import RotatingBlock, Rain, Life, Symbols

fake_timers = None
fake_defaults = None
fake_sheet = None

class PlaceHolder():
    pass

def create_fake_timers():
    global fake_timers, fake_defaults, fake_sheet_data

    fake_sheet_data = PlaceHolder()
    fake_sheet_data.top_colour = "yellow"
    fake_sheet_data.bottom_colour = "blue"

    fake_defaults = PlaceHolder()

    fake_defaults.game_time = "1:40:00"

    fake_defaults.finished_message = "Done"
    fake_defaults.finished_message_colour = "red"
    fake_defaults.finished_message_display_time = "15:00"

    fake_defaults.last_end_message = "Last End"
    fake_defaults.last_end_message_colour = "green"
    fake_defaults.last_end_message_display_time = "15:00"

    fake_timers = CurlingClockTimers.Timers(fake_defaults, fake_sheet_data,lambda : False)
    fake_timers.competition.teams[0].name = "Ratakowsky"
    fake_timers.competition.teams[1].name = "O'Connor"

async def spin(fn):
    while True:
        r = await fn()
        await asyncio.sleep(r if r else 0.1)

async def test_scrolling():
    await display.display_scrolling_text( "hello again. does this scroll", colour="white")

async def test_clock():
    async def view_clock_update():
        display.clock_update()

    await spin(view_clock_update)

async def test_clock10ths():
    async def clock_update10ths():
        display.clock_update(show_tenths=True)

    await spin(clock_update10ths)

async def test_2line():
    await spin(functools.partial(display.two_line_text, "line p" , "line y", centre=True))

async def test_2scrolling():
    await spin(functools.partial(display.two_line_text, "line1 - is too lone" , "line2"))

async def test_break_times():
    await spin(functools.partial(display.break_time_display))

async def test_break_times1():
    display.break_time_set(0.123, "red")

    await spin(functools.partial(display.break_time_display))

async def test_break_times2():
    display.break_time_set(0.123, "red")
    display.break_time_set(0.456, "green")
    await spin(functools.partial(display.break_time_display))

async def test_competition_update():
    global fake_timers

    async def view_competition_update():
        teams = fake_timers.competition.teams
        display_time1 = str(teams[0])
        display_time2 = str(teams[1])
        display.two_time_display(display_time1, teams[0].scoreboard_colour, display_time2, teams[1].scoreboard_colour)

    create_fake_timers()

    fake_timers.competition.resume_team1()

    await spin(view_competition_update)

async def test_teams():
    create_fake_timers()

    teams = fake_timers.competition.teams
    await spin(functools.partial(display.display_team_names, teams[0].name, teams[0].colour, teams[1].name, teams[1].colour, None))

async def test_teams_scrolling():
    create_fake_timers()

    teams = fake_timers.competition.teams
    await spin(functools.partial(display.display_team_names, teams[0].name, teams[0].colour, teams[1].name, teams[1].colour, "vs"))

async def nothing():
    return 0.1

async def test_text():
    display.display_text("test text")
    await spin(functools.partial(nothing))

async def test_blank():
    display.blank()
    await spin(functools.partial(nothing))

async def test_splash():
    async def splash_colour(colour):
        display.display_splash_colour(colour)

    await spin(functools.partial(splash_colour, (121, 200, 80)))

async def test_flash():
    await spin(functools.partial(display.display_flash_text, "192.168.1.80", "red"))

async def test_flash2():
    await spin(functools.partial(display.display_flash_text, "top\nbottom", "red"))

async def test_count_down_update():
    async def count_down_update():
        display.update_timer(str(fake_timers.count_down), "white", "cdt:")

    fake_timers.count_down.resume()
    await spin(count_down_update)

async def test_elapsed_update():
    def elapsed_update():
        display.update_timer(str(fake_timers.elapsed_time), "white", "cdt:")

    fake_timers.elapsed_time.resume()
    await spin(elapsed_update)

async def test_elapsed_10ths_update():
    fake_timers.elapsed_time.show_tenths = True

    async def elapsed_10ths_update():
        display.update_timer(str(fake_timers.elapsed_time), "white", "cdt:", show_tenths=True)

    fake_timers.elapsed_time.resume()
    
    await spin(elapsed_10ths_update)

async def delayed_test(test_fn):
    await asyncio.sleep(1)
    await test_fn()

async def test_dots():
    i = -1
    r, g, b = [128, 129, 128]

    drawable = display.get_cleared_drawable()
    drawable.show()

    n_x_pixels = int(drawable.width / drawable.visible_pixel_dimension)
    n_y_pixels = int(drawable.height / drawable.visible_pixel_dimension)

    while True:
        i += 1

        r = (r + 9) % 255
        g = (g + 31) % 255
        b = (b + 67) % 255

        drawable.start()
        drawable.draw_point(int(i % n_x_pixels) * drawable.visible_pixel_dimension,
                            int(i % n_y_pixels) * drawable.visible_pixel_dimension,
                            (r, g, b))
        drawable.show()
        await asyncio.sleep(0.2)

async def test_circles():
    i = -1
    r, g, b = [128, 129, 128]

    drawable = display.get_cleared_drawable()
    drawable.show()

    center_x = int(drawable.width / 2)
    center_y = int(drawable.height / 2)
    max_d = int(max(drawable.visible_pixels) / 2)
    pd = drawable.visible_pixel_dimension
    i = 1234567890 * max_d - 1
    while True:
        i = (i - 1) % max_d

        r = (r + 9) % 255
        g = (g + 31) % 255
        b = (b + 67) % 255

        drawable.start()
        drawable.draw_circle(center_x, center_y, pd * i, border_colour=(r, g, b))
        display.show(drawable)
        await asyncio.sleep(0.2)

async def test_rects():
    i = -1
    r, g, b = [128, 129, 128]

    drawable = display.get_cleared_drawable()
    drawable.show()

    centerX = int(drawable.width / 2)
    centerY = int(drawable.height / 2)

    max_d = int(max(drawable.visible_pixels) / 2)

    pd = drawable.visible_pixel_dimension
    i = 1234567890 * max_d - 1
    while True:
        i = (i - 1) % max_d

        r = (r + 9) % 255
        g = (g + 31) % 255
        b = (b + 67) % 255

        t = i * pd
        drawable.start()
        drawable.draw_rect(centerX - t, centerY - t, t + t - 1, t + t - 1, border_colour=(r, g, b))
        drawable.show()
        await asyncio.sleep(0.2)

async def test_kapow(which_kapow):
    kapow = which_kapow(display.get_drawable())

    await spin(kapow.next)

async def test_polygons():
    star_vertices = ((000, 300), (300, 300), (400, 000), (500, 300), (800, 300), (550, 500), (650, 800), (400, 600), (150, 800), (250, 500))

    i = -1
    r, g, b = [128, 129, 128]

    drawable = display.get_cleared_drawable()
    drawable.show()

    centerX = int(drawable.width / 2)
    centerY = int(drawable.height / 2)

    max_d = max(drawable.visible_pixels)
    pd = drawable.visible_pixel_dimension

    i = 1234567890 + max_d - 1
    while True:
        i = (i - 1) % max_d

        r = (r + 9) % 255
        g = (g + 31) % 255
        b = (b + 67) % 255

        pi = i * pd
        offset = (centerX - int(((800 / max_d) * i  / 800) * pi) , centerY - int((800 / max_d) * (i / 800) * pi))

        pts = [(int((x / 800) * pi) + offset[0], int((y / 800) * pi) + offset[1]) for x, y in star_vertices]

        drawable.start()
        drawable.draw_polygon(pts, border_colour=(r, g, b))
        drawable.show()
        await asyncio.sleep(0.2)

def main():
    global display, app, test_fn

    is_tv = False
    a = sys.argv.pop(1)
    if a == "TV":
        import TV_Display as display_server

        a = sys.argv.pop(1)
        is_tv = True
    else:
        import LED_RGB_Display as display_server

    create_fake_timers()

    test_functions = {
        "scrolling": test_scrolling,
        "clock": test_clock,
        "clock10ths": test_clock10ths,
        "2line": test_2line,
        "2scrolling": test_2scrolling,
        "break": test_break_times,
        "break1": test_break_times1,
        "break2": test_break_times2,
        "text": test_text,
        "competition": test_competition_update,
        "teams": test_teams,
        "teams_scrolling": test_teams_scrolling,
        "vs": test_teams_scrolling,
        "splash": test_splash,
        "countdown": test_count_down_update,
        "elapsed": test_elapsed_update,
        "elapsed10ths": test_elapsed_10ths_update,
        "flash": test_flash,
        "flash2": test_flash2,
        "blank": test_blank,
        "dots": test_dots,
        "circles": test_circles,
        "rects": test_rects,
        "polygons": test_polygons,
        "block": functools.partial(test_kapow, RotatingBlock),
        "rain": functools.partial(test_kapow, Rain),
        "life": functools.partial(test_kapow, Life),
        "star": functools.partial(test_kapow, lambda x: Symbols(x, "star")),
        "square": functools.partial(test_kapow, lambda x: Symbols(x, "square")),
        "circle": functools.partial(test_kapow, lambda x: Symbols(x, "circle"))
    }
    
    test_fn = test_functions.get(a, None)

    if test_fn is None:
        print(f"{a} is not a valid test")
        print(f"try one of {', '.join(test_functions.keys())}")
        sys.exit(4)

    if is_tv:
        display = display_server.create(sys.argv, "welcome to my nightmare", "test.config")
    else:
        display = display_server.create(sys.argv, "welcome to my nightmare", "defaults/display.toml")

    display.start_display()
    loop = display.run()

    loop.run_until_complete(delayed_test(test_fn))
    

if __name__ == "__main__":
    main()
