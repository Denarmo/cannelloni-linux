#!/bin/sh

# 1. Bring up Wi-Fi on supported devices
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

# 2. Acquire IP address (wait up to 5 seconds)
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

if [ -z "$IP" ] || [ "$IP" = "127.0.0.1" ]; then
	$SAY "Wi-Fi is not connected.
Configure Wi-Fi in Stock OS first."
	exit 0
fi

# 3. Kill any previous FTP server
killall tcpsvd ftpd 2>/dev/null

# 4. Start Nonna's Kitchen FTP server (Busybox ftpd) on port 2121
tcpsvd -vE 0.0.0.0 2121 ftpd -w /mnt/SDCARD &
FTP_PID=$!

# 5. Display status to user until they press A or B
$SAY "Nonna's Kitchen FTP Active!
Address: ftp://$IP:2121
User: cannelloni | Pass: cannelloni

Press A to stop FTP."

# 6. Stop FTP when user closes
kill $FTP_PID 2>/dev/null
killall tcpsvd ftpd 2>/dev/null
