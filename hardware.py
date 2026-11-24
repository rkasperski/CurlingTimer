from auto_config_parser import ConfigSectionHandler


class HardwareConfigSection(ConfigSectionHandler):
    section = "Hardware"

    attributes = {"gpioMapping":       ("gpio_mapping", "adafruit-hat-pwm"),
                  "rows":              ("rows", 16, int, str),
                  "cols":              ("cols", 32, int, str),
                  "chain":             ("chain", 3, int, str),
                  "parallel":          ("parallel", 1, int, str),
                  "pwmBits":           ("pwm_bits", 11, int, str),
                  "brightness":        ("brightness", 100, int, str),
                  "pwmLsbNanoseconds": ("pwm_lsb_nanoseconds", 200, int, str),
                  "showRefresh":       ("show_refresh", 0, int, str),
                  "rgbSequence":       ("rgb_sequence", "RGB"),
                  "rowAddrType":       ("row_addr_type", 0, int, str),
                  "breaktimer":        ("break_timer", 0, int, str),
                  "slowdownGpio":      ("slowdown_gpio", 1, int, str),
                  "scanMode":          ("scan_mode", 0, int, str),
                  "mirrored":          ("mirrored", 0, int, str),
                  "pixelMapper":       ("pixel_mapper", "u-mapper"),
                  "multiplexing":      ("multiplexing", 0, int, str),

                  # when this button is pressed
                  # the device is powered off
                  # clocks have used 19 for this
                  # breaktimers use 5
                  # button = 19
                  "button":            ("button", 0, int, str),

                  # this pin is set to high when ready
                  "powerLED":          ("power_led", 0, int, str),
                  }
