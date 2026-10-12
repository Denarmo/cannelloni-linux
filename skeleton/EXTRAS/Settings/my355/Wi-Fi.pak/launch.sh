#!/bin/sh
set -x
PAK_DIR="$(dirname "$0")"
PAK_NAME="$(basename "$PAK_DIR")"
PAK_NAME="${PAK_NAME%.*}"

[ -z "$SDCARD_PATH" ] && export SDCARD_PATH="/mnt/SDCARD"
if [ -z "$PLATFORM" ]; then
    if [ -f /customer/app/axp_test ] || [ -f /customer/app/MainUI ]; then
        export PLATFORM="miyoomini"
    fi
fi
[ -z "$USERDATA_PATH" ] && export USERDATA_PATH="$SDCARD_PATH/.userdata/$PLATFORM"
[ -z "$LOGS_PATH" ] && export LOGS_PATH="$USERDATA_PATH/logs"

rm -f "$LOGS_PATH/$PAK_NAME.txt"
exec >>"$LOGS_PATH/$PAK_NAME.txt"
exec 2>&1

echo "$0" "$@"
cd "$PAK_DIR" || exit 1
mkdir -p "$USERDATA_PATH/$PAK_NAME"

architecture=arm
if uname -m | grep -q '64'; then
    architecture=arm64
fi

export HOME="$USERDATA_PATH/$PAK_NAME"
export LD_LIBRARY_PATH="$PAK_DIR/lib/$PLATFORM:$PAK_DIR/lib:$SDCARD_PATH/.system/$PLATFORM/lib:/customer/lib:/lib:/usr/lib:$LD_LIBRARY_PATH"
export PATH="$PAK_DIR/bin/$architecture:$PAK_DIR/bin/$PLATFORM:$PAK_DIR/bin:$SDCARD_PATH/.system/$PLATFORM/bin:$PATH"

# Ensure execute permissions on all bundled binaries immediately
chmod +x "$PAK_DIR/bin/"* "$PAK_DIR/bin/$architecture/"* "$PAK_DIR/bin/$PLATFORM/"* 2>/dev/null
[ -f "$PAK_DIR/bin/$architecture/jq" ] && chmod +x "$PAK_DIR/bin/$architecture/jq" 2>/dev/null

# --- Cannelloni Secure Network Storage ---
SECURE_NET_DIR="$SDCARD_PATH/.userdata/shared/.cannelloni"
SECURE_NET_CONF="$SECURE_NET_DIR/network.conf"

SRC_SET='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='
DST_SET='NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm9876543210+/_'

encode_cred() {
    printf "%s" "$1" | base64 | tr -d '\r\n' | tr "$SRC_SET" "$DST_SET"
}

decode_cred() {
    printf "%s" "$1" | tr "$DST_SET" "$SRC_SET" | base64 -d 2>/dev/null
}

migrate_legacy_wifi_txt() {
    OLD_TXT="$SDCARD_PATH/wifi.txt"
    if [ -f "$OLD_TXT" ]; then
        while IFS= read -r line || [ -n "$line" ]; do
            line=$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
            case "$line" in
                \#*|"") continue ;;
                *:*)
                    s=$(echo "$line" | cut -d: -f1 | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
                    p=$(echo "$line" | cut -d: -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
                    if [ -n "$s" ]; then
                        save_network_credential "$s" "$p"
                    fi
                    ;;
            esac
        done < "$OLD_TXT"
        rm -f "$OLD_TXT"
        sync
    fi
    if [ -f "$PAK_DIR/wifi.txt" ]; then
        rm -f "$PAK_DIR/wifi.txt"
    fi
}

save_network_credential() {
    save_s="$1"
    save_p="$2"
    mkdir -p "$SECURE_NET_DIR"
    chmod 700 "$SECURE_NET_DIR" 2>/dev/null
    TMP_CONF="/tmp/netconf.tmp"
    rm -f "$TMP_CONF"
    touch "$TMP_CONF"
    if [ -f "$SECURE_NET_CONF" ]; then
        while IFS= read -r line || [ -n "$line" ]; do
            case "$line" in
                NET:*)
                    enc_s=$(echo "$line" | cut -d: -f2)
                    s=$(decode_cred "$enc_s")
                    if [ "$s" != "$save_s" ]; then
                        echo "$line" >> "$TMP_CONF"
                    fi
                    ;;
                *)
                    echo "$line" >> "$TMP_CONF"
                    ;;
            esac
        done < "$SECURE_NET_CONF"
    else
        echo "# Cannelloni Secure Network Storage" >> "$TMP_CONF"
    fi
    enc_s=$(encode_cred "$save_s")
    enc_p=$(encode_cred "$save_p")
    echo "NET:${enc_s}:${enc_p}" >> "$TMP_CONF"
    mv "$TMP_CONF" "$SECURE_NET_CONF"
    chmod 600 "$SECURE_NET_CONF" 2>/dev/null
    sync
}

