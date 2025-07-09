import os
import re
import sys
import json
import time
import shutil
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from urllib.request import urlopen
from io import BytesIO

try:
    from PIL import Image, ImageTk
except ImportError:
    messagebox.showerror("Missing Dependency", "Please install Pillow:\n\npip install pillow")
    sys.exit(1)

# --- Constants ---
YTDLP_EXECUTABLE = "yt-dlp.exe" if os.name == 'nt' else "yt-dlp"
FFMPEG_EXECUTABLE = "ffmpeg.exe" if os.name == 'nt' else "ffmpeg"
INVALID_FN_CHARS = r'<>:"/\|?*'
LOGS_DIR = "logs"

# --- Helper Functions ---
def sanitize_filename(name):
    """Removes invalid characters from a filename."""
    return re.sub(f"[{re.escape(INVALID_FN_CHARS)}]", "", name)

def ensure_logs_dir():
    """Creates the logs directory if it doesn't exist."""
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)

def save_log(log_text):
    """Saves the download log to a timestamped file."""
    ensure_logs_dir()
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(LOGS_DIR, f"log-{timestamp}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(log_text)
    return path

# --- Main Application ---
class YTDLPDownloaderGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("🎬 YouTube Downloader Pro")
        self.geometry("800x750")
        self.resizable(False, False)
        self.configure(bg="#1e1e1e")

        # --- Style Configuration ---
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.configure_styles()

        # --- Tkinter Variables ---
        self.url_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=os.getcwd())
        self.playlist_var = tk.BooleanVar(value=False)
        self.audio_only_var = tk.BooleanVar(value=False)
        self.subtitles_var = tk.BooleanVar(value=False)
        self.embed_subtitles_var = tk.BooleanVar(value=False)
        self.max_res_var = tk.StringVar(value="none")
        self.custom_template_var = tk.StringVar(value="%(title)s [%(id)s].%(ext)s")
        self.status_var = tk.StringVar(value="Ready")

        # --- Internal State ---
        self.thumbnail_image = None
        self.metadata = {}
        self.download_in_progress = False

        self.create_widgets()
        self.check_dependencies()

    def configure_styles(self):
        """Configures the modern look and feel of the application."""
        # Colors
        bg_color = "#1e1e1e"
        fg_color = "#e0e0e0"
        entry_bg = "#2a2a2a"
        accent_color = "#0a84ff"
        button_fg_color = "#ffffff"

        # General widget styles
        self.style.configure("TLabel", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        self.style.configure("TFrame", background=bg_color)
        self.style.configure("TCheckbutton", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        self.style.map("TCheckbutton",
                       background=[('active', '#333')],
                       indicatorcolor=[('selected', accent_color), ('!selected', '#555')])

        self.style.configure("TEntry", fieldbackground=entry_bg, foreground=fg_color,
                                       insertbackground=fg_color, borderwidth=1, relief="flat")
        self.style.map("TEntry", bordercolor=[('focus', accent_color)])

        self.style.configure("TCombobox", fieldbackground=entry_bg, foreground=fg_color,
                                          arrowcolor=accent_color, borderwidth=1, relief="flat")

        # Custom button style
        self.style.configure("Accent.TButton", background=accent_color, foreground=button_fg_color,
                                             font=("Segoe UI", 12, "bold"), borderwidth=0, relief="flat",
                                             padding=(10, 8))
        self.style.map("Accent.TButton",
                       background=[('active', '#006edc'), ('disabled', '#555')])

        # Progress bar style
        self.style.configure("Gradient.Horizontal.TProgressbar",
                               troughcolor=entry_bg,
                               background=accent_color,
                               borderwidth=0)
    def create_widgets(self):
        """Creates and lays out the widgets in the main window."""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- URL and Fetch Section ---
        url_frame = ttk.Frame(main_frame)
        url_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(url_frame, text="Video/Playlist URL", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 5))
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, font=("Segoe UI", 11))
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 10))

        fetch_btn = ttk.Button(url_frame, text="Fetch Info", command=self.fetch_metadata_thread, style="Accent.TButton")
        fetch_btn.pack(side=tk.LEFT)

        # --- Metadata Display ---
        meta_frame = ttk.Frame(main_frame, style="Card.TFrame")
        meta_frame.pack(fill=tk.X, pady=10)
        self.thumb_label = ttk.Label(meta_frame)
        self.thumb_label.pack(side=tk.LEFT, padx=15, pady=15)
        info_frame = ttk.Frame(meta_frame)
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15))

        self.title_label = ttk.Label(info_frame, text="Title: N/A", font=("Segoe UI", 12, "bold"), wraplength=550)
        self.title_label.pack(anchor="w", pady=(10, 5))
        self.channel_label = ttk.Label(info_frame, text="Channel: N/A", font=("Segoe UI", 9))
        self.channel_label.pack(anchor="w")
        self.duration_label = ttk.Label(info_frame, text="Duration: N/A", font=("Segoe UI", 9))
        self.duration_label.pack(anchor="w")

        # --- Download Options ---
        options_frame = ttk.LabelFrame(main_frame, text="Download Options", padding=15)
        options_frame.pack(fill=tk.X, pady=10)

        # Checkboxes
        check_frame = ttk.Frame(options_frame)
        check_frame.pack(fill=tk.X)
        ttk.Checkbutton(check_frame, text="Download Playlist", variable=self.playlist_var).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Checkbutton(check_frame, text="Audio Only (mp3)", variable=self.audio_only_var).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Checkbutton(check_frame, text="Subtitles", variable=self.subtitles_var).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Checkbutton(check_frame, text="Embed Subtitles", variable=self.embed_subtitles_var).pack(side=tk.LEFT)

        # Other options
        other_options_frame = ttk.Frame(options_frame)
        other_options_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(other_options_frame, text="Max Resolution:").pack(side=tk.LEFT, padx=(0, 5))
        maxres_combo = ttk.Combobox(other_options_frame, textvariable=self.max_res_var, state="readonly", width=10,
                                    values=("none", "1080p", "720p", "480p", "360p"))
        maxres_combo.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(other_options_frame, text="Filename Template:").pack(side=tk.LEFT, padx=(0, 5))
        filename_entry = ttk.Entry(other_options_frame, textvariable=self.custom_template_var, width=40)
        filename_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # --- Output and Format Section ---
        output_frame = ttk.Frame(main_frame)
        output_frame.pack(fill=tk.X, pady=10)
        ttk.Label(output_frame, text="Output Folder:").pack(anchor="w", pady=(0, 5))

        out_entry = ttk.Entry(output_frame, textvariable=self.output_dir_var, width=65)
        out_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 10))
        ttk.Button(output_frame, text="Browse...", command=self.browse_output_folder).pack(side=tk.LEFT)

        # --- Format Selector ---
        format_frame = ttk.Frame(main_frame)
        format_frame.pack(fill=tk.X, pady=(5, 15))
        ttk.Label(format_frame, text="Available Formats:", anchor="w").pack(fill=tk.X, pady=(0, 5))
        self.format_combo = ttk.Combobox(format_frame, state="readonly")
        self.format_combo.pack(fill=tk.X, ipady=4)

        # --- Progress and Log ---
        self.progress = ttk.Progressbar(main_frame, length=760, mode='determinate', style="Gradient.Horizontal.TProgressbar")
        self.progress.pack(fill=tk.X, pady=5)

        self.log_box = tk.Text(main_frame, height=8, bg="#111", fg="#ddd", wrap=tk.WORD, relief="flat",
                               font=("Consolas", 9), yscrollcommand=True, bd=0)
        self.log_box.pack(fill=tk.BOTH, expand=True, pady=10)

        # --- Download Button and Status Bar ---
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        self.download_btn = ttk.Button(bottom_frame, text="⬇  Download", command=self.download_thread, style="Accent.TButton")
        self.download_btn.pack(side=tk.RIGHT)

        self.status_label = ttk.Label(bottom_frame, textvariable=self.status_var, font=("Segoe UI", 9))
        self.status_label.pack(side=tk.LEFT, anchor="w", pady=(5,0))


    def browse_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir_var.set(folder)

    def check_dependencies(self):
        if not shutil.which(YTDLP_EXECUTABLE):
            self.log(f"⚠️ {YTDLP_EXECUTABLE} not found. Please place it in the same folder as the script or in your system's PATH.")
            self.status_var.set(f"Error: {YTDLP_EXECUTABLE} not found.")
        if not shutil.which(FFMPEG_EXECUTABLE):
            self.log("⚠️ ffmpeg not found. Merging video/audio may fail if required.")
        else:
            self.log("✅ yt-dlp and ffmpeg detected.")
            
    def update_status(self, text):
        self.status_var.set(text)
        self.update_idletasks()

    def log(self, text):
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)

    def clear_log(self):
        self.log_box.delete(1.0, tk.END)

    def fetch_metadata_thread(self):
        threading.Thread(target=self.fetch_metadata, daemon=True).start()

    def fetch_metadata(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a video or playlist URL.")
            return

        self.clear_log()
        self.update_status("Fetching video info...")
        self.log("Fetching metadata...")

        try:
            # Hide console window on Windows
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            cmd = [YTDLP_EXECUTABLE, "--dump-single-json", "--no-playlist", url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20, startupinfo=startupinfo, encoding='utf-8')
            
            if result.returncode != 0:
                self.log(f"Failed to fetch metadata: {result.stderr}")
                self.update_status("Error fetching info.")
                return

            meta_json = json.loads(result.stdout)
            self.metadata = meta_json

            # Update UI with metadata
            self.title_label.config(text=meta_json.get("title", "N/A"))
            self.channel_label.config(text=f"Channel: {meta_json.get('uploader', 'N/A')}")
            duration = self.seconds_to_hms(meta_json.get("duration", 0))
            self.duration_label.config(text=f"Duration: {duration}")

            if thumbnail_url := meta_json.get("thumbnail"):
                self.load_thumbnail(thumbnail_url)

            # Populate formats
            formats = [
                f"{f['format_id']} | {f['ext']} | {f.get('resolution', 'audio')} | {f.get('format_note', '')} | {(f.get('filesize') or f.get('filesize_approx', 0)) / (1024*1024):.2f}MB"
                for f in meta_json.get('formats', [])
            ]
            self.format_combo['values'] = formats
            if formats:
                self.format_combo.current(len(formats) - 1) # Select best by default

            self.log("Metadata and formats fetched successfully.")
            self.update_status("Ready to download.")

        except Exception as e:
            self.log(f"Error fetching metadata: {e}")
            self.update_status("Error fetching info.")

    def load_thumbnail(self, url):
        try:
            with urlopen(url) as u:
                raw_data = u.read()
            im = Image.open(BytesIO(raw_data)).resize((160, 90), Image.Resampling.LANCZOS)
            self.thumbnail_image = ImageTk.PhotoImage(im)
            self.thumb_label.config(image=self.thumbnail_image)
        except Exception as e:
            self.log(f"Failed to load thumbnail: {e}")

    def seconds_to_hms(self, s):
        if not s: return "N/A"
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        return f"{int(h)}h {int(m):02d}m {int(sec):02d}s" if h else f"{int(m)}m {int(sec):02d}s"

    def set_ui_state(self, enabled):
        """Enable or disable UI elements during download."""
        self.download_in_progress = not enabled
        state = tk.NORMAL if enabled else tk.DISABLED
        for child in self.winfo_children():
            if isinstance(child, ttk.Frame):
                for widget in child.winfo_children():
                    if 'state' in widget.keys():
                        widget.configure(state=state)
        self.download_btn.configure(state=state)

    def download_thread(self):
        if self.download_in_progress:
            messagebox.showwarning("In Progress", "A download is already running.")
            return
        threading.Thread(target=self.download, daemon=True).start()

    def download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a valid URL.")
            return

        self.set_ui_state(False)
        self.clear_log()
        self.progress['value'] = 0

        try:
            cmd = self.build_command()
            self.log(f"Running command:\n{' '.join(cmd)}\n")
            self.update_status("Downloading...")

            # Hide console window on Windows
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, encoding='utf-8', errors='replace', startupinfo=startupinfo)
            full_log = ""
            for line in process.stdout:
                full_log += line
                self.log(line.strip())
                self.parse_progress(line)
            process.wait()

            if process.returncode == 0:
                self.log("\n✅ Download completed successfully.")
                self.update_status("Download finished.")
                self.progress['value'] = 100
            else:
                self.log(f"\n❌ Download failed with code {process.returncode}.")
                self.update_status("Download failed.")

            log_path = save_log(full_log)
            self.log(f"\nLog saved to: {log_path}")

        except Exception as e:
            self.log(f"Error during download: {e}")
            self.update_status("Download error.")
        finally:
            self.set_ui_state(True)
            
    def build_command(self):
        """Builds the yt-dlp command list from UI options."""
        url = self.url_var.get().strip()
        out_dir = self.output_dir_var.get()
        
        cmd = [YTDLP_EXECUTABLE]

        cmd.append("--progress")
        cmd.append("--no-warnings")

        if self.playlist_var.get():
            cmd.extend(["--yes-playlist"])
        else:
            cmd.extend(["--no-playlist"])

        if self.audio_only_var.get():
            cmd.extend(["-x", "--audio-format", "mp3"])
        else:
            selected_format = self.format_combo.get()
            max_res = self.max_res_var.get()
            
            if max_res != "none":
                res_val = max_res.replace("p", "")
                cmd.extend(["-f", f"bestvideo[height<={res_val}]+bestaudio/best[height<={res_val}]"])
            elif selected_format:
                fmt_code = selected_format.split('|')[0].strip()
                cmd.extend(["-f", fmt_code])

        if self.subtitles_var.get():
            cmd.extend(["--write-sub", "--sub-lang", "en,en-US,en-GB"])
            if self.embed_subtitles_var.get():
                cmd.append("--embed-subs")

        out_template = self.custom_template_var.get().strip() or "%(title)s.%(ext)s"
        out_path = os.path.join(out_dir, out_template)
        cmd.extend(["-o", out_path])

        cmd.append(url)
        return cmd

    def parse_progress(self, line):
        m = re.search(r'\[download\]\s+([\d\.]+)%', line)
        if m:
            percent = float(m.group(1))
            self.progress['value'] = percent
            self.update_status(f"Downloading... {percent:.1f}%")
            self.update_idletasks()

if __name__ == "__main__":
    if not shutil.which(YTDLP_EXECUTABLE):
        messagebox.showerror("Dependency Error", f"{YTDLP_EXECUTABLE} not found. Please place it in the application's directory or in your system's PATH.")
        sys.exit(1)
        
    app = YTDLPDownloaderGUI()
    app.mainloop()