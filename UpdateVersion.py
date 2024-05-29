import time


def updateVersion(fn="version.txt", updateMinor=True):
    version = getVersion(fn)

    print(f"Old: {version}")

    sp = version.split(".")

    if updateMinor:
        sp[1] = str(int(sp[1]) + 1)
    else:
        sp[0] = str(int(sp[0]) + 1)

    version = '.'.join(sp)

    print(f"New: {version}")
    writeVersion(version, fn)

    
def getVersion(fn="version.txt"):
    try:
        with open(fn) as f:
            s = f.readline().strip()
    except Exception:
        print("defaulting to 1")
        return "1.0"

    return s


def writeVersion(v, fn="version.txt"):
    try:
        with open(fn, "w") as f:
            print(v, file=f)

    except Exception:
        print("Ooops")
        raise

    
def writeBuildDate(fn="buildDate.txt"):
    with open(fn, "w") as f:
        print(time.asctime(), file=f)

        
def getBuildDate(fn="buildDate.txt"):
    try:
        with open(fn) as f:
            s = f.readline().strip()
    except Exception:
        print("Oops")
        raise

    return s
