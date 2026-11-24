import tomlkit
from auto_config_parser import ConfigSectionHandler
from utils import my_ip_address, my_host_name


class Sheet:
    __slots__ = ("name", "top_colour", "bottom_colour",
                 "ip", "pin", "pin_expire_time",
                 "has_hardware_clock", "host_name", "ordinal")

    def __init__(self,
                 name, top_colour, bottom_colour,
                 ip, pin, pin_expire_time,
                 has_hardware_clock, host_name, ordinal):
        self.name = name
        self.top_colour = top_colour
        self.bottom_colour = bottom_colour
        self.ip = ip
        self.pin = pin
        self.pin_expire_time = pin_expire_time
        self.has_hardware_clock = has_hardware_clock
        self.host_name = host_name
        self.ordinal = ordinal

    def __str__(self):
        return "name: %s, top_colour:%s , bottom_colour: %s, ip: %s, pin: %s, pin_expire_time: %s, has_hardware_clock: %s, host_name: %s, ordinal: %s" % (self.name, self.top_colour, self.bottom_colour, self.ip, self.pin, self.pin_expire_time, self.has_hardware_clock, self.host_name, self.ordinal)

    def _asdict(self):
        return {s: getattr(self, s) for s in self.__slots__}


class SheetsConfigSection(list, ConfigSectionHandler):
    section = "Sheet"
    variables = {"my_sheet", "rink_config"}

    def __init__(self, config, rink_config):
        self.my_sheet = None
        self.rink_config = rink_config

        list.__init__(self)
        ConfigSectionHandler.__init__(self, config)

    def set_count(self, n=0):
        super().__init__()
        if len(self) > n:
            self = self[0: n]
        elif len(self) < n:
            for i in range(len(self), n):
                sheet_name = f"{self.section}{i + 1}"
                self.append(Sheet(sheet_name,
                                  "blue", "yellow", "Unassigned", "Unassigned", "Unassigned", "No", "Unassigned",
                                  str(i)))

        self.rink_config.number_of_sheets = n

    def to_config(self, config):
        if self.my_sheet:
            config.toml["MyData"]["sheet"] = self.my_sheet.name

        for i, sheet in enumerate(self):
            sheet_name = f"{self.section}{i + 1}"

            if sheet_name in config.toml:
                config.toml[sheet_name].clear()
            else:
                config.toml[sheet_name] = tomlkit.table()

            config.toml[sheet_name]["name"] = sheet.name
            config.toml[sheet_name]["scoreboardTop"] = sheet.top_colour
            config.toml[sheet_name]["scoreboardBottom"] = sheet.bottom_colour
            config.toml[sheet_name]["ip"] = sheet.ip
            config.toml[sheet_name]["pin"] = sheet.pin
            config.toml[sheet_name]["pinExpireTime"] = sheet.pin_expire_time
            config.toml[sheet_name]["hasHardwareClock"] = sheet.has_hardware_clock
            config.toml[sheet_name]["hostName"] = sheet.name.replace(" ", "").lower()

    def from_config(self, config):
        self.clear()

        number_of_sheets = int(config.toml["Rink"]["numberOfSheets"])
        ip = my_ip_address()
        hostname = my_host_name()

        self.my_sheet = None
        for i in range(number_of_sheets):
            sheet_name = f"{self.section}{i + 1}"

            sheet = Sheet(config.toml[sheet_name]["name"],
                          config.toml[sheet_name]["scoreboardTop"],
                          config.toml[sheet_name]["scoreboardBottom"],
                          config.toml[sheet_name].get("ip", "Unassigned"),
                          config.toml[sheet_name].get("pin", "Unassigned"),
                          config.toml[sheet_name].get("pinExpireTime", "Unassigned"),
                          config.toml[sheet_name].get("hasHardwareClock", False),
                          config.toml[sheet_name].get("hostName", "Unassigned"),
                          str(i))

            self.append(sheet)
            if sheet.ip == ip:
                self.my_sheet = sheet

        if not self.my_sheet:
            self.my_sheet = Sheet(sheet_name,
                                 "blue",
                                 "yellow",
                                 ip,
                                 "Unassigned",
                                 "Unassigned",
                                 False,
                                 hostname,
                                 0)
