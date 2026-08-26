# 自动点击器 Pro - 项目结构说明

## 目录结构

```
├── main.py                  # 程序入口
├── requirements.txt         # 运行依赖（pynput / cryptography）
├── pack.py                  # 本地与 CI 共用的打包脚本（PyInstaller 单文件、无控制台）
│
├── config/                  # 配置模块
│   ├── constants.py         # 常量定义（颜色、字体、默认值等）
│   ├── encryption.py        # Fernet 对称加密（宏文件本地混淆级保护）
│   ├── macro_library.py     # 宏库：保存/读取/重命名/删除（加密 .enc 文件 + 元数据）
│   ├── settings_store.py    # 应用设置持久化（~/.autoclicker_pro/settings.json）
│   └── validation.py        # 输入验证（间隔、次数、坐标等）
│
├── core/                    # 核心业务逻辑层
│   ├── engine.py            # ClickerEngine：连点、录制、序列回放、拖拽轨迹平滑重演
│   └── macros.py            # ClickAction 数据模型（点击/按键/移动/拖拽折叠）
│
├── ui/                      # UI 界面层（tkinter/ttk 自定义浅色主题）
│   ├── app.py               # AutoClickerApp 主窗口：布局组装、滚动容器、UI 队列泵
│   ├── theme.py             # ttk 主题样式（Segoe UI、蓝 #0067C0 强调色）
│   └── components/
│       ├── settings_panel.py        # 参数设置区（间隔/次数/热键/点击类型/拾取坐标）
│       ├── action_list.py           # 动作列表（删除/上移/下移/清空）
│       ├── control_buttons.py       # 开始/停止按钮区
│       ├── status_bar.py            # 底部状态栏（固定不随内容滚动）
│       ├── hotkey_settings.py       # 快捷键设置组件
│       ├── macro_library_panel.py   # 宏库面板（列表/元数据/管理操作）
│       ├── field_dialog.py          # 坐标微调编辑对话框
│       └── tutorial_dialog.py       # 新手教程弹窗（首启自动弹出，可不再显示）
│
├── utils/                   # 工具模块
│   ├── hotkey_manager.py    # 全局快捷键管理（F8/F10/F11/ESC）
│   └── win_windows.py       # Win32 窗口枚举与前台窗口定位（窗口锚定坐标）
│
├── tools/
│   └── capture_docs_screens.py  # 文档截图生成脚本（docs/screenshots/*.png）
│
├── tests/                   # 单元测试（165 项：python -m unittest discover tests）
├── docs/                    # 文档
│   ├── TUTORIAL.md          # 用户图文教程
│   ├── PUBLISHING.md        # 发布指南（CI/CD、本地打包、签名与误报）
│   ├── PROJECT_STRUCTURE.md # 本文档
│   ├── screenshots/         # 文档配图（由 tools 脚本生成）
│   └── archive/             # 历史审计存档
└── .github/workflows/       # CI/CD 配置（推送 v* 标签自动构建发布）
```

## 架构设计

### 分层架构
1. **UI 层** (`ui/`): 纯界面展示，不包含业务逻辑
2. **业务逻辑层** (`core/`): 处理所有核心功能
3. **配置层** (`config/`): 管理常量、加密、宏库、验证

### 通信方式
- UI 层通过回调函数接收业务逻辑层的状态更新
- **所有跨线程 UI 更新统一投递到 `AutoClickerApp._ui_queue`**，由主线程每 50ms 轮询消费。
  Tkinter 不是线程安全的，直接从 pynput 监听线程调用 `root.after()` 并无保证，故改为队列泵。
- 全局快捷键回调同样先入队再执行，避免在监听线程里操作控件
- 引擎通过可选的 `ignore_click_predicate` 钩子向 UI 询问"该坐标是否在本窗口内"，
  以便录制时排除用户操作本程序界面产生的点击（引擎本身不依赖 Tk）

## 运行

```bash
pip install -r requirements.txt
python main.py
```

## 测试

```bash
python -m unittest discover tests -v
```

## 打包

```bash
python pack.py          # 交互式（自动补装 PyInstaller）
python pack.py --ci     # 非交互（CI 用）
```

产物为 `dist/AutoClickerPro.exe` 单文件；`*.spec` 为构建副产物，不入库。

## 依赖

- `pynput>=1.7`: 鼠标键盘控制与全局键盘钩子
- `cryptography>=41.0`: 宏文件加密
- `tkinter`: Python 内置 GUI 库（使用标准 `ttk` 控件，**未使用 customtkinter**）
- `pyinstaller>=6.0`: 仅打包用（dev only）
