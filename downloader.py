"""
Universal Media Downloader

A single-file Python script that interactively prompts the user for a URL
and a format choice (video or audio), then downloads the media to a local
`downloads/` folder using yt-dlp.

Supports YouTube, Instagram, Twitter/X, Reddit, and thousands of other
platforms via yt-dlp's extraction engine.
"""

import os
import shutil
import sys


# ---------------------------------------------------------------------------
# Pure helper functions (no I/O, fully testable)
# ---------------------------------------------------------------------------

def validate_url(s: str) -> bool:
    """Return True when s.strip() is non-empty, False otherwise."""
    return s.strip() != ""


def validate_format(s: str) -> str:
    """Return 'video' or 'audio' when s matches exactly; raise ValueError otherwise.

    The check is case-sensitive: 'Video' and 'AUDIO' are rejected.
    """
    if s == "video":
        return "video"
    if s == "audio":
        return "audio"
    raise ValueError(f"Invalid format {s!r}: must be 'video' or 'audio'")


def build_output_template() -> str:
    """Return the yt-dlp outtmpl string that saves files into downloads/."""
    return "downloads/%(title)s.%(ext)s"


# ---------------------------------------------------------------------------
# I/O functions
# ---------------------------------------------------------------------------

def get_url() -> str:
    """Prompt the user for a URL, validate it, and return the stripped string.

    Prints an error to stderr and exits with code 1 if the input is empty
    or whitespace-only.
    """
    raw = input("Enter URL: ")
    if not validate_url(raw):
        print("Error: URL cannot be empty.", file=sys.stderr)
        sys.exit(1)
    return raw.strip()


def get_format() -> str:
    """Prompt the user for a format choice and return 'video' or 'audio'.

    Prints an error to stderr and exits with code 1 if the input is not
    exactly 'video' or 'audio'.
    """
    raw = input("Video or audio? [video/audio]: ")
    try:
        return validate_format(raw)
    except ValueError:
        print("Error: Please enter 'video' or 'audio'.", file=sys.stderr)
        sys.exit(1)


def ensure_downloads_folder() -> None:
    """Create the downloads/ folder if it does not already exist."""
    os.makedirs("downloads", exist_ok=True)


def _aria2c_available() -> bool:
    """Return True if aria2c is installed and on PATH."""
    return shutil.which("aria2c") is not None


def download(url: str, fmt: str) -> None:
    """Download media from *url* in the requested *fmt* ('video' or 'audio').

    Uses yt-dlp with format-appropriate options. If aria2c is installed,
    it is used as the external downloader for faster multi-connection downloads.
    Catches DownloadError, prints the message to stderr, and exits with code 1
    on failure. Prints a success message on completion.
    """
    import yt_dlp  # imported here so the module is importable without yt-dlp installed

    if fmt == "video":
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": build_output_template(),
            "merge_output_format": "mp4",
        }
    else:  # fmt == "audio"
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": build_output_template(),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
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
    except yt_dlp.utils.DownloadError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    print("Download complete! Check the downloads/ folder.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Orchestrate the interactive download workflow.

    If a URL is passed as a command-line argument it is used directly,
    skipping the interactive prompt.
    """
    # Accept an optional URL argument: python downloader.py <url>
    if len(sys.argv) > 1:
        url = sys.argv[1].strip()
        if not validate_url(url):
            print("Error: URL cannot be empty.", file=sys.stderr)
            sys.exit(1)
    else:
        url = get_url()

    fmt = get_format()
    ensure_downloads_folder()
    download(url, fmt)


if __name__ == "__main__":
    main()
