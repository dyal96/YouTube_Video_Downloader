@echo off
title Video Downloader (yt-dlp)
color 0A
echo ================================
echo     Simple Video Downloader    
echo ================================
echo.

set /p url=Enter video URL: 
if "%url%"=="" goto :eof

mkdir "Downloads" 2>nul
yt-dlp.exe -o "Downloads/%%(title)s.%%(ext)s" %url%

echo.
echo Download complete. Press any key to exit.
pause >nul
