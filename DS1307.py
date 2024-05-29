from datetime import datetime, timezone, timedelta
from dateutil import parser as date_parser
from collections import namedtuple

import smbus
import os
import sys
import time

RTCTime = namedtuple("RTCTime", "second, minute, hour, dayOfWeek, day, month, year")


def fromBCD(b):
    return (b >> 4) * 10 + (b & 0xf)


def toBCD(t):
    return (t % 10) + (int(t / 10) << 4)


class DS1307():
    def __init__(self, twi=1, addr=0x68):
        self._bus = smbus.SMBus(twi)
        self._addr = addr

    def setData(self, secs, mins, hrs24, dayOfWeek, monthDay, month, year):
        secs = toBCD(secs)
        mins = toBCD(mins)
        hrs24 = toBCD(hrs24)
        dayOfWeek = toBCD(dayOfWeek)
        monthDay = toBCD(monthDay)
        month = toBCD(month)
        year = toBCD(year % 100)

        self._bus.write_i2c_block_data(self._addr, 0x00, [secs, mins, hrs24, dayOfWeek, monthDay, month, year])
        
        # self._bus.write_byte_data(self._addr, 0x00, secs)
        # self._bus.write_byte_data(self._addr, 0x01, mins)
        # self._bus.write_byte_data(self._addr, 0x02, hrs24)
        # self._bus.write_byte_data(self._addr, 0x03, dayOfWeek)
        # self._bus.write_byte_data(self._addr, 0x04, monthDay)
        # self._bus.write_byte_data(self._addr, 0x05, month)
        # self._bus.write_byte_data(self._addr, 0x06, year)
        
    def getData(self):
        t = [fromBCD(d) for d in self._bus.read_i2c_block_data(self._addr, 0x00, 7)]
        t[6] += 2000

        return RTCTime(*t)
    
    def getDateTime(self, utc=True, century=21, raw=False):
        t = self.getData()
        if raw:
            print(f"raw DS3231: {t}")

        try:
            t = RTCTime(min(t.second, 59), min(t.minute, 59), min(t.hour, 23), min(t.dayOfWeek, 6), min(t.day, 30), min(t.month, 11), min(2050, t.year))
            if utc:
                return datetime(t.year, t.month, t.day, t.hour, t.minute, t.second, tzinfo=timezone.utc)
            else:
                return datetime(t.year, t.month, t.day, t.hour, t.minute, t.second, tzinfo=timezone.utc).astimezone()
        except ValueError:
            print(f"bad DS3231: {t}")

    def setDateTime(self, dt):
        dt = dt.astimezone(timezone.utc)
        self.setData(dt.second, dt.minute, dt.hour, dt.isoweekday(), dt.day, dt.month, dt.year % 100)

    def getDateStr(self, utc=True, raw=False):
        dt = self.getDateTime(utc=utc, raw=raw)
        return dt.strftime("%a %-d %b %Y %-I:%M:%S %p %Z")

    def setToSystemTime(self):
        curTime = datetime.now(timezone.utc)
        while curTime.microsecond > 1000:
            time.sleep(0.00001)
            curTime = datetime.now(timezone.utc)
            
        self.setDateTime(curTime)

    def setDateStr(self, s):
        dt = date_parser.parse(s)
        self.setDateTime(dt)
    
    def setSystemTime(self):
        curTime = self.getDateStr()
        startTime = curTime
        while startTime == curTime:
            curTime = self.getDateStr()

        os.system(f"sudo date -s '{curTime}'")
        os.system("date +'%a %-d %b %Y %-I:%M:%S.%N %p %Z'")

        
def main():
    args = sys.argv[1:]
    utc = False
    setTime = False
    daemon = False

    ds = DS1307(1, 0x68)

    args = sys.argv[1:]
    utc = False

    daemon = False
    raw = False
    setSystemTime = False
    setTime = False
    setToSystemTime = False
    diff = False
    avg = False

    while args and args[0].startswith("-"):
        a = args.pop(0)

        if a == "-u":
            utc = True
        elif a == "-s":
            setTime = True
        elif a == "-S":
            setSystemTime = True
        elif a == "-t":
            setToSystemTime = True
        elif a == "-d":
            daemon = True
        elif a == "--raw":
            raw = True
        elif a == "--diff":
            diff = True
        elif a == "--avg":
            avg = True
        else:
            print(f"{sys.argv[0]} [-s] [-u] [<date-time per date cmd>]")
            sys.exit()

    if setSystemTime:
        ds.setSystemTime()

    if daemon:
        while True:
            curTime = datetime.now(timezone.utc)
            while curTime.microsecond > 100000:
                time.sleep(0.01)
                curTime = datetime.now(timezone.utc)
                
            ds.setDateTime(curTime)
            time.sleep(60)
        
    if setTime:
        print("setting time to")
        ds.setDateStr(args[0])

    if setToSystemTime:
        print("setting time to system time")
        ds.setToSystemTime()
        
    print("rtc:", ds.getDateStr(utc=utc, raw=raw))
    if diff:
        sum = None
        n = 0
        for i in range(0, 10 if avg else 1):
            oldRTC = ds.getDateTime(utc)
            while True:
                startTime = time.time()
                curRTC = ds.getDateTime(utc)

                if oldRTC != curRTC:
                    break
                    
            endTime = time.time()
            if utc:
                now = datetime.utcnow()
            else:
                now = datetime.now().astimezone(tz=None)

            tDiff = abs(curRTC - now)
            n += 1

            t = endTime - startTime
            sum = (sum + tDiff if sum else tDiff) - timedelta(seconds=int(t), microseconds=int(t*1000000))

        print("-")
        print("sys:", now.strftime("%a %-d %b %Y %-I:%M:%S.%f %p %Z"))
        print("rtc:", curRTC.strftime("%a %-d %b %Y %-I:%M:%S.%f %p %Z"))
        print("difference:", sum / n)

        
if __name__ == '__main__':
    main()
