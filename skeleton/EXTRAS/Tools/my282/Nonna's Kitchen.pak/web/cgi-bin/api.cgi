#!/bin/sh

[ -z "$SDCARD" ] && SDCARD="$SDCARD_PATH"
[ -z "$SDCARD" ] && SDCARD="/mnt/SDCARD"
[ ! -d "$SDCARD" ] && [ -d "/storage/roms" ] && SDCARD="/storage/roms"

urldecode() {
    awk 'BEGIN {
        for (i = 1; i < ARGC; i++) {
            s = ARGV[i]
            gsub(/\+/, " ", s)
            while (match(s, /%[0-9A-Fa-f]{2}/)) {
                code = substr(s, RSTART + 1, 2)
                val = (index("123456789abcdef", tolower(substr(code, 1, 1)))) * 16 + (index("123456789abcdef", tolower(substr(code, 2, 1))))
                s = substr(s, 1, RSTART - 1) sprintf("%c", val) substr(s, RSTART + 3)
            }
            print s
        }
    }' "$1"
}

# Parse query string parameters
parse_param() {
    raw_val=$(printf "%s\n" "$QUERY_STRING" | tr '&' '\n' | grep "^$1=" | head -n1 | cut -d= -f2-)
    urldecode "$raw_val"
}

ACTION=$(parse_param "action")
DIR=$(parse_param "dir")
[ -z "$DIR" ] && DIR="Roms"
# Sanitize DIR
DIR=$(echo "$DIR" | sed 's/\.\.//g' | sed 's/^\///')

case "$ACTION" in
    status)
        printf "Content-Type: application/json\r\n\r\n"
        DF_INFO=$(df -h "$SDCARD" 2>/dev/null | awk 'NR==2 {print $2, $3, $4, $5}')
        TOT=$(echo "$DF_INFO" | awk '{print $1}')
        USED=$(echo "$DF_INFO" | awk '{print $2}')
        FREE=$(echo "$DF_INFO" | awk '{print $3}')
        PCT=$(echo "$DF_INFO" | awk '{print $4}' | tr -d '%')
        [ -z "$TOT" ] && TOT="32G"
        [ -z "$USED" ] && USED="10G"
        [ -z "$FREE" ] && FREE="22G"
        [ -z "$PCT" ] && PCT="30"
        printf '{"status":"online","total":"%s","used":"%s","free":"%s","percent":%s}\n' "$TOT" "$USED" "$FREE" "$PCT"
        ;;

    list)
        printf "Content-Type: application/json\r\n\r\n"
        TARGET="$SDCARD/$DIR"
        printf "["
        FIRST=1
        if [ -d "$TARGET" ]; then
            for item in "$TARGET"/*; do
                [ -e "$item" ] || continue
                NAME=$(basename "$item")
                # Skip hidden files
                case "$NAME" in
                    .*|"") continue ;;
                esac
                if [ -d "$item" ]; then
                    TYPE="dir"
                    SIZE=""
                else
                    TYPE="file"
                    BYTES=$(wc -c < "$item" 2>/dev/null | tr -d ' \t\r\n')
                    [ -z "$BYTES" ] && BYTES=0
                    if [ "$BYTES" -ge 1073741824 ] 2>/dev/null; then
                        SIZE="$(awk "BEGIN {printf \"%.1f GB\", $BYTES/1073741824}")"
                    elif [ "$BYTES" -ge 1048576 ] 2>/dev/null; then
                        SIZE="$(awk "BEGIN {printf \"%.1f MB\", $BYTES/1048576}")"
                    elif [ "$BYTES" -ge 1024 ] 2>/dev/null; then
                        SIZE="$(awk "BEGIN {printf \"%.1f KB\", $BYTES/1024}")"
                    else
                        SIZE="${BYTES} B"
                    fi
                fi
                [ "$FIRST" = "0" ] && printf ","
                FIRST=0
                JSON_NAME=$(echo "$NAME" | sed 's/\\/\\\\/g; s/\"/\\"/g')
                printf '{"name":"%s","type":"%s","size":"%s"}' "$JSON_NAME" "$TYPE" "$SIZE"
            done
        fi
        printf "]\n"
        ;;

    upload)
        printf "Content-Type: application/json\r\n\r\n"
        NAME=$(parse_param "name")
        [ -z "$NAME" ] && NAME="upload_$(date +%s)"
        NAME=$(echo "$NAME" | sed 's/\.\.//g' | sed 's/^\///')
        TARGET_FILE="$SDCARD/$DIR/$NAME"
        mkdir -p "$SDCARD/$DIR"
        cat > "$TARGET_FILE"
        JSON_NAME=$(echo "$NAME" | sed 's/\\/\\\\/g; s/\"/\\"/g')
        printf '{"status":"ok","file":"%s"}\n' "$JSON_NAME"
        ;;

    download)
        PATH_PARAM=$(parse_param "path")
        PATH_PARAM=$(echo "$PATH_PARAM" | sed 's/\.\.//g' | sed 's/^\///')
        TARGET_FILE="$SDCARD/$PATH_PARAM"
        if [ -n "$PATH_PARAM" ] && [ -f "$TARGET_FILE" ]; then
            FNAME=$(basename "$TARGET_FILE")
            FSIZE=$(wc -c < "$TARGET_FILE" 2>/dev/null | tr -d ' \t\r\n')
            printf "Content-Type: application/octet-stream\r\n"
            printf "Content-Disposition: attachment; filename=\"%s\"\r\n" "$FNAME"
            [ -n "$FSIZE" ] && printf "Content-Length: %s\r\n" "$FSIZE"
            printf "\r\n"
            cat "$TARGET_FILE"
            exit 0
        else
            printf "Content-Type: text/plain\r\nStatus: 404 Not Found\r\n\r\nFile not found\n"
            exit 0
        fi
        ;;

    delete)
        printf "Content-Type: application/json\r\n\r\n"
        PATH_PARAM=$(parse_param "path")
        PATH_PARAM=$(echo "$PATH_PARAM" | sed 's/\.\.//g' | sed 's/^\///')
        case "$PATH_PARAM" in
            Roms|Bios|Saves|"")
                printf '{"status":"error","message":"cannot delete root folder"}\n'
                exit 0
                ;;
        esac
        if [ -n "$PATH_PARAM" ] && [ -e "$SDCARD/$PATH_PARAM" ]; then
            rm -rf "$SDCARD/$PATH_PARAM"
            printf '{"status":"ok"}\n'
        else
            printf '{"status":"error","message":"file not found"}\n'
        fi
        ;;

    *)
        printf "Content-Type: application/json\r\n\r\n"
        printf '{"status":"online","service":"Nonna'\'s Kitchen"}\n'
        ;;
esac
