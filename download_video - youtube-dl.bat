@echo off
setlocal

:: === Set preferred tool (change to youtube-dl.exe if you prefer) ===
set "YTDL=yt-dlp.exe"

:: === Check if tool exists ===
if not exist "%~dp0%YTDL%" (
    echo.
    echo ❌ %YTDL% not found in this folder.
    echo Download from:
    echo https://github.com/yt-dlp/yt-dlp/releases/latest
    pause
    exit /b
)

:: === Ask for URL ===
set /p url=Enter YouTube URL: 
if "%url%"=="" (
    echo No URL entered. Exiting.
    pause
    exit /b
)

:: === Download video (best MP4 quality) ===
echo.
echo ⏬ Downloading video...
"%~dp0%YTDL%" -f bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best -o "out/%%(title)s.%%(ext)s" %url%

echo.
echo ✅ Done!
pause
