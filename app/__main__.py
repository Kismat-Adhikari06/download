"""Entry point that launches the GTK app."""

import os
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk  # noqa: E402

from .window import DownloaderWindow  # noqa: E402

APP_ID = "com.undermedia.UniversalMediaDownloader"
APP_NAME = "Universal Media Downloader"
APP_ICON = APP_ID


class DownloaderApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.set_resource_base_path("/com/undermedia/UniversalMediaDownloader")
        self.window = None

    def do_activate(self) -> None:
        if self.window is None:
            self.window = DownloaderWindow(self)
        self.window.present()


def main() -> None:
    app = DownloaderApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
