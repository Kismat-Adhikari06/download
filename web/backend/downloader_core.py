"""
downloader_core.py — headless download logic for the web backend.

Reuses helpers from the project-root downloader.py without calling sys.exit().
"""import json
import os
import sys
from pathlib import Path

# Add the project root (two levels up from this file) to sys.path so that
# downloader.py can be imported regardless of the working directory.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from downloader import validate_format, _aria2c_available  # noqa: E402


_netscp_path: str | None = None  # cache the converted path


def _json_to_netscape(json_path: str) -> str:
    """Convert a JSON cookies file to Netscape format and return the new path.

    yt-dlp requires the legacy Netscape cookie format, not JSON.
    """
    with open(json_path, "r") as f:
        cookies = json.load(f)

    lines = [
        "# Netscape HTTP Cookie File",
        "# https://curl.se/docs/http-cookies.html",
        "# This file was auto-converted from JSON by the downloader",
    ]

    for c in cookies:
        domain = c.get("domain", "")
        # hostOnly: if True the cookie was set for a specific host;
        # in Netscape format the leading "." indicates subdomain match.
        host_only = c.get("hostOnly", False)
        flag = "FALSE" if host_only else "TRUE"
        path = c.get("path", "/")
        secure = "TRUE" if c.get("secure", False) else "FALSE"
        expiry = int(c.get("expirationDate", 0))
        name = c.get("name", "")
        value = c.get("value", "")
        lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}")

    out_path = json_path + ".txt"
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    return out_path


def _get_cookies_path() -> str | None:
    """Return path to a Netscape-format cookies file, or None."""
    global _netscp_path
    if _netscp_path:
        return _netscp_path

    path = os.environ.get("COOKIES_FILE") or ""
    if path and os.path.exists(path):
        # If it's a .json file, convert to Netscape format
        if path.endswith(".json"):
            _netscp_path = _json_to_netscape(path)
            return _netscp_path
        _netscp_path = path
        return path

    # Fallback: look for ytcookies.json in the current directory
    fallback = os.path.join(os.getcwd(), "ytcookies.json")
    if os.path.exists(fallback):
        _netscp_path = _json_to_netscape(fallback)
        return _netscp_path

    return None


def download_to_path(url: str, fmt: str, output_dir: str) -> str:
    """Download media from *url* in format *fmt* into *output_dir*.

    Parameters
    ----------
    url:        Media URL (any yt-dlp-supported platform).
    fmt:        ``'video'`` or ``'audio'``.
    output_dir: Absolute path to the directory where the file will be saved.

    Returns
    -------
    str
        Absolute path of the downloaded file.

    Raises
    ------
    yt_dlp.utils.DownloadError
        If yt-dlp fails to download the media.  Does NOT call sys.exit().
    ValueError
        If *fmt* is not ``'video'`` or ``'audio'``.
    """
    import yt_dlp  # deferred so the module is importable without yt-dlp installed

    validate_format(fmt)  # raises ValueError for invalid format

    outtmpl = os.path.join(output_dir, "%(title)s.%(ext)s")

    if fmt == "video":
        ydl_opts: dict = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": outtmpl,
            "merge_output_format": "mp4",
        }
    else:  # fmt == "audio"
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

    # Use cookies file if available (for YouTube authentication)
    cookies_path = _get_cookies_path()
    if cookies_path:
        ydl_opts["cookiefile"] = cookies_path

    if _aria2c_available():
        ydl_opts["external_downloader"] = "aria2c"
        ydl_opts["external_downloader_args"] = [
            "--min-split-size=1M",
            "--max-connection-per-server=16",
            "--max-concurrent-downloads=16",
            "--split=16",
        ]

    # Collect the actual output path via the progress hook
    downloaded_path: list[str] = []

    def _progress_hook(d: dict) -> None:
        if d.get("status") == "finished":
            downloaded_path.append(d["filename"])

    ydl_opts["progress_hooks"] = [_progress_hook]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])  # raises DownloadError on failure

    # Prefer the path captured by the progress hook; fall back to scanning the dir.
    if downloaded_path:
        # For audio, yt-dlp reports the pre-conversion filename; find the .mp3
        candidate = downloaded_path[-1]
        if fmt == "audio":
            mp3_path = Path(candidate).with_suffix(".mp3")
            if mp3_path.exists():
                return str(mp3_path.resolve())
        abs_path = Path(candidate).resolve()
        if abs_path.exists():
            return str(abs_path)

    # Fallback: return the first file found in output_dir
    files = list(Path(output_dir).iterdir())
    if files:
        return str(files[0].resolve())

    raise yt_dlp.utils.DownloadError("Download completed but output file not found")
