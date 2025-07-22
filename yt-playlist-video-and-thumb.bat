@echo off
title Video Downloader (yt-dlp)
color 0A
echo ================================
echo     Simple Video Downloader    
echo ================================
echo.

:: Get URL from clipboard
for /f "delims=" %%a in ('powershell -noprofile Get-Clipboard') do set "url=%%a"

if "%url%"=="" (
    echo ❌ Clipboard is empty or invalid.
    pause
    exit /b
)

echo 📋 URL from clipboard: %url%

:: Create download folder
mkdir "Downloads" 2>nul

:: Download video and thumbnail using yt-dlp
echo.
echo 🔽 Downloading video...
yt-dlp.exe ^
  -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" ^
  --merge-output-format mp4 ^
  --write-thumbnail ^
  --convert-thumbnails jpg ^
  -o "Downloads/%%(title)s.%%(ext)s" ^
  "%url%"

echo.
echo ✅ Download complete.
timeout /t 5
exit
