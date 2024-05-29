import sys

# First we try for a USB DS3231
import USB_DS3231

def help():
    print(f"""{sys.argv[0]} [-r] [--show] [--get] [-s] [--hctosys] 
        [-w] [--systohc] [-l] [--localtime]  [-u] [--utc]  [--set --date <date>]
  Sort of like the builtin hwclock. Sets/Restores and reads DS1307/DS3231 based clocks
  when attached using i2c or usb based. Most of the other options are recognized but
  ignored""")
    
def main():
    try:
        ds = USB_DS3231.DS3231()
        print("found USB DS3231")

    except Exception as e:
        # try for an I2C bus DS1307/DS3231
        import DS1307

        try:
            ds = DS1307.DS1307()
            print("found I2C DS1307/DS3231")
        except Exception as e:
            sys.exit(4)

    args = sys.argv[1:]

    if not len(args):
        help()
        sys.exit()
    
    utc = False
    raw = False
    readTime = False
    hcToSys = False
    setToStr = False
    sysToHc = False
    dateStr = None
    delayTime = None
    verbose = False
    adjFile = None

    while args and args[0].startswith("-"):
        a = args.pop(0)

        if a in ["-u", "--utc"]:
            utc = True
            readTime = True
        elif a in ["-l", "--localtime"]:
            utc = False
            readTime = True
        elif a in ["-s" , "--hctosys"]:
            hcToSys = True
        elif a in ["-w" , "--systohc"]:
            sysToHc = True
        elif a == "--set":
            setToStr = True
        elif a.startswith("--adjfile="):
            adjFile = a.split("=", 1)[-1]
        elif a == "--adjfile":
            adjFile = args.pop(0)
        elif a.startswith("--date="):
            dateStr = a.split("=", 1)[-1]
        elif a == "--date":
            dateStr = args.pop(0)
        elif a.startswith("--delay="):
            delayTime = a.split("=", 1)[-1]
        elif a == "--delay":
            delayTime = args.pop(0)
        elif a in [ "-r", "--show", "--get"]:
            readTime = True
        elif a == "--raw":
            raw = True
        elif a in ["-V", "--version"]:
            print("curling clock hwclock")
        elif a in ["-a", "--adjust"]:
            pass
        elif a in ["-v", "--verbose"]:
            verbose = True
        elif a == "--update-drift":
            pass
        elif a == "--noadjfile":
            pass
        elif a == "--predict":
            pass
        elif a == "--badyear":
            pass
        elif a == "--systz":
            pass
        elif a.startswith("--rtc="):
            pass
        elif a == "-f":
            args.pop(0)
        elif a == "--test":
            print("not implemented")
            return
        else:
            help()
            sys.exit()

    if readTime:
        print(ds.getDateStr(utc=utc))

    if setToStr:
        if not dateStr:
            print("must give -date <date and time>")
            sys.exit(4)
            
        ds.setDateStr(dateStr)

    if hcToSys:
        ds.setSystemTime()

    if sysToHc:
        ds.setToSystemTime()
        
if __name__ == '__main__':
    main()
    



