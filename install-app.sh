#!/usr/bin/env bash
set -euo pipefail

# Install Universal Media Downloader as a proper desktop app:
#   - registers it in your app launcher (with icon)
#   - installs a `universal-media-downloader` command on your PATH
#   - sets up the venv (reusing system GTK/libadwaita) with yt-dlp
# Installs to ~/.local (user-only; no sudo needed).

PREFIX="${PREFIX:-$HOME/.local}"
APP_ID="com.undermedia.UniversalMediaDownloader"
APP_NAME="Universal Media Downloader"
COMMAND="universal-media-downloader"

cd "$(dirname "$0")"
ROOT="$(pwd)"

BIN_DIR="$PREFIX/bin"
APP_DIR="$PREFIX/lib/underdownload"
SHARE_DIR="$PREFIX/share"
APPS_DIR="$SHARE_DIR/applications"
ICON_THEME_DIR="$SHARE_DIR/icons/hicolor"
ICON_SVG="$ICON_THEME_DIR/scalable/apps/$APP_ID.svg"

# ---- 1. Check & install system dependencies -------------------------------
echo "==> Checking system dependencies..."

MISSING=()
command -v ffmpeg >/dev/null 2>&1 || MISSING+=("ffmpeg")
command -v aria2c >/dev/null 2>&1 || MISSING+=("aria2")

GUI_OK=1
python3 -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1'); from gi.repository import Adw" >/dev/null 2>&1 || GUI_OK=0

if [ "$GUI_OK" = "1" ]; then
    echo "    GTK4 + libadwaita + PyGObject: OK"
else
    MISSING+=("gir1.2-gtk-4.0 gir1.2-adw-1 python3-gi")
fi

if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    echo "Some system packages are missing: ${MISSING[*]}"
    echo "These are needed for the app. Installing via apt requires sudo."
    if command -v apt-get >/dev/null 2>&1; then
        read -r -p "Run: sudo apt-get install -y ${MISSING[*]} ? [y/N] " ans
        if [[ "$ans" =~ ^[Yy]$ ]]; then
            sudo apt-get update
            sudo apt-get install -y "${MISSING[@]}"
            echo "    System packages installed."
        else
            echo "Skipped. The app may not launch until these are installed."
        fi
    else
        echo "No apt-get found. Please install these using your distro's"
        echo "package manager, then re-run this script."
    fi
    echo ""
fi

# ---- 2. Build a fresh production venv (reuse system GTK/libadwaita) --------
VENV="$ROOT/.venv"
if [ ! -x "$VENV/bin/python" ]; then
    echo "==> Creating venv ($VENV)..."
    python3 -m venv --system-site-packages "$VENV"
fi

echo "==> Installing Python deps (yt-dlp)..."
"$VENV/bin/pip" install --upgrade -r requirements-gui.txt

# ---- 2. Copy app files into the install dir -------
echo "==> Installing app files -> $APP_DIR ..."
mkdir -p "$APP_DIR" "$BIN_DIR" "$APPS_DIR" "$ICON_THEME_DIR/scalable/apps"
rm -rf "$APP_DIR/app"
cp -ra app "$APP_DIR/app"
cp run.py "$APP_DIR/run.py"

# ---- 3. Launcher command -------
echo "==> Installing launcher -> $BIN_DIR/$COMMAND ..."
cat > "$BIN_DIR/$COMMAND" <<EOF
#!/usr/bin/env bash
exec "$VENV/bin/python" "$APP_DIR/run.py" "\$@"
EOF
chmod +x "$BIN_DIR/$COMMAND"

# ---- 4. Icon -------
echo "==> Installing icon -> $ICON_THEME_DIR ..."
# Remove any stale SVG icon from a previous install so the PNG is used.
rm -f "$ICON_THEME_DIR/scalable/apps/$APP_ID.svg"
find "$ICON_THEME_DIR/scalable" -type d -empty -delete 2>/dev/null || true
cp -r data/icons/hicolor/* "$ICON_THEME_DIR/"
gtk-update-icon-cache -f -t "$ICON_THEME_DIR" 2>/dev/null || true

# ---- 5. Desktop entry -------
echo "==> Installing desktop entry -> $APPS_DIR/$APP_ID.desktop ..."
sed "s|@PREFIX@|$PREFIX|g" \
    "data/desktop/$APP_ID.desktop" > "$APPS_DIR/$APP_ID.desktop"
chmod +x "$APPS_DIR/$APP_ID.desktop"

# ---- 6. Refresh launchers -------
echo "==> Refreshing launcher cache..."
update-desktop-database "$APPS_DIR" 2>/dev/null || true

echo ""
echo "============================================================"
echo " Install complete."
echo "   - Run it from your app menu (search \"Universal\")."
echo "   - Or use the command:  $COMMAND"
echo " NOTE: if it's not in your menu yet, log out/in once."
echo "============================================================"
