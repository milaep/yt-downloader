"""Manajer antrean unduhan berurutan (fondasi fitur antrean fase 2).

Saat ini UI MVP menjalankan satu unduhan langsung lewat core.downloader.
Kelas di sini sudah siap dipakai bila UI antrean multi-item ditambahkan:
    q = DownloadQueue(downloader)
    q.add(QueueItem(url=..., mode=..., quality=..., out_dir=...))
    q.start(on_event=callback)   # callback menerima ("progress"/"done"/"error", item, data)
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

from core.downloader import Downloader


class ItemStatus(str, Enum):
    WAITING = "menunggu"
    DOWNLOADING = "mengunduh"
    DONE = "selesai"
    ERROR = "gagal"
    CANCELLED = "dibatalkan"


@dataclass
class QueueItem:
    """Satu entri unduhan di antrean."""

    url: str
    mode: str                      # "video" | "audio"
    quality: str                   # label kualitas
    out_dir: Path
    title: str = ""
    status: ItemStatus = ItemStatus.WAITING
    progress: float = 0.0          # 0..100
    error: str = ""
    path: str = ""                 # path file hasil saat selesai
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


class DownloadQueue:
    """Menjalankan antrean unduhan satu per satu di satu thread pekerja."""

    def __init__(self, downloader: Downloader) -> None:
        self.downloader = downloader
        self.items: list[QueueItem] = []
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._on_event: Callable[[str, QueueItem, dict], None] | None = None

    def add(self, item: QueueItem) -> QueueItem:
        """Tambah item ke antrean."""
        with self._lock:
            self.items.append(item)
        return item

    def remove(self, item_id: str) -> None:
        """Hapus item (kecuali sedang aktif diunduh)."""
        with self._lock:
            self.items = [i for i in self.items if i.id != item_id]

    def clear_finished(self) -> None:
        """Buang semua item yang sudah selesai/gagal/dibatalkan."""
        with self._lock:
            self.items = [
                i for i in self.items
                if i.status in (ItemStatus.WAITING, ItemStatus.DOWNLOADING)
            ]

    def start(self, on_event: Callable[[str, QueueItem, dict], None]) -> None:
        """Mulai memproses antrean secara berurutan di thread pekerja."""
        if self._worker and self._worker.is_alive():
            return
        self._on_event = on_event
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def cancel_current(self) -> None:
        """Batalkan unduhan yang sedang berjalan."""
        self.downloader.cancel()

    def _emit(self, kind: str, item: QueueItem, data: dict | None = None) -> None:
        if self._on_event:
            self._on_event(kind, item, data or {})

    def _run(self) -> None:
        while True:
            with self._lock:
                pending = next(
                    (i for i in self.items if i.status == ItemStatus.WAITING), None
                )
            if pending is None:
                break
            pending.status = ItemStatus.DOWNLOADING
            self._emit("started", pending)

            def on_progress(data: dict, _item=pending) -> None:
                _item.progress = float(data.get("percent") or 0.0)
                self._emit("progress", _item, data)

            def on_stage(stage: str, _item=pending) -> None:
                self._emit("stage", _item, {"stage": stage})

            def on_done(path: str, _item=pending) -> None:
                _item.status = ItemStatus.DONE
                _item.path = path
                _item.progress = 100.0
                self._emit("done", _item, {"path": path})

            def on_error(exc: Exception, _item=pending) -> None:
                from core.downloader import DownloadCancelled  # hindari impor melingkar

                if isinstance(exc, DownloadCancelled):
                    _item.status = ItemStatus.CANCELLED
                else:
                    _item.status = ItemStatus.ERROR
                _item.error = str(exc)
                self._emit("error", _item, {"exception": exc})

            self.downloader.download(
                url=pending.url,
                mode=pending.mode,
                quality=pending.quality,
                out_dir=pending.out_dir,
                on_progress=on_progress,
                on_stage=on_stage,
                on_done=on_done,
                on_error=on_error,
            )
