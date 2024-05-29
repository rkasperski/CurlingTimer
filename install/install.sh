#!/bin/bash
echo "when asked to reboot your raspbery pi please do so."
echo "After rebooting you will need to rerun this script"
echo
./setup-pi.sh

read -p "Does this device have a real-time clock(ds1307) [y,N]: " yesNo
if [ "$yesNo" = 'y' ] || [ "$yesNo" = 'Y' ]
then
    ./enable-hwclock.sh
    ./setup-ptpd.sh primary
else
    ./setup-ptpd.sh secondary
fi

read -p "have you installed clock timer software [y/N]" yesNo
if [ "$yesNo" != 'Y' ] && [ "$yesNo" != 'y' ]
then
    while true
    do
	read -p "is this a display or break timer? [display, break]: " isDisplay
	if [ "$isDisplay" = "display" ]
	then
	    ./install-curlingtimer-service.sh
        break
	fi
	if [ "$isDisplay" = "break" ]
	then
	    ./install-breaktimer-service.sh
	    break
	fi

	echo "'$isDisplay' is invalid. must be 'display' or 'break'"
    done
fi

echo "installation is complete please reboot"

# Request reboot when necessary
read -p "system requires a reboot; reboot now [Y/n]: " yesNo
if [ "$yesNo" != 'n' ] && [ "$yesNo" != 'N' ]
then
    reboot
fi
