"""Uji cepat logika inti via CLI: cek info, format, dan unduhan kecil.

Pakai: python tests\test_core.py <url_youtube>
Tanpa argumen: memakai video contoh.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.downloader import Downloader, friendly_error  # noqa: E402
from core import formats  # noqa: E402
from utils.ffmpeg_check import find_ffmpeg  # noqa: E402
from utils import helpers  # noqa: E402

DEFAULT_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
OUT_DIR = Path(__file__).resolve().parent / "out"


def main() -> None:
    flags = [a for a in sys.argv[1:] if a.startswith("-")]
    urls = [a for a in sys.argv[1:] if not a.startswith("-")]
    url = urls[0] if urls else DEFAULT_URL
    no_download = "--no-download" in flags
    ffmpeg = find_ffmpeg()
    print("FFmpeg :", ffmpeg)
    dl = Downloader(ffmpeg)

    print("Mengambil info:", url)
    try:
        info = dl.fetch_info(url)
    except Exception as exc:
        print("GAGAL ambil info ->", friendly_error(exc))
        sys.exit(1)

    print("Judul    :", info["title"])
    print("Channel  :", info["uploader"])
    print("Durasi   :", helpers.format_duration(info.get("duration")))
    print("Resolusi :", info["heights"])
    print("Sanitasi :", helpers.sanitize_filename(info["title"]))

    if no_download:
        return

    # Unduh kualitas terendah untuk memverifikasi pipeline (cukup kecil).
    mode = "audio" if "--audio" in flags else "video"
    if mode == "audio":
        quality = next((a for a in flags if a in formats.AUDIO_QUALITIES), "128 kbps")
    else:
        quality = "360p" if 360 in (info.get("heights") or []) else "Terbaik"
    print(f"\nMengunduh uji: mode={mode} kualitas={quality} -> {OUT_DIR}")

    done = threading.Event()

    def on_progress(d):
        pct = d.get("percent") or 0
        print(f"\r  progres: {pct:5.1f}%  tahap={d.get('stage')}", end="", flush=True)

    def on_stage(s):
        print(f"\n  tahap: {s}")

    def on_done(path):
        print(f"\nSELESAI -> {path}")
        p = Path(path)
        print("  ukuran:", helpers.format_size(p.stat().st_size) if p.exists() else "?")
        done.set()

    def on_error(exc):
        print("\nERROR ->", friendly_error(exc))
        done.set()

    threading.Thread(
        target=dl.download,
        args=(url, mode, quality, OUT_DIR, on_progress, on_stage, on_done, on_error),
        daemon=True,
    ).start()

    # Uji pembatalan (opsional, dengan flag --cancel): batal setelah 3 detik.
    if "--cancel" in flags:
        threading.Timer(3.0, dl.cancel).start()

    done.wait(timeout=300)
    print("\nformat string 360p:", formats.video_format_string("360p"))


if __name__ == "__main__":
    main()
