"""Palet warna, font, dan konstanta spasi untuk UI.

Semua widget UI mengambil warna dari sini dan bisa mendaftar sebagai
"watcher" agar otomatis di-update saat tema berganti gelap <-> terang.
"""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

# Palet warna per mode tampilan (spesifikasi desain).
PALETTES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#0F1115",
        "surface": "#1A1D24",
        "elevated": "#232733",
        "border": "#2E3340",
        "primary": "#6C5CE7",
        "primary_hover": "#8073F0",
        "success": "#2ECC71",
        "error": "#FF5C5C",
        "warning": "#F5A623",
        "text": "#F1F3F7",
        "text_secondary": "#9AA0AE",
    },
    "light": {
        "bg": "#F2F4F8",
        "surface": "#FFFFFF",
        "elevated": "#EAEDF4",
        "border": "#D9DEE9",
        "primary": "#6C5CE7",
        "primary_hover": "#5A4BD1",
        "success": "#27AE60",
        "error": "#E74C3C",
        "warning": "#E67E22",
        "text": "#1B1E27",
        "text_secondary": "#6B7280",
    },
}

FONT = "Segoe UI"

# Skala tipografi.
F_TITLE = (FONT, 22, "bold")          # judul aplikasi
F_SECTION = (FONT, 13, "bold")        # label seksi
F_BODY = (FONT, 12)                   # teks utama
F_BODY_BOLD = (FONT, 12, "bold")
F_CAPTION = (FONT, 11)                # teks kecil sekunder
F_CAPTION_BOLD = (FONT, 11, "bold")
F_BUTTON = (FONT, 13, "bold")
F_BUTTON_BIG = (FONT, 14, "bold")
F_INPUT = (FONT, 14)

# Grid spasi 8px.
SP_1 = 8
SP_2 = 16
SP_3 = 24
SP_4 = 32

# Sudut membulat.
RADIUS_CARD = 16
RADIUS_INPUT = 12
RADIUS_BUTTON = 10


class Theme:
    """Menyimpan mode tampilan aktif dan memberi tahu watcher saat berganti."""

    def __init__(self, mode: str = "dark") -> None:
        self.mode = mode if mode in PALETTES else "dark"
        self._watchers: list[Callable[[dict[str, str]], None]] = []
        ctk.set_appearance_mode(self.mode)

    def colors(self) -> dict[str, str]:
        """Kembalikan palet warna untuk mode aktif."""
        return PALETTES[self.mode]

    def color(self, role: str) -> str:
        """Kembalikan satu warna berdasarkan perannya, mis. 'primary'."""
        return PALETTES[self.mode].get(role, "#FF00FF")

    def set_mode(self, mode: str) -> None:
        """Ganti mode tampilan dan paksa semua watcher memperbarui warna."""
        if mode not in PALETTES:
            return
        self.mode = mode
        ctk.set_appearance_mode(mode)
        for fn in list(self._watchers):
            try:
                fn(PALETTES[mode])
            except Exception:  # pragma: no cover - UI tetap hidup walau 1 watcher gagal
                pass

    def toggle(self) -> None:
        """Beralih antara gelap dan terang."""
        self.set_mode("light" if self.mode == "dark" else "dark")

    def watch(self, fn: Callable[[dict[str, str]], None]) -> None:
        """Daftarkan callback yang dipanggil (dan langsung dijalankan) saat tema berubah."""
        self._watchers.append(fn)
        try:
            fn(PALETTES[self.mode])
        except Exception:
            pass
