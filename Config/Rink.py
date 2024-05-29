from AutoConfigParser import ConfigSectionHandler


class RinkConfigSection(ConfigSectionHandler):
    section = "Rink"
    
    attributes = {"numberOfSheets": (int, str, 4),
                  "clockServer": "",
                  "batteryAlert": (bool, str, False),
                  "timezone": "America/Creston"}
