import time
from logger import warning, info
from utils import seconds_to_str, str_to_seconds


class CountDownTimer: # pylint: disable=too-many-instance-attributes
    def __init__(self, time_amt=40*60, has_hours=False):
        self.has_hours = False
        self.time_left = 0
        self.timer_start_time = 0
        self.state = False
        self.is_paused = True
        self.set_time(time_amt, has_hours)
        self.finished_message = None
        self.finished_message_colour = "green"
        self.finished_message_display_time = 0
        self.last_end_message = None
        self.last_end_message_colour = "red"
        self.last_end_message_display_time = 0
        self.__expired = False
        self.expired_time = None
        self.team_id = None

    def set_time(self, time_amt, has_hours=False):
        if isinstance(time_amt, str):
            time_amt = str_to_seconds(time_amt, default=60)

        self.time = time_amt
        self.time_left = time_amt
        self.is_paused = True
        self.timer_start_time = 0.0
        self.has_hours = has_hours
        self.__expired = self.time_left < 0
        self.expired_time = time.monotonic() if self.__expired else None

    def set_finished_message(self, msg, colour="white", display_time=0):
        if isinstance(display_time, str):
            display_time = str_to_seconds(display_time)

        self.finished_message = msg
        self.finished_message_colour = colour
        self.finished_message_display_time = display_time

    def set_last_end_message(self, msg, colour="white", display_time=0):
        if isinstance(display_time, str):
            display_time = str_to_seconds(display_time)

        self.last_end_message = msg
        self.last_end_message_colour = colour
        self.last_end_message_display_time = display_time

    def paused(self):
        return self.is_paused or self.__expired

    def active(self):
        return not self.paused()

    def expired(self):
        return self.__expired

    def resume(self, cur_time=None):
        if self.is_paused:
            self.is_paused = False
            self.timer_start_time = cur_time if cur_time else time.monotonic()

    def pause(self, cur_time=None):
        if not self.is_paused:
            self.is_paused = True
            self.time_left = max(0, self.time_left - \
                                 ((cur_time if cur_time else time.monotonic()) - \
                                  self.timer_start_time))

    def time_remaining(self):
        t = self.time_left
        if not self.is_paused:
            t = max(0, t - (time.monotonic() - self.timer_start_time))

        self.__expired = t <= 0
        if self.__expired and self.expired_time is None:
            self.expired_time = time.monotonic() + t

        return t

    def get_state(self):
        if not self.__expired:
            return "running"

        if self.finished_message_display_time == 0:
            return "onemore"

        return "onemore" \
            if self.finished_message_display_time + self.expired_time > time.monotonic() \
               else "lastend"

    def set_state(self, state):
        self.state = state

    def ajax_response(self, values=None):
        if values is None:
            values = {}

        t = self.time_remaining()
        result = {"active": not self.paused(), "time": seconds_to_str(t), "seconds": t, "state": self.get_state()}
        result.update(values)
        return result

    def __str__(self):
        display_time = self.time_remaining() + 0.99
        if self.has_hours or display_time > 3600:
            formatted = str(int(display_time/3600.0)) + \
                ":" + ("0" + \
                       str(int(display_time / 60 % 60.0)))[-2:] + ":" + ("0" + str(int(display_time % 60)))[-2:]
        else:
            formatted = (" " + str(int(display_time/60.0)))[-2:] + ":" + ("0" + str(int(display_time % 60)))[-2:]

        return formatted


class ElapsedTimeTimer:
    def __init__(self, time_amt=40*60, has_hours=False, show_tenths=False):
        self.has_hours = has_hours
        self.set_initial_time(time_amt)
        self.show_tenths = show_tenths
        self.is_paused = True
        self.timer_start_time = 0
        self.time_passed = 0
        self.time = 0

    def set_initial_time(self, time_amt):
        if isinstance(time_amt, str):
            time_amt = str_to_seconds(time_amt)

        self.time = time_amt
        self.time_passed = time_amt
        self.is_paused = True
        self.timer_start_time = 0.0

    def resume(self, cur_time=None):
        if self.is_paused:
            self.is_paused = False
            self.timer_start_time = cur_time if cur_time else time.monotonic()

    def paused(self):
        return self.is_paused

    def active(self):
        return not self.is_paused

    def pause(self, cur_time=None):
        if not self.is_paused:
            self.is_paused = True
            self.time_passed = self.time_passed + ((cur_time if cur_time else time.monotonic()) - self.timer_start_time)

    def time_elapsed(self):
        t = self.time_passed
        if not self.is_paused:
            t = t + (time.monotonic() - self.timer_start_time)

        return t

    def ajax_response(self, values=None):
        if values is None:
            values = {}

        t = self.time_elapsed()
        result = {"active": not self.paused(), "time": seconds_to_str(t), "seconds": t}
        result.update(values)
        return result

    def parts(self):
        t = self.time_elapsed()

        return (int(t / 3600), int(t / 60) % 60, int(t) % 60, int(t * 10) % 10)

    def format(self, p, show_tenths=None):
        show_tenths = show_tenths or (show_tenths is None and self.show_tenths)
        tenths = f".{p[3]}" if show_tenths else ""

        if p[0]:
            return f"{p[0]}:{p[1]:02}:{p[2]:02}{tenths}"

        return f"{p[1]}:{p[2]:02}{tenths}"

    def __str__(self):
        return self.format(self.parts())


