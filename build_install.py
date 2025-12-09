import sys
import UpdateVersion
import os
import argparse


def createParser():
    parser = argparse.ArgumentParser(description='Build distributable clock targets')
    parser.add_argument('--confirm', action='store_true',
                        help="when present pyinstaller will prompt to overwrite data")
    
    parser.add_argument('--clean', action='store_true', default="",
                        help="when present pyinstaller will re-analyze before building python blobs")
    
    parser.add_argument('-v', '--no-version-update', action='store_true',
                        help="when present the build number will be incremented and major and minor version number will say the same. Updates the build number major.minor.build")
    
    parser.add_argument('-s', '--skip-build-increment', action='store_true',
                        help="when present the none of the build , major and minor version number will be incremented")
    
    parser.add_argument('-d', '--no-build-date-update', action='store_true',
                        help="when present the build date will not be updated")
    
    parser.add_argument('-b', '--skip-build', action='store_true',
                        help="skips rebuilding of the python blobs")
    
    parser.add_argument('--test', action='store_true',
                        help="do a test build. Doesn't increment version number")
    
    parser.add_argument('-t', '--skip-tar', action='store_true',
                        help="skips building of the tar file")
    
    parser.add_argument('-n', '--skip-release-notes', action='store_true',
                        help="skips replacement of latest with version and build date")

    parser.add_argument('--tv', action='store_true',
                        help="build for display on tv")
    
    parser.add_argument('--verbose', action='store_true',
                        help="display vrbose messages")
    
    return parser


def addVersionAndBuildDateToReleaseNotes(version, buildDate, test=False):
    if test:
        version = f"TEST - {version}.x"
        
    os.system("cp info/ReleaseNotes.txt info/ReleaseNotes.txt.old")
    with open("info/ReleaseNotes", "w") as newRelaseNotesF:
        with open("info/ReleaseNotes.txt", "r") as oldReleaseNotesF:
            oldReleaseNotes = oldReleaseNotesF.readlines()

        firstLine = oldReleaseNotes[0].strip()
        if firstLine.startswith("TEST - "):
            oldReleaseNotes = oldReleaseNotes[1:]
        elif firstLine.startswith(version):
            oldReleaseNotes = oldReleaseNotes[1:]

        print(f"{version} - {buildDate}", file=newRelaseNotesF)
        newRelaseNotesF.writelines(oldReleaseNotes)

    if not test:
        os.system("cp info/ReleaseNotes info/ReleaseNotes.txt")

        
def main():
    parser = createParser()
    args = parser.parse_args()

    if not args.test:
        if args.no_version_update:
            if not args.skip_build_increment:
                print("updating build number")
                UpdateVersion.updateVersion(fn="info/version.txt", updateMajor=False, updateMinor=False, updateBuild=True)
        else:
            UpdateVersion.updateVersion(fn="info/version.txt", updateMajor=False, updateMinor=True)

    if args.no_build_date_update:
        print("skipping build date update")
    else:
        UpdateVersion.writeBuildDate(fn="info/buildDate.txt")
        os.system("cp info/buildDate.txt info/builddate")

    pyInstallerOptions = []

    if args.clean:
        pyInstallerOptions.append("--clean")

    if not args.confirm:
        pyInstallerOptions.append("--noconfirm")

    if args.tv:
        os.system("touch build-for-tv")
    else:
        os.system("rm build-for-tv")

    versionNo = UpdateVersion.getVersion(fn="info/version.txt")
    buildDate = UpdateVersion.getBuildDate(fn="info/buildDate.txt")

    with open("Version.py", "w") as f:
        print(f'versionNo="{versionNo}"', file=f)
        print(f'buildDate="{buildDate}"', file=f)
            
    if args.skip_release_notes:
        print("skipping release notes generaton")
    else:
        addVersionAndBuildDateToReleaseNotes(versionNo, buildDate, test=args.test)

    if args.skip_build:
        print("skipping build")
    else:
        cmd = f"pyinstaller {' '.join(pyInstallerOptions)} CurlingTimer.spec"
        if args.verbose:
            print(f"{cmd=}")
        
        if os.system(cmd):
            print("failed to build python blob")
            sys.exit(12)

        cmd = "pyinstaller --onefile hwclock.py --name cc_hwclock"
        if args.verbose:
            print(f"{cmd=}")
        
        if os.system(cmd):
            print("failed to build cc_hwclock python")
            sys.exit(12)

        os.replace("dist/cc_hwclock", "dist/CurlingTimer/cc_hwclock")


    if args.skip_tar:
        print("skipping tar generation")
    else:
        test = ".test" if args.test else ""
        tgt = f"dist/CurlingTimer{test}.{versionNo}.tgz"

        cmd = f"tar -C dist -czf {tgt} CurlingTimer"
        print(cmd)
        if os.system(cmd):
            print("failed to build distributable tar file")
            os.remove(tgt)
            sys.exit(12)

        sumFile = f"dist/CurlingTimer{test}.{versionNo}.sum.txt"
        if os.system(f"sha512sum '{tgt}' | cut -d ' ' -f1 > {sumFile}"):
            print("failed to build distributable tar file")
            os.remove(tgt)
            os.remove(sumFile)
            sys.exit(12)


if __name__ == "__main__":
    main()
