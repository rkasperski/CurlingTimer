FILE="/etc/wpa_supplicant/wpa_supplicant.conf"

while true
do
    read -p "enter wifi SSID[empty to skip]: " SSID
    if [ -z "$SSID" ]
    then
	exit 0
    fi

    if grep -e "$SSID" $FILE
    then
        echo "SSID <$SSID> already exists. change password manually"
    else
        read -p "enter password: " password
        if [ "a$SSID" = 'a' ]
        then
            echo "password was empty"
	    password="None"
        fi
	
        echo "network={" >> $FILE
	echo "    ssid=\"$SSID\"" >> $FILE
	echo "    psk=\"$password\"" >> $FILE
	echo "}" >> $FILE
    fi
done
