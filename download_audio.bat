set /p url=Enter video url: 
yt-dlp -o "out/%%(title)s.%%(ext)s" %url%  -f "bestaudio" --extract-audio