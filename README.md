# Universal Media Downloader — GTK Desktop App

A lightweight, local Linux desktop app (GTK4 + libadwaita, Python/PyGObject)
that wraps the same yt-dlp core engine as the CLI. Download video (MP4) or
audio (MP3) from YouTube and thousands of other sites, with a clean native UI.

## Requirements

- Linux with **GTK4** and **libadwaita**
- Python 3.10+
- Optional: `ffmpeg` (required for MP3 audio), `aria2` (faster downloads)

## Setup & Run (recommended)

Creates a venv (reusing your system GTK4/libadwaita/PyGObject via
`--system-site-packages`, so nothing is installed system-wide) and installs
yt-dlp into it:

```bash
./setup.sh
./run.sh
```

- `setup.sh` — create the `.venv` and install deps (run once / after pulls).
- `run.sh` — launch the app with the venv Python.

If your distro uses PEP 668 ("externally-managed-environment"), this is the
correct approach — it avoids touching system packages entirely.

## Install as a real desktop app (with icon)

Registers the app in your launcher with an icon and a
`universal-media-downloader` command on your PATH (installs to `~/.local`,
no sudo needed):

```bash
./install-app.sh
```

Then find "Universal Media Downloader" in your app menu, or run:

```bash
universal-media-downloader
```

Re-run `install-app.sh` after any code change to update the installed copy.

## Share with a friend (no setup on their end) — Flatpak

The cleanest way to give the app to a friend with **zero manual setup** is a
single-file Flatpak bundle. It wraps the GUI libraries, Python, and yt-dlp
inside one package, so your friend only needs Flatpak (not Python/GTK/ffmpeg).

### Build the bundle (you)
```bash
# one-time: install Flatpak tooling (or check if you have it)
sudo apt-get install flatpak flatpak-builder

./build-flatpak.sh
```
This produces a single file: **`com.undermedia.UniversalMediaDownloader.flatpak`**

### Install it (your friend)
Send them that one file. They just run:
```bash
sudo apt-get install flatpak
flatpak install --user com.undermedia.UniversalMediaDownloader.flatpak
```
or double-click the `.flatpak` file with Flatpak installed. It appears in their
app menu as "Universal Media Downloader". No Python, GTK, or ffmpeg setup.

### Or share via GitHub
Point them at the repo and have them run:
```bash
git clone https://github.com/Kismat-Adhikari06/download.git
cd download
./install-app.sh
```
The script auto-installs system deps (GTK4, libadwaita, ffmpeg, aria2) via
apt when missing.

## Run without a venv

Only if GTK4/libadwaita/PyGObject and yt-dlp are already in your Python:

## Usage

1. Paste a URL (video or playlist).
2. Pick a format: **Video (MP4)** or **Audio (MP3)**.
3. Choose the destination folder (defaults to `~/Downloads`).
4. Click **Download** — progress, speed, and ETA are shown live.

## Notes

- Uses the same yt-dlp config as the CLI: 1080p max video merged to MP4,
  MP3 at 192 kbps for audio, YouTube bot-bypass player clients, and aria2c
  multi-connection acceleration when available.
- Downloads run in a background thread so the UI stays responsive.
