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

## Recommended Usage

- Run in an isolated user account for sensitive automation tasks
- Review the source before running — the entire tool is a single Python file
- Audit the packaged EXE if building from source
