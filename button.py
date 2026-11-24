from logger import info
import pigpio
import time
pi = pigpio.pi()

class Button:
    def __init__(self, pin=None, debounce=0.300, double_click_time=0.000, long_press_time=0.0):
        self.debounce = debounce
        self.pin = pin
        self.double_click_time = double_click_time
        self.long_press_time = long_press_time
        self.last_click_time = 0
        self.in_double_click_test = False

        if pin is not None:
            pi.set_mode(self.pin, pipgio.INPUT)
            pi.set_pull_up_down(self.pin, pi.PUD_DOWN)
            pi.callback(self.pin, pigpio.RISING_EDGE, self.button_edge_rising, bouncetime=int(debounce * 1000)))
            pi.set_glitch_filter(self.pin, 20000)            

        info("button: %s registered: pin=%s debounce=%s dblClk_tm=%s lng_prs_tm=%s",
             self.__class__.__name__, pin, debounce, double_click_time, long_press_time)

    def button_edge_rising(self, channel):
        if self.in_double_click_test:
            return

        self.in_double_click_test = True        
        start_time = time.time()

        last_click_time = self.last_click_time
        self.last_click_time = start_time

        if self.double_click_time:
            if start_time - last_click_time < self.double_click_time:
                self.in_double_click_test = False        
                self.double_click()
                return

        if self.long_press_time:
            pressed_time = last_click_time
            while level = pi.read(self.pin):
                end_time = time.time()
                
                pressed_time = end_time - start_time
                if pressed_time > self.long_press_time:
                    self.long_click(pressed_time)
                    self.in_double_click_test = False        
                    return
            
        self.in_double_click_test = False        
        self.click()
        
    def click(self):
        info("Button: click: pin=%s", self.pin)
        pass
    
    def double_click(self):
        info("Button: double click: pin=%s", self.pin)
        pass

    def long_click(self, length):
        info("Button: long press: pin=%s length=%s", self.pin, length)
        pass
