#!/bin/sh
printf "Content-Type: application/json\r\n\r\n"

SDCARD="/mnt/SDCARD"

# Parse query string parameters
parse_param() {
    echo "$QUERY_STRING" | tr '&' '\n' | grep "^$1=" | cut -d= -f2- | sed -e 's/+/ /g' -e 's/%20/ /g' -e 's/%2F/\//g' -e 's/%2f/\//g'
}

ACTION=$(parse_param "action")
DIR=$(parse_param "dir")
[ -z "$DIR" ] && DIR="Roms"
# Sanitize DIR
DIR=$(echo "$DIR" | sed 's/\.\.//g' | sed 's/^\///')

case "$ACTION" in
    status)
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
                    SIZE="-"
                else
                    TYPE="file"
                    SIZE=$(ls -lh "$item" 2>/dev/null | awk '{print $5}')
                fi
                if [ $FIRST -eq 0 ]; then
                    printf ","
                fi
                FIRST=0
                printf '{"name":"%s","type":"%s","size":"%s"}' "$NAME" "$TYPE" "$SIZE"
            done
        fi
        printf "]\n"
        ;;

    upload)
        NAME=$(parse_param "name")
        [ -z "$NAME" ] && NAME="upload_$(date +%s)"
        NAME=$(echo "$NAME" | sed 's/\.\.//g' | sed 's/^\///')
        TARGET_FILE="$SDCARD/$DIR/$NAME"
        mkdir -p "$(dirname "$TARGET_FILE")"
        if [ -n "$CONTENT_LENGTH" ] && [ "$CONTENT_LENGTH" -gt 0 ]; then
            head -c "$CONTENT_LENGTH" > "$TARGET_FILE"
        else
            cat > "$TARGET_FILE"
        fi
        sync
        printf '{"status":"ok","file":"%s"}\n' "$NAME"
        ;;

    delete)
        PATH_PARAM=$(parse_param "path")
        PATH_PARAM=$(echo "$PATH_PARAM" | sed 's/\.\.//g' | sed 's/^\///')
        if [ -n "$PATH_PARAM" ] && [ -e "$SDCARD/$PATH_PARAM" ]; then
            rm -rf "$SDCARD/$PATH_PARAM"
            sync
            printf '{"status":"ok"}\n'
        else
            printf '{"status":"error","message":"file not found"}\n'
        fi
        ;;

    *)
        printf '{"status":"online","service":"Nonna'\''s Kitchen"}\n'
        ;;
esac
