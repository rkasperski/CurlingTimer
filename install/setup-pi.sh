#!/bin/bash
echo "updating distribution"

read -p  "have you set locale, timezone, wifi country, etc [y/N]: " yesNo
if [ "$yesNo" != 'Y' ] && [ "$yesNo" != 'y' ]
then
    # setup defaults
    echo "setting up default wifi country(CA) and locale(en_CA.UTF8)"
    sudo raspi-config nonint do_wifi_country CA
    sudo raspi-config nonint do_change_locale en_CA.UTF-8

    read -p  "do you want to run raspi-config [y/N]: " yesNo
    if [ "$yesNo" == 'Y' ] || [ "$yesNo" == 'y' ]
    then
        raspi-config
    fi

    read -p "You should reboot now. Reboot? [Y/n]" yesNo
    if [ "$yesNo" != 'N' ] && [ "$yesNo" != 'n' ]
    then
        echo "rerun the install script after reboot"
        echo "restarting in 5 seconds"
        sleep 5
        reboot
    fi
fi

apt-get update
apt-get -y upgrade

read -p "install emacs [y/N]: " yesNo
if [ "$yesNo" = 'Y' ] || [ "$yesNo" = 'y' ]
then
    sudo apt-get -y install emacs
fi

echo "add wifi network"
./add-ssid.sh

# install clock uitility software
apt-get -y install iputils-clockdiff
apt-get -y install ptpd
# disbale unneeded software
if systemctl is-active --quiet systemd-timesyncd.service
then
    echo "stopping and disabling systemd-timesyncd.service"
    systemctl stop systemd-timesyncd.service
    systemctl disable systemd-timesyncd.service
fi

echo "masking unwanted services"
systemctl mask bluetooth.service
systemctl mask cups.service
systemctl mask hciuart.service
systemctl mask alsa-state.service
systemctl mask cups-browsed.service

# Turn off the sound card
if grep -e "blacklist snd_bcm2835" /etc/modprobe.d/raspi-blacklist.conf
then
    echo "sound is already turned off"
else
    echo "turning off sound card"
    echo "blacklist snd_bcm2835" >> /etc/modprobe.d/raspi-blacklist.conf
fi

echo "turning off bluetooth"
systemctl disable bluetooth
service bluetooth stop
systemctl disable hciuart
service  hciuart stop

#disable and remove swap
dphys-swapfile swapoff
dphys-swapfile uninstall
update-rc.d dphys-swapfile remove

if [ -f /etc/systemd/system/log2ram-daily.service ]
then
    echo "log2ram already installed"
else
    echo "installing log2ram"
    mkdir -p ~/dev
    cd ~/dev
    curl -Lo log2ram.tar.gz https://github.com/azlux/log2ram/archive/master.tar.gz
    tar xf log2ram.tar.gz
    cd log2ram-master
    chmod +x install.sh && ./install.sh
fi
