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
│   ├── engine.py            # ClickerEngine 引擎类
│   └── macros.py            # 宏录制与播放
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
│   └── hotkey_manager.py    # 快捷键管理
│
├── tests/                   # 单元测试（43 个）
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
- 所有跨线程 UI 更新使用 `root.after()` 确保在主线程执行

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

- `pynput>=1.7`: 鼠标键盘控制
- `cryptography>=41.0`: 加密功能
- `customtkinter>=5.2`: UI 框架
- `tkinter`: Python 内置 GUI 库
