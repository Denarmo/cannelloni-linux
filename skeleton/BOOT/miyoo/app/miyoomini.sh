#!/bin/sh

echo "=== [$(date +'%Y-%m-%d %H:%M:%S')] miyoomini.sh (stage 1) triggered ==="

IS_PLUS=false
if [ -f "/customer/app/axp_test" ]; then
	IS_PLUS=true
fi
echo "IS_PLUS: $IS_PLUS"

SDCARD_PATH=/mnt/SDCARD
MIYOO_PATH=$(cd "$(dirname "$0")"/.. && pwd)
echo "MIYOO_PATH: $MIYOO_PATH"

cd "$MIYOO_PATH/app"
export LD_LIBRARY_PATH=/lib:/config/lib:/customer/lib

# update bootcmd if necessary
contains() { [ -z "${2##*$1*}" ]; }
MIYOO_VERSION=`/etc/fw_printenv miyoo_version 2>/dev/null`
MIYOO_VERSION=${MIYOO_VERSION#miyoo_version=}
echo "MIYOO_VERSION: $MIYOO_VERSION"

SUPPORTED_VERSION="202205010000" # date after latest known version
if [ -n "$MIYOO_VERSION" ] && [ "$MIYOO_VERSION" -eq "$MIYOO_VERSION" ] 2>/dev/null; then
	if [ "$MIYOO_VERSION" -lt "$SUPPORTED_VERSION" ]; then
		OLD_CMD=`/etc/fw_printenv bootcmd 2>/dev/null`
		NEW_CMD="gpio output 85 1; bootlogo 0 0 0 0 0; mw 1f001cc0 11; gpio out 8 0; sf probe 0;sf read 0x22000000 \${sf_kernel_start} \${sf_kernel_size}; gpio out 8 1; gpio output 4 1; bootm 0x22000000"
		if contains "sleepms" "$OLD_CMD"; then
			echo "Updating bootcmd environment..."
			/etc/fw_setenv bootcmd $NEW_CMD 2>/dev/null
			sleep 1
		fi
	fi
fi

# Ensure updater scripts have execute permissions
echo "Setting executable permissions on .tmp_update..."
chmod +x .tmp_update/updater .tmp_update/*.sh .tmp_update/*/* 2>/dev/null

# .tmp_update/updater does the actual installation (and later, updating)
echo "Ensuring .tmp_update is present at $SDCARD_PATH/..."
[ -d ".tmp_update" ] && cp -rf .tmp_update "$SDCARD_PATH/" 2>/dev/null
[ ! -f "$SDCARD_PATH/.tmp_update/updater" ] && [ -d "$SDCARD_PATH/miyoo354/app/.tmp_update" ] && cp -rf "$SDCARD_PATH/miyoo354/app/.tmp_update" "$SDCARD_PATH/" 2>/dev/null
[ ! -f "$SDCARD_PATH/.tmp_update/updater" ] && [ -d "$SDCARD_PATH/miyoo/app/.tmp_update" ] && cp -rf "$SDCARD_PATH/miyoo/app/.tmp_update" "$SDCARD_PATH/" 2>/dev/null
chmod +x "$SDCARD_PATH/.tmp_update/updater" "$SDCARD_PATH/.tmp_update/"*.sh "$SDCARD_PATH/.tmp_update/"*/* 2>/dev/null

sync
echo "Executing $SDCARD_PATH/.tmp_update/updater..."
$SDCARD_PATH/.tmp_update/updater
UPDATER_EXIT=$?
echo "updater exited with code: $UPDATER_EXIT"
sync

# under no circumstances should stock be allowed to touch this card
if $IS_PLUS; then
	echo "Miyoo Plus shutdown/poweroff sequence..."
	sync
	poweroff
else
	echo "Miyoo Mini reboot sequence..."
	sync
	reboot
fi