class Team(CountDownTimer):
    def __init__(self, name="team1", colour="red", time_in_seconds=40*60, remaining_timeouts=2):
        super().__init__(time_in_seconds)
        self.name = name
        self.colour = colour
        self.scoreboard_colour = colour
        self.remaining_timeouts = remaining_timeouts

    def ajax_response(self, values=None):
        if values is None:
            values = {}

        t = self.time_remaining()
        result = {"name": self.name,
                  "colour": self.colour,
                  "remainingTimeouts": self.remaining_timeouts,
                  "active": not self.paused(),
                  "time": seconds_to_str(t),
                  "seconds": t}
        result.update(values)
        return result


class CompetitionTimer:
    def __init__(self, time_in_seconds=40*60, intermission_time=9*60, timeout_number=2, timeout_length=120):
        self.teams = [Team(name="", time_in_seconds=time_in_seconds, colour="red"),
                      Team(name="", time_in_seconds=time_in_seconds, colour="yellow")]
        self.active_team = 0
        self.intermission_time = intermission_time
        self.timeout_number = timeout_number
        self.timeout_length = timeout_length

    def ajax_response(self, values=None):
        if values is None:
            values = {}

        t1 = self.teams[0].ajax_response()
        t2 = self.teams[1].ajax_response()
        result = {"team1": t1,
                  "team2": t2,
                  "activeTeam": self.active_team + 1,
                  "active": not self.paused(),
                  "intermissionTime": seconds_to_str(self.intermission_time),
                  "timeoutNumber": self.timeout_number,
                  "timeoutLength": self.timeout_length}
        result.update(values)
        return result

    def paused(self):
        return self.teams[0].paused() and self.teams[1].paused()

    def active(self):
        return not self.paused()

    def pause(self, cur_time=None):
        self.teams[0].pause(cur_time=cur_time)
        self.teams[1].pause(cur_time=cur_time)
        return self.teams[0].paused() and self.teams[1].paused()

    def pause_team1(self, cur_time=None):
        self.pause(cur_time=cur_time)
        self.active_team = 0
        return True

    def pause_team2(self, cur_time=None):
        self.pause(cur_time=cur_time)
        self.active_team = 1
        return True

    def resume(self, cur_time=None):
        self.teams[self.active_team].resume(cur_time=cur_time)
        return True

    def resume_team1(self, cur_time=None):
        self.pause()
        self.active_team = 0
        self.teams[self.active_team].resume(cur_time=cur_time)
        return True

    def resume_team2(self, cur_time=None):
        self.pause()
        self.active_team = 1
        self.teams[self.active_team].resume(cur_time=cur_time)
        return True

    def exchange_teams(self, cur_time=None):
        self.pause()
        self.active_team = (self.active_team + 1) % 2
        self.teams[self.active_team].resume(cur_time=cur_time)

        return True


class BreakTimes:
    def __init__(self, name="?", filter_time=0):
        self.times = []
        self.name = name
        self.filter_time = filter_time

    def can_record(self):
        if self.filter_time > 0 and len(self.times) > 0:
            return (time.time() - self.times[-1][1]) >= self.filter_time

        return True

    def add_time(self, break_time):
        if len(self.times) > 0:
            if self.filter_time > 0:
                if (break_time[0] - self.times[-1][1]) < self.filter_time:
                    warning("breaktimers: sensor ignored: %s at_time=%s too soon: %s ft=%s",
                            self.name, break_time, break_time[0] - self.times[-1][1], self.filter_time)
                    return None

        info("breaktimers: sensor: %s time appended: %s", self.name, break_time)
        self.times.append(break_time)

        # bubble sort it into place. Generally nothing should ever move
        for idx in range(len(self.times) - 1, 0, -1):
            if self.times[idx][0] < self.times[idx-1][0]:
                self.times[idx], self.times[idx - 1] = self.times[idx - 1], self.times[idx]

        return len(self.times)

    def set_filter_time(self, filter_time=None):
        self.filter_time = filter_time if filter_time else 0

    def reset_times(self, reset=True, filter_time=None):
        if reset:
            self.times = []

        self.filter_time = filter_time if filter_time else 0

    def get_times(self):
        return self.times
