import os
import sys
import time
import smbus
from collections import namedtuple

from datetime import datetime, timezone, timedelta
from dateutil import parser as date_parser

RTCTime = namedtuple("RTCTime", "second, minute, hour, day_of_week, day, month, year")


def from_bcd(b):
    return (b >> 4) * 10 + (b & 0xf)


def to_bcd(t):
    return (t % 10) + (int(t / 10) << 4)


class DS3231():
    def __init__(self, twi=1, addr=0x68, verbose=False):
        if verbose:
            print(f"{twi=} {addr=}")

        try:
            self._bus = smbus.SMBus(twi)
        except Exception as e:
            raise OSError(f"failed to bind to DS3231 {twi=} addr=0x{addr:02x}")

        self._addr = addr
        self.verbose = verbose

        if verbose:
            print(f"{self._bus=}")


    def set_data(self, secs, mins, hrs24, day_of_week, month_day, month, year):
        secs = to_bcd(secs)
        mins = to_bcd(mins)
        hrs24 = to_bcd(hrs24)
        day_of_week = to_bcd(day_of_week)
        month_day = to_bcd(month_day)
        month = to_bcd(month)
        year = to_bcd(year % 100)

        self._bus.write_i2c_block_data(self._addr, 0x00, [secs, mins, hrs24, day_of_week, month_day, month, year])

        # self._bus.write_byte_data(self._addr, 0x00, secs)
        # self._bus.write_byte_data(self._addr, 0x01, mins)
        # self._bus.write_byte_data(self._addr, 0x02, hrs24)
        # self._bus.write_byte_data(self._addr, 0x03, day_of_week)
        # self._bus.write_byte_data(self._addr, 0x04, month_day)
        # self._bus.write_byte_data(self._addr, 0x05, month)
        # self._bus.write_byte_data(self._addr, 0x06, year)

    def get_data(self):
        data = self._bus.read_i2c_block_data(self._addr, 0x00, 7)
        if self.verbose:
            print(f"{data=}")
            
        t = [from_bcd(d) for d in data]
        t[6] += 2000

        return RTCTime(*t)

    def get_date_time(self, utc=True, century=21, raw=False):
        t = self.get_data()
        if raw:
            print(f"raw DS3231: {t}")

        try:
            t = RTCTime(min(t.second, 59), min(t.minute, 59), min(t.hour, 23), min(t.day_of_week, 6), min(t.day, 30), min(t.month, 11), min(2050, t.year))
            if utc:
                return datetime(t.year, t.month, t.day, t.hour, t.minute, t.second, tzinfo=timezone.utc)

            return datetime(t.year, t.month, t.day, t.hour, t.minute, t.second, tzinfo=timezone.utc).astimezone()
        except ValueError:
            print(f"bad DS3231: {t}")

    def set_date_time(self, dt):
        dt = dt.astimezone(timezone.utc)
        self.set_data(dt.second, dt.minute, dt.hour, dt.isoweekday(), dt.day, dt.month, dt.year % 100)

    def get_date_str(self, utc=True, raw=False):
        dt = self.get_date_time(utc=utc, raw=raw)
        return dt.strftime("%a %-d %b %Y %-I:%M:%S %p %Z")

    def set_to_system_time(self):
        cur_time = datetime.now(timezone.utc)
        while cur_time.microsecond > 1000:
            time.sleep(0.00001)
            cur_time = datetime.now(timezone.utc)

        self.set_date_time(cur_time)

    def set_date_str(self, s):
        dt = date_parser.parse(s)
        self.set_date_time(dt)

    def set_system_time(self):
        cur_time = self.get_date_str()
        start_time = cur_time
        while start_time == cur_time:
            cur_time = self.get_date_str()

        os.system(f"sudo date -s '{cur_time}'")
        os.system("date +'%a %-d %b %Y %-I:%M:%S.%N %p %Z'")
        print(f"hwclock: set system time: {cur_time}")


def main():
    args = sys.argv[1:]
    utc = False
    set_time = False
    daemon = False

    args = sys.argv[1:]
    utc = False

    daemon = False
    raw = False
    set_system_time = False
    set_time = False
    set_to_system_time = False
    diff = False
    avg = False
    twi = 1
    address = 0x68
    verbose = False

    while args and args[0].startswith("-"):
        a = args.pop(0)

        if a == "-v":
            verbose = True
        elif a == "-u":
            utc = True
        elif a == "-s":
            set_time = True
        elif a == "-S":
            set_system_time = True
        elif a == "-t":
            set_to_system_time = True
        elif a == "-d":
            daemon = True
        elif a == "--raw":
            raw = True
        elif a == "--diff":
            diff = True
        elif a == "--avg":
            avg = True
        elif a == "--twi":
            twi = int(args.pop(0))
        elif a == "--address":
            address = int(args.pop(0))
        else:
            print(f"{sys.argv[0]} [-s] [-u] [<date-time per date cmd>]")
            sys.exit()

    ds = DS3231(twi, address, verbose=verbose)

    if set_system_time:
        ds.set_system_time()

    if daemon:
        while True:
            cur_time = datetime.now(timezone.utc)
            while cur_time.microsecond > 100000:
                time.sleep(0.01)
                cur_time = datetime.now(timezone.utc)

            ds.set_date_time(cur_time)
            time.sleep(60)

    if set_time:
        print("setting time to")
        ds.set_date_str(args[0])

    if set_to_system_time:
        print("setting time to system time")
        ds.set_to_system_time()

    print("rtc:", ds.get_date_str(utc=utc, raw=raw))
    if diff:
        sum_tdif = None
        n = 0
        for i in range(0, 10 if avg else 1):
            old_rtc = ds.get_date_time(utc)
            while True:
                start_time = time.time()
                cur_rtc = ds.get_date_time(utc)

                if old_rtc != cur_rtc:
                    break

            end_time = time.time()
            if utc:
                now = datetime.utcnow()
            else:
                now = datetime.now().astimezone(tz=None)

            t_diff = abs(cur_rtc - now)
            n += 1

            t = end_time - start_time
            sum_tdif = ( sum_tdif + t_diff if  sum_tdif else t_diff) - timedelta(seconds=int(t), microseconds=int(t*1000000))

        print("-")
        print("sys:", now.strftime("%a %-d %b %Y %-I:%M:%S.%f %p %Z"))
        print("rtc:", cur_rtc.strftime("%a %-d %b %Y %-I:%M:%S.%f %p %Z"))
        print("difference:",  sum_tdif / n)


if __name__ == '__main__':
    main()
