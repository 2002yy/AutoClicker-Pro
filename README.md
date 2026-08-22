# 全能连点器 Pro

[![Build and Release](https://github.com/2002yy/AutoClicker-Pro/actions/workflows/build.yml/badge.svg)](https://github.com/2002yy/AutoClicker-Pro/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows-blue)](https://github.com/2002yy/AutoClicker-Pro/releases)
> Portfolio note: personal productivity tool project — CI, packaging, encryption and testing focused.
> 作品集说明：个人效率工具项目，重点展示 CI、打包、加密和测试能力。


**一款基于 Python 的 Windows 连点器。支持鼠标连点、鼠标宏录制与回放、全局快捷键与宏文件本地加密存储。**

## Responsible Use

This tool is intended for personal productivity automation, accessibility experiments, UI testing and repetitive desktop workflow automation.

Do not use it to violate software terms of service, bypass anti-cheat systems, automate online games, or perform abusive behavior on third-party services.

## 合规使用说明

本工具用于个人效率自动化、无障碍操作实验、桌面 UI 测试和重复流程辅助。

请勿用于违反软件服务条款、绕过反作弊、在线游戏作弊、批量刷接口或其他滥用场景。


---

## 功能特性

> ⚠️ 以下为**已实现**功能；"规划中"为尚未实现、此前文档曾误述为已实现的部分。

- 🖱️ **鼠标连点** — 支持左键/右键/中键，固定坐标，按配置间隔自动点击（**已实现**）
- 🔴 **宏录制（鼠标 + 键盘）** — 录制鼠标点击与键盘按键序列，回放按录制时的真实节奏执行（时间戳原速回放），支持指定次数重复（**已实现**；录制时落在本程序窗口内的点击自动忽略）
- ⌨️ **键盘连点 / 录制** — 录制键盘按键并在回放时自动按下释放（**已实现**）
- ⌨️ **组合键与拖拽宏** — Ctrl+C / Shift+单击 等修饰键组合录为单条动作并整体还原；拖拽录制移动轨迹（5px/30ms 双阈值采样），回放按原速平滑重演而非瞬移（**已实现**）
- 🪟 **窗口锚定坐标** — 录制时记录点击所在的前台窗口标题与相对偏移，回放时按同名窗口当前位置重算坐标：窗口挪位/多显示器切换后宏依然点得准。找不到目标窗口时自动降级为绝对坐标并在状态栏提示（**已实现**）
- 🔐 **加密存储** — 宏文件采用本地 Fernet 对称加密（**已实现**；密钥存于用户目录 `~/.autoclicker_pro/`，属**本地混淆级**保护，并非对抗同机攻击者的机密保护）
- ⚙️ **灵活配置** — 毫秒级间隔、按住时长、重复次数/间隔设置（**已实现**）
- 📚 **宏库管理** — 宏按名称保存在 `~/.autoclicker_pro/macros/`，下拉即可加载/删除，支持与任意位置 .enc 文件导出/导入（**已实现**）
- ⏱️ **延迟启动 / 自动停止** — 开始前倒计时（等待期可随时取消），并可设置整个运行的最长时长，0 为不限（**已实现**）
- 🔧 **全局快捷键** — F8 启停连点、F10 开始录制、F11 停止录制、ESC 一键全停，窗口失焦时同样生效（**已实现**）
- ✏️ **宏编辑** — 对已录制的动作可删除选中 / 上移 / 下移 / 一键清空，无需为单个误触重录整条序列（**已实现**）
- ⌨️ **快捷键自定义** — 四个全局快捷键均可在界面修改（支持 ctrl+shift+x 组合），自动持久化并在下次启动生效（**已实现**）
- 🎨 **Win11 风格界面** — 基于 ttk 的自定义浅色主题：Segoe UI 字体、蓝(#0067C0)强调色主按钮、扁平卡片与细边框（**已实现**）
- 🚀 **便携运行** — 单文件 EXE，无需安装 Python（**已实现**）

> 说明：功能均已由单元测试覆盖（含 GUI 冒烟测试），测试数以 CI 实时结果为准。加密存储为本地混淆级保护，详见「合法使用与免责声明」。
>
> 回放时序说明：录制产生的序列按各动作的原始时间戳回放（真实节奏）；无时间戳数据的旧文件退回固定"点击间隔"均速回放。
>
> 轨迹说明：拖拽轨迹仅在鼠标按键按住期间采样（双阈值：位移 ≥5px 且间隔 ≥30ms），动作列表中折叠为一行显示，可整段删除。

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

以下为**默认**全局快捷键，均可在界面"全局快捷键"区自定义（自动持久化），窗口在后台时同样生效。

| 快捷键 | 功能 |
|--------|------|
| `F8` | 开始 / 停止连点 |
| `F10` | 开始录制 |
| `F11` | 停止录制 |
| `ESC` | 一键全停（同时终止录制与连点） |

> 说明：全局快捷键依赖系统级键盘钩子。若在受限环境（远程桌面、部分安全软件拦截、无输入权限）下注册失败，
> 程序会在状态栏提示并自动降级为"仅界面按钮 + 窗口内 ESC"，主功能不受影响。
>
> 录制期间，落在本程序窗口内的点击会被自动忽略，因此点击"停止录制"按钮本身不会被录进宏里。键盘按键会被一并捕获（F8/F10/F11/ESC 等控制键除外）：普通键录为轻点，Ctrl/Shift/Alt+按键 录为组合键、回放整体还原；修饰键与鼠标点击的组合（如 Shift+单击）同样支持。

---
## Engineering Highlights

- Layered structure: config / core / ui / utils
- Macro recording and playback with original-timestamp timing (chord & drag aware)
- Fernet encrypted macro storage
- PyInstaller single-file EXE packaging
- GitHub Actions build workflow with GUI smoke tests
- Unit tests (count tracked by CI)


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

## Roadmap

- [x] Macro editing UI
- [x] Hotkey customization
- [x] Coordinate adaptation (window-title anchoring with graceful fallback)
- [x] Mouse movement trajectory recording (smooth drags)
- [x] Multi-profile macro management
- [x] Scheduled auto-click tasks (start delay + auto stop)
- [ ] Internationalization (i18n)

