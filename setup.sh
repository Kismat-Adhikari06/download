#!/usr/bin/env bash
set -euo pipefail

# Setup: create a venv (reusing system GTK/libadwaita via --system-site-packages)
# and install the Python deps (yt-dlp) into it.

cd "$(dirname "$0")"

VENV=".venv"

if [ ! -x "$VENV/bin/python" ]; then
    echo "==> Creating virtual environment in $VENV (reusing system packages)..."
    python3 -m venv --system-site-packages "$VENV"
fi

echo "==> Installing/updating dependencies..."
"$VENV/bin/pip" install --upgrade -r requirements-gui.txt

echo ""
echo "Setup complete. Launch with: ./run.sh"
