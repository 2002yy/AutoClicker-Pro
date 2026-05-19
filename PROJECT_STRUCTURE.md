# 自动点击器 Pro - 项目结构说明

## 📁 目录结构

```
/workspace/
├── main.py                  # 程序入口
├── requirements.txt         # Python 依赖
│
├── config/                  # 配置模块
│   ├── __init__.py         # 模块导出
│   ├── constants.py        # 常量定义（颜色、字体、默认值等）
│   ├── encryption.py       # 加密功能（Fernet 对称加密）
│   └── validation.py       # 输入验证功能
│
├── core/                    # 核心业务逻辑层
│   ├── __init__.py         # 模块导出
│   └── engine.py           # ClickerEngine 引擎类
│
├── ui/                      # UI 界面层
│   ├── __init__.py         # 模块导出
│   ├── app.py              # 主应用程序类
│   └── components/         # UI 组件
│       ├── __init__.py     # 组件导出
│       ├── settings_panel.py    # 设置面板
│       ├── action_list.py       # 动作列表
│       ├── control_buttons.py   # 控制按钮
│       └── status_bar.py        # 状态栏
│
└── tests/                   # 单元测试
    ├── __init__.py
    ├── test_validation.py   # 验证模块测试
    └── test_encryption.py   # 加密模块测试
```

## 🏗️ 架构设计

### 分层架构
1. **UI 层** (`ui/`): 纯界面展示，不包含业务逻辑
2. **业务逻辑层** (`core/`): 处理所有核心功能
3. **配置层** (`config/`): 管理常量、加密、验证

### 通信方式
- UI 层通过回调函数接收业务逻辑层的状态更新
- 所有跨线程 UI 更新使用 `root.after()` 确保在主线程执行

## ✅ 已解决的问题

| 问题 | 解决方案 |
|------|----------|
| 宏录制存储明文 | 使用 Fernet 加密，密钥存储在 `~/.autoclicker_pro/.key` |
| UI 与业务逻辑强耦合 | 完全分离为 `ui/app.py` 和 `core/engine.py` |
| 全局状态依赖 | 使用 `threading.Lock` 保护共享状态 |
| 硬编码魔法值 | 全部移至 `config/constants.py` |
| 方法过长 | 拆分为多个小组件和方法 |
| 重复代码 | 提取公共组件（SettingsPanel, ActionList 等） |
| 配置分散 | 集中到 `config/` 模块管理 |
| 输入验证不足 | 完整的验证规则和错误提示 |
| 多线程竞争 | 属性访问器 + 锁机制 |
| 资源未释放 | `cleanup()` 方法确保清理 |

## 🧪 测试

运行所有测试：
```bash
python -m unittest discover tests -v
```

测试结果：21 个测试全部通过 ✓

## 🚀 运行

```bash
python main.py
```

注意：需要 GUI 环境（X Server）和安装依赖：
```bash
pip install -r requirements.txt
```

## 📦 依赖

- `pynput>=1.7.6`: 鼠标键盘控制
- `cryptography>=3.4.8`: 加密功能
- `tkinter`: Python 内置 GUI 库
