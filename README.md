# 🎉 自动点击器专业版

[![Build and Release](https://github.com/user/repo/actions/workflows/build.yml/badge.svg)](https://github.com/user/repo/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-blue)](https://github.com/user/repo/releases)

**一款功能强大的跨平台自动点击器和宏录制工具**

---

## ✨ 特性亮点

- 🔐 **加密存储**: 宏录制文件采用 Fernet 对称加密，安全保护您的操作序列
- 🧩 **模块化架构**: UI 与业务逻辑完全解耦，代码更易维护
- ⚡ **高性能**: 优化的线程管理，低延迟响应
- 🛡️ **安全防护**: 完整的输入验证和防滥用机制
- 🎨 **现代化界面**: 简洁直观的用户体验
- 🌐 **跨平台支持**: Windows 和 Linux 完美运行

---

## 📦 快速安装

### Windows
1. 前往 [Releases](https://github.com/user/repo/releases) 页面
2. 下载 `AutoClickerPro_Windows.zip`
3. 解压到任意目录
4. 双击运行 `AutoClickerPro.exe`

### Linux
```bash
# 1. 下载安装包
wget https://github.com/user/repo/releases/latest/download/AutoClickerPro_Linux.tar.gz

# 2. 解压
tar -xzvf AutoClickerPro_Linux.tar.gz

# 3. 运行
./AutoClickerPro
```

---

## ⌨️ 快捷键

| 快捷键 | 功能 |
|--------|------|
| `F8` | 开始/停止连点 |
| `F9` | 开始/停止录制 |
| `F10` | 播放宏 |
| `ESC` | 停止当前操作 |

---

## 🚀 从源码构建

### 环境要求
- Python 3.8+
- pip 包管理器

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行程序
```bash
python main.py
```

### 打包为可执行文件
```bash
# Windows
pyinstaller --onefile --name "AutoClickerPro" --add-data "config;config" --add-data "core;core" --add-data "ui;ui" --add-data "utils;utils" main.py

# Linux
pyinstaller --onefile --name "AutoClickerPro" --add-data "config:config" --add-data "core:core" --add-data "ui:ui" --add-data "utils:utils" main.py
```

---

## 🏗️ 项目结构

```
/workspace/
├── main.py              # 程序入口
├── config/              # 配置模块
│   ├── constants.py     # 常量定义
│   ├── encryption.py    # 加密功能
│   └── validation.py    # 输入验证
├── core/                # 核心业务逻辑
│   ├── engine.py        # 主引擎
│   └── macros.py        # 宏管理
├── ui/                  # UI 层
│   ├── app.py           # 主应用窗口
│   └── components/      # UI 组件
├── utils/               # 工具模块
│   └── hotkey_manager.py # 快捷键管理
├── tests/               # 单元测试
└── .github/workflows/   # CI/CD 配置
```

详细文档：[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

---

## 🧪 运行测试

```bash
# 运行所有测试
python -m unittest discover tests -v

# 运行特定测试模块
python -m unittest tests.test_encryption -v
```

当前测试覆盖：**36+ 测试用例** ✅

---

## 📖 使用指南

### 基本连点
1. 设置点击间隔（毫秒）
2. 选择鼠标按键（左/右/中）
3. 点击"开始点击"或按 `F8`

### 录制宏
1. 点击"开始录制"或按 `F9`
2. 执行您的操作序列
3. 按 `ESC` 停止录制
4. 保存宏文件（加密存储）

### 播放宏
1. 加载之前保存的宏文件
2. 设置重复次数和间隔
3. 点击"播放宏"或按 `F10`

---

## 🔒 安全说明

- 宏文件采用 AES-256 加密存储
- 密钥派生使用 PBKDF2-SHA256 算法
- 无网络请求，所有数据本地存储
- 开源代码，透明可审查

详细安全策略：[SECURITY.md](SECURITY.md)  
隐私政策：[PRIVACY.md](PRIVACY.md)

---

## 🛠️ 技术栈

- **GUI 框架**: Tkinter
- **输入模拟**: pynput
- **加密库**: cryptography (Fernet)
- **打包工具**: PyInstaller
- **CI/CD**: GitHub Actions
- **测试框架**: unittest

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📬 联系方式

- 📧 Email: your.email@example.com
- 💬 Issues: [GitHub Issues](https://github.com/user/repo/issues)

---

## 🙏 致谢

感谢以下开源项目：
- [pynput](https://github.com/moses-palmer/pynput)
- [cryptography](https://cryptography.io/)
- [PyInstaller](https://www.pyinstaller.org/)

---

**⌨️ Made with ❤️ by AutoClicker Team**

*最后更新：2024 年 5 月*
