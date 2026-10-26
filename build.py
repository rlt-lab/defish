"""Build a standalone app for the current OS: `uv run --python 3.13 --with imageio-ffmpeg --with pyinstaller --with pillow python build.py`.
PyInstaller can't cross-compile: run on macOS for the .app, on Windows for the .exe.
Folder build on both: a single-file exe unpacks ~70 MB on every launch and trips antivirus more often.
Output: dist/defish/ holds the app plus NOTICE.txt and licenses/; zip that folder to ship."""
import shutil, subprocess, sys
from pathlib import Path
import imageio_ffmpeg
import PyInstaller.__main__

PyInstaller.__main__.run([
    "app.py", "--name", "defish", "--windowed", "--noconfirm", "--onedir",
    "--icon", "icon.png",  # Pillow converts it to .ico / .icns
    "--collect-data", "imageio_ffmpeg",  # bundles the platform's ffmpeg binary
])

out = Path("dist/defish")
if sys.platform == "darwin":  # dist/defish is PyInstaller's intermediate folder; ship the .app in its place
    shutil.rmtree(out)
    out.mkdir()
    shutil.move("dist/defish.app", out)

# The bundled ffmpeg is GPL (it includes x264), so ship its licence and where to get the source.
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
ff = lambda flag: subprocess.run([ffmpeg, "-hide_banner", flag], capture_output=True, text=True).stdout.strip()
(out / "NOTICE.txt").write_text(f"""defish bundles FFmpeg, which runs as a separate program and is licensed under the GNU GPL.
The full licence texts are in the licenses/ folder (GPL-2.0.txt and GPL-3.0.txt).

FFmpeg source code: ffmpeg-{imageio_ffmpeg.get_ffmpeg_version().split('-')[0]}.tar.xz, attached to the same GitHub release as this download
(https://github.com/rlt-lab/defish/releases), and at https://ffmpeg.org/releases/.
This FFmpeg binary comes from imageio-ffmpeg {imageio_ffmpeg.__version__}: https://github.com/imageio/imageio-ffmpeg
Build details for the bundled binary are below. For the source of the libraries it was built with,
open an issue at https://github.com/rlt-lab/defish/issues.

defish also bundles, under permissive licences (texts in licenses/):
  Python and the libraries built into it: OpenSSL, expat, libffi, zlib, libmpdec and others (Python.txt),
  HACL* (HACL.txt), bzip2 (bzip2.txt), liblzma from XZ Utils (xz.txt), Tcl/Tk (Tcl.txt, Tk.txt),
  imageio-ffmpeg (imageio-ffmpeg.txt). SQLite is in the public domain.

{ff("-version")}

{ff("-L")}
""", encoding="utf-8")
shutil.copytree("licenses", out / "licenses", dirs_exist_ok=True)
