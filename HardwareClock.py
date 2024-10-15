import os
import sys
from datetime import datetime, timezone

from Logger import warning, error
import time
try:
    import USB_DS3231
    import DS1307
except ModuleNotFoundError:
    pass

from Utils import runCommand

 
dsRTC = None
hwClockPath = "/usr/sbin/hwclock"
hasHardwareClock = False


def hasRealTimeClock():
    global dsRTC, hwClockPath
    
    if os.path.exists("/dev/rtc"):
        cmd = f"sudo {hwClockPath} --test --utc"
        rc, output = runCommand(cmd)
        warning("hwclock: /dev/rtc hasRealTimeClock=1; %s; rc=%s", cmd, rc)
        return True

    try:
        dsRTC = USB_DS3231.DS3231()
        print("found USB DS3231")
        hwClockPath = "/usr/sbin/cc_hwclock"

    except Exception:
        # try for an I2C bus DS1307/DS3231

        try:
            dsRTC = DS1307.DS1307()
            print("found I2C DS1307/DS3231")
            hwClockPath = "/usr/sbin/cc_hwclock"
        except Exception:
            return False

    try:
        rtcTime = dsRTC.getDateTime(utc=True)
        curTime = datetime.now(timezone.utc)

        warning("hwclock: i2c read ds1307 hasRealTimeClock=1")

        if rtcTime.timestamp() - curTime.timestamp() > 3:
            rc, output = runCommand(f"sudo date -s '{dsRTC.getDateStr(utc=True)}'")
            warning("hwclock: system time is behind '%s' --> %s; rc={%s}",
                    curTime.strftime('%a %-d %b %Y %-I:%M:%S %p %Z'),
                    rtcTime.strftime('%a %-d %b %Y %-I:%M:%S %p %Z'),
                    rc)

        return True
    except IOError:
        pass
            
    warning("hwclock: hasRealTimeClock=0")
    return False


def updateClockTime(newTimeSecsFromMidnight=None, newDate=None, newTimeZone=None):
    global ds1307

    startTime = time.monotonic()

    warning("clock: set request secsFromMidnight=%s date=%s tz=%s", newTimeSecsFromMidnight, newDate, newTimeZone)
    outputList = []
    nn = "\n"
    
    if newTimeZone:
        cmd = f'sudo timedatectl set-timezone "{newTimeZone}"'
        rc, output = runCommand(cmd)
        warning("clock: Set timezone; cmd='%s' rc=%s output=%s", cmd, rc, output)
        if rc:
            outputList.append(output)
            return f"failed to set timezone: {newTimeZone}\ncmd='{cmd}' rc={rc}\n{nn.join(outputList)}"

        outputList.append(f"set new timezone {newTimeZone}")
    
    if newTimeSecsFromMidnight:
        newTimeSecsFromMidnight = newTimeSecsFromMidnight + (time.monotonic() - startTime)
        timeStr = f"{int(newTimeSecsFromMidnight / 3600)}:{int(newTimeSecsFromMidnight % 3600/60):-02d}:{int(newTimeSecsFromMidnight % 60):02d}"

        cmd = f'sudo /bin/date +"%T" -s "{timeStr}"'
        rc, output = runCommand(cmd)
        print(cmd, "\n",  output)
        warning("clock: Set time; cmd='%s' rc=%s output=%s", cmd, rc, output)
        if rc:
            outputList.append(output)
            return f"failed to set time({timeStr}; cmd='{cmd}' rc={rc}\n{nn.join(outputList)}"

        outputList.append("set time done")
                
    if newDate:
        cmd = f'sudo /bin/date +"%F" -s "{newDate} $(date +%H:%M:%S)"'
        rc, output = runCommand(cmd)
        warning("clock: Set date; cmd='%s' rc=%s output=%s", cmd, rc, output)
        if rc:
            outputList.append(output)
            return f"failed to set date({newDate};\ncmd='{cmd}' rc={rc}\n{nn.join(outputList)}"

        outputList.append("set date done")

    return nn.join(outputList)


def setHardwareClock(doRestart=False):
    outputList = []
    nn = '\n'
    if dsRTC:
        cmd = f"sudo {hwClockPath} --systohc --utc"
        try:
            dsRTC.setToSystemTime()
            rc, output = runCommand(cmd)
            print(cmd, "\n",  output)
            outputList.append(output)
            warning("clock: dsRTC; set hwclock cmd='%s' rc=%s output=%s", cmd, rc, output)
            if rc != 0:
                return f"dsRTC failed to set hardware clock;\ncmd='{cmd}' rc={rc}\n{nn.join(outputList)}"
                
            return f"success\n{nn.join(outputList)}"
        except IOError as e:
            warning("clock: Set hwclock; cmd='%s' error=%s", cmd, e)
            return "return failed to set clock DS1307\ncnd='{cmd} error={e}'"
    else:
        # first try the regular command a bunch times
        # as the led rgb hats seem to interfere.
        rc = 12
        cmd = f"sudo {hwClockPath} --systohc --utc"
        for attempt in range(10):
            rc, output = runCommand(cmd)
            warning("clock: Set hwclock;\ncmd='%s' rc=%s\noutput=%s", cmd, rc, output)
            if not rc:
                break
        
            time.sleep(0.25)

        outputList.append(output)
        if not rc:
            return f"success\n{nn.join(outputList)}"

    # next and last try the special fixit command a bunch times
    cmd = f"sudo {hwClockPath} --systohc --verbose --noadjfile --utc"
    for attempt in range(10):
        rc, output = runCommand(cmd)
        warning("clock: Special set hwclock;\ncmd='%s' rc=%s\noutput=%s", cmd, rc, output)
        outputList.append(output)
        if not rc:
            break
        
        time.sleep(0.25)

    if rc:
        error("clock: Sadly, total failure to set hwclock; lastcmd='%s' rc=%s", cmd, rc)
        
        # if nothing else works then setting the clock before the display starts so
        # exit

        return f"failed to set the hardware clock; restarting clock server\n{nn.join(outputList)}"

    if doRestart:
        sys.exit()

    return nn.join(outputList)


def checkForHardwareClock():
    global hasHardwareClock
    
    hasHardwareClock = hasRealTimeClock()