delete_network_credential() {
    del_s="$1"
    [ ! -f "$SECURE_NET_CONF" ] && return
    TMP_CONF="/tmp/netconf.tmp"
    rm -f "$TMP_CONF"
    touch "$TMP_CONF"
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            NET:*)
                enc_s=$(echo "$line" | cut -d: -f2)
                s=$(decode_cred "$enc_s")
                if [ "$s" != "$del_s" ]; then
                    echo "$line" >> "$TMP_CONF"
                fi
                ;;
            *)
                echo "$line" >> "$TMP_CONF"
                ;;
        esac
    done < "$SECURE_NET_CONF"
    mv "$TMP_CONF" "$SECURE_NET_CONF"
    chmod 600 "$SECURE_NET_CONF" 2>/dev/null
    sync
}

get_all_saved_networks() {
    migrate_legacy_wifi_txt
    if [ -f "$SECURE_NET_CONF" ]; then
        while IFS= read -r line || [ -n "$line" ]; do
            case "$line" in
                NET:*)
                    enc_s=$(echo "$line" | cut -d: -f2)
                    decode_cred "$enc_s"
                    ;;
            esac
        done < "$SECURE_NET_CONF"
    fi
}

get_network_password() {
    match_s="$1"
    migrate_legacy_wifi_txt
    if [ -f "$SECURE_NET_CONF" ]; then
        while IFS= read -r line || [ -n "$line" ]; do
            case "$line" in
                NET:*)
                    enc_s=$(echo "$line" | cut -d: -f2)
                    s=$(decode_cred "$enc_s")
                    if [ "$s" = "$match_s" ]; then
                        enc_p=$(echo "$line" | cut -d: -f3)
                        decode_cred "$enc_p"
                        return 0
                    fi
                    ;;
            esac
        done < "$SECURE_NET_CONF"
    fi
    return 1
}

