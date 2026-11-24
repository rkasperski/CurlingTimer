from auto_config_parser import ConfigSectionHandler


class OrganizationConfigSection(ConfigSectionHandler):
    section = "Organization"

    attributes = {"organization": 	("organization","organization"),
                  "unit": 		    ("unit", "unit"),
                  "address": 		("address", "address"),
                  "city": 		    ("city", "city"),
                  "region": 		("region", "region"),
                  "country": 		("country", "country"),
                  "email": 		    ("admin", "admin"),
                  "domain":         ("local", "local"),
                  "hosts":          ("hosts", ""),
                  }
