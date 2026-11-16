"""Deteksi FFmpeg dan pesan petunjuk dalam Bahasa Indonesia."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from utils.helpers import resource_path


def find_ffmpeg() -> str | None:
    """Cari ffmpeg.exe: dulu yang dibundel di bin/, lalu di PATH sistem.

    Return path lengkap, atau None jika tidak ditemukan.
    """
    candidates = [
        resource_path("bin/ffmpeg.exe"),          # dibundel via PyInstaller (_MEIPASS)
        Path(__file__).resolve().parent.parent / "bin/ffmpeg.exe",  # folder proyek
    ]
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).parent / "bin/ffmpeg.exe")  # sebelah exe
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return shutil.which("ffmpeg")


def find_ffprobe() -> str | None:
    """Cari ffprobe.exe dengan urutan yang sama seperti find_ffmpeg()."""
    bundled = resource_path("bin/ffprobe.exe")
    if bundled.is_file():
        return str(bundled)
    return shutil.which("ffprobe")


def ffmpeg_missing_message() -> str:
    """Dialog instruksinya ketika FFmpeg tidak ditemukan."""
    return (
        "FFmpeg tidak ditemukan di komputer ini.\n\n"
        "FFmpeg dibutuhkan untuk menggabungkan video + audio (MP4)\n"
        "dan mengonversi audio menjadi MP3.\n\n"
        "Cara memperbaiki:\n"
        "1. Unduh FFmpeg dari https://www.gyan.dev/ffmpeg/builds/\n"
        "   atau https://github.com/BtbN/FFmpeg-Builds/releases\n"
        "2. Salin ffmpeg.exe (dan ffprobe.exe) ke folder 'bin/'\n"
        "   di sebelah aplikasi ini, atau\n"
        "3. Tambahkan folder FFmpeg ke PATH Windows.\n\n"
        "Setelah itu jalankan ulang aplikasi."
    )
