#!/usr/bin/env python
# encoding: utf-8

import sys
import time

ignoreDefaults ={"write", "<module>", "<listcomp>", "<genexpr>", "<dictcomp>", "<lambda>"}
ignore = ignoreDefaults.copy()

startTime = 0
outfile = None
systemDirs = set()
specialDirs = {"<string>", "<frozen zipimport>", ""}
sitePackages = set()

# this caches system modules as they are found to avoid
# expensive lookups the second time they are seen.
systemModules = set()

#use to count calls so that the call can be paired with the return
counter = 0
pyInstaller = False
pyInstallerLibPath = "/<<<unknown>>>/"
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

    if filename in specialDirs or filename in systemModules:
        return

    if "/PyInstaller/loader" in filename:
        systemModules.add(filename)
        return
        
    if filename.startswith("<frozen importlib._bootstrap"):
        systemModules.add(filename)
        return

    dir = filename.rsplit('/', 1)[0]
    if dir in systemDirs:
        systemModules.add(filename)
        return

    # slow check
    for p in systemDirs:
        if dir.startswith(p):
            isSystem = True

            for p in sitePackages:
                if dir.startswith(p):
                    isSystem = False
                    break
                
            if isSystem:
                systemModules.add(filename)
                return

    #pyinstaller based removal
    if pyInstaller:
        if pyInstallerLibPath in filename:
            if "site-packages" not in filename:
                systemModules.add(filename)
                return

    counter += 1
    st = time.time()
    print('       - %d > %s %s on line %s of %s' % (counter, time.strftime("%H:%M:%S", time.localtime(st)), func_name, line_no, filename),file=outfile)
    return Tracer(st, counter)


def start(skipList=set(), filename=None):
    global ignore, startTime, outfile, systemDirs, version, versionMinor, sitePackages, counter, pyInstaller, pyInstallerLibPath

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
    versionMinor = f"{sys.version_info[0]}.{sys.version_info[1]}"

    for p in sys.path:
        if p.endswith("base_library.zip"):
            pyInstaller = True

    if pyInstaller:
        pyInstallerLibPath
        pyInstallerLibPath = f"/{version}/lib/python{versionMinor}/"
        print("pyInstallerLibPath:", pyInstallerLibPath, file=outfile)
    

    systemDirs = set(filter(lambda s: "site-packages" not in s and versionMinor in s, sys.path))
    print("systemDirs:", systemDirs, file=outfile)
    sitePackages = set(filter(lambda s: "site-packages" in s, sys.path))

    startTime = time.time()
    
    ignore = ignoreDefaults | skipList
        
    sys.settrace(trace_calls)

def stop():
    sys.settrace(None)
    if outfile:
        outfile.close()
    
if __name__ == "__main__":
    import re
    myc = re.compile(r"\w*")
    
    def c(input):
        print('input =', input)
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
