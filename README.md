# 🖱️ AutoClicker Pro (全能连点器)

[个人开发/免费]

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-win)
![License](https://img.shields.io/badge/License-MIT-green)
![UI](https://img.shields.io/badge/UI-CustomTkinter-orange)

一款基于 Python 和 CustomTkinter 开发的现代化 Windows 连点器。
支持鼠标连点、键盘连点、宏录制与回放，拥有美观的 Win11 风格界面。
<img width="1028" height="814" alt="连点器Pro_1 0版 exe_20260111_194957" src="https://github.com/user-attachments/assets/7b13fda0-30c0-4692-a495-5ac8fc20081f" />


## ✨ 功能特性 (Features)

*   **🎨 现代化 UI**：采用 CustomTkinter 构建，完美融入 Windows 11 设计风格，支持高分屏。
*   **🖱️ 鼠标连点**：
    *   支持 左键 / 右键 / 中键。
    *   支持 单击 / 双击。
    *   支持 **固定坐标** 点击（F9 一键抓取）或跟随鼠标位置。
*   **⌨️ 键盘连点**：支持任意键盘按键的自动连按。
*   **🔴 宏录制 (Macro)**：
    *   所见即所得的键鼠操作录制。
    *   支持完美复刻操作节奏与路径。
    *   无限循环回放。
*   **⚙️ 灵活配置**：
    *   支持毫秒级间隔设置。
    *   多种停止条件：无限循环、指定次数、指定时长。
    *   配置自动保存 (JSON)。
*   **🚀 便携运行**：单文件 EXE，无需安装 Python 环境即可运行。

## 🛠️ 安装与使用 (Installation)

### 方式一：直接下载 (推荐)
前往 [Releases 页面](https://github.com/2002yy/AutoClicker-Pro/releases) 下载最新的 `.exe` 文件，双击即可运行。

### 方式二：源码运行
如果你想修改代码或二次开发，请按以下步骤操作：

## 🛠️ 安装与运行

### 安装依赖

在终端中执行以下命令安装所需库：

```bash
pip install -r requirements.txt
```
💡 建议在虚拟环境中运行，避免污染全局 Python 环境。

## 运行程序

```bash
python autoclicker.py
```
📖 快捷键说明

快捷键	 功能

F8	 启动 / 停止 普通连点（鼠标或键盘）

F9	 抓取当前鼠标坐标（填入固定位置）

F10	开始 / 停止 宏录制

F11	开始 / 停止 宏播放

📦 如何打包
本项目包含自动打包脚本。请先安装 pyinstaller：

```bash
pip install pyinstaller
```
然后运行打包脚本生成独立的 .exe 文件：

```bash
python pack.py
```
生成的可执行文件位于 dist/ 目录下。

⚠️ 免责声明
本软件仅供学习交流与辅助日常操作使用。

软件采用前台模拟物理输入的方式运行（非后台注入、非内存修改），不属于外挂。
严禁用于违反游戏用户协议、自动化作弊或任何违法场景。
使用本软件所引发的任何后果（如账号封禁等），作者概不负责。
🤝 贡献与反馈
欢迎提交 Issue 或 Pull Request！
