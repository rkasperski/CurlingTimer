import os
import os.path
import sys
import time
from collections import deque
import logging
import traceback as tb

logMaxList = 2048
logStdOut = None

CRITICAL = logging.CRITICAL
ERROR = logging.ERROR
WARNING = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG
NONE = 0

logLevel = WARNING

class TailLogHandler(logging.Handler):
    def __init__(self, logEntries=100, toStderr=False):
        logging.Handler.__init__(self)
        self.logEntries = logEntries
        self.toStderr = toStderr

    def emit(self, r):
        localTime = time.localtime(time.time())
        displayTime = time.strftime("%H:%M:%S", localTime)
        who = f"{r.module}: {r.funcName}:{r.lineno}"
        
        msg = self.format(r)

        self.logEntries.appendleft([displayTime, r.levelname, who, msg, r.exc_info if r.exc_info else r.stack_info])
        

        if self.toStderr:
            print(f"{displayTime}: {r.levelname} - {who} - {msg}", file=sys.stderr)

    def sendToStderr(self, on=False):
        self.toStderr = on

        
class TailLogger(object):
    def __init__(self, maxlen, toStderr=False):
        self.logEntries = deque(maxlen=maxlen)
        self.handler = TailLogHandler(self.logEntries, toStderr)
        self.toStderr = toStderr

    def contents(self):
        return self.logEntries

    def sendToStderr(self, on=False):
        self.toStderr = on
        self.handler.sendToStderr(on)

        
levelMap = {"critical": CRITICAL,
            "error":    ERROR,
            "warning":  WARNING,
            "info":     INFO,
            "all":      DEBUG,
            "debug":    DEBUG,
            "none":     0}

logger = logging.getLogger(__name__)

tail = TailLogger(logMaxList)
logEntries = tail.logEntries

formatter = logging.Formatter('%(message)s')

log_handler = tail.handler
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)

logger.setLevel(logging.WARNING)

debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
critical = logger.critical
exception = logger.exception
log = logger.log
getEffectiveLevel = logger.getEffectiveLevel

traceback = tb.print_stack

setLevel = logger.setLevel

envDebug = os.environ.get("DEBUG", None) or os.environ.get("DEBUGFILE", None)
fileDebug = os.path.exists("DEBUG") or os.environ.get("DEBUGFILE", None)


def clearLogs():
    logEntries.clear()

def logToStdOut():
    log_handler.sendToStderr(True)

if fileDebug:
    log_handler.sendToStderr(True)

if envDebug:
    logLevel = logging.DEBUG
    print(envDebug)
    try:
        logLevel = int(envDebug)
    except (TypeError, ValueError):
        try:
            logLevel = levelMap[envDebug.lower()]
        except KeyError:
            if envDebug:
                warning("logger", "Could not parse DEBUG: <level>", envDebug)

logger.setLevel(logLevel)
info("logger: logging level is set to: %s", getEffectiveLevel())
