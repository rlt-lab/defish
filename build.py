"""Build a standalone app for the current OS: `uv run --python 3.13 --with imageio-ffmpeg --with pyinstaller --with pillow python build.py`.
PyInstaller can't cross-compile: run on macOS for the .app, on Windows for the .exe.
Folder build on both: a single-file exe unpacks ~70 MB on every launch and trips antivirus more often."""
import PyInstaller.__main__

PyInstaller.__main__.run([
    "app.py", "--name", "defish", "--windowed", "--noconfirm", "--onedir",
    "--icon", "icon.png",  # Pillow converts it to .ico / .icns
    "--collect-data", "imageio_ffmpeg",  # bundles the platform's ffmpeg binary
])
