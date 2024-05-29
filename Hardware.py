from AutoConfigParser import ConfigSectionHandler


class HardwareConfigSection(ConfigSectionHandler):
    section = "Hardware"
    
    attributes = {"gpioMapping":       "adafruit-hat-pwm",
                  "rows":              (int, str, 16),
                  "cols":              (int, str, 32),
                  "chain":             (int, str, 4),
                  "parallel":          (int, str, 1),
                  "pwmBits":           (int, str, 11),
                  "brightness":        (int, str, 100),
                  "pwmLsbNanoseconds": (int, str, 200),
                  "showRefresh":       (int, str, 0),
                  "rgbSequence":       "RGB",
                  "rowAddrType":       (int, str, 0),
                  "breaktimer":        (int, str, 0),
                  "slowdownGpio":      (int, str, 1),
                  "scanMode":          (int, str, 0),
                  "mirrored":          (int, str, 0),
                  "pixelMapper":       "u-mapper",
                  "multiplexing":      (int, str, 0),
                  
                  # when this button is pressed
                  # the device is powered off
                  # clocks have used 19 for this
                  # breaktimers use 5
                  # button = 19
                  "button":            (int, str, 0),
                  
                  # this pin is set to high when ready
                  "powerLED":          (int, str, 0),
                  }
    
    
    
