#!/bin/sh
# BusyBox-compatible CGI: no Python, jq, symlinks or interval-regex dependency.
LC_ALL=C
export LC_ALL
[ -n "$SDCARD" ] || SDCARD="$SDCARD_PATH"
[ -n "$SDCARD" ] || SDCARD=/mnt/SDCARD
[ -d "$SDCARD" ] || SDCARD=/storage/roms
SDCARD=$(CDPATH= cd -- "$SDCARD" 2>/dev/null && pwd -P) || exit 1

urldecode() {
    printf '%s' "$1" | awk 'BEGIN {hex="0123456789abcdef"} {
        result=""
        for (i=1; i<=length($0); i++) {
            c=substr($0,i,1)
            pair=substr($0,i+1,2)
            if (c=="%" && pair ~ /^[0-9a-fA-F][0-9a-fA-F]$/) {
                n=(index(hex,tolower(substr(pair,1,1)))-1)*16+index(hex,tolower(substr(pair,2,1)))-1
                if (n==0 || n==10 || n==13) exit 1
                result=result sprintf("%c",n); i+=2
            } else if (c=="+") result=result " "
            else result=result c
        }
        printf "%s", result
    }'
}
param() {
    value=$(printf '%s\n' "$QUERY_STRING" | tr '&' '\n' | sed -n "s/^$1=//p" | head -n 1)
    urldecode "$value"
}
json_string() {
    printf '%s' "$1" | awk 'BEGIN {printf "\""} {
        if (NR>1) printf "\\n"
        for (i=1;i<=length($0);i++) {
            c=substr($0,i,1)
            if (c=="\\" || c=="\"") printf "\\%s",c
            else if (c=="\t") printf "\\t"
            else if (c=="\r") printf "\\r"
            else if (c ~ /[[:cntrl:]]/) printf "?"
            else printf "%s",c
        }
    } END {printf "\""}'
}
json_header() { printf 'Content-Type: application/json\r\nCache-Control: no-store\r\n\r\n'; }
fail() {
    printf 'Status: %s\r\n' "$1"
    json_header
    printf '{"error":'; json_string "$2"; printf '}\n'
    exit 0
}
# Resolve existing paths physically, including symlinks, within one shared root.
resolve() {
    case "$1" in Roms|Roms/*|Bios|Bios/*|Saves|Saves/*) ;; *) return 1 ;; esac
    case "/$1/" in */../*|*/./*|*//*) return 1 ;; esac
    target=$(readlink -f "$SDCARD/$1") || return 1
    case "$target" in "$SDCARD/Roms"|"$SDCARD/Roms/"*|"$SDCARD/Bios"|"$SDCARD/Bios/"*|"$SDCARD/Saves"|"$SDCARD/Saves/"*) ;; *) return 1 ;; esac
}
require_post() { [ "$REQUEST_METHOD" = POST ] || fail '405 Method Not Allowed' 'Use POST for this operation'; }
ACTION=$(param action) || fail '400 Bad Request' 'Invalid action'
case "$ACTION" in
    status)
        info=$(df -Pk "$SDCARD" 2>/dev/null | awk 'END {print $(NF-4), $(NF-3), $(NF-2), $(NF-1)}')
        set -- $info
        [ "$#" = 4 ] || fail '500 Internal Server Error' 'Unable to read SD card storage'
        json_header
        awk -v total="$1" -v used="$2" -v free="$3" -v percent="${4%%%}" 'BEGIN {
            printf "{\"total\":\"%.1f GB\",\"used\":\"%.1f GB\",\"free\":\"%.1f GB\",\"percent\":%d}\n",total/1048576,used/1048576,free/1048576,percent
        }'
        ;;
    list)
        DIR=$(param dir) || fail '400 Bad Request' 'Invalid folder'
        [ -n "$DIR" ] || DIR=Roms
        resolve "$DIR" && [ -d "$target" ] || fail '404 Not Found' 'Folder not found'
        json_header
        printf '['; comma=
        for item in "$target"/*; do
            [ -e "$item" ] || continue
            name=${item##*/}
            if [ -d "$item" ]; then type=dir; size=; else
                type=file
                bytes=$(stat -c %s "$item" 2>/dev/null) || bytes=0
                size=$(awk -v b="$bytes" 'BEGIN {if(b>=1073741824) printf "%.1f GB",b/1073741824; else if(b>=1048576) printf "%.1f MB",b/1048576; else if(b>=1024) printf "%.1f KB",b/1024; else printf "%d B",b}')
            fi
            printf '%s{"name":' "$comma"; json_string "$name"
            printf ',"type":"%s","size":"%s"}' "$type" "$size"
            comma=,
        done
        printf ']\n'
        ;;
    upload)
        require_post
        DIR=$(param dir) || fail '400 Bad Request' 'Invalid folder'
        NAME=$(param name) || fail '400 Bad Request' 'Invalid filename'
        case "$NAME" in ''|.|..|*/*|*\\*) fail '400 Bad Request' 'Invalid filename' ;; esac
        resolve "$DIR" && [ -d "$target" ] || fail '404 Not Found' 'Folder not found'
        target_file="$target/$NAME"
        [ ! -L "$target_file" ] || fail '400 Bad Request' 'Cannot overwrite a symbolic link'
        temp=$(mktemp "$target/.kitchen-upload.XXXXXX") || fail '500 Internal Server Error' 'Cannot write to this folder'
        trap 'rm -f "$temp"' EXIT
        cat >"$temp" || fail '500 Internal Server Error' 'Could not save upload'
        actual=$(stat -c %s "$temp")
        [ "$actual" = "$CONTENT_LENGTH" ] || fail '400 Bad Request' 'Upload was incomplete'
        mv -f "$temp" "$target_file" || fail '500 Internal Server Error' 'Could not save upload'
        json_header; printf '{"status":"ok"}\n'
        ;;
    download)
        path=$(param path) || fail '400 Bad Request' 'Invalid path'
        resolve "$path" && [ -f "$target" ] || fail '404 Not Found' 'File not found'
        printf 'Content-Type: application/octet-stream\r\nContent-Length: %s\r\n\r\n' "$(stat -c %s "$target")"
        cat "$target"
        ;;
    delete)
        require_post
        path=$(param path) || fail '400 Bad Request' 'Invalid path'
        case "$path" in Roms|Bios|Saves) fail '400 Bad Request' 'Cannot delete a root folder' ;; esac
        resolve "$path" && [ -e "$target" ] || fail '404 Not Found' 'File not found'
        rm -rf "$target" || fail '500 Internal Server Error' 'Could not delete file'
        json_header; printf '{"status":"ok"}\n'
        ;;
    *) fail '400 Bad Request' 'Unknown action' ;;
esac
