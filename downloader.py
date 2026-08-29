"""
Universal Media Downloader

Downloads media from YouTube, Instagram, Twitter/X, Reddit, and thousands of
other platforms via yt-dlp. Supports single videos, playlists, and both video
and audio formats.

Features:
  - Single or multiple URLs (space-separated)
  - Playlist detection with automatic multi-video downloads
  - Real-time progress bar showing %, speed, and ETA
  - Fails gracefully — continues with remaining URLs on error
"""

import os
import shutil
import sys
from typing import Callable

from yt_dlp.networking.impersonate import ImpersonateTarget


# ---------------------------------------------------------------------------
# Pure helper functions (no I/O, fully testable)
# ---------------------------------------------------------------------------

def validate_url(s: str) -> bool:
    """Return True when s.strip() is non-empty, False otherwise."""
    return s.strip() != ""


def parse_urls(raw: str) -> list[str]:
    """Split a raw input string on whitespace and return non-empty stripped URLs."""
    return [u.strip() for u in raw.split() if u.strip()]


def validate_format(s: str) -> str:
    """Return 'video' or 'audio' based on input.

    Accepts:
      - '1' or 'video'  -> 'video'
      - '2' or 'audio'  -> 'audio'
    Raises ValueError for anything else.
    """
    if s in ("1", "video"):
        return "video"
    if s in ("2", "audio"):
        return "audio"
    raise ValueError(f"Invalid format {s!r}: enter 1 (video) or 2 (audio)")


def build_output_template() -> str:
    """Return the yt-dlp outtmpl string that saves files into downloads/."""
    return "downloads/%(title)s.%(ext)s"


# ---------------------------------------------------------------------------
# Progress bar & playlist detection
# ---------------------------------------------------------------------------

def _make_progress_hook() -> Callable:
    """Return a progress hook for yt-dlp that draws a single-line progress bar.

    Uses ASCII-safe characters ("=" for filled, "-" for empty) wrapped in
    brackets so it works on every terminal::

      [===========---------------] 42.3% | 3.2 MiB/s | ETA 00:07

    For playlist items, prefixes with [N/M].
    """
    last_line_len = 0

    def hook(d: dict) -> None:
        nonlocal last_line_len

        status = d.get("status")

        if status == "downloading":
            percent = d.get("_percent_str", "0%").strip()
            speed = d.get("_speed_str", "?").strip()
            eta = d.get("_eta_str", "?").strip()

            # Build classic progress bar: [=====-----]  (25 chars wide)
            bar_width = 25
            try:
                pct = float(percent.replace("%", ""))
                filled = int(bar_width * pct / 100)
            except (ValueError, AttributeError):
                filled = 0
            bar = "[" + "=" * filled + "-" * (bar_width - filled) + "]"

            # Show playlist position if applicable
            playlist_idx = d.get("playlist_index")
            playlist_count = d.get("playlist_count")
            if playlist_idx and playlist_count and playlist_count > 1:
                prefix = f"[{playlist_idx}/{playlist_count}] "
            else:
                prefix = ""

            line = f" {prefix}{bar} {percent} | {speed} | ETA {eta}"

            # Pad to previous length to avoid leftover characters
            if len(line) < last_line_len:
                line = line.ljust(last_line_len)

            sys.stdout.write("\r" + line)
            sys.stdout.flush()
            last_line_len = len(line)

        elif status in ("finished", "error"):
            # Clear progress line so the next output starts clean
            sys.stdout.write("\r" + " " * last_line_len + "\r")
            sys.stdout.flush()
            last_line_len = 0

    return hook


def _get_playlist_info(url: str) -> tuple:
    """Quickly detect if *url* is a playlist.

    Performs a lightweight extraction (no download) and returns
    ``(title, video_count)`` on success, or ``(None, None)`` if the URL
    is not a playlist or the extraction fails.
    """
    import yt_dlp

    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and info.get("_type") == "playlist":
                title = info.get("title")
                entries = info.get("entries") or []
                count = info.get("playlist_count") or len(entries)
                return title, count
    except Exception:
        pass
    return None, None


# ---------------------------------------------------------------------------
# I/O functions
# ---------------------------------------------------------------------------

