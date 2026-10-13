#!/bin/sh
# Cannelloni Secure Network Storage Engine
# Encrypted and protected network credential management.

[ -z "$SDCARD_PATH" ] && SDCARD_PATH="/mnt/SDCARD"
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
