"""
Creates the timers used to track curling games
"""

from timers import CountDownTimer, ElapsedTimeTimer, CompetitionTimer

class Timers():
    def __init__(self, defaults, my_sheet_data, is_idle):
        self.competition = CompetitionTimer()
        self.competition.teams[0].colour = my_sheet_data.top_colour
        self.competition.teams[0].scoreboard_colour = my_sheet_data.top_colour
        self.competition.teams[1].colour = my_sheet_data.bottom_colour
        self.competition.teams[1].scoreboard_colour = my_sheet_data.bottom_colour

        self.count_down = CountDownTimer(defaults.game_time)
        self.count_down.set_finished_message(defaults.finished_message,
                                             defaults.finished_message_colour,
                                             defaults.finished_message_display_time)
        self.count_down.set_last_end_message(defaults.last_end_message,
                                             defaults.last_end_message_colour,
                                             defaults.last_end_message_display_time)
        self.elapsed_time = ElapsedTimeTimer(0)
        self.intermission = CountDownTimer(8 * 60)
        self.intermission.colour = "white"
        self.timeout = CountDownTimer(2 * 60)
        self.timeout.colour = "white"
        self.timeout.teamId = "unknown"
        self.timeout.team = None
        self.is_idle = is_idle

    def is_active(self):
        return self.competition.active() or \
            self.count_down.active() or \
            self.elapsed_time.active() or \
            self.intermission.active() or \
            self.timeout.active()

    def ajax_response(self, response):
        response.update({"active": self.is_active(),
                         "competition": self.competition.ajax_response(),
                         "countdown": self.count_down.ajax_response(),
                         "elapsedtime": self.elapsed_time.ajax_response(),
                         "intermission": self.intermission.ajax_response(),
                         "timeout": self.timeout.ajax_response(),
                         "idle": self.is_idle()})

        return response
