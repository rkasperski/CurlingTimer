import sys

# First we try for a USB DS3231
import ds3231

def help():
    print(f"""{sys.argv[0]} [-r] [--show] [--get] [-s] [--hctosys] 
        [-w] [--systohc] [-l] [--localtime]  [-u] [--utc]  [--set --date <date>]
  Sort of like the builtin hwclock. Sets/Restores and reads DS3231 based clocks
  when attached using i2c. Most of the other options are recognized but
  ignored""")
    
def main():
    args = sys.argv[1:]

    if not len(args):
        help()
        sys.exit()
    
    utc = False
    raw = False
    read_time = False
    hc_to_sys = False
    set_to_str = False
    sys_to_Hc = False
    date_str = None
    delay_time = None
    verbose = False
    adjFile = None
    busid = 1

    while args and args[0].startswith("-"):
        a = args.pop(0)

        if a in ["-u", "--utc"]:
            utc = True
            read_time = True
        elif a in ["-l", "--localtime"]:
            utc = False
            read_time = True
        elif a in ["-s" , "--hctosys"]:
            hc_to_sys = True
        elif a in ["-w" , "--systohc"]:
            sys_to_Hc = True
        elif a == "--set":
            set_to_str = True
        elif a.startswith("--adjfile="):
            adjFile = a.split("=", 1)[-1]
        elif a == "--adjfile":
            adjFile = args.pop(0)
        elif a.startswith("--date="):
            date_str = a.split("=", 1)[-1]
        elif a == "--date":
            date_str = args.pop(0)
        elif a.startswith("--delay="):
            delay_time = a.split("=", 1)[-1]
        elif a == "--delay":
            delay_time = args.pop(0)
        elif a in [ "-r", "--show", "--get"]:
            read_time = True
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
        elif a == "-b" or a == "--bus":
            busid = int(args.pop(0))
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

    try:
        ds = DS3231.DS3231(twi=busid, verbose=verbose)
        print("found DS3231")

    except Exception as e:
        sys.exit(4)

    if read_time:
        print(ds.get_date_str(utc=utc))

    if set_to_str:
        if not date_str:
            print("must give -date <date and time>")
            sys.exit(4)
            
        ds.set_date_str(date_str)

    if hc_to_sys:
        ds.set_system_time()

    if sys_to_Hc:
        ds.set_to_system_time()
        
if __name__ == '__main__':
    main()
    



