#!/bin/bash

exedir="$PWD"
echo "executable-directory=$exedir"
set -x

if ! raspi-config nonint get_i2c
then
    echo "enabling i2c"
    raspi-config nonint do_i2c 0
    echo " i2c set to enabled. please reboot to when installation is over"
    exit 0
fi

apt-get install -y python3-smbus i2c-tools

echo "removing ds1307 i2c-rtc"
sed '/i2c-rtc,ds1307/d' /boot/config.txt >> boot_config.txt

echo "removing hwclock"
sed '/hwclock/d' /etc/rc.local | \
    sed -e "s|exit 0|/sbin/cc_hwclock --hctosys\nexit 0|" \
  > rc.local
echo "/sbin/cc_hwclock --hctosys" >>  rc.local
    
apt-get -y remove fake-hwclock
update-rc.d -f fake-hwclock remove
systemctl disable fake-hwclock

sed 's|^.*hwclock|/sbin/cc_hwclock|g' /lib/udev/hwclock-set | \
    sed -e "/systz/d" \ |
    sed -e "/--rtc/d" \ |
 > hwclock-set        

echo "/sbin/cc_hwclock --hctosys" >>  hwclock-set

cp /boot/config.txt /boot/config.txt.old
cp boot_config.txt /boot/config.txt
cp /lib/udev/hwclock-set /lib/udev/hwclock-set.old
cp hwclock-set  /lib/udev/hwclock-set
cp /etc/rc.local /etc/rc.local.old
cp rc.local /etc/rc.local
cp "$exedir/cc_hwclock" /sbin/cc_hwclock

echo "hwclock installed."
echo "Please reboot system when installation is complete"
