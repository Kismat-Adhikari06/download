"""
Core download engine for the GTK app.

Wraps yt-dlp with the same behaviour as downloader.py but exposes progress
and status through callbacks so the GUI can observe downloads running in a
background thread.
"""

import io
import os
import shutil
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# Pure helper functions (mirrors downloader.py)
# ---------------------------------------------------------------------------

def validate_url(s: str) -> bool:
    """Return True when s.strip() is non-empty, False otherwise."""
    return s.strip() != ""


def parse_urls(raw: str) -> list[str]:
    """Split a raw input string on whitespace and return non-empty stripped URLs."""
    return [u.strip() for u in raw.split() if u.strip()]


def validate_format(s: str) -> str:
    """Return 'video' or 'audio' based on input.

    Accepts '1'/'video' -> 'video' and '2'/'audio' -> 'audio'.
    Raises ValueError for anything else.
    """
    if s in ("1", "video"):
        return "video"
    if s in ("2", "audio"):
        return "audio"
    raise ValueError(f"Invalid format {s!r}: enter 1 (video) or 2 (audio)")


def build_output_template(output_dir: str) -> str:
    """Return the yt-dlp outtmpl string that saves files into output_dir."""
    return os.path.join(output_dir, "%(title)s.%(ext)s")


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _aria2c_available() -> bool:
    """Return True if aria2c is installed and on PATH."""
    return shutil.which("aria2c") is not None


def _cookies_tuple(browser: str) -> tuple:
    """Return a yt-dlp cookiesfrombrowser tuple, handling Snap installs.

    For Brave (and other Chromium-based browsers) installed via Snap,
    the cookies live under ~/snap/... instead of ~/.config. If the
    default location is missing but a Snap location exists, return the
    full profile path so yt-dlp can find the Cookies database — matching
    what `yt-dlp --cookies-from-browser brave:\"/snap/.../Default\"` does.
    """
    import glob

    b = browser.lower()
    # Firefox uses a different storage; no Snap fix needed.
    if b == "firefox":
        return (b, None, None, None)

    config_map = {
        "brave": "BraveSoftware/Brave-Browser",
        "chrome": "google-chrome",
        "chromium": "chromium",
        "edge": "microsoft-edge",
        "opera": "opera",
        "vivaldi": "vivaldi",
    }
    snap_map = {
        "brave": "brave",
        "chrome": "chromium",
        "chromium": "chromium",
        "edge": "microsoft-edge",
    }

    cfg = config_map.get(b)
    if not cfg:
        return (b, None, None, None)

    # If default Cookies exists, the simple tuple works (e.g. apt install).
    default_cookies = os.path.expanduser(f"~/.config/{cfg}/Default/Cookies")
    if os.path.exists(default_cookies):
        return (b, None, None, None)

    # Try Snap locations.
    snap_name = snap_map.get(b, b)
    candidates = [
        os.path.expanduser(f"~/snap/{snap_name}/current/.config/{cfg}/Default"),
        os.path.expanduser(f"~/snap/{snap_name}/common/.config/{cfg}/Default"),
    ]
    candidates += glob.glob(os.path.expanduser(f"~/snap/{snap_name}/*/.config/{cfg}/Default"))

    for cand in candidates:
        if os.path.exists(os.path.join(cand, "Cookies")):
            return (b, cand, None, None)

    # No Cookies found anywhere — return default tuple so yt-dlp gives
    # a clear "could not find ... Cookies database" error.
    return (b, None, None, None)


# ---------------------------------------------------------------------------
# Download engine
# ---------------------------------------------------------------------------

def _make_progress_hook(on_progress: Callable[[dict], None]) -> Callable:
    """Return a yt-dlp progress hook that forwards status dicts to on_progress."""

    def hook(d: dict) -> None:
        on_progress(d)

    return hook


def get_playlist_info(url: str) -> tuple:
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


