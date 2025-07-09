import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os
import json

YTDLP_EXECUTABLE = "yt-dlp.exe" if os.name == 'nt' else "yt-dlp"

class YTDLPDownloader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Downloader - yt-dlp GUI")
        self.geometry("550x480")
        self.resizable(False, False)

        self.url = tk.StringVar()
        self.output_dir = tk.StringVar(value=os.getcwd())
        self.format = tk.StringVar(value="best")

        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text="🎬 Video URL:").pack(pady=5)
        ttk.Entry(self, textvariable=self.url, width=70).pack()

        ttk.Label(self, text="📁 Save To:").pack(pady=5)
        path_frame = ttk.Frame(self)
        path_frame.pack()
        ttk.Entry(path_frame, textvariable=self.output_dir, width=50).pack(side=tk.LEFT)
        ttk.Button(path_frame, text="Browse", command=self.browse_folder).pack(side=tk.LEFT, padx=5)

        ttk.Label(self, text="📦 Format:").pack(pady=5)
        self.format_menu = ttk.Combobox(self, textvariable=self.format, state="readonly", width=30)
        self.format_menu['values'] = [
            "Best (auto)",
            "Best Video + Audio",
            "Audio Only (MP3)",
            "Audio Only (WAV)",
            "Manual Selection (see below)"
        ]
        self.format_menu.pack()

        ttk.Button(self, text="🔍 List Available Formats", command=self.list_formats).pack(pady=5)

        self.progress = ttk.Progressbar(self, length=400, mode='determinate')
        self.progress.pack(pady=5)

        ttk.Button(self, text="⬇ Download", command=self.start_download).pack(pady=5)

        self.output_box = tk.Text(self, height=15, bg="#111", fg="#0f0", wrap="word")
        self.output_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir.set(folder)

    def list_formats(self):
        video_url = self.url.get().strip()
        if not video_url:
            messagebox.showerror("Error", "Please enter a URL first.")
            return

        self.output_box.delete(1.0, tk.END)
        self.output_box.insert(tk.END, "Fetching available formats...\n\n")
        self.update()

        try:
            result = subprocess.run(
                [YTDLP_EXECUTABLE, "-F", video_url],
                capture_output=True, text=True
            )
            self.output_box.insert(tk.END, result.stdout)
        except Exception as e:
            self.output_box.insert(tk.END, f"Error: {e}")

    def start_download(self):
        threading.Thread(target=self.download, daemon=True).start()

    def download(self):
        video_url = self.url.get().strip()
        if not video_url:
            messagebox.showerror("Error", "Please enter a video URL.")
            return

        fmt = self.format.get()
        out_dir = self.output_dir.get()

        self.output_box.delete(1.0, tk.END)
        self.progress['value'] = 0
        self.output_box.insert(tk.END, "Starting download...\n\n")

        cmd = [YTDLP_EXECUTABLE, video_url, "-o", os.path.join(out_dir, "%(title)s.%(ext)s")]

        if fmt == "Audio Only (MP3)":
            cmd += ["-f", "bestaudio", "--extract-audio", "--audio-format", "mp3"]
        elif fmt == "Audio Only (WAV)":
            cmd += ["-f", "bestaudio", "--extract-audio", "--audio-format", "wav"]
        elif fmt == "Best Video + Audio":
            cmd += ["-f", "bv*+ba/b"]
        elif fmt == "Manual Selection (see below)":
            messagebox.showinfo("Use CLI", "Use the format code from above in terminal with yt-dlp -f code")
            return
        else:
            # Best (auto) — do NOT specify format; yt-dlp picks best combo
            pass

        cmd += ["--progress-template", "download:%(progress._percent_str)s"]  # For clean parsing

        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                self.output_box.insert(tk.END, line)
                self.output_box.see(tk.END)

                # Parse progress
                if "download:" in line and "%" in line:
                    percent = line.split("download:")[1].strip().replace("%", "")
                    try:
                        self.progress['value'] = float(percent)
                    except:
                        pass

            process.wait()
            if process.returncode == 0:
                self.output_box.insert(tk.END, "\n✅ Download completed.\n")
            else:
                self.output_box.insert(tk.END, "\n❌ Download failed. Check logs.\n")
        except FileNotFoundError:
            self.output_box.insert(tk.END, "\nError: yt-dlp.exe not found.")
            messagebox.showerror("Missing yt-dlp", "Place yt-dlp.exe in the same folder.")

if __name__ == "__main__":
    app = YTDLPDownloader()
    app.mainloop()
