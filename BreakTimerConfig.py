from AutoConfigParser import ConfigSectionHandler


class BreakTimerConfigSection(ConfigSectionHandler):
    section = "Sensor"

    attributes = {"laserPin": 	        (int, str, 24),
                  "sensorPin": 	        (int, str, 19),
                  "recordingPin":       (int, str, 27),
                  "name":               "sensor",
                  "indicatorPin": 	(int, str, 21),
                  "powerLED": 	        (int, str, 0),
                  "laserOnFlashMS": 	(int, str, 500),
                  "laserOffFlashMS": 	(int, str, 500),
                  }
