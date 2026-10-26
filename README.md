# defish

Pick a ceiling-fisheye classroom video, choose which walls to keep, and export 1–4 flat views as an MP4
with the camera's timestamp in a bar below.

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
Windows status and remaining work: [WINDOWS.md](WINDOWS.md).
