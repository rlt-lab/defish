"""defish: pick a ceiling-fisheye video, export 1-4 flat wall views as an MP4 with the camera timestamp."""
import contextlib
import os
import re
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
# Flat view of the straight-down 180° fisheye, tilted 35° toward one wall. Spinning it with `roll`
# (applied before the tilt) picks the wall; panels are 90° apart.
V360 = ("v360=input=fisheye:ih_fov=180:iv_fov=180:output=flat:d_fov=140:pitch=35:rorder=rpy"
        ":roll={roll}:w={w}:h={h}")
# Camera burns "BGES B210" over "date time" into the top-right corner of the 1920x1920 frame.
# Files rotated 180° (e.g. *-flipped) have it upside down in the bottom-left instead.
STAMP_TR = "crop=480:110:iw-480:0"
STAMP_BL = "crop=480:110:0:ih-110,hflip,vflip"
# Within that upright 480x110 corner: the two text lines, cropped to be laid side by side.
NAME, DATE = "crop=180:36:222:11", "crop=372:36:28:63"
NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def wrap(deg):
    return (deg + 180) % 360 - 180  # v360 accepts -180..180


def cell(p, w, h):
    """xstack position of panel p in the 2x2 grid, clockwise TL, TR, BR, BL. Pixel coords, because
    xstack's w0/h0 form fails when the top-left cell is empty."""
    x, y = [(0, 0), (1, 0), (1, 1), (0, 1)][p]
    return f"{x * w}_{y * h}"


def stamp_bar(stamp, text_h):
    """Chain [m] (the video) + [t0] (raw frame) -> [out]: the video with a thin black bar appended below,
    holding the timestamp as one centered line ("BGES B210   10/05/2026 08:59:02") text_h px tall."""
    bar_h = text_h + 10  # text_h is even, so bar_h is too (yuv420p needs even height)
    return (f"[t0]{stamp},split[n0][d0];[n0]{NAME},pad=iw+30:ih[n];[d0]{DATE}[d];"
            f"[n][d]hstack,scale=-2:{text_h}[t];"
            f"[m]pad=iw:ih+{bar_h}[p];[p][t]overlay=(W-w)/2:H-{bar_h}+({bar_h}-{text_h})/2[out]")


def graph(roll, stamp, panels):
    """filter_complex for export. 1 panel: 1920x1080. 2: side by side, 1920x540. 3-4: 2x2 grid, 1920x1080
    with each panel in the same cell as the preview (3 leaves the unpicked cell black).
    Plus a 30 px timestamp bar below."""
    n = len(panels)
    w, h = (1920, 1080) if n == 1 else (960, 540)
    views = "".join(f"[s{i}]{V360.format(roll=wrap(roll - 90 * p), w=w, h=h)}[v{i}];" for i, p in enumerate(panels))
    ins = "".join(f"[v{i}]" for i in range(n))
    cells = "|".join(cell(p, w, h) for p in panels)
    tile = {1: "null", 2: "hstack=inputs=2"}.get(n, f"xstack=inputs={n}:layout={cells}:fill=black")
    return (f"[0:v]split={n + 1}[t0]{''.join(f'[s{i}]' for i in range(n))};{views}"
            f"{ins}{tile}[m];{stamp_bar(stamp, 20)}")


CELL_W, CELL_H = 400, 225  # one preview cell; the preview grid is 800x450 plus the timestamp bar


def preview_graph(roll, stamp):
    """All four views in the 2x2 grid with the timestamp bar, as [full], plus a dimmed copy as [dim].
    The UI pastes dimmed cells over left-out views, so toggling a view never re-runs ffmpeg."""
    views = "".join(f"[s{p}]{V360.format(roll=wrap(roll - 90 * p), w=CELL_W, h=CELL_H)}[v{p}];" for p in range(4))
    layout = "|".join(cell(p, CELL_W, CELL_H) for p in range(4))
    return (f"[0:v]split=5[t0][s0][s1][s2][s3];{views}[v0][v1][v2][v3]xstack=inputs=4:layout={layout}[m];"
            f"{stamp_bar(stamp, 12)};[out]split[full][d];[d]eq=brightness=-0.32[dim]")


def out_size(n):
    return "1920×570" if n == 2 else "1920×1110"


