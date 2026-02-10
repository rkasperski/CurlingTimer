SCRIPTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo "SCRIPTDIR=$SCRIPTDIR"
EXEDIR="$( dirname "$SCRIPTDIR" )"
echo "EXEDIR=$EXEDIR"
WORKDIR="$( dirname "$EXEDIR" )"
echo "WORKDIR=$WORKDIR"

return
exit

systemctl disable curlingTimer
systemctl disable breakTimer
apt-get -y install pigpiod

echo "checking for data partition"
if ls "/dev/mmcblk0p3"
then
    echo "data partition exists. Adding to fstab";


    if grep -e "/dev/mmcblk0p3" /etc/fstab
    then
        echo "data partition already permanently mounted"
    else
        echo "permanently mounting data parition."
        echo "/dev/mmcblk0p3	     /media/pi/curling-timer	ext4	defaults,noatime	0	1" >> /etc/fstab
    fi

    mountdir="/media/pi/curling-timer"
    if [ ! -d $mountdir ]
    then
	       mkdir -p $mountdir
	       mount /dev/mmcblk0p3 $mountdir
    fi

    df -k

    echo "making target directory on curling-timer"
    mkdir -p /media/pi/curling-timer/curling-timer
fi

echo "installing break timer service"
sed -e "s'replaceexedir'$EXEDIR'" -e "s'replaceworkdir'$WORKDIR'" systemd/breakTimer.service.template > breakTimer.service
mv breakTimer.service /etc/systemd/system/breakTimer.service
systemctl daemon-reload
systemctl enable breakTimer
systemctl start breakTimer
systemctl status breakTimer

echo "breaktimer software is installed."
echo "Please reboot when installation is complete"
