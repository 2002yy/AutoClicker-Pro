# Security

## Input Simulation Method

This tool uses `pynput` to produce OS-level input events. This is the same mechanism the operating system uses when processing physical mouse and keyboard input — no injection, no memory modification, no API hooking.

- **Foreground operation**: The cursor moves visibly and keys are pressed observably
- **No kernel-level access**: Operates at user-space privilege level
- **No bypass mechanisms**: Does not attempt to evade detection or bypass security controls

## Threat Model

| Concern | Status |
|---|---|
| Remote code execution | Not applicable — no network input |
| Data exfiltration | Not applicable — no network access |
| Injection attacks | Not applicable — no external input parsing |
| Privilege escalation | Not applicable — runs at user level |
| Local file access by same user | Encryption key stored as plaintext in `~/.autoclicker_pro/.key` |

## 加密保护局限性

本软件使用 Fernet 对称加密 + PBKDF2 密钥派生对宏文件进行加密存储。

**重要声明：此加密仅为本地混淆保护，非机密级安全。**

- 加密密钥以明文形式存储在 `~/.autoclicker_pro/.key` 文件中
- 在同一操作系统账户下，任何能访问该目录的程序均可读取密钥并解密数据
- Windows 的 `os.chmod(0o600)` 在同账户文件访问场景下无效
- 此设计适用于防止意外泄露，不适用于保护高敏感数据

## Recommended Usage

- Run in an isolated user account for sensitive automation tasks
- Review the source before running — the tool is a multi-module Python project; inspect `config/`, `core/`, `ui/`, `utils/` 与 `main.py`
- Audit the packaged EXE if building from source
