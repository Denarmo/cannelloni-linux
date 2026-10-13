#!/bin/sh

cd "$(dirname "$0")"
[ -z "$SDCARD_PATH" ] && SDCARD_PATH="/storage/roms"
[ ! -d "$SDCARD_PATH" ] && SDCARD_PATH="/mnt/SDCARD"

SECURE_NET_DIR="$SDCARD_PATH/.userdata/shared/.cannelloni"
SECURE_NET_CONF="$SECURE_NET_DIR/network.conf"

SRC_SET='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='
DST_SET='NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm9876543210+/_'

decode_cred() {
    printf "%s" "$1" | tr "$DST_SET" "$SRC_SET" | base64 -d 2>/dev/null
}

# Migrate local or root wifi.txt if found
if [ -f "./wifi.txt" ]; then
    OLD_TXT="./wifi.txt"
elif [ -f "$SDCARD_PATH/wifi.txt" ]; then
    OLD_TXT="$SDCARD_PATH/wifi.txt"
else
    OLD_TXT=""
fi

if [ -n "$OLD_TXT" ] && [ -f "$OLD_TXT" ]; then
    [ -f "$SDCARD_PATH/.system/common/network_store.sh" ] && . "$SDCARD_PATH/.system/common/network_store.sh"
    [ -f "$SDCARD_PATH/.system/bin/network_store.sh" ] && . "$SDCARD_PATH/.system/bin/network_store.sh"
    rm -f "./wifi.txt" "$SDCARD_PATH/wifi.txt" 2>/dev/null
fi

WIFI_NAME=""
WIFI_PASS=""

if [ -f "$SECURE_NET_CONF" ]; then
    first_line=$(grep "^NET:" "$SECURE_NET_CONF" | head -n1)
    if [ -n "$first_line" ]; then
        enc_s=$(echo "$first_line" | cut -d: -f2)
        enc_p=$(echo "$first_line" | cut -d: -f3)
        WIFI_NAME=$(decode_cred "$enc_s")
        WIFI_PASS=$(decode_cred "$enc_p")
    fi
fi

##############

. /etc/profile # NOTE: this nukes Cannelloni's PATH modifications
PATH=/storage/roms/.system/rgb30/bin:$PATH

CUR_NAME=`get_setting wifi.ssid`
CUR_PASS=`get_setting wifi.key`

RES_PATH="$(dirname "$0")/res"
STATUS=$(cat "/sys/class/net/wlan0/operstate")

function disconnect()
{
	echo "disconnect"
	
	wifictl disable &
	show.elf "$RES_PATH/disable.png" 2
	STATUS=down
}

function connect()
{
	echo "connect"
	wifictl enable &
	DELAY=30
	show.elf "$RES_PATH/enable.png" $DELAY &
	for i in `seq 1 $DELAY`; do
		STATUS=$(cat "/sys/class/net/wlan0/operstate")
		if [ "$STATUS" = "up" ]; then
			break
		fi
		sleep 1
	done
	killall -s KILL show.elf
}

{
if [ -n "$WIFI_NAME" ] && { [ "$WIFI_NAME" != "$CUR_NAME" ] || [ "$WIFI_PASS" != "$CUR_PASS" ]; }; then
	echo "change"
	
	if [ "$STATUS" = "up" ]; then
		disconnect
	fi
	
	echo "$WIFI_NAME:***"
	show.elf "$RES_PATH/update.png" 2
	set_setting wifi.ssid "$WIFI_NAME"
	set_setting wifi.key "$WIFI_PASS"
fi

echo "toggle"
if [ "$STATUS" = "up" ]; then
	disconnect
else
	connect
fi
} &> ./log.txt