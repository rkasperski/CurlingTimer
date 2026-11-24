from auto_config_parser import ConfigSectionHandler


class DefaultsConfigSection(ConfigSectionHandler):
    section = "Defaults"

    attributes = {
        "finishedMessage": ("finished_message", "Finish this end and play one more"),
        "finishedMessageColour": ("finished_message_colour", "green"),
        "finishedMessageDisplayTime": ("finished_message_display_time", "15:00"),
        "gameTime": ("game_time", "1:40:00"),
        "lastEndMessage": ("last_end_message", "Last End"),
        "lastEndMessageColour": ("last_end_message_colour", "red"),
        "lastEndMessageDisplayTime": ("last_end_message_display_time", "15:00"),
        "welcomeMessage": ("welcome_message", "Hello"),
        "scrollTeamsSeparator": ("scroll_teams_separator", ""),
        "largeActiveTeamTimer": ("large_active_team_timer", 0, int, str),
        "largeStoppedTeamTimer": ("large_stopped_team_timer", 0, int, str),
        "betweenEndTime": ("between_end_time", 30, int, str),
        "extraEndTime": ("extra_end_time", "4:30"),
        "teamTime": ("team_time", "40:00"),
        "intermissionLength": ("intermission_length", "8:00"),
        "defaultPINExpireTime": ("default_pin_expire_time", "3:00:00"),
        "blankTime": ("blank_time", "30:00"),
        "timeoutLength": ("timeout_length", "0:30"),
        "rockCircumference": ("rock_circumference", 910, int, str),
        "ipOnStart": ("ip_on_start", 1, int, str),
        "numberOfTimeouts": ("number_of_timeouts", 2, int, str),
        "drawServer": ("draw_server", ""),
        "breakFilterTime": ("break_filter_time", 5, int, str),
        }
