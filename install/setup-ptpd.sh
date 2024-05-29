isPrimary="notset"

if [ "-$1" = '-secondary' ]
then
    isPrimary="no"
fi
if [ "-$1" = '-primary' ]
then
    isPrimary="yes"
fi

if [ "-$isPrimary" = '-notset' ]
then
    read -p "Is this a primary time server node? Does it have a hardware clock? [y/N]: " yesNo
    if [ "$yesNo" = 'Y' ] || [ "$yesNo" = 'y' ]
    then
        isPrimary="yes"
    else
        isPrimary="no"
    fi
fi

echo "Has hardware clock=$isPrimary"

apt-get -y install ptpd

if [ "-$isPrimary" = '-yes' ]
then
    cp rtc-clock-ptpd.conf /etc/ptpd.conf
else
    cp sync-clock-ptpd.conf /etc/ptpd.conf
fi

sed /etc/default/ptpd \
    -e 's/START_DAEMON=no/START_DAEMON=yes/g' \
    -e 's|PTPD_OPTS *= *""|PTPD_OPTS="-c /etc/ptpd.conf"|gi' > etc_default_ptpd

cp etc_default_ptpd  /etc/default/ptpd

# use standard technique to force wait for network
raspi-config nonint do_boot_wait 0

# ensure ntp daemon is disabled
systemctl disable systemd-timesyncd.service

systemctl enable ptpd
systemctl restart ptpd
systemctl status ptpd
