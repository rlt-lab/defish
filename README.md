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

defish bundles [FFmpeg](https://ffmpeg.org), which is licensed under the GNU GPL (v2+ in the macOS build, v3 in the
Windows build). Each download includes `NOTICE.txt` with the FFmpeg version, build configuration and where to get
the source, plus the licence texts in `licenses/`.

## Run from source

```
uv run --python 3.13 --with imageio-ffmpeg python app.py
```

## Check

```
uv run --python 3.13 --with imageio-ffmpeg python check.py [fisheye-video]
```

Without a video it uses a synthetic test pattern.

## Build

```
uv run --python 3.13 --with imageio-ffmpeg --with pyinstaller --with pillow python build.py
```

PyInstaller can't cross-compile, so build the `.app` on macOS and the `.exe` on Windows. Every push builds both
in GitHub Actions; download them from the run's artifacts (`defish-macos-latest`, `defish-windows-latest`).

## Release

```
git tag v0.1.0 && git push origin v0.1.0
```

CI builds both, then publishes `defish-macos.zip` and `defish-windows.zip` as a GitHub Release.
