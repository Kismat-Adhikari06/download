"""
GTK4 + libadwaita window for the Universal Media Downloader.
"""

import os
import threading
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango  # noqa: E402

from . import core  # noqa: E402


class DownloaderWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app)
        self.set_title("Universal Media Downloader")
        self.set_default_size(560, 480)

        self._download_dir = _load_saved_dir()
        self._running = False

        self._build_content()

    # ------------------------------------------------------------------ UI

    def _build_content(self) -> None:
        self.toolbar = Adw.ToolbarView()
        self.set_content(self.toolbar)

        header = Adw.HeaderBar()
        self.toolbar.add_top_bar(header)

        self._prefs_button = Gtk.Button(icon_name="open-menu-symbolic")
        self._prefs_button.set_tooltip_text("Preferences")
        self._prefs_button.connect("clicked", self._on_prefs_clicked)
        header.pack_end(self._prefs_button)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)
        content.set_vexpand(True)
        self.toolbar.set_content(content)

        # Status / progress
        self._status_label = Gtk.Label(label="Paste a URL to get started.")
        self._status_label.set_xalign(0)
        self._status_label.set_wrap(True)
        self._status_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._status_label.set_max_width_chars(48)
        if hasattr(Gtk, "NaturalWrapMode"):
            try:
                self._status_label.set_natural_wrap_mode(Gtk.NaturalWrapMode.WORD)
            except Exception:
                pass
        self._status_label.set_justify(Gtk.Justification.LEFT)
        self._status_label.set_hexpand(True)
        self._status_label.set_halign(Gtk.Align.FILL)
        self._status_label.add_css_class("dim-label")
        content.append(self._status_label)

        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_show_text(True)
        self._progress_bar.set_fraction(0.0)
        content.append(self._progress_bar)

        # URL input
        url_group = Adw.PreferencesGroup(title="URL")
        self._url_row = self._make_url_row()
        url_group.add(self._url_row)
        content.append(url_group)

        # Format selector
        format_group = Adw.PreferencesGroup(title="Format")
        self._format_row = Adw.ComboRow(title="Output format")
        self._format_row.set_model(Gtk.StringList.new(
            ["Video (MP4)", "Audio (MP3)", "Image (JPG)", "Image (PNG)"]
        ))
        self._format_row.set_selected(0)
        format_group.add(self._format_row)
        content.append(format_group)

        # Browser cookies for sites that need login (e.g. X videos)
        # Only show browsers that are actually installed on this device.
        self._browser_choices = _detect_browsers()
        cookie_group = Adw.PreferencesGroup(title="Cookies (for X/Twitter etc.)")
        self._cookie_row = Adw.ComboRow(title="Use browser cookies")
        self._cookie_row.set_subtitle("Helps with private/age-restricted posts")
        self._cookie_row.set_model(Gtk.StringList.new([label for label, _ in self._browser_choices]))
        self._cookie_row.set_selected(0)
        cookie_group.add(self._cookie_row)
        content.append(cookie_group)

        # Folder destination
        output_group = Adw.PreferencesGroup(title="Destination")
        self._output_row = Adw.ActionRow(title="Save to folder")
        self._output_row.set_subtitle(self._download_dir)
        self._folder_button = Gtk.Button(label="Browse", valign=Gtk.Align.CENTER)
        self._folder_button.connect("clicked", self._on_browse_clicked)
        self._output_row.add_suffix(self._folder_button)
        output_group.add(self._output_row)
        content.append(output_group)

        # Download button
        self._download_btn = Gtk.Button(label="Download")
        self._download_btn.add_css_class("suggested-action")
        self._download_btn.add_css_class("pill")
        self._download_btn.set_size_request(-1, 44)
        self._download_btn.connect("clicked", self._on_download_clicked)
        content.append(self._download_btn)

    def _make_url_row(self) -> Adw.EntryRow:
        row = Adw.EntryRow()
        row.set_title("Media URL")
        row.set_text("")
        row.connect("activate", self._on_download_clicked)
        row.connect("changed", self._on_url_changed)
        self._url_row = row
        return row

    # ------------------------------------------------------------- events

    def _on_prefs_clicked(self, _btn) -> None:
        dialog = Adw.AboutDialog()
        app: Adw.Application = self.get_application()
        if app is not None:
            dialog.set_application_name(app.get_name())
        dialog.set_version("1.0.0")
        dialog.set_comments("Lightweight media downloader powered by yt-dlp.")
        dialog.set_developer_name("Universal Media Downloader")
        dialog.set_license_type(Gtk.License.MIT_X11)
        dialog.set_website("https://github.com/Kismat-Adhikari06/download")
        dialog.present(self)

    def _on_browse_clicked(self, _btn) -> None:
        chooser = Gtk.FileDialog()
        chooser.set_initial_folder(Gio.File.new_for_path(self._download_dir))
        chooser.select_folder(self, None, self._on_folder_selected)

    def _on_folder_selected(self, dialog, result) -> None:
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error:
            return
        self._download_dir = folder.get_path()
        self._output_row.set_subtitle(self._download_dir)
        _save_dir(self._download_dir)

    def _on_url_changed(self, *_row) -> None:
        # Revert the button to a usable "Download" state once the user edits
        # the URL (e.g. after a completed download set it to "Complete").
        if not self._running and self._download_btn.get_label() != "Download":
            self._download_btn.set_label("Download")
            self._download_btn.set_sensitive(True)

    def _on_download_clicked(self, *_) -> None:
        if self._running:
            return

        url = self._url_row.get_text().strip()
        if not url:
            self._show_error("Please enter a media URL.")
            return

        fmt = FORMATS[self._format_row.get_selected()]
        cookies_browser = self._browser_choices[self._cookie_row.get_selected()][1]
        self._start_download(url, fmt, cookies_browser)

    # --------------------------------------------------------- download

    def _start_download(self, url: str, fmt: str, cookies_browser: Optional[str] = None) -> None:
        self._running = True
        self._download_btn.set_sensitive(False)
        self._download_btn.set_label("Downloading…")
        self._progress_bar.set_fraction(0.0)
        self._progress_bar.set_text("Preparing…")
        self._status_label.set_text("Preparing download…")
        self._status_label.remove_css_class("error")
        self._status_label.remove_css_class("success")
        self._status_label.add_css_class("dim-label")

        thread = threading.Thread(
            target=self._download_worker,
            args=(url, fmt, self._download_dir, cookies_browser),
            daemon=True,
        )
        thread.start()

    def _download_worker(self, url: str, fmt: str, out_dir: str, cookies_browser: Optional[str] = None) -> None:
        label = _fmt_name(fmt)

        def on_progress(d: dict) -> None:
            self._queue_progress(d, label)

        local_dir = os.path.abspath(out_dir)
        path, error = core.download(
            url, fmt, output_dir=local_dir, on_progress=on_progress,
            cookies_browser=cookies_browser,
        )

        if path and os.path.exists(path):
            GLib.idle_add(self._on_success, path)
        else:
            GLib.idle_add(self._on_fail, error)

    def _queue_progress(self, d: dict, label: str) -> None:
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            fraction = (done / total) if total else 0.0
            pct = d.get("_percent_str", "").strip()
            speed = d.get("_speed_str", "").strip()
            eta = d.get("_eta_str", "").strip()
            text = f"{label} · {pct}"
            if speed:
                text += f" · {speed}"
            if eta:
                text += f" · ETA {eta}"
            GLib.idle_add(self._update_progress, max(0.0, min(fraction, 1.0)), text)
        elif status == "finished":
            GLib.idle_add(self._update_progress, 1.0, f"{label} · Done — processing…")
        elif status == "error":
            GLib.idle_add(self._status_label.set_text, "Download failed.")
            GLib.idle_add(self._mark_error)

    def _update_progress(self, fraction: float, text: str) -> None:
        self._progress_bar.set_fraction(fraction)
        self._progress_bar.set_text(text)
        self._status_label.set_text("Downloading…")

    def _reset_ui(self) -> None:
        self._running = False
        self._download_btn.set_sensitive(True)
        self._download_btn.set_label("Download")

    def _on_success(self, path: str) -> None:
        self._running = False
        self._download_btn.set_label("Complete")
        self._download_btn.set_sensitive(False)
        self._progress_bar.set_fraction(1.0)
        self._progress_bar.set_text("Complete")
        self._status_label.set_markup(
            f'<b>Saved:</b> <a href="{GLib.markup_escape_text("file://" + path, -1)}">'
            f"{GLib.markup_escape_text(os.path.basename(path), -1)}</a>"
        )
        self._style_status("success")

    def _on_fail(self, error: Optional[str] = None) -> None:
        self._reset_ui()
        self._progress_bar.set_fraction(0.0)
        msg = "Download failed."
        if error:
            msg = f"Download failed: {error[:300]}"
        self._show_error(msg)

    def _mark_error(self) -> None:
        self._style_status("error")

    def _style_status(self, kind: str) -> None:
        self._status_label.remove_css_class("dim-label")
        self._status_label.remove_css_class("error")
        self._status_label.remove_css_class("success")
        self._status_label.add_css_class(kind)

    def _show_error(self, message: str) -> None:
        self._status_label.set_text(message)
        self._style_status("error")


