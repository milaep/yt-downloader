@echo off
rem ============================================================
rem  Membangun YTDownloader.exe dengan PyInstaller (onefile)
rem  Jalankan dari root proyek: build.bat
rem ============================================================
setlocal

if not exist bin\ffmpeg.exe (
    echo [PERINGATAN] bin\ffmpeg.exe tidak ditemukan.
    echo Unduh FFmpeg lalu salin ffmpeg.exe dan ffprobe.exe ke folder bin\ terlebih dahulu.
    echo Build tetap dilanjutkan, tetapi aplikasi akan meminta FFmpeg saat berjalan.
)

python -m pip install --upgrade pyinstaller
python -m pip install -r requirements.txt

python -m PyInstaller ^
    --noconsole ^
    --onefile ^
    --name YTDownloader ^
    --add-binary "bin\ffmpeg.exe;bin" ^
    --add-binary "bin\ffprobe.exe;bin" ^
    --hidden-import customtkinter ^
    --collect-all customtkinter ^
    --collect-submodules yt_dlp ^
    main.py

if errorlevel 1 (
    echo.
    echo [GAGAL] Build PyInstaller tidak berhasil. Periksa pesan di atas.
    exit /b 1
)

echo.
echo [SUCCES] YTDownloader.exe tersedia di folder dist\
endlocal
