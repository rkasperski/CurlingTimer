from auto_config_parser import ConfigSectionHandler


class BreakTimerConfigSection(ConfigSectionHandler):
    section = "Sensor"

    attributes = {"laserPin": 	        ("laser_pin", 24, int, str),
                  "sensorPin": 	        ("sensor_pin", 19, int, str),
                  "recordingPin":       ("recording_pin", 27, int, str),
                  "name":               ("name", "sensor"),
                  "indicatorPin": 	    ("indicator_pin", 21, int, str),
                  "powerLED": 	        ("power_led", 0, int, str),
                  "laserOnFlashMS": 	("laser_on_flash_ms", 500, int, str),
                  "laserOffFlashMS": 	("laser_off_flash_ms", 500, int, str),
                  }
