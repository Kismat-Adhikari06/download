#!/usr/bin/env bash
set -euo pipefail

# Build a single-file Flatpak bundle (.flatpak) of the app that you can send
# to a friend. Your friend can install it with flatpak (no Python/GTK setup).

cd "$(dirname "$0")"
ROOT="$(pwd)"

APP_ID="com.undermedia.UniversalMediaDownloader"
BRANCH="stable"
BUILD_DIR="$ROOT/build-flatpak"
REPO_DIR="$ROOT/flatpak-repo"
BUNDLE="$ROOT/$APP_ID.flatpak"

command -v flatpak >/dev/null 2>&1 || { echo "ERROR: flatpak not installed."; echo "Install it: sudo apt-get install flatpak"; exit 1; }
command -v flatpak-builder >/dev/null 2>&1 || { echo "ERROR: flatpak-builder not installed."; echo "Install it: sudo apt-get install flatpak-builder"; exit 1; }

echo "==> Adding Flathub remote (for the GNOME runtime)..."
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

echo "==> Ensuring GNOME Platform/SDK runtime is installed..."
flatpak install -y flathub org.gnome.Platform//46 org.gnome.Sdk//46

echo "==> Building the app..."
flatpak-builder \
  --force-clean \
  --state-dir "$ROOT/.flatpak-builder-cache" \
  "$BUILD_DIR" \
  "$ROOT/org.undermedia.UniversalMediaDownloader.yaml"

echo "==> Exporting to local repo..."
rm -rf "$REPO_DIR"
flatpak build-export "$REPO_DIR" "$BUILD_DIR" "$BRANCH"

echo "==> Bundling single file..."
rm -f "$BUNDLE"
flatpak build-bundle "$REPO_DIR" "$BUNDLE" "$APP_ID" "$BRANCH"

echo ""
echo "============================================================"
echo " BUILT: $BUNDLE"
echo " Send this single file to your friend. They just run:"
echo ""
echo "   flatpak install --user $BUNDLE"
echo ""
echo " or double-click the .flatpak file (with Flatpak installed)."
echo " No Python / GTK / ffmpeg setup needed on their side."
echo "============================================================"
