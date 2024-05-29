from AutoConfigParser import ConfigSectionHandler


class OrganizationConfigSection(ConfigSectionHandler):
    section = "Organization"
    
    attributes = {"organization": 	"organization",
                  "unit": 		"unit",
                  "address": 		"address",
                  "city": 		"city",
                  "region": 		"region",
                  "country": 		"country",
                  "email": 		"admin",
                  "domain":             "local",
                  "hosts":              ""}
