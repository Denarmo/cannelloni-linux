#!/usr/bin/env bash
# Cannelloni SD Installer Launcher for Linux
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

# Check for Python 3
if command -v python3 >/dev/null 2>&1; then
    exec python3 "$DIR/cannelloni_installer.py" "$@"
elif command -v python >/dev/null 2>&1; then
    exec python "$DIR/cannelloni_installer.py" "$@"
else
    echo "Error: Python 3 is required to run the Cannelloni SD Installer."
    echo "Please install python3 (e.g. sudo apt install python3 python3-tk)."
    exit 1
fi
