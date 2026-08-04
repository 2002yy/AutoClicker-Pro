# 全能连点器 Pro

[![Build and Release](https://github.com/2002yy/AutoClicker-Pro/actions/workflows/build.yml/badge.svg)](https://github.com/2002yy/AutoClicker-Pro/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows-blue)](https://github.com/2002yy/AutoClicker-Pro/releases)

**一款基于 Python 的 Windows 连点器。支持鼠标连点、鼠标宏录制与回放、全局快捷键与宏文件本地加密存储。**

---

## 功能特性

> ⚠️ 以下为**已实现**功能；"规划中"为尚未实现、此前文档曾误述为已实现的部分。

- 🖱️ **鼠标连点** — 支持左键/右键/中键，固定坐标，按配置间隔自动点击（**已实现**）
- 🔴 **宏录制（鼠标 + 键盘）** — 录制鼠标点击与键盘按键序列并以毫秒精度回放，支持指定次数/时长停止（**已实现**；录制时落在本程序窗口内的点击自动忽略）
- ⌨️ **键盘连点 / 录制** — 录制过程中捕获键盘按键，回放时按"轻点"语义自动按下并释放（**已实现**）
- 🔐 **加密存储** — 宏文件采用本地 Fernet 对称加密（**已实现**；密钥存于用户目录 `~/.autoclicker_pro/`，属**本地混淆级**保护，并非对抗同机攻击者的机密保护）
- ⚙️ **灵活配置** — 毫秒级间隔、按住时长、重复次数/间隔设置（**已实现**）
- 🔧 **全局快捷键** — F8 启停连点、F10 开始录制、F11 停止录制、ESC 一键全停，窗口失焦时同样生效（**已实现**）
- 🎨 **Win11 风格界面** — 基于 ttk 的自定义浅色主题：Segoe UI 字体、蓝(#0067C0)强调色主按钮、扁平卡片与细边框（**已实现**）
- 🚀 **便携运行** — 单文件 EXE，无需安装 Python（**已实现**）

> 说明：上述功能均已实现并通过单元测试（当前共 64 项）。加密存储为本地混淆级保护，详见「合法使用与免责声明」。

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

以下均为**全局快捷键**，程序窗口在后台时同样生效。

| 快捷键 | 功能 |
|--------|------|
| `F8` | 开始 / 停止连点 |
| `F10` | 开始录制 |
| `F11` | 停止录制 |
| `ESC` | 一键全停（同时终止录制与连点） |

> 说明：全局快捷键依赖系统级键盘钩子。若在受限环境（远程桌面、部分安全软件拦截、无输入权限）下注册失败，
> 程序会在状态栏提示并自动降级为"仅界面按钮 + 窗口内 ESC"，主功能不受影响。
>
> 录制期间，落在本程序窗口内的点击会被自动忽略，因此点击"停止录制"按钮本身不会被录进宏里。同时会捕获键盘按键（F8/F10/F11/ESC 等控制键除外），回放时一并执行。

---

## 项目结构

```
├── main.py              # 程序入口
├── config/              # 配置模块
│   ├── constants.py     # 常量定义
│   ├── encryption.py    # 加密功能
│   └── validation.py    # 输入验证
├── core/                # 核心业务逻辑
│   ├── engine.py        # 主引擎（连点 / 录制 / 存取宏）
│   └── macros.py        # ClickAction 数据模型
├── ui/                  # UI 层
│   ├── app.py           # 主应用窗口
│   └── components/      # UI 子组件
├── utils/               # 工具类
│   └── hotkey_manager.py  # 全局快捷键管理器
├── tests/               # 单元测试
├── docs/                # 文档
└── .github/workflows/   # CI/CD 自动构建
```

---

## 运行测试

```bash
python -m unittest discover tests -v
```

运行 `python -m unittest discover tests -v` 查看测试结果。

---

## 技术栈

- **GUI**: Tkinter（`ttk` + 自定义 Win11 风格主题，未使用 customtkinter）
- **输入模拟**: pynput
- **加密**: cryptography (Fernet)
- **打包**: PyInstaller

---

## ⚖️ 合法使用与免责声明

本工具是一个通用的输入自动化程序。它会模拟真实的鼠标点击，**目标程序通常无法区分这些点击是人为的还是自动生成的**。这一特性决定了它既可以合法地用于提高效率，也可能被滥用。请务必在使用前阅读本节。

### 允许的用途

- 自动化重复性的本地办公、测试与运维操作
- 软件的 UI 自动化测试与回归验证
- 因身体原因难以进行重复点击时的**无障碍辅助**
- 在你自己拥有或已获得明确授权的系统上进行自动化

### 明确禁止的用途

- ❌ **违反目标平台服务条款（ToS）的自动化**，包括但不限于网络游戏外挂/脚本、自动打怪挂机
- ❌ 电商刷单、刷量、刷票、刷阅读量、批量注册账号等**虚假流量与欺诈行为**
- ❌ 绕过验证码、人机验证、风控校验或任何访问控制机制
- ❌ 在未经授权的他人设备上运行，或用于监视、干扰他人操作
- ❌ 任何违反你所在国家/地区法律法规的行为

### 免责声明

- 本软件按"**现状**"提供，不附带任何明示或暗示的担保（详见 [LICENSE](LICENSE)）。
- 使用者需**自行承担全部使用后果**，包括但不限于账号封禁、数据损失、服务中断以及由此产生的任何直接或间接损失。
- 作者与贡献者**不对任何滥用行为负责**，也不承担因使用本软件导致的任何法律责任。
- 如果你不确定某个使用场景是否合规，请先阅读目标平台的服务条款，或直接不要使用。

**下载、编译或运行本软件，即表示你已阅读、理解并同意上述条款。**

---

## 许可证

MIT License — 详见 [LICENSE](LICENSE)
