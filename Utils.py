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

import SetupApp

from Logger import error, warning


yearInSeconds = 365 * 86400


def toInt(s, default=0):
    try:
        return int(s)
    except (TypeError, ValueError):
        return default


def secondsToStr(s):
    s += 0.99

    days = ""
    if s > 86400:
        days = str(int(s/86400.0)) + " day(s) "
        s = s % 86400

    hrs = ""
    if s > 3600:
        hrs = str(int(s/3600.0)) + ":"
        s = s % 3600.0

    return days + hrs + str(int(s / 60)) + ":" + (("0" + "%0d" % (s % 60))[-2:])


def strToSeconds(s, default=None):
    if isinstance(s, (int, float)):
        return s

    try:
        timeLimit = s.split(':')
        seconds = float(timeLimit[-1])
        if len(timeLimit) >= 2:
            seconds += float(timeLimit[-2]) * 60
            if len(timeLimit) >= 3:
                seconds += float(timeLimit[-3]) * 3600

    except (TypeError, IndexError, ValueError):
        if default is None:
            raise

        seconds = default

    return seconds


def generatePIN(size=6, chars=string.ascii_uppercase):
    return ''.join(random.choice(chars) for x in range(size))


def myIPAddress():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except socket.error:
            IP = '127.0.0.1'

        s.close()
    return IP

def myHostName():
    return socket.gethostname()


def dropRootPrivileges(user_name=None, groups=[]):
    if os.getuid() != 0:
        return

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
    fp = open(lockfile, 'w')
    try:
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        warning(name + "exitting as I am already running")
        # another instance is running
        sys.exit(0)

    return fp


MemUsage = namedtuple("MemUsage", "time, vmUsed, vmFree, vmAvail, swpTot, swpUse, swpIn, swpOut, prcRSS, prcVMS, prcData, prcText, prcSwap")


def memUsage():
    vm = psutil.virtual_memory()
    pm = psutil.Process().memory_full_info()
    swp = psutil.swap_memory()

    localTime = time.localtime(time.time())
    displayTime = time.strftime("%H:%M:%S %d/%m/%y", localTime)

    return MemUsage(displayTime,
                    int(vm.used/1024), int(vm.free/1024), int(vm.available/1024),
                    int(swp.total/1024), int(swp.used/1024), int(swp.sin/1024), int(swp.sout/1024),
                    int(pm.rss/1024), int(pm.vms/1024), int(pm.data/1024), int(pm.text/1024), int(pm.swap/1024))


def cleanFiles(pattern):
    # get a recursive list of file paths that matches pattern including sub directories
    fileList = glob.glob(pattern, recursive=False)

    nDeleted = 0
    nFailed = 0
    # Iterate over the list of filepaths & remove each file.
    for filePath in fileList:
        try:
            os.remove(filePath)
            nDeleted += 1
        except OSError:
            nFailed += 1

    return (nDeleted, nFailed)


def readFile(fn):
    try:
        with open(fn) as f:
            return f.read()
    except FileNotFoundError:
        return


def getNextFileNumber(filePath):
    largestN = 0
    filePathList = [filePath] if isinstance(filePath, str) else filePath

    for filePath in filePathList:
        for fn in glob.glob(filePath + '.*'):
            sp = fn.rsplit(".", 1)

            if sp[-1].isnumeric():
                n = int(sp[-1])
                if n > largestN:
                    largestN = n

    return largestN + 1


def updateNumberedBackupFiles(filePathPairs):
    """takes a list of file pairs to move. [[from, to]]"""

    n = getNextFileNumber([x[1] for x in filePathPairs])

    for fromFilePath, toFilePath in filePathPairs:
        if os.path.exists(toFilePath):
            try:
                backupName = toFilePath + f".{n}"
                os.rename(toFilePath, backupName)
            except Exception:
                raise OSError(f"failed to rename numbered backup file: {toFilePath} -> {backupName}")

        try:
            os.rename(fromFilePath, toFilePath)
        except Exception:
            raise OSError("failed to rename file: {fromFilePath} -> {toFilePath}")


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
        print(f"Error: File not found at '{filepath}'")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    
def isRebootFileValid(rebootLoopDetectorFn):
    if os.path.isfile(rebootLoopDetectorFn):
        age = get_file_age_in_seconds(rebootLoopDetectorFn)

        if age is None:
            return False


        return age <= 60

    return False


def headTail(fn, headLines=1, tailLines=5, averageLineLength=132):
    if (headLines + tailLines <= 0) or not os.path.isfile(fn):
        return [[], []]

    pos = (tailLines * averageLineLength) + 1

    head = []
    tail = []

    # set file pointer to end
    with open(fn) as f:
        while len(head) < headLines:
            try:
                ln = f.readline()
                if ln is None:
                    break
                
                head.append(ln.rstrip())
            except IOError:
                break
            
        f.seek(0, os.SEEK_END)
        seekPos = f.tell()

        while len(tail) <= tailLines and seekPos != 0:
            seekPos -= pos
            try:
                f.seek(seekPos, os.SEEK_SET)
            except ValueError as e:
                # read the while file
                f.seek(0,os.SEEK_SET)
                seekPos = 0
            except IOError:
                break
            finally:
                tail = f.readlines()
                
            pos *= 2

    return [head, [ln.rstrip() for ln in tail[-min(tailLines, len(tail)):]]]


def ConfigureWifi():
    rc = os.system("sudo /sbin/iwconfig wlan0 power off")
    if rc:
        error("Wifi: failed to turn power management off on wlan0 rc=%d", rc)
    else:
        warning("Wifi: turned power management off on wlan0")


def runCommand(cmd):
    try:
        output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT)
        return 0, output
    except subprocess.CalledProcessError as e:
        return e.returncode, e.output
    
