import os
import sys
from datetime import datetime, timezone
from time import monotonic as time_monotonic, \
    sleep as time_sleep

from logger import warning, error, info
import ds3231
from utils import run_command


ds_rtc = None
hw_clock_path = "/usr/sbin/hwclock"
has_physical_hardware_clock = False


def has_real_time_clock():
    global ds_rtc, hw_clock_path

    if os.path.exists("/dev/rtc"):
        cmd = f"sudo {hw_clock_path} --test --utc"
        rc, output = run_command(cmd)
        warning("hwclock: /dev/rtc hasRealTimeClock=1; %s; rc=%s", cmd, rc)
        return True

    try:
        ds_rtc = ds3231.DS3231()
    except OSError as e:
        info("hwclock: no hardware clock clock %s", e)
        return False

    info("hwclock: found I2C DS3231")
    hw_clock_path = "/usr/sbin/cc_hwclock"

    try:
        rtc_time = ds_rtc.get_date_time(utc=True)
        cur_time = datetime.now(timezone.utc)

        warning("hwclock: i2c read ds3231 hasRealTimeClock=1")

        if rtc_time.timestamp() - cur_time.timestamp() > 3:
            rc, output = run_command(f"sudo date -s '{ds_rtc.get_date_str(utc=True)}'")
            warning("hwclock: system time is behind '%s' --> %s; rc={%s}",
                    cur_time.strftime('%a %-d %b %Y %-I:%M:%S %p %Z'),
                    rtc_time.strftime('%a %-d %b %Y %-I:%M:%S %p %Z'),
                    rc)

        return True
    except IOError:
        pass

    warning("hwclock: has_real_time_clock=0")
    return False


def update_clock_time(new_time_secs_from_midnight=None, new_date=None, new_time_zone=None):
    start_time = time_monotonic()

    warning("clock: set request secsFromMidnight=%s date=%s tz=%s", new_time_secs_from_midnight, new_date, new_time_zone)
    output_list = []
    nn = "\n"

    try:
        if new_time_zone:
            cmd = f'sudo timedatectl set-timezone "{new_time_zone}"'
            rc, output = run_command(cmd)

            if rc:
                output_list.append(output)
                error("clock: failed to set timezone; timezone=%s cmd='%s' rc=%s output=%s", new_time_zone, cmd, rc, output)
                return f"failed to set timezone: {new_time_zone}\ncmd='{cmd}' rc={rc}\n{nn.join(output_list)}"

            output_list.append(f"set new timezone {new_time_zone}")
            info("clock: Set timezone; timezone=%s", new_time_zone)

        if new_time_secs_from_midnight:
            new_time_secs_from_midnight = new_time_secs_from_midnight + (time_monotonic() - start_time)
            time_str = f"{int(new_time_secs_from_midnight / 3600)}:{int(new_time_secs_from_midnight % 3600/60):-02d}:{int(new_time_secs_from_midnight % 60):02d}"

            cmd = f'sudo /bin/date +"%T" -s "{time_str}"'
            info("clock: set cmd: %s", cmd)
            rc, output = run_command(cmd)

            if rc:
                output_list.append(output)
                error("failed to set time; time=%s cmd='%s' rc=%s output=%s", time_str, cmd, rc, output)
                return f"failed to set time({time_str}; cmd='{cmd}' rc={rc}\n{nn.join(output_list)}"

            output_list.append("set time done")
            info("clock: Set time; time='%s'", time_str)

        if new_date:
            cmd = f'sudo /bin/date +"%F" -s "{new_date} $(date +%H:%M:%S)"'
            rc, output = run_command(cmd)

            if rc:
                output_list.append(output)
                error("failed to set date; new date=%s cmd='%s' rc=%s output=%s", new_date, cmd, rc, output)
                return f"failed to set date({new_date};\ncmd='{cmd}' rc={rc}\n{nn.join(output_list)}"

            output_list.append("set date done")
            info("clock: Set date; date=%s", new_date)

    except Exception as e:
        output_list.append(f"update clock time badness {e}")
        error("clock: exception %s set timedate '%s'", e, output_list, exc_info=True)

    return nn.join(output_list)


def set_hardware_clock(do_restart=False):
    output_list = []
    nn = '\n'
    if ds_rtc:
        cmd = f"sudo {hw_clock_path} --systohc --utc"
        try:
            ds_rtc.set_to_system_time()
            rc, output = run_command(cmd)
            output_list.append(output)
            warning("clock: ds_rtc; set hwclock cmd='%s' rc=%s output=%s", cmd, rc, output)
            if rc != 0:
                return f"ds_rtc failed to set hardware clock;\ncmd='{cmd}' rc={rc}\n{nn.join(output_list)}"

            return f"success\n{nn.join(output_list)}"
        except IOError as e:
            error("clock: Set hwclock; cmd='%s' error=%s", cmd, e)
            return "return failed to set clock DS3231\ncnd='{cmd} error={e}'"
    else:
        # first try the regular command a bunch times
        # as the led rgb hats seem to interfere.
        rc = 12
        cmd = f"sudo {hw_clock_path} --systohc --utc"
        for _ in range(10):
            rc, output = run_command(cmd)
            warning("clock: Set hwclock;\ncmd='%s' rc=%s\noutput=%s", cmd, rc, output)
            if not rc:
                break

            time_sleep(0.25)

        output_list.append(output)
        if not rc:
            return f"success\n{nn.join(output_list)}"

    # next and last try the special fixit command a bunch times
    cmd = f"sudo {hw_clock_path} --systohc --verbose --noadjfile --utc"
    for _ in range(10):
        rc, output = run_command(cmd)
        warning("clock: Special set hwclock;\ncmd='%s' rc=%s\noutput=%s", cmd, rc, output)
        output_list.append(output)
        if not rc:
            break

        time_sleep(0.25)

    if rc:
        error("clock: Sadly, total failure to set hwclock; lastcmd='%s' rc=%s", cmd, rc)

        # if nothing else works then setting the clock before the display starts so
        # exit

        return f"failed to set the hardware clock; restarting clock server\n{nn.join(output_list)}"

    if do_restart:
        sys.exit()

    return nn.join(output_list)

def has_hardware_clock():
    global has_physical_hardware_clock

    return has_physical_hardware_clock

def check_for_hardware_clock():
    global has_physical_hardware_clock

    has_physical_hardware_clock = has_real_time_clock()
