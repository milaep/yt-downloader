"""Membangun format-string & opsi yt-dlp sesuai mode (video/audio) dan kualitas."""
from __future__ import annotations

from pathlib import Path

# Label kualitas yang ditampilkan di UI.
VIDEO_QUALITIES = ["Terbaik", "2160p", "1440p", "1080p", "720p", "480p", "360p"]
AUDIO_QUALITIES = ["320 kbps", "192 kbps", "128 kbps", "M4A (asli)"]

# Kualitas video bawaan jika yang tersimpan tidak tersedia untuk video ini.
DEFAULT_VIDEO_QUALITY = "Terbaik"
DEFAULT_AUDIO_QUALITY = "320 kbps"

# Ekstensi file akhir per mode/kualitas (untuk menentukan hasil selesai).
_FINAL_EXT_VIDEO = "mp4"


def is_m4a(quality: str) -> bool:
    """True bila kualitas audio adalah opsi M4A asli (tanpa konversi ulang)."""
    return quality.startswith("M4A")


def video_format_string(quality: str) -> str:
    """Format-string yt-dlp untuk mode video (MP4 dengan suara)."""
    if quality == "Terbaik":
        return (
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]"
            "/bestvideo+bestaudio"
            "/best[ext=mp4]/best"
        )
    height = quality.replace("p", "")
    return (
        f"bestvideo[ext=mp4][height<={height}]+bestaudio[ext=m4a]"
        f"/bestvideo[height<={height}]+bestaudio"
        f"/best[height<={height}]/best"
    )


def audio_format_string(quality: str) -> str:
    """Format-string yt-dlp untuk mode audio."""
    if is_m4a(quality):
        # Ambil stream m4a asli agar tidak di-encode ulang.
        return "bestaudio[ext=m4a]/bestaudio/best"
    return "bestaudio/best"


def audio_postprocessors(quality: str) -> list[dict]:
    """Post-processor untuk mode audio (konversi MP3/M4A + metadata + thumbnail)."""
    pps: list[dict] = []
    if is_m4a(quality):
        # m4a asli: cukup tulis metadata; codec sama, tanpa encode ulang.
        pps.append({"key": "FFmpegExtractAudio", "preferredcodec": "m4a", "preferredquality": "0"})
    else:
        pps.append(
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality.split()[0],  # "320", "192", "128"
            }
        )
        # MP3: sisipkan sampul album + tag ID3.
        pps.append({"key": "FFmpegMetadata"})
        pps.append({"key": "EmbedThumbnail"})
    return pps


def final_extension(mode: str, quality: str) -> str:
    """Ekstensi file hasil akhir yang diharapkan setelah post-processing."""
    if mode == "audio":
        return "m4a" if is_m4a(quality) else "mp3"
    return _FINAL_EXT_VIDEO


def build_options(
    mode: str,
    quality: str,
    out_dir: Path,
    out_name: str,
    ffmpeg_path: str | None,
    progress_hooks: list,
    postprocessor_hooks: list,
) -> dict:
    """Susun dict opsi yt-dlp lengkap untuk satu unduhan."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    opts: dict = {
        "outtmpl": {"default": str(out_dir / f"{out_name}.%(ext)s")},
        "noplaylist": True,
        "overwrites": False,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 3,
        "fragment_retries": 3,
        "socket_timeout": 30,
        "concurrent_fragment_downloads": 4,
        "progress_hooks": progress_hooks,
        "postprocessor_hooks": postprocessor_hooks,
        # Jangan tanya apa pun, langsung pilih pilihan default.
        "nopart": False,
        "restrictfilenames": False,
        "windowsfilenames": True,  # sanitasi karakter terlarang Windows
    }

    if ffmpeg_path:
        opts["ffmpeg_location"] = ffmpeg_path

    if mode == "video":
        opts["format"] = video_format_string(quality)
        opts["merge_output_format"] = "mp4"
    else:
        opts["format"] = audio_format_string(quality)
        pps = audio_postprocessors(quality)
        if any(pp.get("key") == "EmbedThumbnail" for pp in pps):
            opts["writethumbnail"] = True
        opts["postprocessors"] = pps

    return opts
