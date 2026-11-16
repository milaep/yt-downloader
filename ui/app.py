"""Jendela utama aplikasi YT Downloader (CustomTkinter).

Semua pekerjaan jaringan/unduhan berjalan di thread pekerja; UI hanya
membaca event dari queue.Queue melalui after() polling.
"""
from __future__ import annotations

import io
import logging
import queue
import threading
from pathlib import Path
from typing import Any, Callable

import customtkinter as ctk
import requests
from PIL import Image, ImageDraw

import yt_dlp
from core.downloader import DownloadCancelled, Downloader, friendly_error
from core import formats
from ui import theme as th
from ui.components import (
    Badge,
    Card,
    EmptyState,
    ProgressPanel,
    SuccessPanel,
    ToastManager,
    hand_cursor,
    secondary_button,
)
from utils import config, helpers
from utils.ffmpeg_check import find_ffmpeg, ffmpeg_missing_message

logger = logging.getLogger(__name__)

THUMB_SIZE = (280, 158)


class App(ctk.CTk):
    """Jendela utama: header, input URL, pratinjau, opsi, aksi, dan status."""

    APP_W, APP_H = 880, 700
    MIN_W, MIN_H = 760, 600

    def __init__(self) -> None:
        super().__init__()
        cfg = config.load()
        self.cfg = cfg
        self.theme = th.Theme(cfg.get("theme", "dark"))
        self.ffmpeg_path = find_ffmpeg()
        self.downloader = Downloader(self.ffmpeg_path)
        self.toasts = ToastManager(self, self.theme)
        self.ui_queue: queue.Queue[tuple[str, Any]] = queue.Queue()

        self.ui_state = "idle"  # idle | fetching | ready | downloading | done
        self.info: dict | None = None
        self.thumb_image: ctk.CTkImage | None = None
        self.result_path = ""
        self._themable: list[tuple[object, dict[str, str]] | Callable] = []

        self._setup_window()
        self._build_header()
        self._build_url_section()
        self._build_middle()
        self._build_action_area()
        self._build_footer()

        self.theme.watch(self.apply_colors)
        self._on_mode_change(self.mode_seg.get())  # sinkronkan dropdown kualitas dgn mode tersimpan
        self.after(80, self._poll_ui_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if not self.ffmpeg_path:
            self.after(400, self._warn_ffmpeg_missing)

    # ------------------------------------------------------------ kerangka

    def _setup_window(self) -> None:
        self.title("YT Downloader")
        self.geometry(f"{self.APP_W}x{self.APP_H}")
        self.minsize(self.MIN_W, self.MIN_H)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # area tengah membesar

    def _warn_ffmpeg_missing(self) -> None:
        """Dialog berisi instruksi bila FFmpeg tidak ditemukan saat startup."""
        import tkinter.messagebox as mb

        mb.showwarning("FFmpeg tidak ditemukan", ffmpeg_missing_message(), parent=self)

    # -------------------------------------------------------------- header

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent", height=64)
        header.grid(row=0, column=0, sticky="ew", padx=th.SP_3, pady=(th.SP_2, th.SP_1))
        header.grid_columnconfigure(1, weight=1)

        icon = ctk.CTkLabel(
            header, text="▶", width=40, height=40, corner_radius=12,
            fg_color=self.theme.color("primary"), text_color="#FFFFFF",
            font=("Segoe UI", 17, "bold"),
        )
        icon.grid(row=0, column=0, rowspan=2, padx=(0, 12))
        self._themable.append((icon, {"fg_color": "primary"}))

        title = ctk.CTkLabel(header, text="YT Downloader", font=th.F_TITLE,
                             text_color=self.theme.color("text"), anchor="w")
        title.grid(row=0, column=1, sticky="sw")
        self._themable.append((title, {"text_color": "text"}))

        subtitle = ctk.CTkLabel(header, text="Unduh video & audio YouTube", font=th.F_CAPTION,
                                text_color=self.theme.color("text_secondary"), anchor="w")
        subtitle.grid(row=1, column=1, sticky="nw")
        self._themable.append((subtitle, {"text_color": "text_secondary"}))

        btns = ctk.CTkFrame(header, fg_color="transparent")
        btns.grid(row=0, column=2, rowspan=2, sticky="e")

        self.theme_btn = ctk.CTkButton(
            btns, text="🌙", width=38, height=38, corner_radius=12,
            fg_color=self.theme.color("elevated"), hover_color=self.theme.color("border"),
            text_color=self.theme.color("text"), command=self._toggle_theme,
        )
        hand_cursor(self.theme_btn)
        self.theme_btn.pack(side="left", padx=6)
        self._themable.append((self.theme_btn, {
            "fg_color": "elevated", "hover_color": "border", "text_color": "text"}))

        self.settings_btn = ctk.CTkButton(
            btns, text="⚙", width=38, height=38, corner_radius=12,
            fg_color=self.theme.color("elevated"), hover_color=self.theme.color("border"),
            text_color=self.theme.color("text"), font=("Segoe UI", 15),
            command=self._open_settings,
        )
        hand_cursor(self.settings_btn)
        self.settings_btn.pack(side="left")
        self._themable.append((self.settings_btn, {
            "fg_color": "elevated", "hover_color": "border", "text_color": "text"}))

    def _toggle_theme(self) -> None:
        mode = "light" if self.theme.mode == "dark" else "dark"
        self.cfg["theme"] = mode
        config.save({"theme": mode})
        self.theme_btn.configure(text="☀️" if mode == "dark" else "🌙")
        self.theme.set_mode(mode)

    # ---------------------------------------------------------- url seksi

    def _build_url_section(self) -> None:
        card = Card(self, self.theme.colors())
        card.grid(row=1, column=0, sticky="ew", padx=th.SP_3, pady=th.SP_1)
        card.grid_columnconfigure(0, weight=1)
        self.url_card = card

        self.url_entry = ctk.CTkEntry(
            card, height=46, corner_radius=th.RADIUS_INPUT, font=th.F_INPUT,
            fg_color=self.theme.color("elevated"),
            border_color=self.theme.color("border"),
            text_color=self.theme.color("text"),
            placeholder_text_color=self.theme.color("text_secondary"),
            placeholder_text="Tempel link YouTube di sini...",
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=16, pady=16)
        self._themable.append((self.url_entry, {
            "fg_color": "elevated", "border_color": "border",
            "text_color": "text", "placeholder_text_color": "text_secondary"}))
        self.url_entry.bind("<Return>", lambda _e: self.check_link())
        self.url_entry.bind("<Control-v>", lambda _e: self._paste_clipboard() or "break")
        self.bind("<FocusIn>", self._on_window_focus)

        self.paste_btn = secondary_button(card, self.theme.colors(), "📋 Tempel",
                                          self._paste_clipboard, width=104)
        self.paste_btn.grid(row=0, column=1, padx=(0, 10), pady=16)

        self.check_btn = ctk.CTkButton(
            card, text="Cek Link", command=self.check_link, width=124, height=44,
            corner_radius=th.RADIUS_BUTTON, font=th.F_BUTTON,
            fg_color=self.theme.color("primary"), hover_color=self.theme.color("primary_hover"),
            text_color="#FFFFFF",
        )
        hand_cursor(self.check_btn)
        self.check_btn.grid(row=0, column=2, padx=(0, 16), pady=16)
        self._themable.append((self.check_btn, {
            "fg_color": "primary", "hover_color": "primary_hover"}))

    def _paste_clipboard(self) -> str:
        """Salin isi clipboard ke kolom URL."""
        try:
            text = (self.clipboard_get() or "").strip()
        except Exception:
            text = ""
        if text:
            self.url_entry.delete(0, "end")
            self.url_entry.insert("end", text)
        return "break"

    def _on_window_focus(self, event) -> None:
        """Deteksi otomatis URL di clipboard saat jendela mendapat fokus (opsional)."""
        if event.widget is not self or not self.cfg.get("auto_paste"):
            return
        if self.ui_state == "fetching" or self.url_entry.get().strip():
            return
        try:
            text = (self.clipboard_get() or "").strip()
        except Exception:
            return
        if helpers.is_youtube_url(text):
            self.url_entry.insert("end", text)
            self.set_status("URL terdeteksi di clipboard — tekan Cek Link.")
            self._show_toast("URL YouTube terdeteksi di clipboard.", "info", 2500)

    # --------------------------------------------------------- area tengah

    def _build_middle(self) -> None:
        middle = ctk.CTkScrollableFrame(
            self, fg_color=self.theme.color("bg"),
            label_fg_color=self.theme.color("bg"),
            scrollbar_button_color=self.theme.color("border"),
            scrollbar_button_hover_color=self.theme.color("primary"),
        )
        middle.grid(row=2, column=0, sticky="nsew", padx=th.SP_3, pady=th.SP_1)
        middle.grid_columnconfigure(0, weight=1)
        self.middle = middle

        # Keadaan kosong (ditampilkan saat belum ada pratinjau).
        self.empty_state = EmptyState(middle, self.theme.colors())
        self.empty_state.grid(row=0, column=0, sticky="ew", pady=th.SP_1)

        # Panel pesan galat (tersembunyi).
        self.error_card = Card(middle, self.theme.colors())
        self.error_label = ctk.CTkLabel(
            self.error_card, text="", font=th.F_BODY, justify="left",
            wraplength=640, text_color=self.theme.color("error"), anchor="w",
        )
        self.error_label.pack(fill="x", padx=20, pady=16)
        self.error_card.grid(row=0, column=0, sticky="ew", pady=th.SP_1)
        self.error_card.grid_remove()
        self._themable.append((self.error_label, {"text_color": "error"}))

        # Kartu pratinjau (tersembunyi hingga link dicek).
        self.preview_card = Card(middle, self.theme.colors())
        self.preview_card.grid(row=0, column=0, sticky="ew", pady=th.SP_1)
        self.preview_card.grid_remove()
        self.preview_card.grid_columnconfigure(1, weight=1)

        thumb_frame = ctk.CTkFrame(self.preview_card, fg_color="transparent",
                                   width=THUMB_SIZE[0], height=THUMB_SIZE[1])
        thumb_frame.grid(row=0, column=0, rowspan=2, padx=16, pady=16)
        thumb_frame.grid_propagate(False)

        self.thumb_label = ctk.CTkLabel(
            thumb_frame, text="Memuat gambar...", width=THUMB_SIZE[0], height=THUMB_SIZE[1],
            corner_radius=th.RADIUS_INPUT, fg_color=self.theme.color("elevated"),
            font=th.F_CAPTION, text_color=self.theme.color("text_secondary"),
        )
        self.thumb_label.pack(fill="both", expand=True)
        self._themable.append((self.thumb_label, {
            "fg_color": "elevated", "text_color": "text_secondary"}))

        self.duration_badge = Badge(thumb_frame, self.theme.colors(), "0:00", "#14151A")
        self.duration_badge.place(relx=0.0, rely=1.0, anchor="sw", x=8, y=-8)

        info_col = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        info_col.grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=16)
        info_col.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(info_col, text="", font=th.F_BODY_BOLD,
                                        text_color=self.theme.color("text"),
                                        wraplength=400, justify="left", anchor="w")
        self.title_label.grid(row=0, column=0, sticky="ew")
        self._themable.append((self.title_label, {"text_color": "text"}))

        self.channel_label = ctk.CTkLabel(info_col, text="", font=th.F_CAPTION,
                                          text_color=self.theme.color("text_secondary"),
                                          anchor="w")
        self.channel_label.grid(row=1, column=0, sticky="ew")
        self._themable.append((self.channel_label, {"text_color": "text_secondary"}))

        self.res_label = ctk.CTkLabel(info_col, text="", font=th.F_CAPTION,
                                      text_color=self.theme.color("text_secondary"),
                                      anchor="w")
        self.res_label.grid(row=2, column=0, sticky="ew")
        self._themable.append((self.res_label, {"text_color": "text_secondary"}))

        # Daftarkan kartu agar ikut berubah saat tema berganti.
        self._themable.append(self.url_card.apply_colors)
        self._themable.append(self.preview_card.apply_colors)
        self._themable.append(self.empty_state.apply_colors)

        # Kartu opsi (mode, kualitas, folder).
        self.options_card = Card(middle, self.theme.colors())
        self.options_card.grid(row=1, column=0, sticky="ew", pady=th.SP_1)
        self.options_card.grid_columnconfigure(1, weight=1)

        def label(master, text, row):
            lbl = ctk.CTkLabel(master, text=text, font=th.F_CAPTION_BOLD,
                               text_color=self.theme.color("text_secondary"), anchor="w", width=90)
            lbl.grid(row=row, column=0, sticky="w", padx=(20, 12), pady=12)
            self._themable.append((lbl, {"text_color": "text_secondary"}))

        label(self.options_card, "Mode", 0)
        self.mode_seg = ctk.CTkSegmentedButton(
            self.options_card, values=["Video (MP4)", "Audio (MP3)"],
            command=self._on_mode_change, height=34,
            fg_color=self.theme.color("elevated"),
            selected_color=self.theme.color("primary"),
            selected_hover_color=self.theme.color("primary_hover"),
            unselected_color=self.theme.color("elevated"),
            unselected_hover_color=self.theme.color("border"),
            text_color=self.theme.color("text"), font=th.F_BODY_BOLD,
            corner_radius=th.RADIUS_BUTTON,
        )
        self.mode_seg.set("Video (MP4)" if self.cfg.get("mode", "video") == "video" else "Audio (MP3)")
        self.mode_seg.grid(row=0, column=1, sticky="w", padx=8, pady=12)
        self._themable.append((self.mode_seg, {
            "fg_color": "elevated", "selected_color": "primary",
            "selected_hover_color": "primary_hover", "unselected_color": "elevated",
            "unselected_hover_color": "border", "text_color": "text"}))

        label(self.options_card, "Kualitas", 1)
        self.quality_var = ctk.StringVar(value="Terbaik")
        self.quality_menu = ctk.CTkOptionMenu(
            self.options_card, values=["Terbaik"], variable=self.quality_var,
            width=180, height=34, font=th.F_BODY_BOLD,
            fg_color=self.theme.color("elevated"),
            button_color=self.theme.color("border"),
            button_hover_color=self.theme.color("primary"),
            text_color=self.theme.color("text"),
            dropdown_fg_color=self.theme.color("surface"),
            dropdown_hover_color=self.theme.color("primary"),
            dropdown_text_color=self.theme.color("text"),
            corner_radius=th.RADIUS_BUTTON,
        )
        hand_cursor(self.quality_menu)
        self.quality_menu.grid(row=1, column=1, sticky="w", padx=8, pady=12)
        self._themable.append((self.quality_menu, {
            "fg_color": "elevated", "button_color": "border",
            "button_hover_color": "primary", "text_color": "text"}))

        label(self.options_card, "Simpan ke", 2)
        folder_row = ctk.CTkFrame(self.options_card, fg_color="transparent")
        folder_row.grid(row=2, column=1, sticky="ew", padx=8, pady=(12, 16))
        folder_row.grid_columnconfigure(0, weight=1)

        self.folder_label = ctk.CTkLabel(
            folder_row, text=self.cfg.get("download_dir", ""), font=th.F_CAPTION,
            text_color=self.theme.color("text_secondary"), anchor="w",
        )
        self.folder_label.grid(row=0, column=0, sticky="ew")
        self._themable.append((self.folder_label, {"text_color": "text_secondary"}))

        self.folder_btn = secondary_button(folder_row, self.theme.colors(), "Ubah",
                                           self._pick_folder, width=80)
        self.folder_btn.grid(row=0, column=1, padx=(10, 0))

        self._themable.append(self.options_card.apply_colors)
        self._themable.append(self._apply_middle_colors)

    def _apply_middle_colors(self, colors: dict[str, str]) -> None:
        """Samakan latar area tengah (scrollable frame) dengan latar jendela."""
        try:
            self.middle.configure(
                fg_color=colors["bg"], label_fg_color=colors["bg"],
                scrollbar_button_color=colors["border"],
                scrollbar_button_hover_color=colors["primary"],
            )
        except Exception:
            pass

    # ---------------------------------------------------------- area aksi

    def _build_action_area(self) -> None:
        area = ctk.CTkFrame(self, fg_color="transparent")
        area.grid(row=3, column=0, sticky="ew", padx=th.SP_3, pady=(th.SP_1, th.SP_1))
        area.grid_columnconfigure(0, weight=1)

        self.download_btn = ctk.CTkButton(
            area, text="⬇  Download", command=self.start_download, height=50,
            corner_radius=th.RADIUS_INPUT, font=th.F_BUTTON_BIG,
            fg_color=self.theme.color("primary"), hover_color=self.theme.color("primary_hover"),
            text_color="#FFFFFF",
        )
        hand_cursor(self.download_btn)
        self.download_btn.grid(row=0, column=0, sticky="ew")
        self._themable.append((self.download_btn, {
            "fg_color": "primary", "hover_color": "primary_hover"}))

        self.progress_panel = ProgressPanel(area, self.theme.colors(), self._cancel_download)
        self.progress_panel.grid(row=0, column=0, sticky="ew")
        self.progress_panel.grid_remove()
        self._themable.append(self.progress_panel.apply_colors)

        self.success_panel = SuccessPanel(area, self.theme.colors(),
                                          self._open_result_file, self._open_result_folder)
        self.success_panel.grid(row=0, column=0, sticky="ew")
        self.success_panel.grid_remove()
        self._themable.append(self.success_panel.apply_colors)

    # --------------------------------------------------------------- footer

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, fg_color="transparent", height=30)
        footer.grid(row=4, column=0, sticky="ew", padx=th.SP_3, pady=(0, 10))
        footer.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            footer, text="Siap.", font=th.F_CAPTION,
            text_color=self.theme.color("text_secondary"), anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="w")
        self._themable.append((self.status_label, {"text_color": "text_secondary"}))

        ffmpeg_ok = "✓" if self.ffmpeg_path else "✕"
        meta = ctk.CTkLabel(
            footer,
            text=f"yt-dlp {yt_dlp.version.__version__}   •   FFmpeg {ffmpeg_ok}",
            font=th.F_CAPTION, text_color=self.theme.color("text_secondary"), anchor="e",
        )
        meta.grid(row=0, column=1, sticky="e")
        self._themable.append((meta, {"text_color": "text_secondary"}))

    # ---------------------------------------------------------- tema warna

    def apply_colors(self, colors: dict[str, str]) -> None:
        """Terapkan ulang palet warna ke seluruh widget utama."""
        self.configure(fg_color=colors["bg"])
        for entry in self._themable:
            if callable(entry):
                entry(colors)
                continue
            widget, props = entry
            try:
                widget.configure(**{prop: colors[role] for prop, role in props.items()})
            except Exception:
                pass
        self.error_card.apply_colors(colors)

    # ------------------------------------------------------------ interaksi

    def set_status(self, text: str) -> None:
        """Perbarui teks kecil di footer."""
        self.status_label.configure(text=text)

    def show_error(self, message: str) -> None:
        """Tampilkan kartu galat di area tengah."""
        self.empty_state.grid_remove()
        self.preview_card.grid_remove()
        self.error_label.configure(text="⚠  " + message)
        self.error_card.grid()
        self.set_status("Terjadi masalah.")

    def _reset_middle(self) -> None:
        self.error_card.grid_remove()
        self.preview_card.grid_remove()
        self.empty_state.grid()

    def _show_toast(self, message: str, kind: str = "info", duration_ms: int = 3500) -> None:
        self.toasts.show(message, kind, duration_ms)

    def _open_settings(self) -> None:
        from ui.settings import SettingsDialog

        SettingsDialog(self, self.theme, self.cfg)

    def _pick_folder(self) -> None:
        from tkinter import filedialog

        chosen = filedialog.askdirectory(
            parent=self, title="Pilih folder simpan",
            initialdir=self.cfg.get("download_dir", str(Path.home() / "Downloads")),
        )
        if chosen:
            self.cfg["download_dir"] = chosen
            config.save({"download_dir": chosen})
            self.folder_label.configure(text=chosen)

    def _on_close(self) -> None:
        if self.ui_state == "downloading":
            self.downloader.cancel()
        self.destroy()

    # ------------------------------------------------------------- cek link

    def check_link(self) -> None:
        """Ambil info video di thread latar lalu tampilkan pratinjau."""
        url = self.url_entry.get().strip()
        if not url:
            self._show_toast("Tempel dulu tautan YouTube-nya.", "warning")
            return
        if not helpers.is_youtube_url(url):
            self.show_error(
                "Tautan tidak dikenali.\nGunakan tautan YouTube seperti:\n"
                "youtube.com/watch?v=...  •  youtu.be/...  •  youtube.com/shorts/..."
            )
            return
        if self.ui_state in ("fetching", "downloading"):
            return

        self.ui_state = "fetching"
        self._reset_middle()
        self.check_btn.configure(text="Memuat...", state="disabled")
        self.set_status("Mengambil info video...")
        threading.Thread(target=self._fetch_info_worker, args=(url,), daemon=True).start()

    def _fetch_info_worker(self, url: str) -> None:
        try:
            info = self.downloader.fetch_info(url)
            self.ui_queue.put(("info", info))
        except Exception as exc:  # noqa: BLE001
            logger.exception("fetch_info gagal")
            self.ui_queue.put(("fetch_error", exc))

    def _populate_preview(self, info: dict) -> None:
        """Isi kartu pratinjau dari data info."""
        from utils.helpers import ellipse, format_duration

        self.info = info
        self.empty_state.grid_remove()
        self.error_card.grid_remove()
        self.title_label.configure(text=ellipse(info["title"], 110))
        self.channel_label.configure(text=info["uploader"])
        self.res_label.configure(
            text=f"Kualitas maksimal: {info['heights'][0]}p" if info.get("heights") else "Kualitas tidak diketahui"
        )
        self.thumb_label.configure(image="", text="Memuat gambar...")
        self.duration_badge.configure(text=format_duration(info.get("duration")))
        self.preview_card.grid()

        quality_options = self._quality_options(info)
        self._refresh_quality_menu(quality_options, quality_options[0])
        self.set_status("Pratinjau siap — pilih mode & kualitas, lalu klik Download.")
        if info.get("thumbnail"):
            threading.Thread(
                target=self._fetch_thumbnail_worker, args=(info["thumbnail"],), daemon=True
            ).start()

    def _quality_options(self, info: dict) -> list[str]:
        """Susun daftar kualitas sesuai mode aktif dan resolusi tersedia."""
        if self._current_mode() == "audio":
            return list(formats.AUDIO_QUALITIES)
        available = [f"{h}p" for h in (info.get("heights") or []) if h >= 144]
        options = ["Terbaik"] + [
            q for q in formats.VIDEO_QUALITIES[1:] if q in available
        ]
        return options or ["Terbaik"]

    def _refresh_quality_menu(self, options: list[str], default: str) -> None:
        """Isi ulang dropdown kualitas."""
        self.quality_menu.configure(values=options)
        saved = self.cfg.get("quality")
        chosen = default if saved not in options else saved
        self.quality_menu.set(chosen)

    def _fetch_thumbnail_worker(self, url: str) -> None:
        """Unduh & potong thumbnail, kirim siap-pakai ke UI."""
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")

            # Potong ke tengah dengan rasio 16:9 lalu skala.
            target_ratio = THUMB_SIZE[0] / THUMB_SIZE[1]
            w, h = img.size
            if w / h > target_ratio:
                new_w = int(h * target_ratio)
                x0 = (w - new_w) // 2
                img = img.crop((x0, 0, x0 + new_w, h))
            else:
                new_h = int(w / target_ratio)
                y0 = (h - new_h) // 2
                img = img.crop((0, y0, w, y0 + new_h))
            img = img.resize(THUMB_SIZE, Image.LANCZOS)

            # Sudut membulat via mask alpha.
            mask = Image.new("L", THUMB_SIZE, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle([0, 0, THUMB_SIZE[0] - 1, THUMB_SIZE[1] - 1],
                                   radius=th.RADIUS_INPUT, fill=255)
            img.putalpha(mask)

            # Kirim PIL image mentah; CTkImage dibuat di thread UI (tkinter
            # tidak aman untuk thread).
            self.ui_queue.put(("thumb", img))
        except Exception:  # noqa: BLE001 - thumbnail gagal = tidak fatal
            logger.exception("Gagal memuat thumbnail")
            self.ui_queue.put(("thumb", None))

    # ------------------------------------------------------------- unduhan

    def _current_mode(self) -> str:
        return "audio" if self.mode_seg.get().startswith("Audio") else "video"

    def _on_mode_change(self, _value: str) -> None:
        mode = self._current_mode()
        options = self._quality_options(self.info) if self.info else (
            list(formats.AUDIO_QUALITIES) if mode == "audio" else ["Terbaik"]
        )
        self._refresh_quality_menu(options, options[0])

    def start_download(self) -> None:
        """Mulai unduhan di thread latar; UI berpindah ke panel progres."""
        if not self.info:
            self._show_toast("Cek link dulu sebelum mengunduh.", "warning")
            return
        if self.ui_state == "downloading":
            return
        if not self.ffmpeg_path:
            self._warn_ffmpeg_missing()
            return

        mode = self._current_mode()
        quality = self.quality_var.get()
        out_dir = self.cfg.get("download_dir", str(Path.home() / "Downloads"))
        url = self.info["url"]

        config.save({"mode": mode, "quality": quality})
        self.ui_state = "downloading"
        self.download_btn.grid_remove()
        self.progress_panel.grid()
        self.progress_panel.bar.set(0)
        self.progress_panel.percent_label.configure(text="0%")
        self.progress_panel.stage_label.configure(text="Bersiap...")
        self.progress_panel.detail_label.configure(text="-")
        self.set_status("Mengunduh...")

        threading.Thread(
            target=self._download_worker, args=(url, mode, quality, out_dir), daemon=True
        ).start()

    def _download_worker(self, url: str, mode: str, quality: str, out_dir: str) -> None:
        def on_progress(data: dict) -> None:
            self.ui_queue.put(("progress", data))

        def on_stage(stage: str) -> None:
            self.ui_queue.put(("stage", stage))

        def on_done(path: str) -> None:
            self.ui_queue.put(("done", path))

        def on_error(exc: Exception) -> None:
            self.ui_queue.put(("error", exc))

        self.downloader.download(
            url=url, mode=mode, quality=quality, out_dir=Path(out_dir),
            on_progress=on_progress, on_stage=on_stage,
            on_done=on_done, on_error=on_error,
        )

    def _cancel_download(self) -> None:
        """Tombol Batal: set flag pembatalan di downloader."""
        self.downloader.cancel()
        self.set_status("Membatalkan...")
        self.progress_panel.cancel_btn.configure(state="disabled", text="Membatalkan...")

    def _open_result_file(self) -> None:
        if self.result_path:
            helpers.open_file(self.result_path)

    def _open_result_folder(self) -> None:
        if self.result_path:
            helpers.open_folder(Path(self.result_path).parent, select=self.result_path)

    # --------------------------------------------------------- antrean UI

    def _poll_ui_queue(self) -> None:
        """Baca semua event dari thread pekerja dan perbarui UI (dipanggil via after)."""
        try:
            while True:
                kind, payload = self.ui_queue.get_nowait()
                handler = getattr(self, f"_on_{kind}", None)
                if handler:
                    handler(payload)
        except queue.Empty:
            pass
        except Exception:  # noqa: BLE001 - jangan biarkan polling mati
            logger.exception("Gagal memproses event UI")
        finally:
            self.after(80, self._poll_ui_queue)

    # handler event (payload tunggal)

    def _on_info(self, info: dict) -> None:
        self.check_btn.configure(text="Cek Link", state="normal")
        self.ui_state = "ready"
        if info.get("playlist"):
            self.show_error(
                f"Playlist terdeteksi: \"{info.get('title', 'Playlist')}\" "
                f"({info.get('count', '?')} video).\n"
                "Dukungan playlist akan hadir di pembaruan berikutnya. "
                "Untuk sekarang, gunakan tautan satu video."
            )
            self.ui_state = "idle"
            return
        if info.get("is_live"):
            self.show_error("Ini siaran langsung dan belum bisa diunduh.")
            self.ui_state = "idle"
            return
        self._populate_preview(info)

    def _on_fetch_error(self, exc: Exception) -> None:
        self.check_btn.configure(text="Cek Link", state="normal")
        self.ui_state = "idle"
        self.show_error(friendly_error(exc))
        self._show_toast("Gagal mengambil info video.", "error")

    def _on_thumb(self, pil_image) -> None:
        """Buat CTkImage dari hasil unduhan thumbnail (dijalankan di thread UI)."""
        if pil_image is None:
            return
        # Lepas referensi gambar lama dari label agar foto lama bisa dihapus
        # dengan aman saat CTkImage lama di-GC (hindari dangling pyimage).
        self.thumb_label.configure(image="")
        self.thumb_image = ctk.CTkImage(
            light_image=pil_image, dark_image=pil_image, size=THUMB_SIZE
        )
        self.thumb_label.configure(image=self.thumb_image, text="")

    def _on_progress(self, data: dict) -> None:
        if self.ui_state != "downloading":
            return
        self.progress_panel.update_progress(data)
        detail = self._progress_detail(data)
        if detail:
            self.progress_panel.set_detail(detail)

    @staticmethod
    def _progress_detail(data: dict) -> str:
        from utils.helpers import format_eta, format_size, format_speed

        parts = []
        if data.get("speed"):
            parts.append(f"Kecepatan: {format_speed(data['speed'])}")
        if data.get("eta") is not None:
            parts.append(f"Sisa: {format_eta(data['eta'])}")
        if data.get("downloaded") is not None and data.get("total"):
            parts.append(
                f"{format_size(data['downloaded'])} dari {format_size(data['total'])}"
            )
        return "    ".join(parts) if parts else "-"

    def _on_stage(self, stage: str) -> None:
        if self.ui_state == "downloading":
            self.progress_panel.set_stage(stage)
            self.set_status(stage + "...")

    def _on_done(self, path: str) -> None:
        self.result_path = path
        self.ui_state = "done"
        self.progress_panel.grid_remove()
        self.progress_panel.cancel_btn.configure(state="normal", text="Batal")
        self.success_panel.set_path(path)
        self.success_panel.grid()
        self.download_btn.grid()  # kembali tersedia jika ingin mengunduh ulang
        self.set_status("Unduhan selesai.")
        self._show_toast("Unduhan selesai ✓", "success")

    def _on_error(self, exc: Exception) -> None:
        self.progress_panel.grid_remove()
        self.progress_panel.cancel_btn.configure(state="normal", text="Batal")
        self.download_btn.grid()
        if isinstance(exc, DownloadCancelled) or "dibatalkan" in str(exc).lower():
            self.ui_state = "ready"
            self.set_status("Unduhan dibatalkan.")
            self._show_toast("Unduhan dibatalkan.", "warning")
            return
        self.ui_state = "idle"
        self.show_error(friendly_error(exc))
        self._show_toast("Unduhan gagal.", "error")
