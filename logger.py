import os
import os.path
import sys
import time
from collections import deque
from logging import CRITICAL, ERROR, WARNING, INFO, DEBUG, \
    Formatter as logging_Formatter, \
    getLogger as logging_getLogger, \
    Handler as logging_Handler

import traceback as tb


log_max_list = 2048 # pylint: disable=invalid-name
log_std_out = None # pylint: disable=invalid-name

log_level = INFO  # pylint: disable=invalid-name

class TailLogHandler(logging_Handler):
    def __init__(self, entries, to_stderr=False):
        logging_Handler.__init__(self)
        self.entries = entries
        self.to_stderr = to_stderr

    def emit(self, record):
        local_time = time.localtime(time.time())
        display_time = time.strftime("%H:%M:%S", local_time)
        who = f"{record.module}: {record.funcName}:{record.lineno}"

        msg = self.format(record)

        self.entries.appendleft([display_time,
                                 record.levelname,
                                 who,
                                 msg,
                                 record.exc_info if record.exc_info else record.stack_info])

        if self.to_stderr:
            print(f"{display_time}: {record.levelname} - {who} - {msg}", file=sys.stderr)

    def send_to_stderr(self, on=False):
        self.to_stderr = on


class TailLogger:
    def __init__(self, maxlen, to_stderr=False):
        self.log_entries = deque(maxlen=maxlen)
        self.handler = TailLogHandler(self.log_entries, to_stderr)
        self.to_stderr = to_stderr

    def contents(self):
        return self.log_entries

    def send_to_stderr(self, on=False):
        self.to_stderr = on
        self.handler.send_to_stderr(on)

level_map = {"critical": CRITICAL,
             "error":    ERROR,
             "warning":  WARNING,
             "info":     INFO,
             "debug":    DEBUG,
             "all":      1,
             "none":     0}

logger = logging_getLogger(__name__)

tail = TailLogger(log_max_list)
log_entries = tail.log_entries

formatter = logging_Formatter('%(message)s')

log_handler = tail.handler
log_handler.setFormatter(formatter)

logger.addHandler(log_handler)

logger.setLevel(INFO)
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
critical = logger.critical
exception = logger.exception
log = logger.log
getEffectiveLevel = logger.getEffectiveLevel

def getLevelName():  # pylint: disable=invalid-name
    level = getEffectiveLevel()

    if level <= DEBUG:
        return "debug"

    if level <= INFO:
        return "info"

    if level <= WARNING:
        return "warning"

    return "error"

traceback = tb.print_stack

setLevel = logger.setLevel

env_debug = os.environ.get("DEBUG", "")
file_debug = os.path.exists("DEBUG") or os.environ.get("DEBUGFILE", "")

def clear_logs():
    log_entries.clear()

def log_to_stdout():
    log_handler.send_to_stderr(True)

if file_debug:
    print("logging to file")
    log_handler.send_to_stderr(True)

if env_debug:
    log_level = DEBUG
    print(env_debug)
    try:
        log_level = int(env_debug)
    except (TypeError, ValueError):
        try:
            log_level = level_map[env_debug.lower()]
        except KeyError:
            if env_debug:
                warning("logger Could not parse DEBUG: <%s>", env_debug)

setLevel(log_level)

info("logger: logging level is set to: %s %s", getEffectiveLevel(), getLevelName())
