#!/usr/bin/env python
# encoding: utf-8

import sys
import time

ignore_defaults ={"write", "<module>", "<listcomp>", "<genexpr>", "<dictcomp>", "<lambda>"}
ignore = ignore_defaults.copy()

start_time = 0
outfile = None
system_dirs = set()
special_dirs = {"<string>", "<frozen zipimport>", ""}
site_packages = set()

# this caches system modules as they are found to avoid
# expensive lookups the second time they are seen.
system_modules = set()

#use to count calls so that the call can be paired with the return
counter = 0
py_installer = False
py_installer_lib_path = "/<<<unknown>>>/"
version = "unknown"
minorVersion = "unknown"

class Tracer:
    def __init__(self, when, id):
        self.t = when
        self.id = id

    def __call__(self, frame, event, arg):
        if event == "return":
            co = frame.f_code
            func_name = co.co_name
            line_no = frame.f_lineno
            filename = co.co_filename

            et = time.time()
            print('%8.4f %d < %s %s on line %s of %s' % (et - self.t, self.id, time.strftime("%H:%M:%S", time.localtime(et)), func_name, line_no, filename),file=outfile)       

def trace_calls(frame, event, arg):
    global counter

    if event != 'call':
        return

    co = frame.f_code
    func_name = co.co_name

    if func_name[0] == '<':
        return

    if func_name in ignore:
        return

    line_no = frame.f_lineno
    filename = co.co_filename

    if filename in special_dirs or filename in system_modules:
        return

    if "/PyInstaller/loader" in filename:
        system_modules.add(filename)
        return

    if filename.startswith("<frozen importlib._bootstrap"):
        system_modules.add(filename)
        return

    directory = filename.rsplit('/', 1)[0]
    if directory in system_dirs:
        system_modules.add(filename)
        return

    # slow check
    for p in system_dirs:
        if directory.startswith(p):
            is_system = True

            for p in site_packages:
                if directory.startswith(p):
                    is_system = False
                    break

            if is_system:
                system_modules.add(filename)
                return

    #pyinstaller based removal
    if py_installer:
        if py_installer_lib_path in filename:
            if "site-packages" not in filename:
                system_modules.add(filename)
                return

    counter += 1
    st = time.time()
    str_t = time.strftime("%H:%M:%S", time.localtime(st))
    print(f'       - %{counter} > {str_t} {func_name} on line {line_no} of {filename}',
          file=outfile)
    return Tracer(st, counter)


def start(skipList=set(), filename=None):
    global ignore, start_time, outfile, system_dirs, \
        version, version_minor, site_packages, counter, \
        py_installer, py_installer_lib_path

    counter = 0

    if filename:
        outfile = open(filename, "w")
    else:
        outfile = sys.stdout

    print("path:", sys.path, file=outfile)
    print("version:", sys.version, file=outfile)
    print("prefix:", sys.prefix, file=outfile)
    version = f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"
    print("version:", version, file=outfile)
    version_minor = f"{sys.version_info[0]}.{sys.version_info[1]}"

    for p in sys.path:
        if p.endswith("base_library.zip"):
            py_installer = True

    if py_installer:
        py_installer_lib_path = f"/{version}/lib/python{versionM_minor}/"
        print("py_installer_lib_path:", py_installer_lib_path, file=outfile)


    system_dirs = set(filter(lambda s: "site-packages" not in s and versionM_minor in s, sys.path))
    print("system_dirs:", system_dirs, file=outfile)
    site_packages = set(filter(lambda s: "site-packages" in s, sys.path))

    start_time = time.time()

    ignore = ignore_defaults | skipList

    sys.settrace(trace_calls)

def stop():
    sys.settrace(None)
    if outfile:
        outfile.close()

if __name__ == "__main__":
    import re
    myc = re.compile(r"\w*")

    def c(data):
        print('input =', data)
        print('Leaving c()')

    def b(arg):
        val = arg * 5
        c(val)
        print('Leaving b()')

    def a():
        print(time.time())
        b(2)
        print('Leaving a()')

    start(filename="splog2")
    t = Tracer(11, 0)
    t(None, None,None)
    a()
    stop()
