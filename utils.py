import fcntl
import glob
import os
import subprocess
import pwd
import random
import socket
import string
import sys
import time
import traceback as tb
import grp
from collections import namedtuple
import psutil

from logger import error, warning


YEAR_IN_SECONDS = 365 * 86400


def to_int(s, default=0):
    try:
        return int(s)
    except (TypeError, ValueError):
        return default


def seconds_to_str(s):
    s += 0.99

    days = ""
    if s > 86400:
        days = str(int(s/86400.0)) + " day(s) "
        s = s % 86400

    hrs = ""
    if s > 3600:
        hrs = str(int(s/3600.0)) + ":"
        s = s % 3600

    return f"{days}{hrs}{int(s / 60)}:{int(s) % 60:02d}"


def str_to_seconds(s, default=None):
    if isinstance(s, (int, float)):
        return s

    try:
        time_limit = s.split(':')
        seconds = float(time_limit[-1])
        if len(time_limit) >= 2:
            seconds += float(time_limit[-2]) * 60
            if len(time_limit) >= 3:
                seconds += float(time_limit[-3]) * 3600

    except (TypeError, IndexError, ValueError):
        if default is None:
            raise

        seconds = default

    return seconds


def generate_pin(size=6, chars=string.ascii_uppercase):
    return ''.join(random.choice(chars) for x in range(size))


def my_ip_address():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except socket.error:
            ip = '127.0.0.1'

        s.close()
    return ip

def my_host_name():
    return socket.gethostname()


def drop_root_privileges(user_name=None, groups=None):
    if os.getuid() != 0:
        return

    if groups is None:
        groups=[]

    # Get the uid/gid from the name
    if not user_name:
        user_name = os.getenv("SUDO_USER")

    pwnam = pwd.getpwnam(user_name)

    # Remove group privileges
    if groups is not None:
        os.setgroups([grp.getgrnam(n).gr_gid for n in groups])

    # Try setting the new uid/gid
    os.setgid(pwnam.pw_gid)
    os.setuid(pwnam.pw_uid)

    # Ensure a reasonable umask
    os.umask(0o22)


def singleton(name):
    lockfile = '/tmp/lock01_' + name
    with open(lockfile, 'w', encoding="utf-8") as fp:
        try:
            fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            warning("% exitting as I am already running", name)
            # another instance is running
            sys.exit(0)

    return fp


MemUsage = namedtuple("MemUsage", "time, vmUsed, vmFree, vmAvail, swpTot, swpUse, " \
                      "swpIn, swpOut, prcRSS, prcVMS, prcData, prcText, prcSwap")

def mem_usage():
    vm = psutil.virtual_memory()
    pm = psutil.Process().memory_full_info()
    swp = psutil.swap_memory()

    local_time = time.localtime(time.time())
    display_time = time.strftime("%H:%M:%S %d/%m/%y", local_time)

    return MemUsage(display_time,
                    int(vm.used/1024), int(vm.free/1024), int(vm.available/1024),
                    int(swp.total/1024), int(swp.used/1024), int(swp.sin/1024), int(swp.sout/1024),
                    int(pm.rss/1024), int(pm.vms/1024), int(pm.data/1024), int(pm.text/1024), int(pm.swap/1024))


def clean_files(pattern):
    # get a recursive list of file paths that matches pattern including sub directories
    file_list = glob.glob(pattern, recursive=False)

    number_deletedeted = 0
    number_failed = 0
    # Iterate over the list of filepaths & remove each file.
    for file_path in file_list:
        try:
            os.remove(file_path)
            number_deletedeted += 1
        except OSError:
            number_failed += 1

    return (number_deletedeted, number_failed)


def read_file(fn):
    try:
        with open(fn, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def get_next_file_number(prm_file_path):
    largest_number = 0
    file_path_list = [prm_file_path] if isinstance(prm_file_path, str) else prm_file_path

    for file_path in file_path_list:
        for fn in glob.glob(file_path + '.*'):
            sp = fn.rsplit(".", 1)

            if sp[-1].isnumeric():
                largest_number = max(largest_number, int(sp[-1]))

    return largest_number + 1


def update_numbered_backup_files(file_path_pairs):
    """takes a list of file pairs to move. [[from, to]]"""

    n = get_next_file_number([x[1] for x in file_path_pairs])

    for from_file_path, to_file_path in file_path_pairs:
        if os.path.exists(to_file_path):
            try:
                backup_name = to_file_path + f".{n}"
                os.rename(to_file_path, backup_name)
            except Exception:
                raise OSError(f"failed to rename numbered backup file: {to_file_path} -> {backup_name}")  # pylint: disable=raise-missing-from

        try:
            os.rename(from_file_path, to_file_path)
        except Exception:
            raise OSError("failed to rename file: {from_file_path} -> {to_file_path}")  # pylint: disable=raise-missing-from


def traceback(msg=None):
    if msg:
        print(msg, file=sys.stderr)

    print("".join(tb.format_list(tb.extract_stack(limit=50)[1:])), file=sys.stderr)


def get_file_age_in_seconds(filepath):
    """
    Calculates the age of a file in seconds based on its last modification time.
    """
    try:
        # Get the last modification time of the file (timestamp in seconds since epoch)
        modification_time = os.path.getmtime(filepath)

        # Get the current time (timestamp in seconds since epoch)
        current_time = time.time()

        # Calculate the difference
        file_age = current_time - modification_time
        return file_age
    except FileNotFoundError:
        error("Error: File not found at %s", filepath)
    except Exception as e:  # pylint: disable=broad-exception-caught
        error("An error occurred: %s", e)

    return None


def is_reboot_file_valid(reboot_loop_detector_func):
    if os.path.isfile(reboot_loop_detector_func):
        age = get_file_age_in_seconds(reboot_loop_detector_func)

        if age is None:
            return False


        return age <= 60

    return False


def head_tail(fn, head_lines=1, tail_lines=5, average_line_length=132):
    if (head_lines + tail_lines <= 0) or not os.path.isfile(fn):
        return [[], []]

    pos = (tail_lines * average_line_length) + 1

    head = []
    tail = []

    # set file pointer to end
    with open(fn, encoding="utf-8") as f:
        while len(head) < head_lines:
            try:
                ln = f.readline()
                if ln is None:
                    break

                head.append(ln.rstrip())
            except IOError:
                break

        f.seek(0, os.SEEK_END)
        seek_pos = f.tell()

        while len(tail) <= tail_lines and seek_pos != 0:
            seek_pos -= pos
            try:
                f.seek(seek_pos, os.SEEK_SET)
            except ValueError:
                # read the while file
                f.seek(0,os.SEEK_SET)
                seek_pos = 0
            except IOError:
                break
            finally:
                tail = f.readlines()

            pos *= 2

    return [head, [ln.rstrip() for ln in tail[-min(tail_lines, len(tail)):]]]


def configure_wifi():
    rc = os.system("sudo /sbin/iwconfig wlan0 power off")
    if rc:
        error("Wifi: failed to turn power management off on wlan0 rc=%d", rc)
    else:
        warning("Wifi: turned power management off on wlan0")


def run_command(cmd):
    try:
        output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT)
        return 0, output
    except subprocess.CalledProcessError as e:
        return e.returncode, e.output