FORMATS = ["video", "audio", "image_jpg", "image_png"]


def _detect_browsers() -> list[tuple[str, Optional[str]]]:
    """Return [(label, value), ...] for browsers installed on this device.

    Always includes 'None' first. Checks for the executable in PATH via
    shutil.which. If none are found, falls back to Firefox + Chrome so the
    UI is still useful (e.g. flatpak sandbox where PATH is limited).
    """
    import shutil

    candidates: list[tuple[str, str, list[str]]] = [
        ("Firefox", "firefox", ["firefox", "firefox-esr"]),
        ("Chrome", "chrome", ["google-chrome", "google-chrome-stable", "chrome"]),
        ("Chromium", "chromium", ["chromium", "chromium-browser"]),
        ("Brave", "brave", ["brave-browser", "brave"]),
        ("Edge", "edge", ["microsoft-edge", "microsoft-edge-stable", "edge"]),
        ("Opera", "opera", ["opera"]),
        ("Vivaldi", "vivaldi", ["vivaldi", "vivaldi-stable"]),
    ]

    detected: list[tuple[str, Optional[str]]] = [("None", None)]
    for label, value, bins in candidates:
        if any(shutil.which(b) for b in bins):
            detected.append((label, value))

    # Fallback if we're in a sandbox with a stripped PATH and nothing was
    # detected — still offer the two most common choices.
    if len(detected) == 1:
        detected.extend([("Firefox", "firefox"), ("Chrome", "chrome")])
    return detected


