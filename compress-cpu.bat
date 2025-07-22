@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title CPU Video Compressor - Basic & Safe

REM Create output folder
if not exist "Compress files" mkdir "Compress files"

REM Loop through all dragged files
for %%F in (%*) do (
    if exist "%%~F" (
        set "filename=%%~nF"
        set "ext=%%~xF"

        REM Check if filename ends with _compressed (skip)
        echo %%~nF | findstr /i "_compressed$" >nul
        if !errorlevel! equ 0 (
            echo ⏭️ Skipping already compressed: %%~nxF
        ) else (
            REM Get video height via ffprobe
            for /f "delims=" %%H in ('ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "%%~F"') do (
                set "height=%%H"
            )

            REM Decide bitrate by height
            if !height! LSS 1440 (
                set "bitrate=15000k"
                echo 🔧 Compressing 720p/1080p: %%~nxF at 15 Mbps
            ) else (
                set "bitrate=30000k"
                echo 🔧 Compressing 4K+: %%~nxF at 30 Mbps
            )

            set "outfile=Compress files\%%~nF_compressed.mp4"

            REM Run ffmpeg compression (CPU libx264)
            ffmpeg -i "%%~F" -c:v libx264 -preset slow -b:v !bitrate! -c:a copy "!outfile!"

            echo ✅ Done: !outfile!
        )
    ) else (
        echo ❌ File not found: %%~F
    )
)

echo.
echo ✅ All done.
pause
