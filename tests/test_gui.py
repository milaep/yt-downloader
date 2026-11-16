r"""Uji end-to-end GUI: cek link, pratinjau, unduh, selesai, ganti tema.

Jalankan: python tests/test_gui.py
Tangkapan layar disimpan di docs/.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.app import App  # noqa: E402

URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
DOCS = Path(__file__).resolve().parent.parent / "docs"


def shot(app: App, name: str) -> None:
    app.update()
    app.update_idletasks()
    u = ctypes.windll.user32
    hwnd = u.GetParent(app.winfo_id()) or int(app.winfo_id())
    r = ctypes.wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    from PIL import ImageGrab

    ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom)).save(DOCS / name)
    print("shot:", name, "| ui_state =", app.ui_state)


def wait_state(app: App, state: str, timeout: float = 90.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.update()
        if app.ui_state == state:
            return True
        time.sleep(0.1)
    return False


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    app = App()
    app.geometry("880x700+60+60")
    app.update()
    shot(app, "gui_1_empty_dark.png")

    # 1) Cek link
    app.url_entry.insert(0, URL)
    app.check_link()
    if not wait_state(app, "ready", 60):
        print("GAGAL: pratinjau tidak siap")
        shot(app, "gui_fail.png")
        app.destroy()
        sys.exit(1)
    # tunggu thumbnail
    for _ in range(80):
        app.update()
        if app.thumb_image is not None:
            break
        time.sleep(0.1)
    time.sleep(0.5)
    app.update()
    shot(app, "gui_2_preview_dark.png")

    # 2) Pilih audio & cek daftar kualitas
    app.mode_seg.set("Audio (MP3)")
    app._on_mode_change("Audio (MP3)")
    app.update()
    print("kualitas audio:", app.quality_var.get(), app.quality_menu.cget("values"))

    # 3) Unduh MP3
    app.start_download()
    if not wait_state(app, "done", 240):
        print("GAGAL: unduhan tidak selesai")
        shot(app, "gui_fail_download.png")
        app.destroy()
        sys.exit(1)
    time.sleep(0.5)
    app.update()
    shot(app, "gui_3_done_dark.png")
    print("hasil:", app.result_path)

    # 4) Ganti tema terang
    app._toggle_theme()
    time.sleep(0.4)
    app.update()
    shot(app, "gui_4_light.png")

    # 5) Cek link lagi di mode terang (mode video)
    app.mode_seg.set("Video (MP4)")
    app._on_mode_change("Video (MP4)")
    app.url_entry.delete(0, "end")
    app.url_entry.insert(0, URL)
    app.check_link()
    wait_state(app, "ready", 60)
    for _ in range(80):
        app.update()
        if app.thumb_image is not None:
            break
        time.sleep(0.1)
    time.sleep(0.5)
    app.update()
    shot(app, "gui_5_preview_light.png")

    app.destroy()
    print("SELESAI: semua tahap GUI lulus")


if __name__ == "__main__":
    main()
