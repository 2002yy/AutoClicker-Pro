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
| `tkinter`（Python 标准库） | UI framework | None |
| `pynput` | Input simulation | None |
| `pyinstaller` | Packaging (dev only) | None |

None of these dependencies include network communication, telemetry, or data collection.

## 加密保护级别

本软件使用 Fernet 对称加密对本地宏文件进行加密存储。

**加密仅为本地混淆保护，非机密级安全。**

- 加密密钥以明文存储在 `~/.autoclicker_pro/.key`
- 同账户下可访问该目录的程序可读取密钥并解密数据
- 适用于防止意外泄露，不适用于保护高敏感数据

## 安全声明

- 本软件不收集、传输或存储任何个人数据
- 所有数据仅保存在本地机器上
- 加密设计目标为防君子不防小人
