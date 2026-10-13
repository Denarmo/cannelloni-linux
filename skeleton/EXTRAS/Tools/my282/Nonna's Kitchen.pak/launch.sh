#!/bin/sh
# The process shown on screen owns the web server for its entire lifetime.
PAK_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
[ -n "$SDCARD_PATH" ] || SDCARD_PATH=/mnt/SDCARD
[ -d "$SDCARD_PATH" ] || SDCARD_PATH=/storage/roms
export SDCARD_PATH
export SDCARD="$SDCARD_PATH"
SAY="${SYSTEM_PATH:-$SDCARD_PATH/.system/$PLATFORM}/bin/say.elf"
[ -x "$SAY" ] || SAY=say.elf
HTTPD_PID=
MESSAGE_PID=
RUNTIME_DIR=

stop_message() {
    if [ -n "$MESSAGE_PID" ]; then
        kill "$MESSAGE_PID" 2>/dev/null
        wait "$MESSAGE_PID" 2>/dev/null
        MESSAGE_PID=
    fi
}
cleanup() {
    stop_message
    if [ -n "$HTTPD_PID" ]; then
        kill "$HTTPD_PID" 2>/dev/null
        wait "$HTTPD_PID" 2>/dev/null
        HTTPD_PID=
    fi
    if [ -n "$RUNTIME_DIR" ]; then
        rm -rf "$RUNTIME_DIR"
        RUNTIME_DIR=
    fi
}
trap cleanup EXIT
trap 'exit 0' INT TERM HUP

get_ip() {
    ip -4 addr show dev wlan0 2>/dev/null | awk '/inet / {split($2,a,"/"); print a[1]; exit}'
}
IP=$(get_ip)
[ -n "$IP" ] || IP=$(ifconfig wlan0 2>/dev/null | awk '/inet addr:/ {sub("addr:","",$2); print $2; exit}')
if [ -z "$IP" ] || [ "$IP" = 127.0.0.1 ]; then
    "$SAY" "Wi-Fi is not connected.
Open Settings > Wi-Fi and connect first."
    exit 1
fi

# Run CGI from an executable filesystem. FAT SD cards may be mounted noexec
# and cannot hold the symlinks used by earlier versions of this tool.
RUNTIME_DIR=$(mktemp -d /tmp/cannelloni-kitchen.XXXXXX) || exit 1
mkdir -p "$RUNTIME_DIR/cgi-bin" "$SDCARD_PATH/Roms" "$SDCARD_PATH/Bios" "$SDCARD_PATH/Saves"
if ! cp "$PAK_DIR/web/index.html" "$RUNTIME_DIR/index.html" ||
   ! cp "$PAK_DIR/web/cgi-bin/api.cgi" "$RUNTIME_DIR/cgi-bin/api.cgi" ||
   ! chmod 700 "$RUNTIME_DIR/cgi-bin/api.cgi"; then
    "$SAY" "Unable to prepare the web service."
    exit 1
fi

# -f is essential: without it httpd daemonizes and $! is not the listener.
busybox httpd -f -p 1091 -h "$RUNTIME_DIR" >"$RUNTIME_DIR/httpd.log" 2>&1 &
HTTPD_PID=$!
sleep 1
if ! kill -0 "$HTTPD_PID" 2>/dev/null; then
    "$SAY" "Unable to start Nonna's Kitchen.
Port 1091 may already be in use."
    exit 1
fi
"$SAY" "Nonna's Kitchen is serving
http://$IP:1091

Keep this screen open to transfer files.
Press A or B to stop and exit." &
MESSAGE_PID=$!
wait "$MESSAGE_PID"
MESSAGE_PID=
# EXIT also handles interruption, failure and normal button dismissal.
