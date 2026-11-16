"""Dialog pengaturan: folder bawaan, tempel otomatis, dan perbarui yt-dlp."""
from __future__ import annotations

import subprocess  # noqa: S404 - pip dipanggil dengan argumen tetap
import sys
import threading

import customtkinter as ctk
from PIL import Image  # noqa: F401 - Pillow dipakai bersama app

from ui import theme as th
from ui.components import Card, hand_cursor, secondary_button
from utils import config


class SettingsDialog(ctk.CTkToplevel):
    """Jendela pengaturan ringan (modeless, satu instance)."""

    def __init__(self, master, theme: th.Theme, cfg: dict) -> None:
        super().__init__(master)
        self.theme = theme
        self.cfg = cfg

        self.title("Pengaturan")
        self.geometry("420x330")
        self.resizable(False, False)
        self.transient(master)
        self.attributes("-topmost", True)
        self.after(120, lambda: self.attributes("-topmost", False))
        self.configure(fg_color=theme.color("bg"))
        self.grid_columnconfigure(0, weight=1)

        card = Card(self, theme.colors())
        card.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="Pengaturan", font=th.F_TITLE,
                     text_color=theme.color("text")).grid(
            row=0, column=0, sticky="w", padx=20, pady=(20, 8))

        # Folder simpan bawaan
        ctk.CTkLabel(card, text="Folder simpan bawaan", font=th.F_CAPTION_BOLD,
                     text_color=theme.color("text_secondary"), anchor="w").grid(
            row=1, column=0, sticky="ew", padx=20)
        folder_row = ctk.CTkFrame(card, fg_color="transparent")
        folder_row.grid(row=2, column=0, sticky="ew", padx=20, pady=(4, 12))
        folder_row.grid_columnconfigure(0, weight=1)
        self.folder_label = ctk.CTkLabel(folder_row, text=cfg.get("download_dir", ""),
                                         font=th.F_CAPTION,
                                         text_color=theme.color("text"),
                                         anchor="w", wraplength=240)
        self.folder_label.grid(row=0, column=0, sticky="ew")
        btn_folder = secondary_button(folder_row, theme.colors(), "Ubah", self._pick_folder, width=70)
        hand_cursor(btn_folder)
        btn_folder.grid(row=0, column=1, padx=(8, 0))

        # Tempel otomatis
        self.auto_paste_var = ctk.BooleanVar(value=cfg.get("auto_paste", False))
        auto = ctk.CTkSwitch(
            card, text="Tempel otomatis dari clipboard saat aplikasi aktif",
            variable=self.auto_paste_var, command=self._save,
            font=th.F_BODY, text_color=theme.color("text"),
            progress_color=theme.color("primary"),
        )
        hand_cursor(auto)
        auto.grid(row=3, column=0, sticky="w", padx=20, pady=(8, 12))

        # Tombol perbarui yt-dlp
        self.update_btn = ctk.CTkButton(
            card, text="Perbarui yt-dlp", command=self._update_ytdlp, height=38,
            corner_radius=th.RADIUS_BUTTON, font=th.F_BODY_BOLD,
            fg_color=theme.color("primary"), hover_color=theme.color("primary_hover"),
            text_color="#FFFFFF",
        )
        hand_cursor(self.update_btn)
        self.update_btn.grid(row=4, column=0, sticky="ew", padx=20, pady=(4, 12))

        self.status_label = ctk.CTkLabel(card, text="", font=th.F_CAPTION,
                                         text_color=theme.color("text_secondary"),
                                         wraplength=340, justify="left", anchor="w")
        self.status_label.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 4))

        close_btn = ctk.CTkButton(
            card, text="Tutup", command=self.destroy, height=36, width=100,
            corner_radius=th.RADIUS_BUTTON, font=th.F_BODY_BOLD,
            fg_color=theme.color("elevated"), hover_color=theme.color("border"),
            text_color=theme.color("text"), border_width=1,
            border_color=theme.color("border"),
        )
        hand_cursor(close_btn)
        close_btn.grid(row=6, column=0, sticky="e", padx=20, pady=(8, 20))

    def _pick_folder(self) -> None:
        from tkinter import filedialog

        chosen = filedialog.askdirectory(
            parent=self, title="Pilih folder simpan",
            initialdir=self.cfg.get("download_dir", ""),
        )
        if chosen:
            self.cfg["download_dir"] = chosen
            self.folder_label.configure(text=chosen)
            self._save()

    def _save(self) -> None:
        self.cfg["auto_paste"] = bool(self.auto_paste_var.get())
        config.save({"download_dir": self.cfg.get("download_dir"),
                     "auto_paste": self.cfg["auto_paste"]})

    def _update_ytdlp(self) -> None:
        """Jalankan pip install -U yt-dlp di thread latar."""
        self.update_btn.configure(state="disabled", text="Memperbarui...")
        self.status_label.configure(text="Memperbarui yt-dlp, mohon tunggu...")

        def worker() -> None:
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
                    capture_output=True, text=True, timeout=300, check=True,
                )
                self.after(0, lambda: self._update_done(True,
                            (result.stdout or "").strip().splitlines()[-1:]))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._update_done(False, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _update_done(self, ok: bool, message: list[str] | str) -> None:
        self.update_btn.configure(state="normal", text="Perbarui yt-dlp")
        if ok:
            self.status_label.configure(text="yt-dlp berhasil diperbarui. "
                                             "Nyalakan ulang aplikasi agar berlaku.")
        else:
            self.status_label.configure(text=f"Perbarui gagal: {message}")
