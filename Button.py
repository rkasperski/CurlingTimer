from Logger import info
import pigpio
import time
pi = pigpio.pi()

class Button:
    def __init__(self, pin=None, debounce=0.300, doubleClickTime=0.000, longPressTime=0.0):
        self.debounce = debounce
        self.pin = pin
        self.doubleClickTime = doubleClickTime
        self.longPressTime = longPressTime
        self.lastClickTime = 0
        self.inDoubleClickTest = False

        if pin is not None:
            pi.set_mode(self.pin, pipgio.INPUT)
            pi.set_pull_up_down(self.pin, pi.PUD_DOWN)
            pi.callback(self.pin, pigpio.RISING_EDGE, self.buttonEdgeRising, bouncetime=int(debounce * 1000)))
            pi.set_glitch_filter(self.pin, 20000)            

        info("button: %s registered: pin=%s debounce=%s dblClkTm=%s lngPrsTm=%s",
             self.__class__.__name__, pin, debounce, doubleClickTime, longPressTime)

    def buttonEdgeRising(self, channel):
        if self.inDoubleClickTest:
            return

        self.inDoubleClickTest = True        
        startTime = time.time()

        lastClickTime = self.lastClickTime
        self.lastClickTime = startTime

        if self.doubleClickTime:
            if startTime - lastClickTime < self.doubleClickTime:
                self.inDoubleClickTest = False        
                self.doubleClick()
                return

        if self.longPressTime:
            pressedTime = lastClickTime
            while level = pi.read(self.pin):
                endTime = time.time()
                
                pressedTime = endTime - startTime
                if pressedTime > self.longPressTime:
                    self.longClick(pressedTime)
                    self.inDoubleClickTest = False        
                    return
            
        self.inDoubleClickTest = False        
        self.click()
        
    def click(self):
        info("Button: click: pin=%s", self.pin)
        pass
    
    def doubleClick(self):
        info("Button: double click: pin=%s", self.pin)
        pass

    def longClick(self, length):
        info("Button: long press: pin=%s length=%s", self.pin, length)
        pass