def _fmt_name(fmt: str) -> str:
    return {
        "video": "Video",
        "audio": "Audio",
        "image_jpg": "Image",
        "image_png": "Image",
    }.get(fmt, fmt)


def _default_download_dir() -> str:
    """Return the OS-appropriate default Downloads folder (Windows/Linux)."""
    if os.name == "nt":
        home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
        return os.path.join(home, "Downloads")
    return os.path.join(os.path.expanduser("~"), "Downloads")


def _config_path() -> str:
    base = GLib.get_user_config_dir() or os.path.expanduser("~/.config")
    return os.path.join(base, "com.undermedia.UniversalMediaDownloader", "settings.json")


def _load_saved_dir() -> str:
    """Return saved download dir from config, or the default."""
    default = _default_download_dir()
    try:
        with open(_config_path(), "r", encoding="utf-8") as f:
            data = __import__("json").load(f)
        saved = data.get("download_dir")
        if saved and isinstance(saved, str) and os.path.isdir(saved):
            return saved
        if saved and isinstance(saved, str):
            return saved
    except Exception:
        pass
    return default


def _save_dir(path: str) -> None:
    """Persist *path* so it survives restarts (per-device)."""
    import json

    cfg = _config_path()
    try:
        os.makedirs(os.path.dirname(cfg), exist_ok=True)
        data: dict = {}
        try:
            with open(cfg, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
        data["download_dir"] = path
        with open(cfg, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass
