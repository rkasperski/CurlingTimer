from AutoConfigParser import ConfigSectionHandler


class UsersConfigSection(dict, ConfigSectionHandler):
    section = "Users"

    def __init__(self, config):
        dict.__init__(self)
        ConfigSectionHandler.__init__(self, config)
    
    def getAttributeList(self):
        return set(self.keys())

    def getDefinition(self, n):
        return (str, str, None)

    def addUser(self, user, password):
        self.config.modified = True
        self[user] = password

    def delUser(self, user):
        if user in self:
            self.config.modified = True
            del self[user]
            self.config.toml[self.section].remove(user)

    def set(self, n, v):
        self[n] = v

    def get(self, n, *args):
        try:
            return self[n]
        except KeyError:
            if len(args) > 0:
                return args[0]

            raise
