# Windows Input Automation Tool

<p>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Platform-Windows-win" alt="Windows">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT">
  <img src="https://img.shields.io/badge/UI-CustomTkinter-orange" alt="CustomTkinter">
</p>

A lightweight Windows input automation tool built with Python and CustomTkinter.
It supports mouse clicking, keyboard repetition, macro recording and local JSON configuration.
This project is intended for desktop automation learning and accessibility-style repetitive task reduction.

<img width="1028" alt="screenshot" src="https://github.com/user-attachments/assets/7b13fda0-30c0-4692-a495-5ac8fc20081f">

## Features

- **Mouse automation**: Left / right / middle click, single / double click, fixed-position or cursor-follow
- **Keyboard automation**: Repeat any key at configurable intervals
- **Macro recording**: Record and replay mouse + keyboard sequences with timing fidelity
- **Flexible stop conditions**: Unlimited loop, fixed count, or timed duration
- **Configuration persistence**: Settings saved to local JSON, restored on restart
- **Portable executable**: Single-file EXE via PyInstaller, no Python runtime required

## Quick Start

```bash
pip install -r requirements.txt
python autoclicker.py
```

### Download

Pre-built EXE available on the [Releases page](https://github.com/2002yy/AutoClicker-Pro/releases).

### Controls

| Key | Function |
|---|---|
| F8 | Start / stop click loop |
| F9 | Capture current mouse position |
| F10 | Start / stop macro recording |
| F11 | Start / stop macro playback |

## How It Works

This tool uses `pynput` to simulate physical input events at the OS level — the same mechanism as a physical mouse or keyboard. It operates in the foreground: the mouse cursor moves and keys are pressed visibly. This approach maximizes compatibility (works with virtually all Windows applications) at the cost of foreground-only operation.

For a detailed technical explanation, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Packaging

```bash
pip install pyinstaller
python pack.py
# Output: dist/AutoClickerPro.exe
```

See [docs/PACKAGING.md](docs/PACKAGING.md) for details.

## Security & Privacy

- **No network access**: All processing is local. Zero telemetry, no data collection.
- **Foreground simulation only**: Uses `pynput` for OS-level input simulation — not injection, not memory modification.
- **See**: [SECURITY.md](SECURITY.md), [PRIVACY.md](PRIVACY.md)

## Disclaimer

This software is provided for educational purposes and legitimate desktop automation only.
It uses foreground input simulation (not hook injection, not memory modification).
Do not use for violating software terms of service, cheating in online games, or any illegal activity.
The author assumes no liability for misuse.
