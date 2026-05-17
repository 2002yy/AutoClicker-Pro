# Privacy

## Zero Data Collection

This application **does not** collect, transmit, or store any personal data.

- **No network requests**: The application never connects to the internet
- **No telemetry**: No usage analytics, crash reports, or performance data
- **No identifiers**: No device IDs, user IDs, or session tokens
- **No persistent logs**: No keystroke logging or activity history beyond the current session

## Local-Only Storage

The only data written to disk is:

- **Configuration file**: `config.json` (local) — stores user preference settings
- **EXE output**: `dist/AutoClickerPro.exe` — generated only when the user runs `pack.py`

Both are stored entirely on the user's machine. No data ever leaves the local environment.

## Third-Party Dependencies

| Package | Purpose | Network |
|---|---|---|
| `customtkinter` | UI framework | None |
| `pynput` | Input simulation | None |
| `pyinstaller` | Packaging (dev only) | None |

None of these dependencies include network communication, telemetry, or data collection.
