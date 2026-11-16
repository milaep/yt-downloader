"""Pengaturan aplikasi disimpan sebagai JSON di %APPDATA%/YTDownloader/config.json."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

_CONFIG_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "YTDownloader"
_CONFIG_FILE = _CONFIG_DIR / "config.json"

DEFAULTS: dict = {
    "download_dir": str(Path.home() / "Downloads"),
    "mode": "video",            # "video" | "audio"
    "quality": "Terbaik",       # label kualitas terakhir yang dipakai
    "theme": "dark",            # "dark" | "light"
    "auto_paste": False,        # deteksi otomatis clipboard saat aplikasi aktif
}

_lock = threading.Lock()


def _ensure_dir() -> None:
    try:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def load() -> dict:
    """Baca konfigurasi; kembalikan DEFAULTS yang sudah digabung isi file."""
    with _lock:
        data = dict(DEFAULTS)
        try:
            if _CONFIG_FILE.is_file():
                data.update(json.loads(_CONFIG_FILE.read_text("utf-8")))
        except (OSError, json.JSONDecodeError):
            pass
        return data


def save(values: dict) -> None:
    """Simpan sebagian/penuh nilai konfigurasi (merge dengan yang sudah ada)."""
    with _lock:
        data = dict(DEFAULTS)
        try:
            if _CONFIG_FILE.is_file():
                data.update(json.loads(_CONFIG_FILE.read_text("utf-8")))
        except (OSError, json.JSONDecodeError):
            pass
        data.update(values)
        _ensure_dir()
        try:
            _CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
        except OSError:
            pass


def config_path() -> Path:
    """Lokasi file konfigurasi (untuk ditampilkan/di-debug)."""
    return _CONFIG_FILE
