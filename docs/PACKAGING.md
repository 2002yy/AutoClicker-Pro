# Packaging

Build a single-file Windows executable using PyInstaller.

## Prerequisites

```bash
pip install pyinstaller
```

## Build

```bash
python pack.py
```

The script will:
1. Check for required packages (`pyinstaller`, `customtkinter`, `pynput`)
2. Auto-install any missing dependencies
3. Run PyInstaller with the following configuration:
   - `--onefile`: Single EXE output
   - `--windowed`: No console window
   - `--add-data`: Bundle CustomTkinter resources
   - `--noconfirm`: Overwrite without prompting

Output: `dist/AutoClickerPro.exe`

## Customization

Edit `pack.py` to change:

| Variable | Default | Description |
|---|---|---|
| `SOURCE_FILE` | `autoclicker.py` | Entry point |
| `EXE_NAME` | `AutoClickerPro` | Output filename |

## Manual PyInstaller

```bash
pyinstaller --onefile --windowed --add-data="$(python -c "import customtkinter;print(customtkinter.__file__)"):customtkinter" autoclicker.py
```

## Anti-Virus Notes

Single-file PyInstaller EXEs may trigger false positives due to packing heuristics. This is a known limitation of Python packaging — the source code is fully readable in `autoclicker.py` for independent audit.
