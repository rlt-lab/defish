"""Build a standalone app for the current OS: `uv run --python 3.13 --with pyinstaller --with pillow python build.py`.
Needs ffmpeg/out/ from `ffmpeg/build.sh` first (CI builds it; the Windows one is cross-compiled on Linux).
PyInstaller can't cross-compile: run on macOS for the .app, on Windows for the .exe.
Folder build on both: a single-file exe unpacks ~70 MB on every launch and trips antivirus more often.
Output: dist/defish/ holds the app plus NOTICE.txt and licenses/; zip that folder to ship."""
import os, shutil, subprocess, sys
from pathlib import Path
import PyInstaller.__main__

ffmpeg = Path("ffmpeg/out") / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
PyInstaller.__main__.run([
    "app.py", "--name", "defish", "--windowed", "--noconfirm", "--onedir",
    "--icon", "icon.png",  # Pillow converts it to .ico / .icns
    "--add-binary", f"{ffmpeg}{os.pathsep}.",  # app.py runs it from sys._MEIPASS
    "--exclude-module", "imageio_ffmpeg",  # dev-only; its prebuilt FFmpeg isn't shipped
])

out = Path("dist/defish")
if sys.platform == "darwin":  # dist/defish is PyInstaller's intermediate folder; ship the .app in its place
    shutil.rmtree(out)
    out.mkdir()
    shutil.move("dist/defish.app", out)

# The bundled FFmpeg is GPL (it includes x264): ship the licence and point to the complete source.
ff = lambda flag: subprocess.run([ffmpeg, "-hide_banner", flag], capture_output=True, text=True).stdout.strip()
target = "macos" if sys.platform == "darwin" else "windows"
(out / "NOTICE.txt").write_text(f"""defish bundles FFmpeg with x264, which runs as a separate program and is licensed under the
GNU General Public License, version 2 or later. The licence text is in licenses/GPL-2.0.txt.

Complete source code for this FFmpeg: ffmpeg-source-{target}.tar.gz, attached to the same release as this download
at https://github.com/rlt-lab/defish/releases. It holds the FFmpeg, x264 and zlib sources and build.sh, the
script that built this exact binary (also at https://github.com/rlt-lab/defish/blob/main/ffmpeg/build.sh).

defish also bundles, under permissive licences (texts in licenses/):
  Python and the libraries built into it: OpenSSL, expat, libffi, zlib, libmpdec and others (Python.txt),
  HACL* (HACL.txt), bzip2 (bzip2.txt), liblzma from XZ Utils (xz.txt), Tcl/Tk (Tcl.txt, Tk.txt).
  SQLite is in the public domain.{'''
  FFmpeg on Windows also links zlib (zlib.txt) and the mingw-w64 runtime (mingw-w64.txt).''' if target == "windows" else ""}

Bundled FFmpeg build:

{ff("-version")}
""", encoding="utf-8")
shutil.copytree("licenses", out / "licenses", dirs_exist_ok=True)
shutil.copytree("ffmpeg/out/licenses", out / "licenses", dirs_exist_ok=True)
