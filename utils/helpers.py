"""Fungsi bantu umum: path resource, sanitasi nama file, pemformatan, pembuka file."""
from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

_INVALID_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')
_MULTI_SPACE = re.compile(r"\s+")

# Pola URL YouTube yang didukung (watch, youtu.be, shorts, music, playlist).
YT_URL_RE = re.compile(
    r"^(https?://)?(www\.|m\.|music\.)?"
    r"(youtube\.com/(watch\?|shorts/|playlist\?|embed/)|youtu\.be/)[^\s]+$",
    re.IGNORECASE,
)


def resource_path(relative: str) -> Path:
    """Path file resource, aman untuk PyInstaller onefile (sys._MEIPASS)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent  # root proyek saat dev
    return base / relative


def is_youtube_url(url: str) -> bool:
    """Cek kasar apakah teks berbentuk URL YouTube."""
    return bool(url) and bool(YT_URL_RE.match(url.strip()))


def sanitize_filename(name: str, max_len: int = 150) -> str:
    """Bersihkan judul agar aman sebagai nama file di Windows."""
    name = _INVALID_CHARS.sub("_", name)
    name = _MULTI_SPACE.sub(" ", name).strip(" .")
    return name[:max_len].strip(" .") or "video"


def format_duration(seconds: float | None) -> str:
    """Durasi menjadi teks seperti '3:24' atau '1:02:05'."""
    if seconds is None:
        return "--:--"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_eta(seconds: float | None) -> str:
    """ETA ringkas: '45 dtk', '3 mnt 12 dtk', '1 jam 5 mnt'."""
    if seconds is None:
        return "-"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h} jam {m} mnt"
    if m:
        return f"{m} mnt {s} dtk"
    return f"{s} dtk"


def format_size(n: float | None) -> str:
    """Ukuran byte menjadi '12,3 MB'."""
    if n is None:
        return "-"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def format_speed(bps: float | None) -> str:
    """Kecepatan byte/s menjadi '2,4 MB/dtk'."""
    if not bps:
        return "-"
    return f"{format_size(bps)}/dtk"


def unique_path(base_path: Path) -> Path:
    """Hindari menimpa file lama: jika sudah ada, tambahkan ' (1)', ' (2)', dst."""
    if not base_path.exists():
        return base_path
    stem, suffix = base_path.stem, base_path.suffix
    parent = base_path.parent
    for i in range(1, 1000):
        candidate = parent / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
    return parent / f"{stem} ({int(time.time())}){suffix}"


def open_file(path: str | Path) -> None:
    """Buka file dengan aplikasi bawaan Windows."""
    try:
        import os

        os.startfile(str(path))  # noqa: S606 - Windows only
    except Exception:
        pass


def open_folder(path: str | Path, select: str | Path | None = None) -> None:
    """Buka folder di Explorer; jika `select` diisi, file tersebut disorot."""
    try:
        if select:
            subprocess.Popen(["explorer", "/select,", str(select)])  # noqa: S603 S607
        else:
            subprocess.Popen(["explorer", str(path)])  # noqa: S603 S607
    except Exception:
        pass


def ellipse(text: str, limit: int = 90) -> str:
    """Potong teks panjang dengan ellipsis (…)."""
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
