# YT Downloader

Aplikasi desktop Windows untuk mengunduh **video (MP4)** dan **audio (MP3)** dari YouTube
dengan tampilan modern — dibangun dengan **Python**, **yt-dlp** (sebagai library), dan
**CustomTkinter**.

![Tema gelap](https://imgur.com/a/MPutP5y) <!-- opsional: tambahkan tangkapan layar Anda -->

## ✨ Fitur

- **Cek Link** — pratinjau video (thumbnail, judul, channel, durasi) sebelum mengunduh.
- **Mode Video (MP4)** — resolusi Terbaik/2160p/1440p/1080p/720p/480p/360p (hanya menampilkan
  resolusi yang tersedia untuk video tersebut), video + audio digabot otomatis via FFmpeg.
- **Mode Audio (MP3)** — 320/192/128 kbps dengan sampul & metadata tersemat, plus opsi
  **M4A (asli)** tanpa konversi ulang.
- **Tombol Tempel** + tempel otomatis dari clipboard (opsional di Pengaturan).
- **Progres lengkap** — persentase, kecepatan, ETA, ukuran, dan tahap
  (Mengunduh → Menggabungkan → Mengonversi), serta tombol **Batal**.
- **Selesai ✓** — tombol **Buka File** dan **Buka Folder**.
- **Tema gelap/terang**, notifikasi toast, folder simpan tersimpan antar sesi.
- Pesan galat ramah dalam Bahasa Indonesia (link salah, video pribadi, dibatasi usia,
  diblokir wilayah, tanpa internet, siaran langsung, FFmpeg hilang).

## 📁 Struktur Proyek

```
yt-downloader/
├─ main.py              # titik masuk + logging
├─ core/
│  ├─ downloader.py     # pembungkus yt-dlp: fetch_info, download, progres, batal
│  ├─ formats.py        # format-string & opsi yt-dlp per mode/kualitas
│  └─ queue.py          # manajer antrean unduhan (fondasi fase 2)
├─ ui/
│  ├─ app.py            # jendela utama
│  ├─ components.py     # widget: kartu, badge, toast, panel progres, dll.
│  ├─ settings.py       # dialog pengaturan
│  └─ theme.py          # warna, font, spasi
├─ utils/
│  ├─ config.py         # pengaturan JSON di %APPDATA%/YTDownloader
│  ├─ ffmpeg_check.py   # deteksi FFmpeg
│  └─ helpers.py        # sanitasi nama file, format durasi/ukuran/kecepatan
├─ bin/ffmpeg.exe       # FFmpeg dibundel
├─ requirements.txt
└─ build.bat            # skrip build PyInstaller
```

## 🚀 Menjalankan dari Kode Sumber

1. Pasang Python 3.11+ (dari [python.org](https://www.python.org/downloads/), centang
   *Add to PATH* saat instalasi).
2. Siapkan FFmpeg:
   - unduh build Windows dari [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) atau
     [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds/releases),
   - salin `ffmpeg.exe` dan `ffprobe.exe` ke folder `bin/`.
3. Pasang dependensi dan jalankan:

   ```bat
   pip install -r requirements.txt
   python main.py
   ```

> Jika FFmpeg hilang, aplikasi tetap terbuka dan menampilkan dialog petunjuk pemasangan.

## 📦 Membangun .exe (PyInstaller)

Jalankan dari root proyek:

```bat
build.bat
```

Hasilnya `dist\YTDownloader.exe` — satu file, tanpa perlu Python terpasang di komputer lain.
FFmpeg di folder `bin\` ikut dibundel ke dalam exe (hasil akhir ±150–350 MB, tergantung build
FFmpeg yang dipakai). Karena format onefile, buka pertama bisa terasa lebih lambat beberapa
detik saat mengekstrak ke folder sementara.

## 🗂️ Lokasi Data Aplikasi

| Data             | Lokasi                                        |
|------------------|-----------------------------------------------|
| Pengaturan       | `%APPDATA%\YTDownloader\config.json`          |
| Log (debugging)  | `%APPDATA%\YTDownloader\logs\app.log`         |
| Folder simpan    | bawaan: folder `Downloads`, bisa diubah di UI |

## 📝 Daftar Uji Singkat (Checklist)

- [ ] **Cek link valid** — tempel `https://www.youtube.com/watch?v=...` → klik Cek Link →
      pratinjau muncul < ~3 detik, thumbnail tampil.
- [ ] **Link salah** — tempel teks acak → pesan "Tautan tidak dikenali" muncul.
- [ ] **Video pribadi/tidak tersedia** — muncul pesan ramah, bukan traceback.
- [ ] **Video MP4 1080p** — unduh, buka file: ada suara (video+audio tergabung).
- [ ] **MP3 320 kbps** — hasil `.mp3` bisa diputar, sampul & tag metadata tersemat.
- [ ] **M4A (asli)** — hasil `.m4a` tersimpan tanpa konversi ulang.
- [ ] **Progres & batal** — progres bar berjalan mulus; Batal menghentikan unduhan seketika.
- [ ] **UI responsif** — jendela tidak macet selama Cek Link/Download; bisa dipindah/di-resize.
- [ ] **Tanpa internet** — putuskan jaringan → pesan "Tidak ada koneksi internet".
- [ ] **Folder simpan** — pilih folder lain via Ubah, unduh lagi → file masuk folder itu;
      pengaturan tetap setelah aplikasi ditutup.
- [ ] **Buka File / Buka Folder** — keduanya membuka lokasi yang benar.
- [ ] **Tema** — ganti gelap/terang: semua kartu, tombol, dan teks ikut berubah konsisten.
- [ ] **Toast** — notifikasi sukses/gagal muncul di kanan bawah dan hilang sendiri.
- [ ] **FFmpeg hilang** — hapus sementara `bin\ffmpeg.exe` dan hapus dari PATH →
      dialog instruksi muncul saat aplikasi dibuka.
- [ ] **build.bat** — menghasilkan `dist\YTDownloader.exe` yang berjalan di Windows bersih.

## 🗺️ Peta Jalan (Fase 2)

Struktur kode sudah siap untuk fitur lanjutan berikut:

- [ ] Dukungan playlist (pilih semua / sebagian video) — `core/queue.py` sudah menyiapkan antrean.
- [ ] Antrean unduhan multi-item dengan baris progres masing-masing.
- [ ] Riwayat unduhan (SQLite) dengan pencarian.
- [ ] Opsi unduh subtitle.
- [ ] Halaman pengaturan lengkap (template nama file, tema sistem, dll.).

## ⚖️ Catatan Legal

Aplikasi ini hanya alat bantu. Harap hormati hak cipta dan Ketentuan Layanan YouTube —
unduh hanya konten yang Anda miliki izinnya.
