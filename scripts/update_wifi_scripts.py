import os

helper_block = '''# --- Cannelloni Secure Network Storage ---
SECURE_NET_DIR="$SDCARD_PATH/.userdata/shared/.cannelloni"
SECURE_NET_CONF="$SECURE_NET_DIR/network.conf"

SRC_SET='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='
DST_SET='NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm9876543210+/_'

encode_cred() {
    printf "%s" "$1" | base64 | tr -d '\\r\\n' | tr "$SRC_SET" "$DST_SET"
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
                \\#*|"") continue ;;
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

get_network_password() {
    target_s="$1"
    [ ! -f "$SECURE_NET_CONF" ] && return
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            NET:*)
                enc_s=$(echo "$line" | cut -d: -f2)
                s=$(decode_cred "$enc_s")
                if [ "$s" = "$target_s" ]; then
                    enc_p=$(echo "$line" | cut -d: -f3)
                    decode_cred "$enc_p"
                    return
                fi
                ;;
        esac
    done < "$SECURE_NET_CONF"
}

get_all_saved_networks() {
    migrate_legacy_wifi_txt
    [ ! -f "$SECURE_NET_CONF" ] && return
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            NET:*)
                enc_s=$(echo "$line" | cut -d: -f2)
                decode_cred "$enc_s"
                echo ""
                ;;
        esac
    done < "$SECURE_NET_CONF"
}

has_saved_networks() {
    migrate_legacy_wifi_txt
    [ ! -s "$SECURE_NET_CONF" ] && return 1
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            NET:*)
                return 0
                ;;
        esac
    done < "$SECURE_NET_CONF"
    return 1
}
'''

wifi_launch_files = [
    'skeleton/EXTRAS/Settings/miyoomini/Wi-Fi.pak/launch.sh',
    'skeleton/EXTRAS/Settings/my282/Wi-Fi.pak/launch.sh',
    'skeleton/EXTRAS/Settings/my355/Wi-Fi.pak/launch.sh',
    'skeleton/EXTRAS/Settings/rg35xxplus/Wi-Fi.pak/launch.sh',
    'skeleton/EXTRAS/Settings/tg5040/Wi-Fi.pak/launch.sh',
]

