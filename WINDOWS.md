# defish for Windows: task list

The code is already cross-platform (Tkinter + imageio-ffmpeg, with Windows branches for hiding
console windows, DPI awareness, Ctrl shortcuts, and "Show in folder"). Nothing has been run on Windows yet.
PyInstaller can't cross-compile, so the .exe has to be built on Windows.

## 1. Code fixes before the first build
- [x] Decode ffmpeg output as UTF-8. `run()` and the export `Popen` use `text=True`, which on Windows
      decodes with the system code page (cp1252). A file name with accents or other non-ASCII characters can then
      crash the app with `UnicodeDecodeError`. Add `encoding="utf-8", errors="replace"` to both.
- [x] Wrap `SetProcessDpiAwareness(1)` in `try/except` so the app still starts if the call isn't available.
- [x] Quitting mid-export: `close()` kills ffmpeg but exits before the worker thread deletes the
      half-written MP4. Delete it in `close()` after `proc.wait()`.
- [x] Add an app icon (`.ico` for Windows, `.icns` for macOS) and pass `--icon` in `build.py`.
      `icon.png` is a placeholder in the app's colours; PyInstaller converts it (needs `--with pillow`).

## 2. Build
- [ ] Choose where to build:
  - **GitHub Actions** (already set up in `.github/workflows/build.yml`): push the folder to a GitHub repo
    and download the `defish-windows-latest` artifact. No Windows machine needed.
  - **A Windows PC** (or a VM): `uv run --python 3.13 --with imageio-ffmpeg --with pyinstaller --with pillow python build.py`.
    On a Windows-on-ARM VM (e.g. Parallels on Apple Silicon), use an x64 Python
    (`--python cpython-3.13-windows-x86_64-none`), because imageio-ffmpeg ships an x64 ffmpeg.
- [x] Single-file or folder: `build.py` now makes a folder (`--onedir`) on both OSes. A single `--onefile` exe
      unpacks about 70 MB to a temp folder on every launch: slower to start, and more often flagged by antivirus.
- [ ] Ship the folder as a zip (the CI artifact already is one) or wrap it in an installer
      (Inno Setup is free and adds Start-menu shortcuts and uninstall).
- [ ] Run `check.py` on Windows. It renders every panel combination and a libx264 export to a non-ASCII file
      name, which confirms the bundled ffmpeg has `v360`, `xstack`, `signalstats` and `libx264`.
      CI runs it on a synthetic clip before each build; on a Windows PC also run `python check.py "<test clip>"`.
      It should print `ok: all 15 panel combinations + preview + libx264 export`.

## 3. Test on Windows
- [ ] Windows 10 and Windows 11.
- [ ] Display scaling at 100%, 125%, 150%. Text scales but the 800×450 preview doesn't, so check that
      the heading, Open button and footer still fit and nothing is clipped.
- [ ] Fonts: headings and buttons render in Segoe UI and the ✓ badge displays.
- [ ] No black console windows flash when opening a video or exporting.
- [ ] Ctrl+O opens a video; Ctrl+E exports.
- [ ] Files: the 10 s test clip, the full 21 min video (check export time and the progress bar), the flipped
      file, a name with spaces, a name with accents, a file on a network drive or in a OneDrive folder.
- [ ] Export into a folder you can't write to: the error message is clear and no partial file is left.
- [ ] "Show in folder" opens Explorer with the exported file selected.
- [ ] Quit during an export: the confirm prompt appears, ffmpeg stops (check Task Manager), and no partial file is left.

## 4. Ship
- [ ] Code signing. Unsigned, Windows SmartScreen shows "Windows protected your PC" and users must click
      More info → Run anyway; some school IT setups block unsigned apps outright. Options: Azure Trusted Signing
      (cheapest, about $10/month) or an OV/EV certificate from a CA. Sign the exe and the installer.
- [ ] If antivirus flags the build, submit it to Microsoft as a false positive (security intelligence portal).
- [ ] Include the ffmpeg licence: the bundled ffmpeg contains x264 (GPL), so distribution needs the
      GPL notice and a way to get the source. Same requirement as the Mac build.
- [ ] Decide how users get it (shared drive, website, school software portal) and write one page of
      install + use instructions with screenshots.
