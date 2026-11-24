"""
Defines the configuration parameters that are in the Server Section
"""
from auto_config_parser import ConfigSectionHandler


class ServerConfigSection(ConfigSectionHandler):
    """
    Defines the configuration parameters that are in the Server Section
    """
    section = "Server"

    #__slots__ = ("secret_key", "setup", "server_port", "server_scheme", "ssl_certificate", "ssl_key", "config")

    attributes = {"secretKey": 		("secret_key", "6dI_RJRknEVkhWCJ9rwScHwsq0P97fH7XT4s_J2FpRU="),
                  "setup":          ("setup", 0 , int, str),
                  "serverPort": 	("server_port", "80"),
                  "serverScheme":   ("server_scheme", "http"),
                  "SSLCertificate":	("ssl_certificate", "ssl.crt"),
                  "SSLKey":		    ("ssl_key", "ssl.key"),
                  "config":		    ("config", None)
                  }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.default_secret_key = "6dI_RJRknEVkhWCJ9rwScHwsq0P97fH7XT4s_J2FpRU="
        self.secret_key = self.default_secret_key

    def is_default_secret_key(self):
        "Is the secret the default one. aka has it been changed"
        return self.secret_key in [None, "", "Unassigned",  self.default_secret_key]
