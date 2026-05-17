# Architecture

```
┌──────────────────────────────────────────────────────┐
│                  autoclicker.py                       │
│                                                      │
│  ┌──────────────┐    ┌──────────────────────────┐   │
│  │  UI Layer     │    │  Automation Engine       │   │
│  │  CustomTkinter│    │  ┌────────────────────┐ │   │
│  │  · Main window│    │  │ MouseController    │ │   │
│  │  · Help popup │    │  │ KeyboardController │ │   │
│  │  · Contact    │    │  └────────────────────┘ │   │
│  └──────┬───────┘    └──────────┬───────────────┘   │
│         │                       │                   │
│         └───────┬───────────────┘                   │
│                 ▼                                   │
│  ┌──────────────────────────────┐                   │
│  │  State Machine               │                   │
│  │  · idle / clicking / macros  │                   │
│  │  · threaded (non-blocking)   │                   │
│  └──────────────────────────────┘                   │
│                 │                                   │
│                 ▼                                   │
│  ┌──────────────────────────────┐                   │
│  │  Persistence                 │                   │
│  │  · JSON config save/load     │                   │
│  │  · Auto-restore on startup   │                   │
│  └──────────────────────────────┘                   │
└──────────────────────────────────────────────────────┘
         │
         ▼
  pynput (OS-level input simulation)
         │
         ▼
  Windows input subsystem
```

## Layers

| Layer | Responsibility |
|---|---|
| **UI** | CustomTkinter window, form controls, hotkey binding |
| **State** | Tracks running/idle, stop conditions, macro state |
| **Engine** | Threaded execution of click loops and macro sequences |
| **Persistence** | JSON read/write for configuration restore |

## Thread Model

The UI runs on the main thread. Automation loops run on a background daemon thread to keep the UI responsive. A threading `Event` flag signals the loop to stop.

## Dependencies

| Dependency | Role |
|---|---|
| `customtkinter` | Modern UI toolkit (wraps tkinter) |
| `pynput.mouse` | Mouse event simulation + listener |
| `pynput.keyboard` | Keyboard event simulation + listener |
| `json` (stdlib) | Configuration persistence |
| `threading` (stdlib) | Background execution |
| `datetime` (stdlib) | Timed stop conditions |
