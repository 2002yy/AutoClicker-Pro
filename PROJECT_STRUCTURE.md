# 自动点击器 Pro - 项目结构说明

## 目录结构

```
├── main.py                  # 程序入口
├── requirements.txt         # Python 依赖
├── pack.py                  # 打包脚本
│
├── config/                  # 配置模块
│   ├── constants.py         # 常量定义（颜色、字体、默认值等）
│   ├── encryption.py        # 加密功能（Fernet 对称加密）
│   └── validation.py        # 输入验证功能
│
├── core/                    # 核心业务逻辑层
│   ├── engine.py            # ClickerEngine：连点、录制、宏存取
│   └── macros.py            # ClickAction 数据模型
│
├── ui/                      # UI 界面层
│   ├── app.py               # 主应用程序类
│   └── components/          # UI 组件
│       ├── settings_panel.py
│       ├── action_list.py
│       ├── control_buttons.py
│       └── status_bar.py
│
├── utils/                   # 工具模块
│   └── hotkey_manager.py    # 全局快捷键管理（F8/F10/F11/ESC）
│
├── tests/                   # 单元测试（51 个）
├── docs/                    # 文档
└── .github/workflows/       # CI/CD 配置
```

## 架构设计

### 分层架构
1. **UI 层** (`ui/`): 纯界面展示，不包含业务逻辑
2. **业务逻辑层** (`core/`): 处理所有核心功能
3. **配置层** (`config/`): 管理常量、加密、验证

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

## 依赖

- `pynput>=1.7`: 鼠标键盘控制与全局键盘钩子
- `cryptography>=41.0`: 宏文件加密
- `tkinter`: Python 内置 GUI 库（使用标准 `ttk` 控件，**未使用 customtkinter**）
