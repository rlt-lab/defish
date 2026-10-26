# defish

Pick a ceiling-fisheye classroom video, choose which walls to keep, and export 1–4 flat views as an MP4
with the camera's timestamp in a bar below.

## Download

- **macOS** (Apple Silicon): [defish-macos.zip](https://github.com/rlt-lab/defish/releases/latest/download/defish-macos.zip)
- **Windows** (64-bit): [defish-windows.zip](https://github.com/rlt-lab/defish/releases/latest/download/defish-windows.zip)

Unzip and run: `defish.app` on macOS, `defish.exe` on Windows. Nothing else to install. All versions:
[Releases](https://github.com/rlt-lab/defish/releases).

The app isn't signed yet, so the first launch needs one extra step:
- **macOS:** right-click `defish.app` → Open → Open. If that's not offered, go to System Settings → Privacy & Security
  → Open Anyway.
- **Windows:** on "Windows protected your PC", click More info → Run anyway.

## Licence

defish bundles [FFmpeg](https://ffmpeg.org) with x264, licensed under the GNU GPL v2 or later. It's built from
source by [`ffmpeg/build.sh`](ffmpeg/build.sh), and every release includes the complete corresponding source
(`ffmpeg-source-macos.tar.gz`, `ffmpeg-source-windows.tar.gz`: the FFmpeg, x264 and zlib sources plus the build script).
Each download includes `NOTICE.txt` and the licence texts in `licenses/` for FFmpeg and the other bundled components
(Python, Tcl/Tk and others).

## Run from source

Uses imageio-ffmpeg's prebuilt FFmpeg for development.

```
uv run --python 3.13 --with imageio-ffmpeg python app.py
```

## Check

```
uv run --python 3.13 --with imageio-ffmpeg python check.py [fisheye-video]
```

Without a video it uses a synthetic test pattern. To check a specific FFmpeg (as CI does with the one that ships),
set `IMAGEIO_FFMPEG_EXE` to its path.

## Build

```
ffmpeg/build.sh macos    # needs pkgconf (brew install pkgconf); Windows: ffmpeg/build.sh windows on Linux with mingw-w64
uv run --python 3.13 --with pyinstaller --with pillow python build.py
```

PyInstaller can't cross-compile, so build the `.app` on macOS and the `.exe` on Windows. Every push builds both
in GitHub Actions; download them from the run's artifacts (`defish-macos`, `defish-windows`).

## Release

```
git tag vX.Y.Z && git push origin vX.Y.Z
```

CI builds both, then publishes `defish-macos.zip`, `defish-windows.zip` and the FFmpeg source bundles as a GitHub Release.
