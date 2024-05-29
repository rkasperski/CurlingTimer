read -p "install usb drive for data[Y,n]:" yesNo
if [ "$yesNo" != 'n' ] && [ "$yesNo" != 'N' ]
then
    echo "Drive must be formatted for ext4 and must have the volume lavel 'curling-timer'"
    mkdir -p /media/pi/curling-timer
    blkdev=`blkid --label 'curling-timer'`
    if [ $? != 0 ]
    then
        echo "failed to find a usb drive with the volume label 'curling-timer'"
        echo "skipping ..."
        echo "you can try again by running 'sudo mount-curling-timer.sh'"
        exit
    fi

    echo "mounting curling-timer at /media/pi/curling-timer"
    sudo mount -t ext4 -o defaults "$blkdev" /media/pi/curling-timer

    if grep -e "$blkdev" /etc/fstab
    then
        echo "curling-timer partition already permanently mounted"
    else
        echo "permanently mounting data parition."
        echo "$blkdev	     /media/pi/curling-timer	ext4	defaults,noatime	0	1" >> /etc/fstab
    fi

    df -k

    echo "making target directory on curling-timer"
    mkdir -p /media/pi/curling-timer/curling-timer

fi
