from AutoConfigParser import ConfigSectionHandler


class ServerConfigSection(ConfigSectionHandler):
    section = "Server"
    
    attributes = {"secretKey": 		"6dI_RJRknEVkhWCJ9rwScHwsq0P97fH7XT4s_J2FpRU=",
                  "setup":              (int, str, 0),
                  "serverPort": 	"80",
                  "serverScheme":       "http",
                  "SSLCertificate":	"ssl.crt",
                  "SSLKey":		"ssl.key",
                  "config":		None
                  }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.defaultSecretKey = "6dI_RJRknEVkhWCJ9rwScHwsq0P97fH7XT4s_J2FpRU="

    def isDefaultSecretKey(self):
        return self.secretKey in [None, "", "Unassigned",  self.defaultSecretKey]