def download(
    url: str,
    fmt: str,
    output_dir: str = "downloads",
    on_progress: Optional[Callable[[dict], None]] = None,
    cookies_browser: Optional[str] = None,
) -> tuple:
    """Download media from *url* in the requested *fmt*.

    Supported *fmt* values:
      - 'video'          -> MP4 (up to 1080p)
      - 'audio'          -> MP3 (192 kbps)
      - 'image_jpg'      -> video thumbnail saved as JPG
      - 'image_png'      -> video thumbnail saved as PNG

    Saves files into *output_dir*. *on_progress* is called with the yt-dlp
    progress status dict (status, filename, downloaded_bytes, total_bytes,
    _percent_str, _speed_str, _eta_str, playlist_index, playlist_count...).

    Returns ``(path, error)``: path is the absolute path of the downloaded
    file on success (or None), error is a string message on failure (or None).
    """
    import yt_dlp  # imported here so the module is importable without yt-dlp installed

    os.makedirs(output_dir, exist_ok=True)

    is_image = fmt in ("image_jpg", "image_png")
    if is_image:
        img_fmt = "png" if fmt == "image_png" else "jpg"
        return _download_image(url, img_fmt, output_dir, cookies_browser)

    hooks: list = []
    if on_progress:
        hooks.append(_make_progress_hook(on_progress))

    ydl_opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": hooks,
        "restrictfilenames": False,
    }

    if fmt == "video":
        ydl_opts.update({
            "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "outtmpl": build_output_template(output_dir),
            "merge_output_format": "mp4",
        })
    else:  # fmt == "audio"
        ydl_opts.update({
            "format": "bestaudio/best",
            "outtmpl": build_output_template(output_dir),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })

    # Use a broader set of player clients to bypass YouTube bot detection.
    ydl_opts["extractor_args"] = {
        "youtube": {
            "player_client": ["android", "mweb", "ios", "tv"],
            "skip": ["web"],
        }
    }

    if cookies_browser:
        ydl_opts["cookiesfrombrowser"] = _cookies_tuple(cookies_browser)

    # PornHub (and similar) is blocked via TLS fingerprinting — cookies alone
    # aren't enough. yt-dlp may auto-select an unavailable target like
    # chrome150; use ImpersonateTarget() so it auto-picks any available target.
    if any(d in url.lower() for d in ["pornhub.com", "pornhub"]):
        try:
            from yt_dlp.networking.impersonate import ImpersonateTarget

            ydl_opts["impersonate"] = ImpersonateTarget()
        except Exception:
            pass

    # Use aria2c for faster downloads if available.
    if _aria2c_available():
        ydl_opts["external_downloader"] = "aria2c"
        ydl_opts["external_downloader_args"] = [
            "--min-split-size=1M",
            "--max-connection-per-server=16",
            "--max-concurrent-downloads=16",
            "--split=16",
        ]

    downloaded_paths: list[str] = []

    def _finished_hook(d: dict) -> None:
        if d.get("status") == "finished":
            mp = d.get("info_dict", {}).get("_filename") or d.get("filename")
            if mp and os.path.exists(mp):
                downloaded_paths.append(mp)

    if on_progress:
        # wrap so we also capture the finished path
        inner = on_progress

        def combined(d: dict) -> None:
            _finished_hook(d)
            inner(d)

        ydl_opts["progress_hooks"] = [combined]
    else:
        ydl_opts["progress_hooks"] = [_make_progress_hook(_finished_hook)]

    error: Optional[str] = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as exc:  # noqa: BLE001  — cookies errors may not be DownloadError
        raw = str(exc)
        low = raw.lower()
        # Browser/cookies didn't work — tell user to try the right browser.
        if cookies_browser and any(k in low for k in ["cookies", "cookie", "browser", "keyring", "decrypt"]):
            raw += f" — could not load cookies from {cookies_browser}. Make sure you're logged into that site in {cookies_browser}, or try a different browser (e.g. Firefox where you're logged in) or 'None'."
        elif "No video could be found" in raw:
            if any(d in url for d in ["twitter.com", "x.com"]):
                if cookies_browser:
                    raw += f" — even with {cookies_browser} cookies, X still blocked it. Make sure you're logged into X in {cookies_browser}, or try a different browser where you're logged in."
                else:
                    raw += " — X is blocking this video. Try picking the browser where you're logged into X (e.g. Firefox) in the Cookies dropdown, or use Image (JPG/PNG) for its thumbnail."
            else:
                raw += " — this post has no video. Try Image (JPG/PNG) to download its thumbnail."
        error = raw

    if error:
        # Download failed — don't return a stale file from a previous run.
        return (None, error)

    if downloaded_paths and os.path.exists(downloaded_paths[0]):
        return (downloaded_paths[0], None)

    # Fallback: yt-dlp may have merged files (e.g. Twitter m3u8) and the hook
    # didn't capture the final path. Scan the output dir for the newest file.
    fallback = _find_latest_file(output_dir)
    if fallback:
        # Only return it if it was created *during* this download (within last 10s),
        # otherwise it's a leftover from a previous run.
        try:
            if (os.path.getmtime(fallback) + 10) >= __import__("time").time():
                return (fallback, None)
        except OSError:
            pass
    return (None, error)


