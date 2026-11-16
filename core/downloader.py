"""Pembungkus yt-dlp: ambil info video, unduh dengan progres, dan pembatalan.

Kelas ini berjalan di thread pekerja (dipanggil dari UI lewat thread), dan
berkomunikasi lewat callback: on_progress(dict), on_stage(str), on_done(path),
on_error(exception). Semua callback dipanggil dari thread pekerja — UI wajib
meneruskannya ke queue miliknya sendiri.
"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Callable

import yt_dlp

from core import formats
from utils import helpers

logger = logging.getLogger(__name__)

# Interval minimum antar update progres (detik) agar UI tidak kewalahan.
PROGRESS_THROTTLE = 0.1

# Pemetaan nama post-processor -> teks tahap (Bahasa Indonesia).
PP_STAGES = {
    "Merger": "Menggabungkan",
    "ExtractAudio": "Mengonversi",
    "FFmpegExtractAudio": "Mengonversi",
    "Metadata": "Menambahkan metadata",
    "FFmpegMetadata": "Menambahkan metadata",
    "EmbedThumbnail": "Menyematkan sampul",
    "MoveFiles": "Menyelesaikan",
    "FixupM4a": "Memperbaiki file",
}


class DownloadCancelled(Exception):
    """Dilempar di dalam hook yt-dlp untuk membatalkan unduhan."""


def friendly_error(exc: Exception) -> str:
    """Ubah exception yt-dlp/network menjadi pesan ramah Bahasa Indonesia."""
    text = (str(exc) or "").lower()

    if isinstance(exc, DownloadCancelled):
        return "Unduhan dibatalkan."
    if any(x in text for x in ("unsupported url", "unable to extract", "is not a valid url")):
        return "Link tidak dikenali. Pastikan tautan YouTube valid, mis. youtube.com/watch?v=... atau youtu.be/..."
    if "private video" in text:
        return "Video ini bersifat pribadi sehingga tidak bisa diunduh."
    if "members-only" in text:
        return "Video ini khusus untuk member channel tersebut."
    if any(x in text for x in ("confirm your age", "age-restricted", "inappropriate")):
        return "Video ini dibatasi usia dan perlu masuk akun untuk diunduh."
    if any(x in text for x in ("not available in your country", "blocked it in your country", "geo")):
        return "Video ini diblokir/dibatasi di wilayah (negara) Anda."
    if any(x in text for x in ("video unavailable", "has been removed", "account associated")):
        return "Video tidak tersedia atau telah dihapus dari YouTube."
    if any(x in text for x in ("is live", "live event will begin", "upcoming")):
        return "Video ini siaran langsung/akan tayang, belum bisa diunduh."
    if any(x in text for x in ("premieres in", "premiere")):
        return "Video ini belum ditayangkan (masih dijadwal premiere)."
    if any(x in text for x in ("getaddrinfofailed", "connection", "timed out", "network", "urlopen error", "temporarily unreachable", "check your internet")):
        return "Tidak ada koneksi internet. Periksa jaringan Anda lalu coba lagi."
    if "ffmpeg" in text:
        return "FFmpeg tidak ditemukan/bermasalah. Periksa pengaturan FFmpeg aplikasi."
    if "http error 429" in text or "too many requests" in text:
        return "YouTube membatasi permintaan (terlalu sering). Coba lagi beberapa menit lagi."
    if "sign in to confirm" in text or "cookies" in text:
        return "YouTube meminta verifikasi. Coba lagi nanti atau gunakan koneksi berbeda."
    # Fallback: potong pesan teknis yang wajar.
    short = str(exc).strip().splitlines()[0][:180] if str(exc).strip() else "Terjadi kesalahan yang tidak diketahui."
    return f"Gagal: {short}"


def extract_info_safe(url: str) -> dict:
    """Ambil metadata video via yt-dlp (tanpa mengunduh).

    Return dict ringkas: id, title, uploader, duration, thumbnail, url,
    heights (daftar resolusi tersedia), is_live, playlist.
    Melempar exception asli bila gagal (UI menerjemahkan via friendly_error).
    """
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": False,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if info is None:
        raise RuntimeError("Tidak ada data yang diterima dari YouTube.")

    # Playlist terdeteksi (belum didukung di UI MVP).
    if info.get("_type") == "playlist" and info.get("entries"):
        entries = info.get("entries") or []
        first = entries[0] if entries else {}
        return {
            "playlist": True,
            "title": info.get("title") or "Playlist",
            "count": info.get("playlist_count") or len(entries),
            "first_url": (first.get("webpage_url") or first.get("url") or url),
        }

    heights = sorted(
        {
            int(f["height"])
            for f in (info.get("formats") or [])
            if f.get("height") and f.get("vcodec", "none") != "none"
        },
        reverse=True,
    )

    return {
        "playlist": False,
        "id": info.get("id"),
        "url": info.get("webpage_url") or info.get("original_url") or url,
        "title": info.get("title") or "Tanpa judul",
        "uploader": info.get("uploader") or info.get("channel") or "Tanpa channel",
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "is_live": bool(info.get("is_live")),
        "heights": heights,
    }


class Downloader:
    """Menjalankan satu unduhan dengan dukungan progres, tahap, dan batal."""

    def __init__(self, ffmpeg_path: str | None = None) -> None:
        self.ffmpeg_path = ffmpeg_path
        self._cancel = threading.Event()
        self._last_push = 0.0

    # ------------------------------------------------------------------ API

    def fetch_info(self, url: str) -> dict:
        """Ambil metadata video (panggil dari thread pekerja)."""
        return extract_info_safe(url)

    def cancel(self) -> None:
        """Minta pembatalan unduhan yang sedang berjalan (aman dipanggil dari UI)."""
        self._cancel.set()

    def download(
        self,
        url: str,
        mode: str,
        quality: str,
        out_dir: Path,
        on_progress: Callable[[dict], None] | None = None,
        on_stage: Callable[[str], None] | None = None,
        on_done: Callable[[str], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Unduh satu video/audio (blokir sampai selesai — jalankan di thread).

        Semua callback opsional dan dipanggil dari thread yang sama
        (thread pemanggil, yaitu thread pekerja UI).
        """
        self._cancel.clear()
        self._last_push = 0.0

        # Info dulu untuk judul -> nama file bersih & unik.
        try:
            info = extract_info_safe(url)
            if info.get("playlist"):
                raise RuntimeError(
                    "Tautan adalah playlist. Buka video per video terlebih dahulu."
                )
            if info.get("is_live"):
                raise RuntimeError("Siaran langsung belum bisa diunduh.")
        except Exception as exc:  # noqa: BLE001 - diteruskan ke UI
            if on_error:
                on_error(exc)
            return

        out_name = helpers.sanitize_filename(info["title"])
        final_ext = formats.final_extension(mode, quality)
        expected_path = helpers.unique_path(Path(out_dir) / f"{out_name}.{final_ext}")
        # unique_path membandingkan path berekstensi; cukup dipakai sebagai nama target.
        out_name = expected_path.stem

        opts = formats.build_options(
            mode=mode,
            quality=quality,
            out_dir=Path(out_dir),
            out_name=out_name,
            ffmpeg_path=self.ffmpeg_path,
            progress_hooks=[self._make_progress_hook(on_progress, on_stage)],
            postprocessor_hooks=[self._make_pp_hook(on_stage)],
        )

        try:
            logger.info("Mulai unduhan: %s (%s, %s)", info["title"], mode, quality)
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except DownloadCancelled:
            logger.info("Unduhan dibatalkan pengguna.")
            if on_error:
                on_error(DownloadCancelled("Unduhan dibatalkan."))
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unduhan gagal.")
            if on_error:
                on_error(exc)
            return

        # Tentukan file hasil akhir.
        path = self._find_final_file(Path(out_dir), out_name, final_ext)
        logger.info("Unduhan selesai: %s", path)
        if on_done:
            on_done(str(path))

    # ------------------------------------------------------------- internal

    def _push(self, on_progress: Callable[[dict], None] | None, data: dict, force: bool = False) -> None:
        """Kirim event progres ke callback, dibatasi ~10x/detik."""
        if on_progress is None:
            return
        now = time.monotonic()
        if not force and (now - self._last_push) < PROGRESS_THROTTLE:
            return
        self._last_push = now
        on_progress(data)

    def _make_progress_hook(
        self,
        on_progress: Callable[[dict], None] | None,
        on_stage: Callable[[str], None] | None,
    ) -> Callable[[dict], None]:
        def hook(d: dict) -> None:
            if self._cancel.is_set():
                raise DownloadCancelled()
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                percent = (downloaded / total * 100.0) if total else 0.0
                self._push(
                    on_progress,
                    {
                        "stage": "Mengunduh",
                        "percent": percent,
                        "downloaded": downloaded,
                        "total": total,
                        "speed": d.get("speed"),
                        "eta": d.get("eta"),
                        "filename": d.get("filename"),
                    },
                )
            elif status == "finished":
                if on_stage:
                    on_stage("Menggabungkan")
                self._push(
                    on_progress,
                    {"stage": "Menggabungkan", "percent": 100.0, "downloaded": None,
                     "total": None, "speed": None, "eta": None},
                    force=True,
                )
        return hook

    def _make_pp_hook(self, on_stage: Callable[[str], None] | None) -> Callable[[dict], None]:
        def hook(d: dict) -> None:
            if self._cancel.is_set():
                raise DownloadCancelled()
            if d.get("status") == "started" and on_stage:
                name = d.get("postprocessor") or ""
                stage = PP_STAGES.get(name, name or "Memproses")
                on_stage(stage)
        return hook

    @staticmethod
    def _find_final_file(out_dir: Path, stem: str, ext: str) -> Path:
        """Cari file hasil akhir; fallback ke file terbaru dengan stem serupa."""
        out_dir = Path(out_dir)
        candidate = out_dir / f"{stem}.{ext}"
        if candidate.exists():
            return candidate
        for ext_try in (ext, "mp4", "mp3", "m4a", "webm", "mkv"):
            matches = sorted(out_dir.glob(f"{stem}*.{ext_try}"),
                             key=lambda p: p.stat().st_mtime, reverse=True)
            if matches:
                return matches[0]
        # Terakhir: ambil file termuda di folder (kasus jarang).
        all_files = sorted(out_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        return all_files[0] if all_files else candidate
