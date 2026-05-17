"""
downloader_core.py — headless download logic for the web backend.

Reuses helpers from the project-root downloader.py without calling sys.exit().
"""

import json
import logging
import os
import sys
from pathlib import Path

# Set up a logger for this module
logger = logging.getLogger(__name__)

# Add the project root (two levels up from this file) to sys.path so that
# downloader.py can be imported regardless of the working directory.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from downloader import validate_format, _aria2c_available  # noqa: E402


_netscp_path: str | None = None  # cache the converted cookie path


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

    # 1. Check COOKIES_FILE env var (set on Render dashboard)
    env_path = os.environ.get("COOKIES_FILE") or ""
    if env_path and os.path.exists(env_path):
        if env_path.endswith(".json"):
            _netscp_path = _json_to_netscape(env_path)
            return _netscp_path
        _netscp_path = env_path
        return env_path

    # 2. Look for cookies.txt next to this file
    local_path = os.path.join(os.path.dirname(__file__), "cookies.txt")
    if os.path.exists(local_path):
        _netscp_path = local_path
        return local_path

    # 3. Look for ytcookies.json next to this file (for backward compat)
    json_fallback = os.path.join(os.path.dirname(__file__), "ytcookies.json")
    if os.path.exists(json_fallback):
        _netscp_path = _json_to_netscape(json_fallback)
        return _netscp_path

    logger.warning("No cookies file found. YouTube may require sign-in on datacenter IPs.")
    return None


def _get_ytdlp_version() -> str:
    """Return the installed yt-dlp version string."""
    try:
        import yt_dlp
        return yt_dlp.version.__version__
    except Exception:
        return "unknown"


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
            "format": "best",
            "outtmpl": outtmpl,
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

    # Try to bypass YouTube bot detection by using mobile/TV player clients.
    # The default "web" client is most aggressively blocked on datacenter IPs.
    ydl_opts["extractor_args"] = {
        "youtube": {
            "player_client": ["android", "mweb", "ios", "tv"],
        }
    }

    # Use a mobile User-Agent to further avoid bot detection
    ydl_opts["user_agent"] = (
        "Mozilla/5.0 (Linux; Android 14; Pixel 7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.6099.144 Mobile Safari/537.36"
    )

    # Use cookies file to bypass YouTube's "Sign in to confirm" prompt.
    # The file must be in Netscape format (NOT JSON).
    # Set via COOKIES_FILE env var, or looks for cookies.txt in the backend dir.
    cookies_path = _get_cookies_path()
    if cookies_path:
        ydl_opts["cookiefile"] = cookies_path
        logger.info(f"Using cookies: {cookies_path}")

    # Enable verbose logging so we can see what yt-dlp is actually doing
    ydl_opts["verbose"] = True
    ydl_opts["logger"] = logger

    # Use aria2c for faster downloads if available
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

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])  # raises DownloadError on failure
    except yt_dlp.utils.DownloadError as exc:
        # Wrap the error with extra debug info
        debug_info = (
            f"\n[DEBUG] yt-dlp version: {_get_ytdlp_version()}"
            f"\n[DEBUG] URL: {url}"
            f"\n[DEBUG] Format: {fmt}"
            f"\n[DEBUG] extrator_args: {ydl_opts.get('extractor_args', {})}"
            f"\n[DEBUG] user_agent set: {'user_agent' in ydl_opts}"
            f"\n[DEBUG] aria2c available: {_aria2c_available()}"
        )
        raise yt_dlp.utils.DownloadError(str(exc) + debug_info)

    # Prefer the path captured by the progress hook; fall back to scanning the dir.
    if downloaded_path:
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
