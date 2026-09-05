# Building a standalone Windows `.exe`

These steps package the generator into a single Windows executable that runs
without a separate Python installation, using
[PyInstaller](https://pyinstaller.org/).

Run them **on a Windows machine** (PyInstaller builds for the OS it runs on).

## 1. Set up

Install Python 3.9+ from [python.org](https://www.python.org/downloads/) with the
**“tcl/tk and IDLE”** feature checked, then from the project root:

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
```

`requirements-dev.txt` includes PyInstaller. (Tkinter comes with the python.org
installer; there is no separate package to install.)

## 2. Build

A one‑file, windowed (no console) build:

```bat
pyinstaller --noconfirm --clean --onefile --windowed ^
  --name "CA-DL-Barcode-Generator" ^
  run.py
```

The executable is written to `dist\CA-DL-Barcode-Generator.exe`.

Notes:
- `--windowed` hides the console window (this is a GUI app).
- `--onefile` produces a single `.exe`; drop it for a faster‑starting folder
  build (`dist\CA-DL-Barcode-Generator\`).
- PyInstaller detects `pdf417gen`, `PIL`, and `tkinter` automatically. If a hook
  ever misses a `pdf417gen` submodule, add
  `--collect-submodules pdf417gen`.

## 3. Optional: reproducible spec file

To keep the build configuration in version control, generate and commit a spec
file, then build from it:

```bat
pyi-makespec --onefile --windowed --name "CA-DL-Barcode-Generator" run.py
pyinstaller --noconfirm --clean CA-DL-Barcode-Generator.spec
```

## 4. Run

Double‑click `dist\CA-DL-Barcode-Generator.exe`, or from a terminal:

```bat
dist\CA-DL-Barcode-Generator.exe
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: tkinter` at runtime | Reinstall Python with the **tcl/tk** option checked. |
| SmartScreen warning on first launch | Expected for an unsigned local build — “More info” → “Run anyway”, or code‑sign the `.exe`. |
| Antivirus flags the one‑file `.exe` | A known PyInstaller false‑positive; a folder (non‑`--onefile`) build usually avoids it, or code‑sign it. |
| Slow first start (one‑file) | One‑file builds unpack to a temp dir on launch; use a folder build for faster startup. |