def get_urls() -> list[str]:
    """Prompt the user for one or more URLs, parse them, and return a list.

    URLs can be separated by spaces. Prints an error and exits with code 1
    if no valid URLs are provided.
    """
    raw = input("Enter URL(s) (separate multiple with spaces): ")
    urls = parse_urls(raw)
    if not urls:
        print("Error: at least one URL is required.", file=sys.stderr)
        sys.exit(1)
    return urls


def get_format() -> str:
    """Prompt the user for a format choice and return 'video' or 'audio'.

    Accepts '1' or 'video' for video, '2' or 'audio' for audio.
    Prints an error and exits with code 1 on invalid input.
    """
    raw = input("Format: 1) Video  2) Audio  [1/2]: ")
    try:
        return validate_format(raw)
    except ValueError:
        print("Error: enter 1 for video or 2 for audio.", file=sys.stderr)
        sys.exit(1)


def ensure_downloads_folder() -> None:
    """Create the downloads/ folder if it does not already exist."""
    os.makedirs("downloads", exist_ok=True)


def _aria2c_available() -> bool:
    """Return True if aria2c is installed and on PATH."""
    return shutil.which("aria2c") is not None


def download(url: str, fmt: str) -> bool:
    """Download media from *url* in the requested *fmt* ('video' or 'audio').

    Shows a real-time progress bar (%, speed, ETA) during download.
    Detects playlist content automatically and displays per-video progress
    as ``[N/M] ████░░░░ 45% | 3 MiB/s | ETA 00:07``.

    If aria2c is installed it is used as the external downloader for faster
    multi-connection downloads. Catches DownloadError and returns False
    on failure.
    """
    import yt_dlp  # imported here so the module is importable without yt-dlp installed

    # Shared options for both formats
    ydl_opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [_make_progress_hook()],
    }

    try:
        ydl_opts['impersonate'] = ImpersonateTarget()
    except Exception:
        pass

    if fmt == "video":
        ydl_opts.update({
            "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "outtmpl": build_output_template(),
            "merge_output_format": "mp4",
        })
    else:  # fmt == "audio"
        ydl_opts.update({
            "format": "bestaudio/best",
            "outtmpl": build_output_template(),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })

    # Use a broader set of player clients to bypass YouTube bot detection on servers.
    ydl_opts["extractor_args"] = {
        "youtube": {
            "player_client": ["android", "mweb", "ios", "tv"],
            "skip": ["web"],
        }
    }

    # Use aria2c for faster downloads if available (splits into 16 connections)
    if _aria2c_available():
        ydl_opts["external_downloader"] = "aria2c"
        ydl_opts["external_downloader_args"] = [
            "--min-split-size=1M",
            "--max-connection-per-server=16",
            "--max-concurrent-downloads=16",
            "--split=16",
        ]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except yt_dlp.utils.DownloadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Orchestrate the download workflow.

    If one or more URLs are passed as command-line arguments they are used
    directly, skipping the interactive prompt. Otherwise, prompts the user
    interactively for URL(s) and format.

    For playlist URLs, the playlist title and video count are displayed before
    downloading begins. Each video in the playlist shows real-time progress.
    """
    if len(sys.argv) > 1:
        urls = [u.strip() for u in sys.argv[1:] if u.strip()]
        if not urls:
            print("Error: at least one URL is required.", file=sys.stderr)
            sys.exit(1)
    else:
        urls = get_urls()

    fmt = get_format()
    ensure_downloads_folder()

    total = len(urls)
    successes = 0
    failures = 0

    for i, url in enumerate(urls, start=1):
        # Check if this URL is a playlist
        playlist_title, playlist_count = _get_playlist_info(url)

        if playlist_title and playlist_count:
            label = f'{playlist_title!r} ({playlist_count} video{"s" if playlist_count != 1 else ""})'
            print(f"\n[{i}/{total}] Playlist: {label}")
        else:
            print(f"\n[{i}/{total}] Downloading: {url}")

        if download(url, fmt):
            successes += 1
        else:
            failures += 1

    if failures:
        print(f"\nDone! {successes} succeeded, {failures} failed.")
        sys.exit(1)
    else:
        print(f"\nAll done! {successes} file(s) saved to the downloads/ folder.")


if __name__ == "__main__":
    main()