has_saved_networks() {
    migrate_legacy_wifi_txt
    if [ -f "$SECURE_NET_CONF" ]; then
        if grep -q "^NET:" "$SECURE_NET_CONF" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

get_ssid_and_ip() {
    if ! wifi-enabled; then
        return
    fi

    ssid=""
    ip_address=""

    for i in $(seq 1 4); do
        if [ "$PLATFORM" = "my355" ]; then
            ssid="$(wpa_cli -i wlan0 status 2>/dev/null | grep ssid= | grep -v bssid= | cut -d'=' -f2)"
            ip_address="$(wpa_cli -i wlan0 status 2>/dev/null | grep ip_address= | cut -d'=' -f2)"
        else
            ssid="$(iw dev wlan0 link 2>/dev/null | grep SSID: | cut -d':' -f2- | sed -e 's/^[ \t]*//' -e 's/[ \t]*$//')"
            ip_address="$(ip addr show wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1)"
            [ -z "$ip_address" ] && ip_address="$(ifconfig wlan0 2>/dev/null | awk '/inet addr:/ {print $2}' | cut -d: -f2 | head -n1)"
        fi

        if [ -n "$ip_address" ] && [ -n "$ssid" ]; then
            break
        fi
        sleep 1
    done

    if [ -z "$ssid" ]; then
        ssid="N/A"
    fi
    if [ -z "$ip_address" ]; then
        ip_address="N/A"
    fi

    printf "%s\t%s" "$ssid" "$ip_address"
}

main_screen() {
    cannelloni_list_file="/tmp/cannelloni-list"
    rm -f "$cannelloni_list_file" "/tmp/cannelloni-output"
    touch "$cannelloni_list_file"

    template_file="$PAK_DIR/res/settings.json"

    start_on_boot=false
    if will_start_on_boot; then
        start_on_boot=true
    fi

    enabled=false
    ssid="N/A"
    ip_address="N/A"
    if wifi-enabled; then
        enabled=true
        template_file="$PAK_DIR/res/settings.enabled.json"
        ssid_and_ip="$(get_ssid_and_ip)"
        if [ -n "$ssid_and_ip" ]; then
            ssid="$(echo "$ssid_and_ip" | cut -f1)"
            ip_address="$(echo "$ssid_and_ip" | cut -f2)"
            if [ -n "$ssid" ] && [ "$ssid" != "N/A" ]; then
                template_file="$PAK_DIR/res/settings.connected.json"
                if [ "$ip_address" = "N/A" ] || [ -z "$ip_address" ]; then
                    template_file="$PAK_DIR/res/settings.no-ip.json"
                fi
            fi
        fi
    fi

    cp "$template_file" "$cannelloni_list_file"
    if [ "$enabled" = true ]; then
        sed -i "s/IS_ENABLED/1/" "$cannelloni_list_file"
    else
        sed -i "s/IS_ENABLED/0/" "$cannelloni_list_file"
    fi
    if [ "$start_on_boot" = true ]; then
        sed -i "s/IS_START_ON_BOOT/1/" "$cannelloni_list_file"
    else
        sed -i "s/IS_START_ON_BOOT/0/" "$cannelloni_list_file"
    fi
    sed -i "s/NETWORK_SSID/$ssid/" "$cannelloni_list_file"
    sed -i "s/NETWORK_IP_ADDRESS/$ip_address/" "$cannelloni_list_file"

    killall cannelloni-presenter >/dev/null 2>&1 || true
    cannelloni-list --disable-auto-sleep --item-key settings --file "$cannelloni_list_file" --format json --cancel-text "EXIT" --title "Wifi Configuration" --write-location /tmp/cannelloni-output --write-value state
}

networks_screen() {
    cannelloni_list_file="/tmp/cannelloni-list"
    rm -f "$cannelloni_list_file" "/tmp/cannelloni-output"
    touch "$cannelloni_list_file"

    show_message "Scanning for networks" forever
    DELAY=15

    if [ "$PLATFORM" = "my355" ]; then
        wpa_cli -i wlan0 scan 2>/dev/null
        for i in $(seq 1 "$DELAY"); do
            wpa_cli -i wlan0 scan_results 2>/dev/null | grep -v "ssid" | cut -f 5 | sort -u >>"$cannelloni_list_file"
            if [ -s "$cannelloni_list_file" ]; then
                break
            fi
            sleep 1
        done
    else
        for i in $(seq 1 "$DELAY"); do
            iw dev wlan0 scan 2>/dev/null | grep SSID: | cut -d':' -f2- | sed -e 's/^[ \t]*//' -e 's/[ \t]*$//' | sort -u >>"$cannelloni_list_file"
            if [ -s "$cannelloni_list_file" ]; then
                break
            fi
            sleep 1
        done
    fi

    killall cannelloni-presenter >/dev/null 2>&1 || true
    cannelloni-list --disable-auto-sleep --file "$cannelloni_list_file" --format text --confirm-text "CONNECT" --title "Wifi Networks" --write-location /tmp/cannelloni-output
}

saved_networks_screen() {
    cannelloni_list_file="/tmp/cannelloni-list"
    rm -f "$cannelloni_list_file" "/tmp/cannelloni-output"
    touch "$cannelloni_list_file"

    get_all_saved_networks | sed '/^$/d' >"$cannelloni_list_file"

    if [ ! -s "$cannelloni_list_file" ]; then
        show_message "No saved networks found" 2
        return 1
    fi

    killall cannelloni-presenter >/dev/null 2>&1 || true
    cannelloni-list --disable-auto-sleep --file "$cannelloni_list_file" --format text --title "Wifi Networks" --confirm-text "FORGET" --write-location /tmp/cannelloni-output
}

password_screen() {
    SSID="$1"

    rm -f "/tmp/cannelloni-output"
    initial_password="$(get_network_password "$SSID")"

    killall cannelloni-presenter >/dev/null 2>&1 || true
    cannelloni-keyboard --title "Enter Password" --initial-value "$initial_password" --write-location /tmp/cannelloni-output
    exit_code=$?
    if [ "$exit_code" -eq 2 ]; then
        return 2
    fi
    if [ "$exit_code" -eq 3 ]; then
        return 3
    fi
    if [ "$exit_code" -ne 0 ]; then
        show_message "Error entering password" 2
        return 1
    fi

    password="$(cat /tmp/cannelloni-output)"
    if [ -z "$password" ]; then
        show_message "Password cannot be empty" 2
        return 1
    fi

    save_network_credential "$SSID" "$password"
    return 0
}

show_message() {
    message="$1"
    seconds="$2"

    if [ -z "$seconds" ]; then
        seconds="forever"
    fi

    killall cannelloni-presenter >/dev/null 2>&1 || true
    echo "$message" 1>&2
    if [ "$PLATFORM" = "miyoomini" ]; then
        SAY_BIN="$SDCARD_PATH/.system/miyoomini/bin/say.elf"
        [ ! -x "$SAY_BIN" ] && SAY_BIN="say.elf"
        if command -v "$SAY_BIN" >/dev/null 2>&1 || [ -x "$SAY_BIN" ]; then
            if [ "$seconds" = "forever" ]; then
                "$SAY_BIN" "$message" &
            else
                "$SAY_BIN" "$message" &
                SAY_PID=$!
                sleep "$seconds"
                kill $SAY_PID 2>/dev/null
            fi
        fi
        return 0
    fi
    if [ "$seconds" = "forever" ]; then
        cannelloni-presenter --message "$message" --timeout -1 &
    else
        cannelloni-presenter --message "$message" --timeout "$seconds"
    fi
}

disable_start_on_boot() {
    if [ -f "$SDCARD_PATH/.userdata/$PLATFORM/auto.sh" ]; then
        sed -i "/${PAK_NAME}.pak-on-boot/d" "$SDCARD_PATH/.userdata/$PLATFORM/auto.sh"
        sed -i "/Wi-Fi.pak-on-boot/d" "$SDCARD_PATH/.userdata/$PLATFORM/auto.sh"
        sync
    fi
    return 0
}

enable_start_on_boot() {
    mkdir -p "$SDCARD_PATH/.userdata/$PLATFORM"
    if [ ! -f "$SDCARD_PATH/.userdata/$PLATFORM/auto.sh" ]; then
        echo '#!/bin/sh' >"$SDCARD_PATH/.userdata/$PLATFORM/auto.sh"
        echo '' >>"$SDCARD_PATH/.userdata/$PLATFORM/auto.sh"
    fi

    echo "test -f \"\$SDCARD_PATH/Settings/\$PLATFORM/$PAK_NAME.pak/bin/on-boot\" && \"\$SDCARD_PATH/Settings/\$PLATFORM/$PAK_NAME.pak/bin/on-boot\" # ${PAK_NAME}.pak-on-boot" >>"$SDCARD_PATH/.userdata/$PLATFORM/auto.sh"
    chmod +x "$SDCARD_PATH/.userdata/$PLATFORM/auto.sh"
    sync
    return 0
}

will_start_on_boot() {
    if [ -f "$SDCARD_PATH/.userdata/$PLATFORM/auto.sh" ]; then
        if grep -q -E "(${PAK_NAME}|Wi-Fi)\.pak-on-boot" "$SDCARD_PATH/.userdata/$PLATFORM/auto.sh" >/dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

write_config() {
    ENABLING_WIFI="${1:-true}"

    echo "Generating wpa_supplicant.conf"
    template_file="$PAK_DIR/res/wpa_supplicant.conf.tmpl"
    if [ "$PLATFORM" = "miyoomini" ] || [ "$PLATFORM" = "my282" ] || [ "$PLATFORM" = "my355" ]; then
        template_file="$PAK_DIR/res/wpa_supplicant.conf.$PLATFORM.tmpl"
    fi

    cp "$template_file" "$PAK_DIR/res/wpa_supplicant.conf"
    if [ "$PLATFORM" = "rg35xxplus" ]; then
        echo "Generating netplan.yaml"
        cp "$PAK_DIR/res/netplan.yaml.tmpl" "$PAK_DIR/res/netplan.yaml"
    fi

    migrate_legacy_wifi_txt

    if [ "$ENABLING_WIFI" = "true" ]; then
        has_passwords=false
        priority_used=false

        if [ -f "$SECURE_NET_CONF" ]; then
            while IFS= read -r line || [ -n "$line" ]; do
                case "$line" in
                    NET:*)
                        enc_s=$(echo "$line" | cut -d: -f2)
                        enc_p=$(echo "$line" | cut -d: -f3)
                        ssid=$(decode_cred "$enc_s")
                        psk=$(decode_cred "$enc_p")
                        [ -z "$ssid" ] && continue
                        has_passwords=true
                        {
                            echo "network={"
                            echo "    ssid=\"$ssid\""
                            if [ "$priority_used" = false ]; then
                                echo "    priority=1"
                                priority_used=true
                            fi
                            if [ -z "$psk" ]; then
                                echo "    key_mgmt=NONE"
                            else
                                echo "    psk=\"$psk\""
                            fi
                            echo "}"
                        } >>"$PAK_DIR/res/wpa_supplicant.conf"
                        if [ "$PLATFORM" = "rg35xxplus" ]; then
                            {
                                echo "                \"$ssid\":"
                                echo "                    password: \"$psk\""
                            } >>"$PAK_DIR/res/netplan.yaml"
                        fi
                        ;;
                esac
            done < "$SECURE_NET_CONF"
        fi
    fi

    if [ "$PLATFORM" = "miyoomini" ]; then
        cp "$PAK_DIR/res/wpa_supplicant.conf" /etc/wifi/wpa_supplicant.conf 2>/dev/null
        cp "$PAK_DIR/res/wpa_supplicant.conf" /appconfigs/wpa_supplicant.conf 2>/dev/null
    elif [ "$PLATFORM" = "my282" ]; then
        cp "$PAK_DIR/res/wpa_supplicant.conf" /etc/wifi/wpa_supplicant.conf 2>/dev/null
        cp "$PAK_DIR/res/wpa_supplicant.conf" /config/wpa_supplicant.conf 2>/dev/null
    elif [ "$PLATFORM" = "my355" ]; then
        cp "$PAK_DIR/res/wpa_supplicant.conf" /userdata/cfg/wpa_supplicant.conf 2>/dev/null
    elif [ "$PLATFORM" = "rg35xxplus" ]; then
        cp "$PAK_DIR/res/wpa_supplicant.conf" /etc/wpa_supplicant/wpa_supplicant.conf 2>/dev/null
        cp "$PAK_DIR/res/netplan.yaml" /etc/netplan/01-netcfg.yaml 2>/dev/null
        if [ "$has_passwords" = false ]; then
            rm -f /etc/netplan/01-netcfg.yaml
        fi
    elif [ "$PLATFORM" = "tg5040" ]; then
        cp "$PAK_DIR/res/wpa_supplicant.conf" /etc/wifi/wpa_supplicant.conf 2>/dev/null
    fi
    sync
}

has_credentials() {
    has_saved_networks
}

wifi_off() {
    echo "Preparing to toggle wifi off"

    if ! write_config "false"; then
        return 1
    fi

    if ! service-off; then
        return 1
    fi
    return 0
}

wifi_on() {
    echo "Preparing to toggle wifi on"

    if ! write_config "true"; then
        return 1
    fi

    if ! service-on; then
        return 1
    fi

    if ! has_credentials; then
        show_message "No saved Wi-Fi networks found" 2
        return 0
    fi

    DELAY=20
    for i in $(seq 1 "$DELAY"); do
        STATUS=$(cat "/sys/class/net/wlan0/operstate" 2>/dev/null)
        if [ "$STATUS" = "up" ]; then
            break
        fi
        sleep 1
    done

    if [ "$STATUS" != "up" ]; then
        return 1
    fi
}

forget_network_loop() {
    next_screen="main"
    while true; do
        saved_networks_screen
        exit_code=$?
        if [ "$exit_code" -eq 2 ]; then
            break
        fi
        if [ "$exit_code" -eq 3 ]; then
            next_screen="exit"
            break
        fi
        if [ "$exit_code" -ne 0 ]; then
            next_screen="main"
            break
        fi

        SSID="$(cat /tmp/cannelloni-output)"
        delete_network_credential "$SSID"
        if ! write_config "true"; then
            show_message "Failed to write wireless config" 2
            break
        fi

        show_message "Refreshing connection" forever
        if ! wifi_off; then
            show_message "Failed to stop wifi" 2
            break
        fi

        if ! wifi_on; then
            show_message "Failed to restart wifi" 2
            break
        fi
        break
    done

    killall cannelloni-presenter >/dev/null 2>&1 || true
    echo "$next_screen" >/tmp/wifi-next-screen
}

network_loop() {
    if ! wifi-enabled; then
        show_message "Enabling wifi" forever
        if ! service-on; then
            show_message "Failed to enable wifi" 2
            return 1
        fi
    fi

    next_screen="main"
    while true; do
        networks_screen
        exit_code=$?
        if [ "$exit_code" -eq 2 ]; then
            break
        fi
        if [ "$exit_code" -eq 3 ]; then
            next_screen="exit"
            break
        fi
        if [ "$exit_code" -ne 0 ]; then
            show_message "Error selecting a network" 2
            next_screen="main"
            break
        fi

        SSID="$(cat /tmp/cannelloni-output)"
        password_screen "$SSID"
        exit_code=$?
        if [ "$exit_code" -eq 2 ]; then
            continue
        fi
        if [ "$exit_code" -eq 3 ]; then
            next_screen="exit"
            break
        fi
        if [ "$exit_code" -ne 0 ]; then
            continue
        fi

        show_message "Connecting to $SSID" forever
        if ! wifi_on; then
            show_message "Failed to start wifi" 2
            break
        fi
        break
    done

    killall cannelloni-presenter >/dev/null 2>&1 || true
    echo "$next_screen" >/tmp/wifi-next-screen
}

cleanup() {
    rm -f /tmp/stay_awake /tmp/wifi-next-screen
    killall cannelloni-presenter >/dev/null 2>&1 || true
}

main() {
    echo "1" >/tmp/stay_awake
    trap "cleanup" EXIT INT TERM HUP QUIT

    if [ "$PLATFORM" = "tg3040" ] && [ -z "$DEVICE" ]; then
        export DEVICE="brick"
        export PLATFORM="tg5040"
    fi

    if [ "$PLATFORM" = "miyoomini" ] && [ -z "$DEVICE" ]; then
        export DEVICE="miyoomini"
        if [ -f /customer/app/axp_test ]; then
            export DEVICE="miyoominiplus"
        fi
    fi

    # Check for binaries with executable fallback
    if ! command -v cannelloni-keyboard >/dev/null 2>&1 && [ ! -x "$PAK_DIR/bin/$PLATFORM/cannelloni-keyboard" ]; then
        show_message "cannelloni-keyboard not found" 2
        return 1
    fi

    if ! command -v cannelloni-list >/dev/null 2>&1 && [ ! -x "$PAK_DIR/bin/$PLATFORM/cannelloni-list" ]; then
        show_message "cannelloni-list not found" 2
        return 1
    fi

    if ! command -v cannelloni-presenter >/dev/null 2>&1 && [ ! -x "$PAK_DIR/bin/$PLATFORM/cannelloni-presenter" ]; then
        show_message "cannelloni-presenter not found" 2
        return 1
    fi

    allowed_platforms="miyoomini my282 my355 tg5040 rg35xxplus"
    if ! echo "$allowed_platforms" | grep -q "$PLATFORM"; then
        show_message "$PLATFORM is not a supported platform" 2
        return 1
    fi

    if [ "$PLATFORM" = "miyoomini" ]; then
        if [ ! -f /customer/app/axp_test ]; then
            show_message "Wifi not supported on non-Plus version of the Miyoo Mini" 2
            return 1
        fi

        if ! grep -q 8188fu /proc/modules 2>/dev/null; then
            insmod "$PAK_DIR/res/miyoomini/8188fu.ko" 2>/dev/null
        fi

        # Power on hardware Wi-Fi chip and initialize interface
        /customer/app/axp_test wifion 2>/dev/null
        ifconfig wlan0 up 2>/dev/null
    fi

    if [ "$PLATFORM" = "rg35xxplus" ]; then
        RGXX_MODEL="$(strings /mnt/vendor/bin/dmenu.bin 2>/dev/null | grep ^RG)"
        if [ "$RGXX_MODEL" = "RG28xx" ]; then
            show_message "Wifi not supported on RG28XX" 2
            return 1
        fi
    fi

    while true; do
        main_screen
        exit_code=$?
        # exit codes: 2 = back button, 3 = menu button
        if [ "$exit_code" -ne 0 ]; then
            break
        fi

        output="$(cat /tmp/cannelloni-output)"
        selected_index="$(echo "$output" | jq -r '.selected')"
        selection="$(echo "$output" | jq -r ".settings[$selected_index].name")"

        if [ "$selection" = "Enable" ]; then
            selected_option_index="$(echo "$output" | jq -r ".settings[$selected_index].selected")"
            selected_option="$(echo "$output" | jq -r ".settings[$selected_index].options[$selected_option_index]")"

            if [ "$selected_option" = "true" ]; then
                if ! wifi-enabled; then
                    show_message "Enabling wifi" forever
                    if ! wifi_on; then
                        show_message "Failed to enable wifi" 2
                        continue
                    fi
                fi
            else
                if wifi-enabled; then
                    show_message "Disabling wifi" forever
                    if ! wifi_off; then
                        show_message "Failed to disable wifi" 2
                        continue
                    fi
                fi
            fi
        elif [ "$selection" = "Start on boot" ]; then
            selected_option_index="$(echo "$output" | jq -r ".settings[$selected_index].selected")"
            selected_option="$(echo "$output" | jq -r ".settings[$selected_index].options[$selected_option_index]")"

            if [ "$selected_option" = "true" ]; then
                if ! will_start_on_boot; then
                    show_message "Enabling start on boot" forever
                    if ! enable_start_on_boot; then
                        show_message "Failed to enable start on boot" 2
                        continue
                    fi
                fi
            else
                if will_start_on_boot; then
                    show_message "Disabling start on boot" forever
                    if ! disable_start_on_boot; then
                        show_message "Failed to disable start on boot" 2
                        continue
                    fi
                fi
            fi
        elif echo "$selection" | grep -q "^Connect to network$"; then
            network_loop
            next_screen="$(cat /tmp/wifi-next-screen 2>/dev/null)"
            if [ "$next_screen" = "exit" ]; then
                break
            fi
        elif echo "$selection" | grep -q "^Forget a network$"; then
            forget_network_loop
            next_screen="$(cat /tmp/wifi-next-screen 2>/dev/null)"
            if [ "$next_screen" = "exit" ]; then
                break
            fi
        elif echo "$selection" | grep -q "^Refresh connection$"; then
            show_message "Disconnecting from wifi" forever
            if ! wifi_off; then
                show_message "Failed to stop wifi" 2
                return 1
            fi

            show_message "Updating wifi config" forever
            if ! write_config "true"; then
                show_message "Failed to write config" 2
            fi

            show_message "Refreshing connection" forever
            if ! service-on; then
                show_message "Failed to enable wifi" 2
                continue
            fi
        fi
    done
}

main "$@"
