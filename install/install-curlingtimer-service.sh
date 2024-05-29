SCRIPTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo $SCRIPTDIR
EXEDIR="$( dirname "$SCRIPTDIR" )"
echo $EXEDIR
WORKDIR="$( dirname "$EXEDIR" )"
echo $WORKDIR

systemctl disable curlingTimer
systemctl disable breakTimer

mount-curling-timer.sh

echo "installing curling timer service"
sed -e "s'replaceexedir'$EXEDIR'" -e "s'replaceworkdir'$WORKDIR'" systemd/curlingTimer.service.template > curlingTimer.service
mv curlingTimer.service /etc/systemd/system/curlingTimer.service
systemctl daemon-reload
systemctl enable curlingTimer
systemctl start curlingTimer
systemctl status curlingTimer

echo "display software is installed."
echo "Please reboot when installation is complete"
