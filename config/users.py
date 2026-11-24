from auto_config_parser import ConfigSectionHandler
from passlib.hash import pbkdf2_sha256

class UsersConfigSection(dict, ConfigSectionHandler):
    section = "Users"

    def __init__(self, config):
        dict.__init__(self)
        ConfigSectionHandler.__init__(self, config)

    def get_attribute_list(self):
        return self.keys()

    def get_definition(self, n):
        return (n, None, str, str)

    def set(self, user, password):
        self._config.modified = True
        self[user] = password

    def set_password(self, user, password):
        self._config.modified = True

        is_admin = self.is_administrator(user)

        self[user] = ("Admin:" if is_admin else "") + pbkdf2_sha256.hash(password)
        return True

    def add_user(self, user, password, is_admin=False):
        if user in self:
            return False
        
        self._config.modified = True
        self[user] = ("Admin:" if is_admin else "") + pbkdf2_sha256.hash(password)
        return True

    def del_user(self, user):
        if user in self:
            self._config.modified = True
            del self[user]
            self._config.toml[self.section].remove(user)
            return True

        return False

    def has_user(self, user):
        return user in self

    def has_users(self):
        return len(self) > 0

    def has_admin_user(self):
        for user in self:
            if self.is_administrator(user):
                return True

        return False

    def is_administrator(self, user):
        user_password = self.get(user, None)

        is_admin = user_password and user_password.startswith("Admin:$")
        return is_admin

    def verify(self, user, password):
        if (user_password_hash := self.get(user, None)) is None:
            return False

        if user_password_hash.startswith("Admin:$"):
            user_password_hash = user_password_hash[6:]

        valid_user = user_password_hash and \
            ((user_password_hash == "" and password == "") or \
             (pbkdf2_sha256.verify(password, user_password_hash)))

        return valid_user
