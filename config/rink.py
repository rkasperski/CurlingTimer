"""
defines the portion of the configuration file that contains information
of the rink
"""
from auto_config_parser import ConfigSectionHandler


class RinkConfigSection(ConfigSectionHandler):
    """definition of the Rink section"""
    section = "Rink"

    attributes = {"numberOfSheets": 	("number_of_sheets", 4, int, str),
                  "clockServer": 		("clock_server", ""),
                  "batteryAlert": 		("battery_alert", False , bool, str),
                  "timezone": 			("timezone", "America/Creston"),
                  "clubName": 			("club_name", "Just A Rink")}
