#!/bin/sh
# Run from a Linux/macOS host with Docker and make, not inside a toolchain.
set -eu
cd "$(dirname "$0")/.."
git rev-parse --short HEAD > workspace/hash.txt
if [ "$#" -eq 0 ]; then
    set -- gkdpixel m17 magicmini miyoomini my282 my355 rg35xx rg35xxplus rgb30 tg5040 trimuismart zero28
fi
for platform in "$@"; do
    case "$platform" in
        gkdpixel|m17|magicmini|miyoomini|my282|my355|rg35xx|rg35xxplus|rgb30|tg5040|trimuismart|zero28) ;;
        *) echo "Unknown platform: $platform" >&2; exit 1 ;;
    esac
    make -f makefile.toolchain PLATFORM="$platform" frontends
done
