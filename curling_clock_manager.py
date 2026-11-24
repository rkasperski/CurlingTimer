from sys import _getframe as sys_getframe
from asyncio import create_task as asyncio_create_task, \
    sleep as asyncio_sleep, \
    CancelledError as asyncio_CancelledError
from time import monotonic as time_monotonic, \
    time as time_time

from logger import error, info
from zero_configuration_manager import close as zero_conf_manager_close, \
    publish as zero_conf_manager_publish
from break_timer_client import DisplayBreakTimeTracker
from configuration_manager import start_tasks as configuration_manager_start_tasks, \
     stop_tasks as configuration_manager_stop_tasks
from hardware_clock import has_hardware_clock

from utils import drop_root_privileges, my_ip_address, str_to_seconds
from curling_clock_timers import Timers

from draws import create_draw_manager
from kapow import get_registered as kapow_get_registered

manager = None # pylint: disable=invalid-name


class CurlingClockManager: # pylint: disable=too-many-instance-attributes, too-many-public-methods, too-many-arguments, too-many-positional-arguments
    def __init__(self, display, config,
                 port=80, token_authenticator=None, user="pi", group="pi"): # pylint: disable=too-many-positional-arguments
        self.display_function = self.start_up
        self.port = port
        self.display = display
        self.user = user
        self.group = group
        self.config = config

        self.blank_time = str_to_seconds(config.defaults.blank_time)
        self.next_blank_time = 0
        self.last_interaction_time = time_monotonic()
        self.last_interaction_resetter = "main"

        self.publish(port=port)
        self.drop_priviledges = True
        self.kapow = None
        self.token_authenticator = token_authenticator
        self.display_break_time_tracker = DisplayBreakTimeTracker()
        self.draw_manager = create_draw_manager()
        self.start_time = time_monotonic()
        self.break_time_update = 0
        self.timers = Timers(self.config.defaults, self.config.sheets.my_sheet, self.is_idle)
        self.rock_throw_listener = None
        self.welcome_message = config.defaults.welcome_message
        self.scrolling_text = "scrolling unset"
        self.scrolling_text_colour = "white"
        self.flash_text = "flash unset"
        self.flash_text_colour = "white"
        self.white = (255, 255, 255)

        self.set_defaults_from_config()
        self.call_on_view_change = None

    def get_sheets(self):
        return self.config.sheets

    def set_call_on_view_change(self, call_on_view_change):
        self.call_on_view_change = call_on_view_change

    def clear_set_call_on_view_change(self, call_on_view_change):
        if self.call_on_view_change == call_on_view_change:
            self.call_on_view_change = None

    def set_defaults_from_config(self):
        defaults = self.config.defaults
        self.welcome_message = defaults.welcome_message

        self.set_scrolling_text(self.welcome_message)
        self.blank_time = str_to_seconds(defaults.blank_time)

        count_down = self.timers.count_down
        count_down.set_finished_message(defaults.finished_message,
                                        defaults.finished_message_colour,
                                        defaults.finished_message_display_time)
        count_down.set_last_end_message(defaults.last_end_message,
                                        defaults.last_end_message_colour,
                                        defaults.last_end_message_display_time)

    async def start_tasks(self, app):
        await configuration_manager_start_tasks(app)
        await self.draw_manager.start_tasks(app)

        app['display_text'] = asyncio_create_task(self.update_task(app))

    async def stop_tasks(self, app):
        if self.rock_throw_listener:
            await self.rock_throw_listener.close()

        info("CurlingClockManager: stop tasks - start")
        info("CurlingClockManager: stop tasks - Zero Conf")
        await zero_conf_manager_close()

        info("CurlingClockManager: stop tasks - configuration manager")
        await configuration_manager_stop_tasks(app)

        info("CurlingClockManager: stop tasks - draw manager")
        await self.draw_manager.stop_tasks(app)

        info("CurlingClockManager: stop tasks - display manager")
        app['display_text'].cancel()
        await app['display_text']
        info("CurlingClockManager: stop tasks - done")

    def set_colours(self, colours):
        self.display.set_colours(colours)

    def get_colours(self):
        return self.display.get_colours()

    def get_drawable(self):
        return self.display.get_drawable()

    def is_idle(self):
        if self.last_interaction_time == 0:
            return True

        cur_time = time_monotonic()
        if self.next_blank_time:
            if self.next_blank_time > cur_time:
                return False

            info("is idle: display period expired: curTime=%s blank_time=%s", cur_time, self.next_blank_time)
            self.next_blank_time = 0
            self.force_idle()

            return True

        idle = self.last_interaction_time + self.blank_time < cur_time
        return idle

    #def set_blank_time(self, blank_time):
    #    self.blank_time = blank_time

    def reset_idle_time(self, active_until=None, active_interval=None):
        m_time = time_monotonic()
        if active_until is not None:
            current_local_time = time_time()
            # active_until is local time so convert to monotonic time
            self.next_blank_time = m_time + max(active_until - current_local_time, 0) + 0.25
            info("reset_idle_time curTime=%s m_time=%s until=%s:%s",
                 current_local_time, m_time, self.next_blank_time, self.next_blank_time - m_time, stacklevel=2)
        else:
            self.next_blank_time = 0

        if active_interval:
            current_local_time = time_time()
            # need a little bit of extra time so that the next state displays before the
            # idle time test is triggered
            self.next_blank_time = max(self.next_blank_time, m_time + active_interval + 0.25)
            info("reset_idle_time for=%s cur_time=%s m_time=%s until=%s:%s",
                 active_interval, current_local_time, m_time,
                 self.next_blank_time, self.next_blank_time - m_time, stacklevel=2)

        self.last_interaction_time = m_time
        self.last_interaction_resetter = sys_getframe().f_back.f_code.co_name

    def force_idle(self, current_view=None):
        """forces the display to go blank. If current_view is given then it must match the
        current view for the foce idle to bb done. When succesful the  display view
        is returned else None"""
        if current_view and current_view != self.display_function:
            return None

        if self.call_on_view_change:
            self.call_on_view_change(None)
            self.call_on_view_change = None

        self.abort()
        self.last_interaction_time = 0
        return self.display_function

    def get_idle_time(self):
        return time_monotonic() - self.last_interaction_time

    def get_idle_resetter(self):
        return self.last_interaction_resetter

    def publish(self, port=80):
        try:
            zero_conf_manager_publish("_clockdisplay._tcp.local.", port)
        except Exception as e: # pylint: disable=broad-exception-caught
            error("curlingtimer: startup: failed to register clock displa %s", e)

    def abort(self):
        self.display.abort()

    def register_rock_throw_listener(self, listener):
        self.rock_throw_listener = listener

    def set_kapow(self, name):
        registered = kapow_get_registered()
        if name not in registered:
            name = "life"

        self.kapow = registered[name](self.get_drawable())
        self.set_view(self.view_kapow_next)

    async def view_kapow_next(self):
        delay = await self.kapow.next()
        return delay

    def is_active(self):
        return self.display.is_active()

    def set_flash_text(self, text, colour="white"):
        self.flash_text = text.strip()
        self.flash_text_colour = colour

    def set_scrolling_text(self, text, colour="white"):
        self.scrolling_text = text.rstrip()
        self.scrolling_text_colour = colour

    def set_view(self, new_view=None, reset_idle=True, current_view=None):
        """Sets the view what's to be displayed. If current_view is supplied it must match
        the displayview for the new view to be applied. If the new view is applied then
        the old view is returned else None"""
        old_view = self.display_function

        if current_view and current_view != old_view:
            return None

        if new_view != self.display_function:
            if self.call_on_view_change:
                self.call_on_view_change(new_view)
                self.call_on_view_change = None

        self.abort()
        self.display_function = new_view

        if reset_idle:
            self.reset_idle_time()

        info("set view=%s", self.display_function.__name__, stacklevel=2)

        return old_view

    async def start_up(self):
        host_ip = my_ip_address()

        if host_ip == self.config.rink.clock_server:
            hwc = has_hardware_clock()
            if self.config.rink.battery_alert != hwc:
                self.config.rink.battery_alert = True

        if self.config.defaults.ip_on_start:
            self.set_view(self.view_show_ip_at_start)
        else:
            self.show_startup_msg()

    def show_startup_msg(self):
        my_sheet = self.config.sheets.my_sheet
        self.reset_idle_time()
        host_ip = my_ip_address()

        self.set_scrolling_text(self.welcome_message)
        self.set_view(self.view_display_scrolling_text)

        if self.config.server.setup == 0:
            if self.config.server.is_default_secret_key():
                self.set_scrolling_text("setup: secret_key")
            else:
                self.set_scrolling_text("setup: sheets")

            self.reset_idle_time(active_interval=300)
            return

        if (not my_sheet) or my_sheet.ip != host_ip:
            self.set_scrolling_text(f"{host_ip}:{self.port}", colour="red")

    async def view_competition_update(self):
        competition = self.timers.competition
        if competition.active():
            self.reset_idle_time()

        teams = competition.teams
        if self.config.defaults.large_active_team_timer:
            active_team = teams[competition.active_team]
            if self.config.defaults.large_stopped_team_timer or active_team.active():
                self.display.update_timer(str(active_team),
                                          active_team.scoreboard_colour,
                                          f"team-{competition.active_team}")
        else:
            display_time1 = str(teams[0])
            display_time2 = str(teams[1])

            self.display.two_time_display(display_time1, teams[0].scoreboard_colour,
                                          display_time2, teams[1].scoreboard_colour)

        return 0.05

    async def view_blank_screen(self):
        self.display.blank()

    async def view_display_scrolling_text(self, text=None, how_long=None):
        if text is not None:
            self.set_scrolling_text(text)

        if how_long is not None:
            self.reset_idle_time(active_interval=how_long)

        self.abort()
        await self.display.display_scrolling_text(self.scrolling_text, colour=self.scrolling_text_colour)

    async def view_show_ip_at_start(self, show_time=60):
        cur_time = time_monotonic()

        if cur_time - self.start_time > show_time:
            self.show_startup_msg()
        else:
            host_ip = my_ip_address()

            await self.display.two_line_text(host_ip, str(self.port), display_time=show_time)

    async def view_display_text(self, text=None, how_long=None):
        if text is not None:
            self.set_scrolling_text(text)

        if how_long is not None:
            self.reset_idle_time(active_interval=how_long)

        self.display.display_text(self.scrolling_text, colour=self.scrolling_text_colour)

    async def update_null(self):
        pass

    async def view_team_names(self):
        teams = self.timers.competition.teams
        await self.display.display_team_names(teams[0].name, teams[0].colour,
                                              teams[1].name, teams[1].colour,
                                              self.config.defaults.scroll_teams_separator)

    async def view_team_names_count_down(self):
        teams = self.timers.competition.teams
        await self.display.display_team_names(teams[0].name, teams[0].colour,
                                              teams[1].name, teams[1].colour,
                                              self.config.defaults.scroll_teams_separator)

    async def view_elapsed_time_update(self):
        elapsed_time = self.timers.elapsed_time
        if elapsed_time.active():
            self.reset_idle_time()

        t = elapsed_time.parts()

        display_time = elapsed_time.format(t)

        self.display.update_timer(display_time, self.white, "elt:")

    async def view_count_down_update(self):
        count_down = self.timers.count_down
        state = count_down.get_state()
        if state == "running":
            if count_down.active():
                self.reset_idle_time()

            display_time = str(count_down)
            self.display.update_timer(display_time, self.white, "cdt:")
        elif state == "onemore":
            if self.set_view(self.view_count_down_finished, reset_idle=False, current_view=self.view_count_down_update):
                self.reset_idle_time(active_interval=count_down.finished_message_display_time)
        else:
            self.set_view(self.view_count_down_last_end, current_view=self.view_count_down_update)

        return 0.05

    async def view_count_down_finished(self):
        self.abort()
        count_down = self.timers.count_down
        if await self.display.display_scrolling_text( \
                count_down.finished_message if count_down.finished_message else "Done",
                colour=count_down.finished_message_colour if count_down.finished_message_colour else "green",
                display_time=count_down.finished_message_display_time,
                two_line_ok=False):
            if count_down.last_end_message and count_down.last_end_message_display_time:
                if self.set_view(self.view_count_down_last_end, reset_idle=False,
                                 current_view=self.view_count_down_finished):
                    self.reset_idle_time(active_interval=count_down.last_end_message_display_time)
            else:
                self.force_idle(current_view=self.view_count_down_finished)

    async def view_count_down_last_end(self):
        self.abort()
        count_down = self.timers.count_down
        if await self.display.display_scrolling_text( \
                    count_down.last_end_message if count_down.last_end_message else "Last End",
                    colour=count_down.last_end_message_colour if count_down.last_end_message_colour else "red",
                    display_time=count_down.last_end_message_display_time,
                    two_line_ok=False):
            self.force_idle()

    async def view_intermission_update(self):
        timer = self.timers.intermission

        if timer.active():
            self.reset_idle_time()

        if timer.time_remaining() == 0:
            self.set_view(self.view_competition_update)
            return 0

        self.display.update_timer(str(timer), timer.colour, "intermission:")
        return 0.05

    async def view_between_end_timer_update(self):
        timer = self.timers.intermission
        self.display.update_timer(str(timer), timer.colour, "intra:")

        if timer.active():
            self.reset_idle_time()

        if timer.time_remaining() == 0:
            self.set_view(self.view_competition_update)

        return 0.05

    async def view_timeout_update(self):
        timer = self.timers.timeout
        self.display.update_timer(str(timer), timer.colour, "timeout:")

        if timer.active():
            self.reset_idle_time()

        if timer.time_remaining() == 0:
            timer.team.remaining_timeouts -= 1
            timer.pause()
            print(f"{timer.team_id=}")
            if timer.team_id == "team1":
                self.timers.competition.resume_team1()
            elif timer.team_id == "team2":
                self.timers.competition.resume_team2()

            self.set_view(self.view_competition_update)

        return 0.05

    async def view_clock_update(self):
        self.display.clock_update()
        return 0.05

    async def view_splash_colour(self):
        self.display.display_splash_colour()

    async def set_splash_colour(self, colour="white"):
        self.display.set_splash_colour(colour)

    async def view_display_flash_text(self):
        await self.display.display_flash_text(self.flash_text, colour=self.flash_text_colour)

    def break_times_needs_update(self):
        self.break_time_update = 0

    async def view_break_time_update(self):
        if self.rock_throw_listener:
            break_time_update = self.rock_throw_listener.get_last_update_time()
            if break_time_update > self.break_time_update:
                events = self.rock_throw_listener.get_events()
                if events:
                    for event in events:
                        for tm, clr, ev_name, speed in event[1][0: min(2, len(event[1]))]:
                            self.display.break_time_set(tm, clr)

                self.break_time_update = break_time_update
        else:
            self.display.break_time_clear()

        await self.display.break_time_display()

    def break_time_clear(self):
        self.display.break_time_clear()
        self.break_time_update = 0
        if self.rock_throw_listener:
            self.rock_throw_listener.clear_events()

    async def update_task(self, app):
        await asyncio_sleep(1)

        if self.drop_priviledges:
            drop_root_privileges(self.user, groups=[self.group, "adm"])
            self.drop_priviledges = False

        last_display = self.update_null
        is_idle = self.is_idle()

        while True:
            try:
                wait_time = None
                if self.is_idle():
                    if not is_idle:
                        info("idle: blanking screen ct=%s nbt=%s lit=%s",
                             time_monotonic(), self.next_blank_time, self.last_interaction_time)
                        if self.call_on_view_change:
                            self.call_on_view_change(None)
                            self.call_on_view_change = None

                        is_idle = True
                        self.display.blank()
                else:
                    if is_idle:
                        info("idle: showing screen ct=%s nbt=%s lit=%s",
                             time_monotonic(), self.next_blank_time, self.last_interaction_time)
                        is_idle = False

                    if self.display_function != last_display: # pylint: disable=comparison-with-callable
                        info("display: %s from %s", self.display_function.__name__, last_display.__name__)
                        last_display = self.display_function

                    wait_time = await self.display_function()

                await asyncio_sleep(wait_time if wait_time else 0.05)

            except asyncio_CancelledError:
                return
            except KeyboardInterrupt:
                error("exit via keyboard interrupt")
                raise
            except Exception: # pylint: disable=broad-exception-caught
                error("curlingtimer: update task", exc_info=True)


def create(display, config, port=80, token_authenticator=None, user="pi", group="pi"):
    global manager # pylint: disable=global-statement

    if not manager:
        manager = CurlingClockManager(display, config, port=port,
                                      token_authenticator=token_authenticator,
                                      user=user, group=group)

    return manager

def get_manager():
    return manager
