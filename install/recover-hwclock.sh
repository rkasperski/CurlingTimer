# magic incantation for
# hwclock: ioctl(RTC_RD_TIME) to /dev/rtc0 to read the time failed: Invalid argument
# must run as sudo

hwclock --systohc -D --noadjfile --utc
