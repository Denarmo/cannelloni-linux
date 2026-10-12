#!/bin/sh

LOG_FILE="/mnt/SDCARD/cannelloni_install.log"
echo "=== [$(date +'%Y-%m-%d %H:%M:%S')] miyoomini.sh (stage 1) triggered ===" >> "$LOG_FILE" 2>&1

IS_PLUS=false
if [ -f "/customer/app/axp_test" ]; then
	IS_PLUS=true
fi
echo "IS_PLUS: $IS_PLUS" >> "$LOG_FILE" 2>&1

SDCARD_PATH=/mnt/SDCARD
MIYOO_PATH=$(cd "$(dirname "$0")"/.. && pwd)
echo "MIYOO_PATH: $MIYOO_PATH" >> "$LOG_FILE" 2>&1

cd "$MIYOO_PATH/app"
export LD_LIBRARY_PATH=/lib:/config/lib:/customer/lib

# update bootcmd if necessary
contains() { [ -z "${2##*$1*}" ]; }
MIYOO_VERSION=`/etc/fw_printenv miyoo_version 2>/dev/null`
MIYOO_VERSION=${MIYOO_VERSION#miyoo_version=}
echo "MIYOO_VERSION: $MIYOO_VERSION" >> "$LOG_FILE" 2>&1

SUPPORTED_VERSION="202205010000" # date after latest known version
if [ -n "$MIYOO_VERSION" ] && [ "$MIYOO_VERSION" -eq "$MIYOO_VERSION" ] 2>/dev/null; then
	if [ "$MIYOO_VERSION" -lt "$SUPPORTED_VERSION" ]; then
		OLD_CMD=`/etc/fw_printenv bootcmd 2>/dev/null`
		NEW_CMD="gpio output 85 1; bootlogo 0 0 0 0 0; mw 1f001cc0 11; gpio out 8 0; sf probe 0;sf read 0x22000000 \${sf_kernel_start} \${sf_kernel_size}; gpio out 8 1; gpio output 4 1; bootm 0x22000000"
		if contains "sleepms" "$OLD_CMD"; then
			echo "Updating bootcmd environment..." >> "$LOG_FILE" 2>&1
			/etc/fw_setenv bootcmd $NEW_CMD 2>/dev/null
			sleep 1
		fi
	fi
fi

# Ensure updater scripts have execute permissions
echo "Setting executable permissions on .tmp_update..." >> "$LOG_FILE" 2>&1
chmod +x .tmp_update/updater .tmp_update/*.sh .tmp_update/*/* 2>/dev/null

# .tmp_update/updater does the actual installation (and later, updating)
echo "Copying .tmp_update to $SDCARD_PATH/..." >> "$LOG_FILE" 2>&1
cp -rf .tmp_update $SDCARD_PATH/ >> "$LOG_FILE" 2>&1
chmod +x $SDCARD_PATH/.tmp_update/updater $SDCARD_PATH/.tmp_update/*.sh $SDCARD_PATH/.tmp_update/*/* 2>/dev/null

sync
echo "Executing $SDCARD_PATH/.tmp_update/updater..." >> "$LOG_FILE" 2>&1
$SDCARD_PATH/.tmp_update/updater >> "$LOG_FILE" 2>&1
UPDATER_EXIT=$?
echo "updater exited with code: $UPDATER_EXIT" >> "$LOG_FILE" 2>&1
sync

# under no circumstances should stock be allowed to touch this card
if $IS_PLUS; then
	echo "Miyoo Plus shutdown/poweroff sequence..." >> "$LOG_FILE" 2>&1
	sync
	poweroff
else
	echo "Miyoo Mini reboot sequence..." >> "$LOG_FILE" 2>&1
	sync
	reboot
fi