def _find_latest_file(directory: str) -> Optional[str]:
    """Return the most recently created file in *directory*, or None."""
    if not os.path.isdir(directory):
        return None
    candidates = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def _download_image(url: str, img_fmt: str, output_dir: str, cookies_browser: Optional[str] = None) -> tuple:
    """Download images for *url* and save as JPG or PNG.

    For YouTube and most sites: grabs the highest-resolution thumbnail.
    For Twitter/X: uses the syndication API to get tweet photos.

    Returns ``(path, error)``.
    """
    import urllib.request

    from PIL import Image

    is_twitter = any(d in url for d in ["twitter.com", "x.com"])

    if is_twitter:
        return _download_twitter_image(url, img_fmt, output_dir)

    # Non-Twitter: extract thumbnail via yt-dlp
    import yt_dlp  # noqa: F401

    try:
        ydl_thumb_opts: dict = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "ignore_no_formats_error": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "mweb", "ios", "tv"],
                    "skip": ["web"],
                }
            },
        }
        if cookies_browser:
            ydl_thumb_opts["cookiesfrombrowser"] = _cookies_tuple(cookies_browser)
        info = yt_dlp.YoutubeDL(ydl_thumb_opts).extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        return (None, f"Could not get media info: {exc}")

    # Choose the best (highest preference) thumbnail URL.
    thumb_url = None
    thumbnails = (info or {}).get("thumbnails") or []
    if thumbnails:
        best = max(thumbnails, key=lambda t: (t.get("preference") or 0, t.get("height") or 0, t.get("width") or 0))
        thumb_url = best.get("url")
    if not thumb_url:
        thumb_url = (info or {}).get("thumbnail")
    if not thumb_url:
        return (None, "No thumbnail found for this media.")

    title = (info or {}).get("title") or "thumbnail"
    safe_title = "".join(c for c in title if c not in '/\\:*?"<>|').strip() or "thumbnail"
    out_path = os.path.join(output_dir, f"{safe_title}.{img_fmt}")

    try:
        with urllib.request.urlopen(thumb_url, timeout=30) as resp:
            data = resp.read()
    except Exception as exc:  # noqa: BLE001
        return (None, f"Could not download thumbnail: {exc}")

    return _save_image(data, out_path, img_fmt)


def _download_twitter_image(url: str, img_fmt: str, output_dir: str) -> tuple:
    """Download tweet photos by scraping the X/Twitter status page.

    Falls back to the syndication API if the page scrape finds nothing.

    Returns ``(path, error)``.
    """
    import html as html_lib
    import json
    import re
    import urllib.request

    m = re.search(r"/status/(\d+)", url)
    if not m:
        return (None, "Could not find a tweet ID in this URL.")
    tweet_id = m.group(1)

    # Primary: scrape https://x.com/i/web/status/<id> for pbs.twimg.com/media URLs.
    photo_urls: list[str] = []
    try:
        req = urllib.request.Request(
            f"https://x.com/i/web/status/{tweet_id}",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            page = resp.read().decode("utf-8", errors="ignore")

        raw = re.findall(r"https://pbs\.twimg\.com/media/[^\"]+", page)
        # Normalise (&amp; -> &) and de-duplicate, keep only the media ID part.
        seen: set[str] = set()
        for u in raw:
            u = html_lib.unescape(u)
            # Strip size params, keep base so we can request full res.
            base = u.split("?")[0]
            if base in seen:
                continue
            seen.add(base)
            # Request full-resolution image.
            photo_urls.append(base + "?format=jpg&name=orig")
    except Exception:  # noqa: BLE001
        pass

    # Fallback: syndication API.
    if not photo_urls:
        try:
            api_url = f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&token=x"
            req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            typename = data.get("__typename", "")
            if typename == "TweetTombstone":
                # Syndication says Tombstone, but the live page had content.
                # Only treat as deleted if we also found nothing via scraping.
                return (None, "This tweet appears to be deleted or unavailable.")
            if typename not in ("Tweet", ""):
                pass  # don't hard-fail — fall through to no-photos case below

            photos = data.get("photos") or []
            if not photos:
                media = data.get("mediaDetails") or []
                photos = [m for m in media if m.get("type") == "photo"]

            for photo in photos:
                u = photo.get("url") or photo.get("media_url_https") or ""
                if not u:
                    continue
                if "?" not in u:
                    u += "?format=jpg&name=orig"
                if u not in photo_urls:
                    photo_urls.append(u)
        except Exception:  # noqa: BLE001
            pass

    if not photo_urls:
        return (None, "No images found in this tweet. It may have no photos, or X is blocking the request.")

    tweet_title = f"tweet_{tweet_id}"
    saved: list[str] = []
    for i, photo_url in enumerate(photo_urls):
        fname = f"{tweet_title}_{i+1}.{img_fmt}"
        out_path = os.path.join(output_dir, fname)

        try:
            req = urllib.request.Request(photo_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                img_data = resp.read()
        except Exception:  # noqa: BLE001
            continue

        result, _err = _save_image(img_data, out_path, img_fmt)
        if result:
            saved.append(result)

    if not saved:
        return (None, "Found tweet images but could not download any of them.")

    return (saved[0], None)


def _save_image(data: bytes, out_path: str, img_fmt: str) -> tuple:
    """Convert raw image bytes to JPG/PNG and save.

    Returns ``(path, error)``.
    """
    from PIL import Image

    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        if img_fmt == "jpg":
            img.save(out_path, "JPEG", quality=92)
        else:
            img.save(out_path, "PNG")
    except Exception as exc:  # noqa: BLE001
        return (None, f"Could not convert image: {exc}")

    return (out_path, None)
