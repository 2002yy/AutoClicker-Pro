# 全能连点器 Pro

[![Build and Release](https://github.com/2002yy/AutoClicker-Pro/actions/workflows/build.yml/badge.svg)](https://github.com/2002yy/AutoClicker-Pro/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows-blue)](https://github.com/2002yy/AutoClicker-Pro/releases)
> Portfolio note: personal productivity tool project — CI, packaging, encryption and testing focused.
> 作品集说明：个人效率工具项目，重点展示 CI、打包、加密和测试能力。


**一款基于 Python 的 Windows 连点器。支持鼠标连点、键盘连点、宏录制与回放，拥有美观的 Win11 风格界面。**

## Responsible Use

This tool is intended for personal productivity automation, accessibility experiments, UI testing and repetitive desktop workflow automation.

Do not use it to violate software terms of service, bypass anti-cheat systems, automate online games, or perform abusive behavior on third-party services.

## 合规使用说明

本工具用于个人效率自动化、无障碍操作实验、桌面 UI 测试和重复流程辅助。

请勿用于违反软件服务条款、绕过反作弊、在线游戏作弊、批量刷接口或其他滥用场景。


---

## 功能特性

- 🖱️ **鼠标连点** — 支持左键/右键/中键，单击/双击，固定坐标或跟随鼠标
- ⌨️ **键盘连点** — 支持任意键盘按键的自动连按
- 🔴 **宏录制 (Macro)** — 录制键鼠操作并以毫秒精度回放，支持无限循环
- 🔐 **加密存储** — 宏文件采用 Fernet 对称加密
- ⚙️ **灵活配置** — 毫秒级间隔设置，支持无限循环/指定次数/指定时长停止条件
- 🚀 **便携运行** — 单文件 EXE，无需安装 Python

---

## 下载与使用

### 直接下载（推荐）

前往 [Releases 页面](https://github.com/2002yy/AutoClicker-Pro/releases) 下载最新的 `AutoClickerPro.exe`，双击即用。

### 源码运行

```bash
pip install -r requirements.txt
python main.py
```

### 打包 EXE

```bash
pip install pyinstaller
python pack.py
```

---

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `ESC` | 停止录制 |

---
## Engineering Highlights

- Layered structure: config / core / ui / utils
- Macro recording and playback with millisecond precision
- Fernet encrypted macro storage
- PyInstaller single-file EXE packaging
- GitHub Actions build workflow
- 43 unit tests


## 项目结构

```
├── main.py              # 程序入口
├── config/              # 配置模块
│   ├── constants.py     # 常量定义
│   ├── encryption.py    # 加密功能
│   └── validation.py    # 输入验证
├── core/                # 核心业务逻辑
│   ├── engine.py        # 主引擎
│   └── macros.py        # 宏录制与播放
├── ui/                  # UI 层
│   ├── app.py           # 主应用窗口
│   └── components/      # UI 子组件
├── utils/               # 工具类
│   └── hotkey_manager.py
├── tests/               # 单元测试
├── docs/                # 文档
└── .github/workflows/   # CI/CD 自动构建
```

---

## 运行测试

```bash
python -m unittest discover tests -v
```

当前 43 个测试全部通过。

---

## 技术栈

- **GUI**: Tkinter
- **输入模拟**: pynput
- **加密**: cryptography (Fernet)
- **打包**: PyInstaller

---

## 许可证

MIT License — 详见 [LICENSE](LICENSE)

## Roadmap

- [ ] Macro editing UI
- [ ] Scheduled auto-click tasks
- [ ] Multi-profile macro management
- [ ] Hotkey customization
- [ ] Internationalization (i18n)

