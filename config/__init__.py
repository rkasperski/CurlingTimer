"""
Config

This package reads the toml file and maps the toml variables in camel case
 to python variables in snake case.
"""
from auto_config_parser import AutoConfigParser

import config.rink as rink
import config.sheets as sheets
import config.users as users
import config.defaults as defaults
import config.organization as organization
import config.server as server
import config.colours as colours

sections = ["Rink", "MyData", "Defaults", "Wifi", "Server", "Users", "Unassigned", "Colours", "Organization"]

display = None


def open(filename="config.ini"):
    global display # pylint: disable=global-statement

    if display:
        return display

    display = AutoConfigParser(filename=filename, sections=sections)

    display.rink = rink.RinkConfigSection(display)
    display.users = users.UsersConfigSection(display)
    display.sheets = sheets.SheetsConfigSection(display, display.rink)
    display.defaults = defaults.DefaultsConfigSection(display)
    display.server = server.ServerConfigSection(display)
    display.colours = colours.ColoursConfigSection(display)
    display.organization = organization.OrganizationConfigSection(display)

    display.modified = False
    display.quiet = False

    return display

def get_display_config():
    global display # pylint: disable=global-statement

    return display
