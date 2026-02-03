"""Application entrypoint.

Run in development:
    python -m purway_geotagger.app

In packaged form (PyInstaller), this becomes the main script.
"""

from __future__ import annotations

import sys
import os
from PySide6.QtWidgets import QApplication

from purway_geotagger.gui.main_window import MainWindow
from purway_geotagger.gui.theme import apply_theme
from purway_geotagger.core.settings import AppSettings
from purway_geotagger.util.platform import configure_macos_app_identity


def main() -> int:
    configure_macos_app_identity()

    app = QApplication(sys.argv)

    settings = AppSettings.load()
    apply_theme(app, settings.ui_theme)
    if settings.exiftool_path:
        os.environ["PURWAY_EXIFTOOL_PATH"] = settings.exiftool_path
    win = MainWindow(settings=settings)
    win.show()

    code = app.exec()
    settings.save()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
