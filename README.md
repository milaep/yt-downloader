# YT Downloader

Aplikasi desktop Windows untuk download video dan audio dari YouTube. Dibuat menggunakan Python, CustomTkinter, dan yt-dlp.

## Features

- **Video Downloader** — Download video dalam format MP4 dengan pilihan resolusi hingga 2160p (tergantung ketersediaan video).
- **Audio Downloader** — Download audio dalam format MP3 (320, 192, atau 128 kbps) atau M4A tanpa konversi ulang.
- **Video Preview** — Cek judul, channel, thumbnail, dan durasi sebelum download.
- **Download Progress** — Menampilkan persentase, kecepatan download, ukuran file, dan estimasi waktu selesai.
- **Cancel Download** — Menghentikan proses download kapan saja.
- **Clipboard Support** — Tombol paste dan opsi untuk mendeteksi link YouTube dari clipboard secara otomatis.
- **Download Location** — Pilih folder penyimpanan sesuai kebutuhan.
- **Light & Dark Theme** — Pilihan tema terang dan gelap.
- **FFmpeg Integration** — Menggabungkan video dan audio serta menangani konversi format.

Pesan error ditampilkan dalam Bahasa Indonesia, termasuk ketika link tidak valid, video tidak tersedia, atau FFmpeg belum terpasang.

## Project Structure

```text
yt-downloader/
├── main.py
├── core/
│   ├── downloader.py
│   ├── formats.py
│   └── queue.py
├── ui/
│   ├── app.py
│   ├── components.py
│   ├── settings.py
│   └── theme.py
├── utils/
│   ├── config.py
│   ├── ffmpeg_check.py
│   └── helpers.py
├── bin/
│   └── ffmpeg.exe
├── requirements.txt
└── build.bat
```

## Requirements

Sebelum menjalankan aplikasi dari source code, pastikan sudah tersedia:

- Python 3.11 atau lebih baru
- FFmpeg dan FFprobe
- pip

### Installation

**1. Clone repository**

```bash
git clone <repository-url>
cd yt-downloader
```

**2. Siapkan FFmpeg**

Download FFmpeg untuk Windows dari salah satu sumber berikut:

- [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
- [BtbN FFmpeg Builds](https://github.com/BtbN/FFmpeg-Builds/releases)

Letakkan `ffmpeg.exe` dan `ffprobe.exe` di folder `bin/`.

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Jalankan aplikasi**

```bash
python main.py
```

Jika FFmpeg tidak ditemukan, aplikasi akan menampilkan pesan yang menjelaskan cara memasangnya.

## Build Windows Executable

Untuk membuat file `.exe`, jalankan:

```bat
build.bat
```

Hasil build akan berada di:

```text
dist/
└── YTDownloader.exe
```

Aplikasi menggunakan PyInstaller dengan mode `onefile`, sehingga Python tidak perlu diinstal pada komputer tujuan.

FFmpeg juga ikut disertakan dalam executable. Ukuran file akhir bergantung pada build FFmpeg yang digunakan.

## Application Data

File konfigurasi dan log disimpan di `%APPDATA%\YTDownloader`.

| File | Lokasi |
|---|---|
| Config | `%APPDATA%\YTDownloader\config.json` |
| Log | `%APPDATA%\YTDownloader\logs\app.log` |
| Download | Folder Downloads (default) atau folder pilihan pengguna |

## Testing Checklist

Beberapa hal yang perlu diuji:

- [ ] Link YouTube valid dan informasi video berhasil ditampilkan.
- [ ] Link tidak valid menampilkan pesan error.
- [ ] Video pribadi atau tidak tersedia ditangani dengan baik.
- [ ] Download MP4 menghasilkan video dengan audio.
- [ ] Download MP3 menghasilkan file yang bisa diputar beserta metadata.
- [ ] Download M4A berhasil tanpa konversi ulang.
- [ ] Progress download berjalan dan tombol Cancel berfungsi.
- [ ] Aplikasi tetap responsif selama proses download.
- [ ] Kondisi tanpa koneksi internet ditangani dengan baik.
- [ ] Folder penyimpanan bisa diubah dan tersimpan setelah aplikasi ditutup.
- [ ] Tombol Open File dan Open Folder berfungsi.
- [ ] Pergantian tema diterapkan ke seluruh tampilan.
- [ ] Notifikasi berhasil dan gagal muncul dengan benar.
- [ ] Aplikasi memberikan peringatan jika FFmpeg tidak ditemukan.
- [ ] File `.exe` hasil build bisa dijalankan di Windows tanpa Python.

## Planned Features

Beberapa fitur yang mungkin ditambahkan berikutnya:

- [ ] Download playlist dengan pilihan video.
- [ ] Antrean download untuk beberapa video.
- [ ] Riwayat download menggunakan SQLite.
- [ ] Download subtitle.
- [ ] Pengaturan format dan template nama file.

## Notes

Aplikasi ini dibuat untuk penggunaan pribadi dan pembelajaran. Pastikan kamu memiliki izin untuk mengunduh konten yang dipilih dan tetap mengikuti hak cipta serta ketentuan layanan YouTube.
