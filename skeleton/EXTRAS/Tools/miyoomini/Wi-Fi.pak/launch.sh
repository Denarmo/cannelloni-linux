#!/bin/sh

# Bring up Wi-Fi on supported devices
if [ -f "/customer/app/axp_test" ]; then
	/customer/app/axp_test wifion 2>/dev/null
	ifconfig wlan0 up 2>/dev/null
	if [ -f "/appconfigs/wpa_supplicant.conf" ]; then
		killall wpa_supplicant 2>/dev/null
		wpa_supplicant -B -D nl80211 -iwlan0 -c /appconfigs/wpa_supplicant.conf 2>/dev/null
		udhcpc -i wlan0 -s /etc/init.d/udhcpc.script -q 2>/dev/null &
	fi
fi

ifconfig wlan0 up 2>/dev/null

IP=""
for i in 1 2 3 4 5; do
	IP=$(ip -4 addr show dev wlan0 2>/dev/null | awk '/inet / {print $2}' | cut -d/ -f1)
	if [ -z "$IP" ]; then
		IP=$(ifconfig wlan0 2>/dev/null | awk '/inet addr:/ {print $2}' | cut -d: -f2)
	fi
	if [ -n "$IP" ] && [ "$IP" != "127.0.0.1" ]; then
		break
	fi
	sleep 1
done

SAY="/mnt/SDCARD/.system/miyoomini/bin/say.elf"
if ! [ -x "$SAY" ]; then
	SAY="say.elf"
fi

if [ -n "$IP" ] && [ "$IP" != "127.0.0.1" ]; then
	$SAY "Wi-Fi Status: Connected
IP Address: $IP

Press A to close."
else
	$SAY "Wi-Fi Status: Disconnected
To connect, configure your network
in the Miyoo stock OS settings first.

Press A to close."
fi
