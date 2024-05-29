from AutoConfigParser import ConfigSectionHandler
from Utils import myIPAddress, myHostName
import tomlkit


class Sheet:
    __slots__ = ("name", "topColour", "bottomColour", "ip", "pin", "pinExpireTime", "hasHardwareClock", "hostName", "ordinal")

    def __init__(self, name, topColour, bottomColour, ip, pin, pinExpireTime, hasHardwareClock, hostName, ordinal):
        self.name = name
        self.topColour = topColour
        self.bottomColour = bottomColour
        self.ip = ip
        self.pin = pin
        self.pinExpireTime = pinExpireTime
        self.hasHardwareClock = hasHardwareClock
        self.hostName = hostName
        self.ordinal = ordinal

    def __str__(self):
        return "name: %s, topColour:%s , bottomColour: %s, ip: %s, pin: %s, pinExpireTime: %s, hasHardwareClock: %s, hostName: %s, ordinal: %s" % (self.name, self.topColour, self.bottomColour, self.ip, self.pin, self.pinExpireTime, self.hasHardwareClock, self.hostName, self.ordinal)

    def _asdict(self):
        return {s: getattr(self, s) for s in self.__slots__}

    
class SheetsConfigSection(list, ConfigSectionHandler):
    section = "Sheet"
    variables = {"mySheet", "rinkConfig"}
    
    def __init__(self, config, rinkConfig):
        self.mySheet = None
        self.rinkConfig = rinkConfig
        
        list.__init__(self)
        ConfigSectionHandler.__init__(self, config)

    def setCount(self, n=0):
        super().__init__()
        if len(self) > n:
            self = self[0: n]
        elif len(self) < n:
            for i in range(len(self), n):
                sheetName = f"{self.section}{i + 1}"
                self.append(Sheet(sheetName, "blue", "yellow", "Unassigned", "Unassigned", "Unassigned", "No", "Unassigned", str(i)))

        self.rinkConfig.numberOfSheets = n

    def toConfig(self, config):
        if self.mySheet:
            config.toml["MyData"]["sheet"] = self.mySheet.name
             
        for i, sheet in enumerate(self):
            sheetName = f"{self.section}{i + 1}"

            if sheetName in config.toml:
                config.toml[sheetName].clear()
            else:
                config.toml[sheetName] = tomlkit.table()
                
            config.toml[sheetName]["name"] = sheet.name
            config.toml[sheetName]["scoreboardTop"] = sheet.topColour
            config.toml[sheetName]["scoreboardBottom"] = sheet.bottomColour
            config.toml[sheetName]["ip"] = sheet.ip
            config.toml[sheetName]["pin"] = sheet.pin
            config.toml[sheetName]["pinExpireTime"] = sheet.pinExpireTime
            config.toml[sheetName]["hasHardwareClock"] = sheet.hasHardwareClock
            config.toml[sheetName]["hostName"] = sheet.hostName

    def fromConfig(self, config):
        self.clear()

        numberOfSheets = int(config.toml["Rink"]["numberOfSheets"])
        ip = myIPAddress()
        hostname = myHostName()

        self.mySheet = None
        for i in range(numberOfSheets):
            sheetName = f"{self.section}{i + 1}"

            sheet = Sheet(config.toml[sheetName]["name"],
                          config.toml[sheetName]["scoreboardTop"],
                          config.toml[sheetName]["scoreboardBottom"],
                          config.toml[sheetName].get("ip", "Unassigned"),
                          config.toml[sheetName].get("pin", "Unassigned"),
                          config.toml[sheetName].get("pinExpireTime", "Unassigned"),
                          config.toml[sheetName].get("hasHardwareClock", False),
                          config.toml[sheetName].get("hostName", "Unassigned"),
                          str(i))

            self.append(sheet)
            if sheet.ip == ip:
                self.mySheet = sheet

        if not self.mySheet:
            self.mySheet = Sheet(sheetName,
                                 "blue",
                                 "yellow",
                                 ip,
                                 "Unassigned",
                                 "Unassigned",
                                 False,
                                 hostname,
                                 0)
            
            
