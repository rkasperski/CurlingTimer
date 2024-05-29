from AutoConfigParser import AutoConfigParser

import Config.Rink as rink
import Config.Sheets as sheets

import Config.Users as users
import Config.Defaults as defaults
import Config.Organization as organization
import Config.Server as server
import Config.Colours as colours

sections = ["Rink", "MyData", "Defaults", "Wifi", "Server", "Users", "Unassigned", "Colours", "Organization"]

display = None


def open(fileName="config.ini"):
    global display

    if display:
        return display
    
    display = AutoConfigParser(filename=fileName, sections=sections)

    display.rink = rink.RinkConfigSection(display)
    display.users = users.UsersConfigSection(display)
    display.sheets = sheets.SheetsConfigSection(display, display.rink)
    display.defaults = defaults.DefaultsConfigSection(display)
    display.server = server.ServerConfigSection(display)
    display.colours = colours.ColoursConfigSection(display)
    display.organization = organization.OrganizationConfigSection(display)

    display._modified = False

    return display
