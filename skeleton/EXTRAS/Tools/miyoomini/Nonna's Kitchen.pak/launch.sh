#!/bin/sh

# Check if Wi-Fi is already connected with a valid IP
get_ip() {
	ip -4 addr show dev wlan0 2>/dev/null | awk '/inet / {print $2}' | cut -d/ -f1 | head -n1
}

IP=$(get_ip)
if [ -z "$IP" ] || [ "$IP" = "127.0.0.1" ]; then
	IP=$(ifconfig wlan0 2>/dev/null | awk '/inet addr:/ {print $2}' | cut -d: -f2 | head -n1)
fi

SAY="/mnt/SDCARD/.system/miyoomini/bin/say.elf"
if ! [ -x "$SAY" ]; then
	SAY="say.elf"
fi

# If not connected yet, try bringing Wi-Fi up cleanly WITHOUT killing existing connections
if [ -z "$IP" ] || [ "$IP" = "127.0.0.1" ]; then
	WIFI_ON="/mnt/SDCARD/Tools/miyoomini/Wi-Fi.pak/bin/service-on"
	if [ -f "$WIFI_ON" ]; then
		/bin/sh "$WIFI_ON" >/dev/null 2>&1
	elif [ -f "/customer/app/axp_test" ]; then
		/customer/app/axp_test wifion 2>/dev/null
		ifconfig wlan0 up 2>/dev/null
		if ! pgrep wpa_supplicant >/dev/null 2>&1 && [ -f "/appconfigs/wpa_supplicant.conf" ]; then
			wpa_supplicant -B -D nl80211 -iwlan0 -c /appconfigs/wpa_supplicant.conf 2>/dev/null
			udhcpc -i wlan0 -s /etc/init.d/udhcpc.script -q 2>/dev/null &
		fi
	fi

	# Wait up to 10 seconds for IP address assignment
	for i in 1 2 3 4 5 6 7 8 9 10; do
		IP=$(get_ip)
		[ -z "$IP" ] && IP=$(ifconfig wlan0 2>/dev/null | awk '/inet addr:/ {print $2}' | cut -d: -f2 | head -n1)
		if [ -n "$IP" ] && [ "$IP" != "127.0.0.1" ]; then
			break
		fi
		sleep 1
	done
fi

if [ -z "$IP" ] || [ "$IP" = "127.0.0.1" ]; then
	$SAY "Wi-Fi is not connected.
Configure Wi-Fi in Tools > Wi-Fi first."
	exit 0
fi

# Start FTP server on port 2121
killall tcpsvd ftpd 2>/dev/null
tcpsvd -vE 0.0.0.0 2121 ftpd -w /mnt/SDCARD &
FTP_PID=$!

$SAY "Nonna's Kitchen FTP Active!
Address: ftp://$IP:2121
User: cannelloni | Pass: cannelloni

Press A to stop FTP."

# Stop FTP when user closes (leaving Wi-Fi active!)
kill $FTP_PID 2>/dev/null
killall tcpsvd ftpd 2>/dev/null