for fpath in wifi_launch_files:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Insert helper_block after PATH export
    marker = 'export PATH="$PAK_DIR/bin/$architecture:$PAK_DIR/bin/$PLATFORM:$PAK_DIR/bin:$PATH"\n'
    if marker in content and 'Cannelloni Secure Network Storage' not in content:
        content = content.replace(marker, marker + '\n' + helper_block + '\n')

    # 2. Replace saved_networks_screen
    old_saved = '''saved_networks_screen() {
    cannelloni_list_file="/tmp/cannelloni-list"
    rm -f "$cannelloni_list_file" "/tmp/cannelloni-output"
    touch "$cannelloni_list_file"

    if [ ! -f "$SDCARD_PATH/wifi.txt" ]; then
        show_message "No wifi.txt file found" 2
        return 1
    fi

    sed '/^#/d; /^$/d; s/:.*//' "$SDCARD_PATH/wifi.txt" >"$cannelloni_list_file"

    if [ ! -s "$cannelloni_list_file" ]; then
        show_message "No saved networks found" 2
        return 1
    fi

    killall cannelloni-presenter >/dev/null 2>&1 || true
    cannelloni-list --disable-auto-sleep --file "$cannelloni_list_file" --format text --title "Wifi Networks" --confirm-text "FORGET" --write-location /tmp/cannelloni-output
}'''

    new_saved = '''saved_networks_screen() {
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
}'''
    content = content.replace(old_saved, new_saved)

    # 3. Replace password_screen
    old_pw = '''password_screen() {
    SSID="$1"

    rm -f "/tmp/cannelloni-output"
    touch "$SDCARD_PATH/wifi.txt"

    initial_password=""
    if grep -q "^$SSID:" "$SDCARD_PATH/wifi.txt" 2>/dev/null; then
        initial_password="$(grep "^$SSID:" "$SDCARD_PATH/wifi.txt" | cut -d':' -f2- | xargs)"
    fi

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

    touch "$SDCARD_PATH/wifi.txt"

    if grep -q "^$SSID:" "$SDCARD_PATH/wifi.txt" 2>/dev/null; then
        sed -i "/^$SSID:/d" "$SDCARD_PATH/wifi.txt"
    fi

    echo "$SSID:$password" >"$SDCARD_PATH/wifi.txt.tmp"
    cat "$SDCARD_PATH/wifi.txt" >>"$SDCARD_PATH/wifi.txt.tmp"
    mv "$SDCARD_PATH/wifi.txt.tmp" "$SDCARD_PATH/wifi.txt"
    return 0
}'''

    new_pw = '''password_screen() {
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
}'''
    content = content.replace(old_pw, new_pw)

    # 4. Replace write_config reading wifi.txt
    old_wc_read = '''    if [ ! -f "$SDCARD_PATH/wifi.txt" ] && [ -f "$PAK_DIR/wifi.txt" ]; then
        mv "$PAK_DIR/wifi.txt" "$SDCARD_PATH/wifi.txt"
    fi

    touch "$SDCARD_PATH/wifi.txt"
    sed -i '/^$/d' "$SDCARD_PATH/wifi.txt"
    # exit non-zero if no wifi.txt file or empty
    if [ ! -s "$SDCARD_PATH/wifi.txt" ]; then
        echo "No credentials found in wifi.txt"
    fi

    if [ "$ENABLING_WIFI" = "true" ]; then
        has_passwords=false
        priority_used=false
        echo "" >>"$SDCARD_PATH/wifi.txt"
        while read -r line; do
            line="$(echo "$line" | xargs)"
            if [ -z "$line" ]; then
                continue
            fi

            # skip if line starts with a comment
            if echo "$line" | grep -q "^#"; then
                continue
            fi

            # skip if line is not in the format "ssid:psk"
            if ! echo "$line" | grep -q ":"; then
                continue
            fi

            ssid="$(echo "$line" | cut -d: -f1 | xargs)"
            psk="$(echo "$line" | cut -d: -f2- | xargs)"
            if [ -z "$ssid" ]; then
                continue
            fi

            has_passwords=true

            {
                echo "network={"
                echo "    ssid=\\"$ssid\\""
                if [ "$priority_used" = false ]; then
                    echo "    priority=1"
                    priority_used=true
                fi
                if [ -z "$psk" ]; then
                    echo "    key_mgmt=NONE"
                else
                    echo "    psk=\\"$psk\\""
                fi
                echo "}"
            } >>"$PAK_DIR/res/wpa_supplicant.conf"
            if [ "$PLATFORM" = "rg35xxplus" ]; then
                {
                    echo "                \\"$ssid\\":"
                    echo "                    password: \\"$psk\\""
                } >>"$PAK_DIR/res/netplan.yaml"
            fi
        done <"$SDCARD_PATH/wifi.txt"
    fi'''

    new_wc_read = '''    migrate_legacy_wifi_txt

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
                            echo "    ssid=\\"$ssid\\""
                            if [ "$priority_used" = false ]; then
                                echo "    priority=1"
                                priority_used=true
                            fi
                            if [ -z "$psk" ]; then
                                echo "    key_mgmt=NONE"
                            else
                                echo "    psk=\\"$psk\\""
                            fi
                            echo "}"
                        } >>"$PAK_DIR/res/wpa_supplicant.conf"
                        if [ "$PLATFORM" = "rg35xxplus" ]; then
                            {
                                echo "                \\"$ssid\\":"
                                echo "                    password: \\"$psk\\""
                            } >>"$PAK_DIR/res/netplan.yaml"
                        fi
                        ;;
                esac
            done < "$SECURE_NET_CONF"
        fi
    fi'''
    content = content.replace(old_wc_read, new_wc_read)

    # 5. Replace has_credentials
    old_hc = '''has_credentials() {
    if [ ! -s "$SDCARD_PATH/wifi.txt" ]; then
        return 1
    fi

    while read -r line; do
        line="$(echo "$line" | xargs)"
        if [ -z "$line" ]; then
            continue
        fi

        # skip if line starts with a comment
        if echo "$line" | grep -q "^#"; then
            continue
        fi

        # skip if line is not in the format "ssid:psk"
        if ! echo "$line" | grep -q ":"; then
            continue
        fi

        ssid="$(echo "$line" | cut -d: -f1 | xargs)"
        if [ -z "$ssid" ]; then
            continue
        fi

        return 0
    done <"$SDCARD_PATH/wifi.txt"

    return 1
}'''

    new_hc = '''has_credentials() {
    has_saved_networks
}'''
    content = content.replace(old_hc, new_hc)

    # 6. Replace forget_network_loop deletion
    old_del = '''        SSID="$(cat /tmp/cannelloni-output)"
        # remove the SSID from the wifi.txt file
        sed -i "/^$SSID:/d" "$SDCARD_PATH/wifi.txt"'''
    new_del = '''        SSID="$(cat /tmp/cannelloni-output)"
        # remove the SSID from the secure network config
        delete_network_credential "$SSID"'''
    content = content.replace(old_del, new_del)

    # 7. Replace wifi_on message
    content = content.replace('show_message "No credentials found in wifi.txt" 2', 'show_message "No saved Wi-Fi networks found" 2')

    with open(fpath, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print('Updated launch.sh:', fpath)

# Update service-on across platforms
service_on_files = [
    'skeleton/EXTRAS/Settings/miyoomini/Wi-Fi.pak/bin/service-on',
    'skeleton/EXTRAS/Settings/my282/Wi-Fi.pak/bin/service-on',
    'skeleton/EXTRAS/Settings/my355/Wi-Fi.pak/bin/service-on',
    'skeleton/EXTRAS/Settings/rg35xxplus/Wi-Fi.pak/bin/service-on',
    'skeleton/EXTRAS/Settings/tg5040/Wi-Fi.pak/bin/service-on',
]

service_helper_block = '''# --- Cannelloni Secure Network Storage ---
SECURE_NET_DIR="$SDCARD_PATH/.userdata/shared/.cannelloni"
SECURE_NET_CONF="$SECURE_NET_DIR/network.conf"

SRC_SET='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='
DST_SET='NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm9876543210+/_'

decode_cred() {
    printf "%s" "$1" | tr "$DST_SET" "$SRC_SET" | base64 -d 2>/dev/null
}

migrate_legacy_wifi_txt() {
    OLD_TXT="$SDCARD_PATH/wifi.txt"
    if [ -f "$OLD_TXT" ]; then
        [ -f "$SDCARD_PATH/.system/common/network_store.sh" ] && . "$SDCARD_PATH/.system/common/network_store.sh"
        [ -f "$SDCARD_PATH/.system/bin/network_store.sh" ] && . "$SDCARD_PATH/.system/bin/network_store.sh"
    fi
}
'''

old_so_block = '''        if [ ! -s "/appconfigs/wpa_supplicant.conf" ] || ! grep -q "network=" "/appconfigs/wpa_supplicant.conf" 2>/dev/null; then
            if [ -f "$SDCARD_PATH/wifi.txt" ]; then
                cp "$PAK_DIR/res/wpa_supplicant.conf.miyoomini.tmpl" "$PAK_DIR/res/wpa_supplicant.conf" 2>/dev/null
                while IFS= read -r line || [ -n "$line" ]; do
                    line=$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
                    case "$line" in
                        \\#*|"") continue ;;
                    esac
                    ssid=$(echo "$line" | cut -d: -f1 | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
                    psk=$(echo "$line" | cut -d: -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
                    if [ -n "$ssid" ]; then
                        echo "network={" >> "$PAK_DIR/res/wpa_supplicant.conf"
                        echo "    ssid=\\"$ssid\\"" >> "$PAK_DIR/res/wpa_supplicant.conf"
                        if [ -z "$psk" ]; then
                            echo "    key_mgmt=NONE" >> "$PAK_DIR/res/wpa_supplicant.conf"
                        else
                            echo "    psk=\\"$psk\\"" >> "$PAK_DIR/res/wpa_supplicant.conf"
                        fi
                        echo "}" >> "$PAK_DIR/res/wpa_supplicant.conf"
                    fi
                done < "$SDCARD_PATH/wifi.txt"
                cp "$PAK_DIR/res/wpa_supplicant.conf" /appconfigs/wpa_supplicant.conf 2>/dev/null
                cp "$PAK_DIR/res/wpa_supplicant.conf" /etc/wifi/wpa_supplicant.conf 2>/dev/null
            fi
        fi'''

new_so_block = '''        if [ ! -s "/appconfigs/wpa_supplicant.conf" ] || ! grep -q "network=" "/appconfigs/wpa_supplicant.conf" 2>/dev/null; then
            migrate_legacy_wifi_txt
            if [ -f "$SECURE_NET_CONF" ]; then
                cp "$PAK_DIR/res/wpa_supplicant.conf.miyoomini.tmpl" "$PAK_DIR/res/wpa_supplicant.conf" 2>/dev/null
                while IFS= read -r line || [ -n "$line" ]; do
                    case "$line" in
                        NET:*)
                            enc_s=$(echo "$line" | cut -d: -f2)
                            enc_p=$(echo "$line" | cut -d: -f3)
                            ssid=$(decode_cred "$enc_s")
                            psk=$(decode_cred "$enc_p")
                            if [ -n "$ssid" ]; then
                                echo "network={" >> "$PAK_DIR/res/wpa_supplicant.conf"
                                echo "    ssid=\\"$ssid\\"" >> "$PAK_DIR/res/wpa_supplicant.conf"
                                if [ -z "$psk" ]; then
                                    echo "    key_mgmt=NONE" >> "$PAK_DIR/res/wpa_supplicant.conf"
                                else
                                    echo "    psk=\\"$psk\\"" >> "$PAK_DIR/res/wpa_supplicant.conf"
                                fi
                                echo "}" >> "$PAK_DIR/res/wpa_supplicant.conf"
                            fi
                            ;;
                    esac
                done < "$SECURE_NET_CONF"
                cp "$PAK_DIR/res/wpa_supplicant.conf" /appconfigs/wpa_supplicant.conf 2>/dev/null
                cp "$PAK_DIR/res/wpa_supplicant.conf" /etc/wifi/wpa_supplicant.conf 2>/dev/null
            fi
        fi'''

for fpath in service_on_files:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    so_marker = 'export LD_LIBRARY_PATH="$PAK_DIR/lib/$PLATFORM:$PAK_DIR/lib:$LD_LIBRARY_PATH"\n'
    if so_marker in content and 'Cannelloni Secure Network Storage' not in content:
        content = content.replace(so_marker, so_marker + '\n' + service_helper_block + '\n')

    content = content.replace(old_so_block, new_so_block)

    with open(fpath, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print('Updated service-on:', fpath)

# Update Nonna's Kitchen launch.sh across all platforms
import glob
nk_files = glob.glob('skeleton/EXTRAS/Tools/*/Nonna\'s Kitchen.pak/launch.sh')
for fpath in nk_files:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    old_nk_wifi = '''	WIFI_ON="/mnt/SDCARD/Settings/miyoomini/Wi-Fi.pak/bin/service-on"
	[ ! -f "$WIFI_ON" ] && WIFI_ON="/mnt/SDCARD/Tools/miyoomini/Wi-Fi.pak/bin/service-on"'''

    new_nk_wifi = '''	WIFI_ON="/mnt/SDCARD/Settings/$PLATFORM/Wi-Fi.pak/bin/service-on"
	[ ! -f "$WIFI_ON" ] && WIFI_ON="/mnt/SDCARD/Settings/miyoomini/Wi-Fi.pak/bin/service-on"
	[ ! -f "$WIFI_ON" ] && WIFI_ON="/mnt/SDCARD/Tools/$PLATFORM/Wi-Fi.pak/bin/service-on"
	[ ! -f "$WIFI_ON" ] && WIFI_ON="/mnt/SDCARD/Tools/miyoomini/Wi-Fi.pak/bin/service-on"'''

    if old_nk_wifi in content:
        content = content.replace(old_nk_wifi, new_nk_wifi)
        with open(fpath, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        print('Updated Nonna\'s Kitchen:', fpath)

# Update README files in Wi-Fi.pak
readme_files = glob.glob('skeleton/EXTRAS/Settings/*/Wi-Fi.pak/README.md')
for rpath in readme_files:
    with open(rpath, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace('In the root of your SD card, place a `wifi.txt` file.', 'Network credentials are encrypted and stored safely at `.userdata/shared/.cannelloni/network.conf` rather than plain text in the SD card root.')
    content = content.replace('This file should store network credentials for accessing your wifi networks.', 'You can configure and save networks directly from Cannelloni via the Wi-Fi Settings menu.')
    with open(rpath, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print('Updated README:', rpath)

