"""
Handles the creation and update of the version number and build-date
"""
import time
from os import path, remove


def update_version(fn="version.txt", update_major=False, update_minor=False, label=None):
    version = get_version(fn)

    sp = version.split(".")
    major_no, minor_no, build_no = sp[0:3]
    build_no = int(build_no) + 1

    if update_major:
        major_no = int(major_no) + 1
        minor_no = 1
    elif update_minor:
        minor_no = int(minor_no) + 1
    else:
        if (len(sp) == 3 and (label is None or label in ["", "release"])) or \
           (len(sp) >= 4 and sp[3] == "release"):
            minor_no = int(minor_no) + 1

    new_version = f"{major_no}.{minor_no}.{build_no}"
    if label == "rc":
        label = "rc1"
        if  len(sp) >= 4 and sp[3].startswith("rc"):
            try:
                n = int(sp[3][2:])
                label = f"rc{n + 1}"
            except (ValueError, IndexError):
                pass

    if label:
        new_version = f"{new_version}.{label}"

    write_version(new_version, fn)

    return new_version

def get_version(fn="version.txt"):
    try:
        if path.isfile(fn):
            with open(fn, encoding="utf-8") as f:
                s = f.readline().strip()
        else:
            return "1.1.0.test"
    except OSError:
        print(f"Error while reading version: {e}")
        raise

    return s


def write_version(v, fn="version.txt"):
    try:
        with open(fn, "w", encoding="utf-8") as f:
            print(v, file=f)

    except OSError as e:
        print(f"Error while writing version: {e}")
        raise


def write_build_date(fn="build_date.txt"):
    when = time.asctime()
    
    try:
        with open(fn, "w", encoding="utf-8") as f:
            print(when, file=f)
    except OSError as e:
        print(f"Error while writing build date: {e}")

    return when

def get_build_date(fn="build_date.txt"):
    try:
        with open(fn, "r", encoding="utf-8") as f:
            s = f.readline().strip()
    except OSError:
        print(f"Error while reading build date: {e}")
        raise

    return s

def run_tests():
    fn = "test-version.txt"

    if path.isfile(fn):
        remove(fn)

    version = get_version(fn)
    print(version)
    assert version == "1.1.0.test"

    version = update_version(fn)
    print(version)
    assert version == "1.1.1"

    version = update_version(fn, label="rc")
    print(version)
    assert version == "1.1.2.rc1"

    version = update_version(fn, label="rc")
    print(version)
    assert version == "1.1.3.rc2"
    
    version = update_version(fn, label="rc")
    print(version)
    assert version == "1.1.4.rc3"

    version = update_version(fn, update_minor=True, label="rc1")
    print(version)
    assert version == "1.2.5.rc1"

    version = update_version(fn, update_major=True, label="rc1")
    print(version)
    assert version == "2.1.6.rc1"

    version = update_version(fn)
    print(version)
    assert version == "2.1.7"

    if path.isfile(fn):
        remove(fn)

    
if __name__ == '__main__':
    run_tests()
