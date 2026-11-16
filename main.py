"""Titik masuk aplikasi: siapkan logging, cek FFmpeg, lalu tampilkan jendela."""
from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from utils import config
from utils.ffmpeg_check import find_ffmpeg, ffmpeg_missing_message

APP_NAME = "YT Downloader"


def setup_logging() -> None:
    """Kirim log ke %APPDATA%/YTDownloader/logs/app.log (maks 5 MB x 2)."""
    log_dir = Path(config.config_path()).parent / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = logging.handlers.RotatingFileHandler(
            log_dir / "app.log", maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8"
        )
    except OSError:
        handler = logging.StreamHandler()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[handler, logging.StreamHandler(sys.stdout)],
    )


def main() -> None:
    setup_logging()
    logging.getLogger(__name__).info("Aplikasi dimulai")

    # Cek FFmpeg lebih awal agar pengguna langsung tahu bila perlu dipasang.
    if find_ffmpeg() is None:
        import tkinter.messagebox as mb
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        mb.showwarning(f"{APP_NAME} — FFmpeg tidak ditemukan", ffmpeg_missing_message())
        root.destroy()

    from ui.app import App

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
