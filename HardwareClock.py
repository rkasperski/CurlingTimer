import os
import sys
from datetime import datetime, timezone
from time import monotonic as time_monotonic

from Logger import warning, error, info, exception
import DS3231
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
        dsRTC = DS3231.DS3231()
    except OSError as e:
        info("hwclock: no hardware clock clock %s", e)
        return False

    info("hwclock: found I2C DS3231")
    hwClockPath = "/usr/sbin/cc_hwclock"

    try:
        rtcTime = dsRTC.getDateTime(utc=True)
        curTime = datetime.now(timezone.utc)

        warning("hwclock: i2c read ds3231 hasRealTimeClock=1")

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
    startTime = time_monotonic()

    warning("clock: set request secsFromMidnight=%s date=%s tz=%s", newTimeSecsFromMidnight, newDate, newTimeZone)
    outputList = []
    nn = "\n"

    try:
        if newTimeZone:
            cmd = f'sudo timedatectl set-timezone "{newTimeZone}"'
            rc, output = runCommand(cmd)

            if rc:
                outputList.append(output)
                error("clock: failed to set timezone; timezone=%s cmd='%s' rc=%s output=%s", newTimeZone, cmd, rc, output)
                return f"failed to set timezone: {newTimeZone}\ncmd='{cmd}' rc={rc}\n{nn.join(outputList)}"
            else:
                outputList.append(f"set new timezone {newTimeZone}")
                info("clock: Set timezone; timezone=%s", newTimeZone)
    
        if newTimeSecsFromMidnight:
            newTimeSecsFromMidnight = newTimeSecsFromMidnight + (time_monotonic() - startTime)
            timeStr = f"{int(newTimeSecsFromMidnight / 3600)}:{int(newTimeSecsFromMidnight % 3600/60):-02d}:{int(newTimeSecsFromMidnight % 60):02d}"
            
            cmd = f'sudo /bin/date +"%T" -s "{timeStr}"'
            info("clock: set cmd: %s", cmd)
            rc, output = runCommand(cmd)

            if rc:
                outputList.append(output)
                error("failed to set time; time=%s cmd='%s' rc=%s output=%s", timeStr, cmd, rc, output)
                return f"failed to set time({timeStr}; cmd='{cmd}' rc={rc}\n{nn.join(outputList)}"
            else:
                outputList.append("set time done")
                info("clock: Set time; time='%s'", timeStr)
                
        if newDate:
            cmd = f'sudo /bin/date +"%F" -s "{newDate} $(date +%H:%M:%S)"'
            rc, output = runCommand(cmd)
            
            if rc:
                outputList.append(output)
                error("failed to set date; new date=%s cmd='%s' rc=%s output=%s", newDate, cmd, rc, output)
                return f"failed to set date({newDate};\ncmd='{cmd}' rc={rc}\n{nn.join(outputList)}"
            else:
                outputList.append("set date done")
                info("clock: Set date; date=%s", newDate)

    except Exception as e:
        outputList.append(f"update clock time badness {e}")
        error("clock: exception %s set timedate '%s'", e, data, exc_info=True)

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
            error("clock: Set hwclock; cmd='%s' error=%s", cmd, e)
            return "return failed to set clock DS3231\ncnd='{cmd} error={e}'"
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