def run(args):
    return subprocess.run([FFMPEG, "-hide_banner", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", creationflags=NO_WINDOW)


def duration(path):
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", run(["-i", path]).stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0


def find_stamp(path, seek):
    """Return the crop for whichever corner holds the timestamp (the brighter one; the other is black)."""
    def brightness(crop):
        out = run(["-ss", seek, "-i", path, "-frames:v", "1", "-vf",
                   f"{crop},signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-f", "null", "-"]).stderr
        m = re.search(r"YAVG=([\d.]+)", out)
        return float(m[1]) if m else 0.0
    return STAMP_BL if brightness(STAMP_BL) > brightness(STAMP_TR) else STAMP_TR


def reveal(path):
    """Show the file in Finder / Explorer."""
    if sys.platform == "darwin":
        subprocess.run(["open", "-R", path])
    elif sys.platform == "win32":
        subprocess.run(["explorer", f"/select,{os.path.normpath(path)}"])


# Chalkboard slate, with the accent sampled from the camera's own burned-in timestamp.
SLATE, RAISED, LINE = "#1E2B2B", "#263535", "#34474A"
CHALK, DUST, AMBER, AMBER_HI = "#E9EEEA", "#8FA19C", "#F39A2B", "#F7B25A"
REVEAL = "Show in Finder" if sys.platform == "darwin" else "Show in folder"
GRID = {(0, 0): 0, (1, 0): 1, (1, 1): 2, (0, 1): 3}  # (col, row) -> view, matching cell()


class App:
    def __init__(self, root):
        self.root, self.src, self.roll, self.dur, self.stamp = root, None, 0, 0.0, STAMP_TR
        self.progress, self.status, self.proc, self.saved = 0.0, None, None, None
        self.picked, self.hover, self.busy = [True] * 4, None, False
        tmp = tempfile.mkdtemp()
        self.full_png, self.dim_png = os.path.join(tmp, "full.png"), os.path.join(tmp, "dim.png")

        root.title("defish")
        root.configure(bg=SLATE)
        root.resizable(False, False)
        families = set(tkfont.families())
        face = next((f for f in ("Avenir Next", "Segoe UI") if f in families), "TkDefaultFont")
        self.f_title = (face, 20, "bold")
        self.f_body = (face, 13)
        self.f_small = (face, 11)

        s = ttk.Style()
        s.theme_use("clam")  # the native themes ignore colours; clam looks the same on macOS and Windows
        s.configure("TButton", font=self.f_body, padding=(16, 8), borderwidth=0, focusthickness=2,
                    background=RAISED, foreground=CHALK, lightcolor=RAISED, darkcolor=RAISED, focuscolor=AMBER)
        s.map("TButton", background=[("disabled", SLATE), ("active", LINE)], foreground=[("disabled", DUST)],
              lightcolor=[("active", LINE)], darkcolor=[("active", LINE)])
        s.configure("Go.TButton", background=AMBER, foreground=SLATE, lightcolor=AMBER, darkcolor=AMBER,
                    focuscolor=CHALK, font=(face, 13, "bold"))
        s.map("Go.TButton", background=[("disabled", RAISED), ("active", AMBER_HI)],
              foreground=[("disabled", DUST)], lightcolor=[("disabled", RAISED), ("active", AMBER_HI)],
              darkcolor=[("disabled", RAISED), ("active", AMBER_HI)])
        s.configure("TProgressbar", troughcolor=RAISED, background=AMBER, bordercolor=SLATE,
                    lightcolor=AMBER, darkcolor=AMBER, thickness=4)

        pad = 24
        head = tk.Frame(root, bg=SLATE)
        head.pack(fill="x", padx=pad, pady=(pad, 16))
        tk.Label(head, text="defish", font=self.f_title, bg=SLATE, fg=CHALK).pack(side="left")
        self.open_btn = ttk.Button(head, text="Open video…", command=self.open)
        self.open_btn.pack(side="right")
        self.file = tk.Label(head, text="", font=self.f_body, bg=SLATE, fg=DUST)
        self.file.pack(side="left", padx=(16, 0), pady=(6, 0))

        self.canvas = tk.Canvas(root, width=2 * CELL_W, height=2 * CELL_H + 22, bg=RAISED,
                                highlightthickness=0, cursor="hand2")
        self.canvas.pack(padx=pad)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_move)
        self.canvas.bind("<Leave>", lambda e: self.set_hover(None))

        self.foot = foot = tk.Frame(root, bg=SLATE)
        foot.pack(fill="x", padx=pad, pady=(16, pad))
        self.export_btn = ttk.Button(foot, text="Export", style="Go.TButton", command=self.export, state="disabled")
        self.export_btn.pack(side="right")
        self.reveal_btn = ttk.Button(foot, text=REVEAL, command=lambda: reveal(self.saved))
        self.status_lbl = tk.Label(foot, text="", font=self.f_body, bg=SLATE, fg=DUST, anchor="w")
        self.status_lbl.pack(side="left", fill="x", expand=True)
        self.bar = ttk.Progressbar(root, maximum=1.0, length=2 * CELL_W)

        mod = "Command" if sys.platform == "darwin" else "Control"
        root.bind(f"<{mod}-o>", lambda e: self.busy or self.open())
        root.bind(f"<{mod}-e>", lambda e: str(self.export_btn["state"]) == "normal" and self.export())
        self.draw()

    # ---------- preview: the 2x2 grid is the panel picker ----------

    def draw(self):
        c = self.canvas
        c.delete("all")
        if not self.src:
            c.create_text(CELL_W, CELL_H - 12, text="Open a classroom video to begin", fill=CHALK, font=self.f_body)
            c.create_text(CELL_W, CELL_H + 16, text="Pick which walls to keep, then export a flat MP4.",
                          fill=DUST, font=self.f_small)
            return
        view = tk.PhotoImage(width=self.full.width(), height=self.full.height())
        view.tk.call(view, "copy", self.full)
        for p in range(4):
            x, y = self.cell_xy(p)
            if not self.picked[p]:
                view.tk.call(view, "copy", self.dim, "-from", x, y, x + CELL_W, y + CELL_H, "-to", x, y)
        self.view = view  # keep a reference or Tk drops the image
        c.create_image(0, 0, image=view, anchor="nw")
        for p in range(4):
            x, y = self.cell_xy(p)
            on, hot = self.picked[p], self.hover == p
            if on:
                c.create_rectangle(x + 2, y + 2, x + CELL_W - 2, y + CELL_H - 2, outline=AMBER, width=4)
                c.create_oval(x + 12, y + 12, x + 36, y + 36, fill=AMBER, outline="")
                c.create_text(x + 24, y + 24, text="✓", fill=SLATE, font=(self.f_body[0], 13, "bold"))
            elif hot:
                c.create_rectangle(x + 2, y + 2, x + CELL_W - 2, y + CELL_H - 2, outline=DUST, width=2)
            if hot or not on:
                msg = ("Click to leave out" if on else "Click to include") if hot else "Left out"
                tid = c.create_text(x + CELL_W / 2, y + CELL_H / 2, text=msg, fill=CHALK, font=self.f_body)
                bx = c.bbox(tid)
                c.tag_lower(c.create_rectangle(bx[0] - 12, bx[1] - 6, bx[2] + 12, bx[3] + 6,
                                               fill=SLATE, outline=""), tid)

    @staticmethod
    def cell_xy(p):
        col, row = next(k for k, v in GRID.items() if v == p)
        return col * CELL_W, row * CELL_H

    def cell_at(self, e):
        if not self.src or e.y >= 2 * CELL_H:
            return None
        return GRID.get((e.x // CELL_W, e.y // CELL_H))

    def set_hover(self, p):
        if p != self.hover:
            self.hover = p
            if self.src:
                self.draw()

    def on_move(self, e):
        self.set_hover(None if self.busy else self.cell_at(e))

    def on_click(self, e):
        if self.busy:
            return
        if not self.src:
            return self.open()
        p = self.cell_at(e)
        if p is not None:
            self.picked[p] = not self.picked[p]
            self.saved = None
            self.draw()
            self.update_footer()

    def update_footer(self):
        n = sum(self.picked)
        self.reveal_btn.pack_forget()
        if not self.src:
            return
        if n == 0:
            self.export_btn.config(text="Export", state="disabled")
            self.status_lbl.config(text="Click at least one view to include it.", fg=DUST)
        else:
            self.export_btn.config(text=f"Export {n} view{'s' * (n > 1)}…", state="normal")
            if self.saved:
                self.status_lbl.config(text=f"Saved {os.path.basename(self.saved)}", fg=CHALK)
                self.reveal_btn.pack(side="right", padx=(0, 12))
            else:
                layout = {1: "full frame", 2: "side by side", 3: "2×2 grid", 4: "2×2 grid"}[n]
                self.status_lbl.config(text=f"{layout.capitalize()}, {out_size(n)}, timestamp bar below", fg=DUST)

    # ---------- open / export ----------

    def open(self):
        path = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.mov *.m4v *.avi *.mkv"), ("All files", "*.*")])
        if path:
            self.load(path)

    def load(self, path):
        dur = duration(path)
        seek = str(min(3.0, dur / 2))
        stamp = find_stamp(path, seek)
        # Upside-down timestamp means the file was rotated 180°; undo it so views match the camera's native view.
        roll = 180 if stamp == STAMP_BL else 0
        r = run(["-v", "error", "-y", "-ss", seek, "-i", path, "-frames:v", "1", "-filter_complex",
                 preview_graph(roll, stamp), "-map", "[full]", "-update", "1", self.full_png,
                 "-map", "[dim]", "-update", "1", self.dim_png])
        if r.returncode:
            messagebox.showerror("Couldn't open video",
                                 f"{os.path.basename(path)} isn't a fisheye video this app can read.\n\n{r.stderr[-600:]}")
            return
        self.src, self.dur, self.seek, self.stamp, self.roll = path, dur, seek, stamp, roll
        self.full, self.dim = tk.PhotoImage(file=self.full_png), tk.PhotoImage(file=self.dim_png)
        self.picked, self.saved = [True] * 4, None
        mins, secs = divmod(round(dur), 60)
        self.file.config(text=f"{os.path.basename(path)}   {mins}:{secs:02d}")
        self.draw()
        self.update_footer()

    def export(self):
        base = os.path.splitext(os.path.basename(self.src))[0].removesuffix(".mp4")
        out = filedialog.asksaveasfilename(initialdir=os.path.dirname(self.src), initialfile=f"{base}-flat.mp4",
                                           defaultextension=".mp4", filetypes=[("MP4", "*.mp4")])
        if not out:
            return
        if os.path.abspath(out) == os.path.abspath(self.src):
            messagebox.showerror("Pick another name", "That would overwrite the original video. Choose a different file name.")
            return
        self.busy, self.saved, self.progress, self.status = True, None, 0.0, None
        self.set_hover(None)
        for b in (self.open_btn, self.export_btn):
            b.config(state="disabled")
        self.reveal_btn.pack_forget()
        self.canvas.config(cursor="")
        self.bar["value"] = 0
        self.bar.pack(before=self.foot, padx=24, pady=(12, 0))
        fg = graph(self.roll, self.stamp, [p for p in range(4) if self.picked[p]])
        self.out = out
        threading.Thread(target=self.encode, args=(out, fg), daemon=True).start()
        self.poll()

    def encode(self, out, fg):
        cmd = [FFMPEG, "-v", "error", "-y", "-i", self.src, "-filter_complex", fg,
               "-map", "[out]", "-map", "0:a?",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
               "-progress", "pipe:1", "-nostats", out]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                     encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
        # Drain stderr in the background so a chatty ffmpeg can't block on a full pipe.
        err = []
        t = threading.Thread(target=lambda: err.append(self.proc.stderr.read()), daemon=True)
        t.start()
        for line in self.proc.stdout:
            if line.startswith("out_time_us=") and self.dur:
                us = line.split("=")[1].strip()
                if us.isdigit():
                    self.progress = min(int(us) / 1e6 / self.dur, 1.0)
        self.proc.wait()
        t.join()
        if self.proc.returncode == 0:
            self.status = ("ok", out)
        else:
            if os.path.exists(out):
                os.remove(out)  # a half-written MP4 won't play; don't leave it looking like a result
            self.status = ("error", "".join(err)[-1500:])

    def poll(self):
        self.bar["value"] = self.progress
        if self.status is None:
            self.status_lbl.config(text=f"Exporting… {self.progress:.0%}", fg=CHALK)
            self.root.after(250, self.poll)
            return
        self.busy = False
        self.bar.pack_forget()
        self.canvas.config(cursor="hand2")
        self.open_btn.config(state="normal")
        kind, msg = self.status
        self.saved = msg if kind == "ok" else None
        self.update_footer()
        if kind != "ok":
            self.status_lbl.config(text="Export didn't finish. Nothing was saved.", fg=CHALK)
            messagebox.showerror("Export didn't finish", f"ffmpeg stopped with this error:\n\n{msg}")

    def close(self):
        if self.proc and self.proc.poll() is None:
            if not messagebox.askyesno("Stop exporting?", "The export isn't finished. Stop it and quit?"):
                return
            self.proc.kill()
            self.proc.wait()
            with contextlib.suppress(OSError):  # the worker thread may have removed it already
                os.remove(self.out)
        self.root.destroy()


if __name__ == "__main__":
    if sys.platform == "win32":
        import ctypes
        with contextlib.suppress(Exception):
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # crisp text on scaled displays instead of blurry bitmaps
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()
