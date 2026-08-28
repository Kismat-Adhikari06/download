#!/usr/bin/env bash
set -euo pipefail

# Run the GTK4 + libadwaita Universal Media Downloader using the venv Python.

cd "$(dirname "$0")"

if [ -x ".venv/bin/python" ]; then
    exec .venv/bin/python run.py "$@"
else
    echo "venv not found. Run ./setup.sh first (or: python3 -m venv --system-site-packages .venv)"
    echo "Falling back to system python3..."
    exec python3 run.py "$@"
fi
