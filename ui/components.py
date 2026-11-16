"""Widget UI yang dapat dipakai ulang: kartu, badge, toast, panel progres, dll."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ui import theme as th


# --------------------------------------------------------------------- cursor

def _set_cursor(widget, name: str) -> None:
    """Atur kursor lewat panggilan tk mentah (kompatibel dengan semua widget CTk)."""
    try:
        top = widget.winfo_toplevel()
        top.tk.call(str(top), "configure", "-cursor", name)
    except Exception:
        pass


def hand_cursor(widget) -> None:
    """Kursor berubah jadi tangan saat mouse berada di atas widget."""
    def on_enter(_event) -> None:
        _set_cursor(widget, "hand2")

    def on_leave(event) -> None:
        # Abaikan Leave yang disebabkan pindah ke widget anak.
        w, h = widget.winfo_width(), widget.winfo_height()
        if 0 <= event.x < w and 0 <= event.y < h:
            return
        _set_cursor(widget, "arrow")

    widget.bind("<Enter>", on_enter, add="+")
    widget.bind("<Leave>", on_leave, add="+")


# ----------------------------------------------------------------------- card

class Card(ctk.CTkFrame):
    """Kartu permukaan membulat dengan border halus."""

    def __init__(self, master, colors: dict[str, str], **kw) -> None:
        super().__init__(
            master,
            corner_radius=th.RADIUS_CARD,
            fg_color=colors["surface"],
            border_width=1,
            border_color=colors["border"],
            **kw,
        )
        self._colors = colors

    def apply_colors(self, colors: dict[str, str]) -> None:
        """Perbarui warna saat tema berganti."""
        self._colors = colors
        self.configure(fg_color=colors["surface"], border_color=colors["border"])


def section_label(master, colors: dict[str, str], text: str) -> ctk.CTkLabel:
    """Label seksi kecil bergaya semibold warna sekunder."""
    label = ctk.CTkLabel(
        master, text=text.upper(), font=th.F_SECTION,
        text_color=colors["text_secondary"], anchor="w",
    )
    return label


def secondary_button(master, colors: dict[str, str], text: str, command: Callable, width: int = 110) -> ctk.CTkButton:
    """Tombol sekunder (permukaan naik, tanpa warna aksen)."""
    btn = ctk.CTkButton(
        master, text=text, command=command, width=width, height=38,
        corner_radius=th.RADIUS_BUTTON, font=th.F_BODY_BOLD,
        fg_color=colors["elevated"], hover_color=colors["border"],
        text_color=colors["text"], border_width=1, border_color=colors["border"],
    )
    hand_cursor(btn)
    return btn


def danger_button(master, colors: dict[str, str], text: str, command: Callable, width: int = 96) -> ctk.CTkButton:
    """Tombol merah untuk aksi destruktif seperti Batal."""
    btn = ctk.CTkButton(
        master, text=text, command=command, width=width, height=34,
        corner_radius=th.RADIUS_BUTTON, font=th.F_CAPTION_BOLD,
        fg_color=colors["error"], hover_color=colors["error"],
        text_color="#FFFFFF",
    )
    hand_cursor(btn)
    return btn


# ---------------------------------------------------------------------- badge

class Badge(ctk.CTkLabel):
    """Badge kecil (mis. durasi) dengan latar setengah gelap."""

    def __init__(self, master, colors: dict[str, str], text: str, bg: str) -> None:
        super().__init__(
            master, text=text, font=th.F_CAPTION_BOLD,
            fg_color=bg, text_color="#FFFFFF", corner_radius=8, height=24,
            padx=10,
        )


# ---------------------------------------------------------------------- toast

class ToastManager:
    """Notifikasi non-blokir di pojok kanan bawah jendela."""

    def __init__(self, root, theme: th.Theme) -> None:
        self.root = root
        self.theme = theme
        self._current: ctk.CTkFrame | None = None
        self._anim_job = None

    def show(self, message: str, kind: str = "info", duration_ms: int = 3500) -> None:
        """Tampilkan toast; kind: info | success | error | warning."""
        colors = self.theme.colors()
        bg = {
            "success": colors["success"],
            "error": colors["error"],
            "warning": colors["warning"],
            "info": colors["elevated"],
        }[kind]
        fg_text = "#FFFFFF" if kind != "info" else colors["text"]
        icon = {"success": "✓  ", "error": "✕  ", "warning": "⚠  ", "info": "ℹ  "}[kind]

        self._dismiss()
        toast = ctk.CTkFrame(
            self.root, corner_radius=12, fg_color=bg,
            border_width=1, border_color=colors["border"],
        )
        label = ctk.CTkLabel(
            toast, text=icon + message, font=th.F_BODY_BOLD,
            text_color=fg_text, justify="left", wraplength=320,
        )
        label.pack(padx=16, pady=12)
        toast.place(relx=1.0, rely=1.0, anchor="se", x=-24, y=-48 + 24)  # mulai agak turun
        self._current = toast
        self._animate(toast, start_y=-48 + 24, end_y=-48)

        self.root.after(duration_ms, self._dismiss)

    def _animate(self, toast: ctk.CTkFrame, start_y: int, end_y: int) -> None:
        """Geser toast naik dengan mulus."""
        steps, current = 8, [start_y]
        step_size = max(1, (start_y - end_y) // steps)

        def step() -> None:
            if self._current is not toast or not toast.winfo_exists():
                return
            current[0] = max(end_y, current[0] - step_size)
            toast.place_configure(y=current[0])
            if current[0] > end_y:
                self._anim_job = toast.after(16, step)

        step()

    def _dismiss(self) -> None:
        if self._current and self._current.winfo_exists():
            self._current.destroy()
        self._current = None


# --------------------------------------------------------------- progress bar

class ProgressPanel(ctk.CTkFrame):
    """Panel progres unduhan: bar, persen, tahap, kecepatan, ETA, tombol Batal."""

    def __init__(self, master, colors: dict[str, str], on_cancel: Callable[[], None]) -> None:
        super().__init__(master, corner_radius=th.RADIUS_CARD,
                         fg_color=colors["surface"], border_width=1,
                         border_color=colors["border"])
        self._colors = colors

        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 6))
        top.grid_columnconfigure(1, weight=1)

        self.percent_label = ctk.CTkLabel(top, text="0%", font=th.F_BODY_BOLD,
                                          text_color=colors["primary"])
        self.percent_label.grid(row=0, column=0, sticky="w")

        self.stage_label = ctk.CTkLabel(top, text="Bersiap...", font=th.F_CAPTION,
                                        text_color=colors["text_secondary"], anchor="e")
        self.stage_label.grid(row=0, column=1, sticky="e")

        self.bar = ctk.CTkProgressBar(
            self, height=10, corner_radius=5,
            fg_color=colors["elevated"], progress_color=colors["primary"],
        )
        self.bar.grid(row=1, column=0, sticky="ew", padx=20, pady=4)
        self.bar.set(0)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=20, pady=(2, 12))
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_columnconfigure(3, weight=0)

        self.detail_label = ctk.CTkLabel(bottom, text="-", font=th.F_CAPTION,
                                         text_color=colors["text_secondary"], anchor="w")
        self.detail_label.grid(row=0, column=0, sticky="w")

        self.cancel_btn = danger_button(bottom, colors, "Batal", on_cancel)
        self.cancel_btn.grid(row=0, column=3, sticky="e")

    def update_progress(self, data: dict) -> None:
        """Perbarui bar dan angka-angka dari event progres."""
        percent = data.get("percent") or 0.0
        self.bar.set(max(0.0, min(1.0, percent / 100.0)))
        self.percent_label.configure(text=f"{percent:.1f}%".replace(".", ","))

    def set_stage(self, stage: str) -> None:
        """Perbarui teks tahap (Mengunduh / Menggabungkan / Mengonversi)."""
        self.stage_label.configure(text=stage)
        if stage != "Mengunduh":
            self.bar.set(1.0)
            self.percent_label.configure(text="100%")
            self.detail_label.configure(text=f"{stage}... sedang diproses")

    def set_detail(self, detail: str) -> None:
        """Perbarui baris detail (kecepatan, ETA, ukuran)."""
        self.detail_label.configure(text=detail)

    def apply_colors(self, colors: dict[str, str]) -> None:
        """Perbarui warna saat tema berganti."""
        self._colors = colors
        self.configure(fg_color=colors["surface"], border_color=colors["border"])
        self.percent_label.configure(text_color=colors["primary"])
        self.stage_label.configure(text_color=colors["text_secondary"])
        self.bar.configure(fg_color=colors["elevated"], progress_color=colors["primary"])
        self.detail_label.configure(text_color=colors["text_secondary"])
        self.cancel_btn.configure(fg_color=colors["error"], hover_color=colors["error"])


class SuccessPanel(ctk.CTkFrame):
    """Panel keberhasilan: 'Selesai ✓' plus tombol Buka File / Buka Folder."""

    def __init__(self, master, colors: dict[str, str],
                 on_open_file: Callable[[], None], on_open_folder: Callable[[], None]) -> None:
        super().__init__(master, corner_radius=th.RADIUS_CARD,
                         fg_color=colors["surface"], border_width=1,
                         border_color=colors["border"])
        self._colors = colors
        self.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self, text="Selesai ✓", font=th.F_BUTTON_BIG, text_color=colors["success"],
        )
        self.title_label.grid(row=0, column=0, columnspan=2, pady=(16, 2), padx=20)

        self.path_label = ctk.CTkLabel(
            self, text="", font=th.F_CAPTION, text_color=colors["text_secondary"],
            wraplength=380, justify="center",
        )
        self.path_label.grid(row=1, column=0, columnspan=2, pady=(0, 10), padx=20)

        self.open_file_btn = ctk.CTkButton(
            self, text="Buka File", command=on_open_file, width=120, height=38,
            corner_radius=th.RADIUS_BUTTON, font=th.F_BODY_BOLD,
            fg_color=colors["primary"], hover_color=colors["primary_hover"],
            text_color="#FFFFFF",
        )
        hand_cursor(self.open_file_btn)
        self.open_file_btn.grid(row=2, column=0, pady=(0, 16), padx=(20, 6), sticky="e")

        self.open_folder_btn = secondary_button(self, colors, "Buka Folder", on_open_folder, width=120)
        self.open_folder_btn.grid(row=2, column=1, pady=(0, 16), padx=(6, 20), sticky="w")

    def set_path(self, path: str) -> None:
        """Tampilkan path file hasil (dipendekkan agar muat)."""
        from utils.helpers import ellipse

        self.path_label.configure(text=ellipse(path.replace("\\\\", "\\"), 80))

    def apply_colors(self, colors: dict[str, str]) -> None:
        """Perbarui warna saat tema berganti."""
        self._colors = colors
        self.configure(fg_color=colors["surface"], border_color=colors["border"])
        self.title_label.configure(text_color=colors["success"])
        self.path_label.configure(text_color=colors["text_secondary"])
        self.open_file_btn.configure(fg_color=colors["primary"], hover_color=colors["primary_hover"])
        self.open_folder_btn.configure(
            fg_color=colors["elevated"], hover_color=colors["border"], text_color=colors["text"],
            border_color=colors["border"],
        )


class EmptyState(ctk.CTkFrame):
    """Keadaan kosong: ilustrasi emoji + petunjuk singkat."""

    def __init__(self, master, colors: dict[str, str]) -> None:
        super().__init__(master, corner_radius=th.RADIUS_CARD,
                         fg_color=colors["surface"], border_width=1,
                         border_color=colors["border"])
        self._colors = colors
        self.grid_columnconfigure(0, weight=1)

        self.icon_label = ctk.CTkLabel(self, text="🎬", font=("Segoe UI Emoji", 34))
        self.icon_label.grid(row=0, column=0, pady=(18, 4))

        self.title_label = ctk.CTkLabel(self, text="Belum ada video", font=th.F_SECTION,
                                        text_color=colors["text"])
        self.title_label.grid(row=1, column=0)

        self.hint_label = ctk.CTkLabel(
            self, text="Tempel tautan YouTube di atas, lalu klik \u201cCek Link\u201d\nuntuk melihat pratinjau video.",
            font=th.F_CAPTION, text_color=colors["text_secondary"], justify="center",
        )
        self.hint_label.grid(row=2, column=0, pady=(4, 18))

    def apply_colors(self, colors: dict[str, str]) -> None:
        """Perbarui warna saat tema berganti."""
        self._colors = colors
        self.configure(fg_color=colors["surface"], border_color=colors["border"])
        self.title_label.configure(text_color=colors["text"])
        self.hint_label.configure(text_color=colors["text_secondary"])
