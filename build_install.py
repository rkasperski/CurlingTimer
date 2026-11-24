"""
builds the installable packages.
There are three separate executables
- CurlingTimer for led displays
- CurlingTimer for tvs
- BreakTimer
"""
import sys
import os
import re
import argparse
from update_version import write_build_date, update_version


def create_parser():
    """
    Creates the parser for the command line
    """
    parser = argparse.ArgumentParser(description= """Build distributable clock timer targets.

The version number is automatically managed. The build number is incremented
on every build attempt regardless of the success of failure of the attempt.
The major number is only incremented when the -M flag is passed. It sets the
minor number to 1 and overrides any other handling of the minor number.
If the current version has no label or the label is 'release' the minor
version number will be incremented. -m forces the minor number to be incremented.
Only one of --label, --release or --release-candidate can be provided.
""")

    parser.add_argument('-l', '--label',
                        type=str, default=None,
                        help="defines the label part of the version string.")

    parser.add_argument('-r', '--release',
                        action='store_true',
                        help="defines the label portion as 'release'")

    parser.add_argument('-c', '--release-candidate', '--rc',
                        action='store_true',
                        help="defines the label portion as 'rcN' where N is auto increasing from 1" \
                        "this is the default")

    parser.add_argument('--confirm', action='store_true',
                        help="when present pyinstaller will prompt to overwrite data.")

    parser.add_argument('--clean', action='store_true', default="",
                        help="when present pyinstaller will re-analyze before building python blobs")

    parser.add_argument('-M', '--major', action='store_true',
                        help="when present the major version number will be updated. " \
                        "Updates the major number major.minor.build[.label]")

    parser.add_argument('-m', '--minor', action='store_true',
                        help="when present the minor version number will be updated. " \
                        "Updates the minor number major.minor.build[.label].")

    parser.add_argument('--tv', action='store_true',
                        help="build for display on tv")

    parser.add_argument('--hwclock', action='store_true',
                        help="build for hwclock(DS3231). Can only specify one of hwclock, led, tv or breaktimer")

    parser.add_argument('--led', action='store_true',
                        help="build for display on rgb led matrix. Can only specify " \
                        "one of hwclock, led, tv or breaktimer")

    parser.add_argument('--breaktimer', action='store_true',
                        help="build for break timers. Can only specify one of hwclock, led, tv or breaktimer")

    parser.add_argument('--verbose', action='store_true',
                        help="display verbose messages. Can only specify one of hwclock, led, tv or breaktimer")

    return parser

re_version_date_matcher = re.compile(r'(?P<major>\d+)\.(?P<minor>\d+)\.(?P<build>\d+)(\.(?P<label>\w+))? - '
                                     r'(?P<day_name>\w+) (?P<month_name>\w+) (?P<month_day>\d+) '
                                     r'(?P<hour>\d+):(?P<minute>\d+):(?P<second>\d+) (?P<year>\d+)')

def add_version_and_build_date_to_release_notes(version, build_date, fn="ReleaseNotes.txt"):
    """
    adds build and version to release notes
    """
    os.system("cp info/ReleaseNotes.txt info/ReleaseNotes.txt.old")
    with open("info/ReleaseNotes", "w", encoding="utf-8") as new_release_notes_f:
        with open("info/ReleaseNotes.txt", "r", encoding="utf-8") as old_release_notes_f:
            old_release_notes = old_release_notes_f.readlines()

        first_line = old_release_notes[0].strip()

        m = re_version_date_matcher.match(first_line)
        print(m.groupdict())

        if (label := m.group("label")) is not None and label != "release":
            old_release_notes.pop(0)

        print(f"{version} - {build_date}", file=new_release_notes_f)
        new_release_notes_f.writelines(old_release_notes)

    os.system("cp info/ReleaseNotes info/ReleaseNotes.txt")


# pylint: disable=too-many-statements
# pylint: disable=too-many-branches
def main():
    """
    builds the requested executable
    """
    parser = create_parser()
    args = parser.parse_args()

    label = "rc"
    if sum([x != None for x in [args.label, args.release, args.release_candidate]]) <= 1:
        print("must specify only one of --label --release or --release-candidate")
        sys.exit(4)

    if args.label:
        label = args.label
    elif args.release:
        label = "release"

    if sum([args.tv, args.led, args.breaktimer, args.hwclock]) != 1:
        print("must specify only one of --tv --led --breaktimer --hwclock")
        sys.exit(4)

    version_str = update_version(fn="info/version.txt",
                                 update_major=args.major, update_minor=args.minor, label=label)

    build_date = write_build_date(fn="info/build_date.txt")
    os.system("cp info/build_date.txt info/build_date")

    print(f"processing version={version_str}")

    py_installer_options = []

    if args.clean:
        py_installer_options.append("--clean")

    if not args.confirm:
        py_installer_options.append("--noconfirm")

    with open("version.py", "w", encoding="utf-8") as f:
        print(f'version="{version_str}"', file=f)
        print(f'build_date="{build_date}"', file=f)

    add_version_and_build_date_to_release_notes(version_str, build_date)

    tar_tgt = None
    tar_src = None
    spec_file = None
    if args.led:
        spec_file = "curling_timer.led.spec"
        tar_tgt = f"CurlingTimer.led.{version_str}.tgz"
        sum_tgt = f"CurlingTimer.led.{version_str}.sum.txt"
        tar_src = "CurlingTimer.led"
        transform_arg = "--transform 's,^CurlingTimer.led,CurlingTimer,'"
    elif args.tv:
        spec_file = "CurlingTimer.tv.spec"
        tar_tgt = f"CurlingTimer.tv.{version_str}.tgz"
        sum_tgt = f"CurlingTimer.tv.{version_str}.sum.txt"
        tar_src = "CurlingTimer.tv"
        transform_arg = "--transform 's,^CurlingTimer.tv,CurlingTimer,'"
    elif args.breaktimer:
        spec_file = "break_timer.spec"
        tar_tgt = f"BreakTimer.{version_str}.tgz"
        sum_tgt = f"BreakTimer.{version_str}.sum.txt"
        tar_src = "BreakTimer"
        transform_arg = ""
    else:
        spec_file = None
        tar_tgt = f"hwclock.{version_str}.tgz"
        sum_tgt = f"hwclock.{version_str}.sum.txt"
        tar_src = "cc_hwclock"
        transform_arg = ""

    if spec_file:
        cmd = f"pyinstaller {' '.join(py_installer_options)} {spec_file}"
    else:
        cmd = "pyinstaller --onefile hwclock.py --name cc_hwclock"

    print(cmd)
    if os.system(cmd):
        print("failed to build python blob")
        sys.exit(12)

    tgt_path = os.path.join("dist", tar_tgt)
    sum_path = os.path.join("dist", sum_tgt)

    cmd = f"tar -C dist -czf {tgt_path} {transform_arg} {tar_src}"
    print(cmd)
    if os.system(cmd):
        print("failed to build distributable tar file")
        os.remove(tgt_path)
        sys.exit(12)

    if os.system(f"sha512sum '{tgt_path}' | cut -d ' ' -f1 > {sum_path}"):
        print("failed to build distributable tar file")
        os.remove(tgt_path)
        os.remove(sum_path)
        sys.exit(12)

    print(f"finished processing version={version_str}")
            


if __name__ == "__main__":
    main()
