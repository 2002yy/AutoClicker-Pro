# 🚀 自动点击器 Pro — 发布指南

> 本文档为唯一的发布入口，已合并 `PUBLISH_GUIDE.md`（CI/CD 流程 + FAQ）、`RELEASE_GUIDE.md`（本地打包 + 签名/误报处理）以及 `docs/PACKAGING.md`（PyInstaller 打包说明）三份内容。

## 📋 目录

- [快速开始](#快速开始)
- [CI/CD 工作流说明](#cicd-工作流说明)
- [本地手动打包](#本地手动打包)
- [代码签名与杀毒软件误报](#代码签名与杀毒软件误报)
- [Release 说明模板](#release-说明模板)
- [常见问题](#常见问题)
- [安全提示](#安全提示)

---

## ⚡ 快速开始

### 方式一：推送标签自动发布（推荐）

```bash
# 1. 提交所有更改
git add .
git commit -m "准备发布 v2.0.1"

# 2. 创建版本标签（格式：v主版本.次版本.修订号）
git tag v2.0.1

# 3. 推送到 GitHub（包含标签）
git push origin main --tags
```

推送后，GitHub Actions 会自动：
1. ✅ 在 Windows 环境编译 `.exe` 文件（`--onefile --windowed`）
2. ✅ 在 Linux 环境编译可执行文件
3. ✅ 创建 GitHub Release 并上传两个平台的安装包与 `SHA256SUMS.txt`
4. ✅ 生成发布说明（含中文 + 杀软误报声明 + SHA-256 校验块）

### 方式二：手动触发构建

1. 进入仓库 **Actions** 标签页
2. 选择 **Build and Release** 工作流
3. 点击 **Run workflow** 按钮
4. 输入版本号（如 `v2.0.1`）并运行

---

## 🔄 CI/CD 工作流说明

```
推送标签 v* 或 手动触发
         ↓
    ┌────────────┐
    │ 构建阶段   │
    ├────────────┤
    │ Windows    │──→ AutoClickerPro_Windows.zip（含 .exe + README + LICENSE）
    │ Linux      │──→ AutoClickerPro_Linux.tar.gz
    └────────────┘
         ↓
    ┌────────────┐
    │ 发布阶段   │ 计算 SHA-256 → 生成 changelog → create-release（含校验文件）
    └────────────┘
         ↓
    GitHub Release
```

| 平台 | 文件名 | 内容 |
|------|--------|------|
| **Windows** | `AutoClickerPro_Windows.zip` | `AutoClickerPro.exe` + README + LICENSE |
| **Linux** | `AutoClickerPro_Linux.tar.gz` | `AutoClickerPro` + README + LICENSE |

> 注意：CI 在构建前会运行单元测试；Windows job 跑 `python -m unittest discover tests -v`（Linux runner 无 X server，pynput 无法导入，故不在该侧执行）。
> **构建产物 `build/`、`dist/` 已加入 `.gitignore`，请勿提交。**

---

## 📦 本地手动打包

`build/`、`dist/` 产物已在 `.gitignore` 中忽略，请勿提交。

### Windows（推荐用打包脚本）

```bash
pip install pyinstaller pynput cryptography
python pack.py
```

`pack.py` 会先检查并自动安装缺失依赖（pyinstaller / pynput / cryptography），再以 `--onefile --windowed --clean --noconfirm` 调用 PyInstaller，输出 `dist/AutoClickerPro.exe`。（脚本末尾有 `input("按回车键退出...")`，仅适合本地双击运行，CI 不使用此脚本。）

也可直接调用 PyInstaller：

```bash
pip install -r requirements.txt
pyinstaller --onefile --windowed --name "AutoClickerPro" main.py
```

> `--windowed` **不可省略**，否则运行时会额外弹出黑色控制台窗口。如需图标，把 `icon.ico` 放在同级目录并加 `--icon=icon.ico`。

### Linux

```bash
pip install -r requirements.txt
pyinstaller --onefile --name "AutoClickerPro" main.py
chmod +x dist/AutoClickerPro
```

### 注意事项
- **不要**对已被 pip 收录的 Python 包用 `--add-data` 重复打包（如 `config;config`），会造成冗余与导入歧义。
- 若改用 `AutoClickerPro.spec`，请勿在其中写死本机绝对路径（如 `C:\Users\...\`），否则换机器构建必失败且泄露路径。

---

## 🛡️ 代码签名与杀毒软件误报

这是**发布前必须处理**的一项，否则大量用户会在下载时直接被浏览器或杀软拦截。

### 为什么会被误报

本程序同时具备三个在杀软眼中高度可疑的特征，误报几乎是必然的，而不是意外：

| 特征 | 杀软的判定 |
|------|-----------|
| 使用 pynput 注册系统级键盘钩子 | 疑似**键盘记录器（Keylogger）** |
| 模拟鼠标/键盘点击、注入输入事件 | 疑似**远控 / 自动化恶意软件** |
| PyInstaller `--onefile` 自解压运行 | 疑似**加壳程序（Packer）**，与勒索软件常用手法一致 |

在 VirusTotal 上，未签名的 PyInstaller 单文件 EXE 通常会有 **5–20 家引擎**标红，其中绝大多数是启发式误报（`Trojan.Generic`、`Wacatac`、`Heur.AdvML` 之类的泛化名称）。

### 处理方式（按性价比排序）

1. **提供 SHA-256 校验值** — 成本为零，先做这一步。每个 Release 都会自动生成 `SHA256SUMS.txt`，也可手动：
   ```powershell
   Get-FileHash .\AutoClickerPro.exe -Algorithm SHA256
   ```

2. **在 Release 说明中主动声明误报** — 成本为零，能显著降低用户疑虑（见下方模板）。

3. **向厂商提交误报申诉** — 免费，需要几天到几周。主要入口：
   - Microsoft Defender：<https://www.microsoft.com/en-us/wdsi/filesubmission>
   - 卡巴斯基、诺顿、Avast 等均有各自的 false positive 提交表单

4. **购买代码签名证书并签名** — 唯一的根治手段，需要付费。
   - **OV 证书**：约 $200–400/年，签名后仍需积累 SmartScreen 信誉，前期可能照样弹警告
   - **EV 证书**：约 $400–700/年，**签发即具备 SmartScreen 信誉**，可立即消除"未知发布者"警告；需硬件令牌或云 HSM
   - 签名命令：
     ```bash
     signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a dist\AutoClickerPro.exe
     signtool verify /pa /v dist\AutoClickerPro.exe
     ```
   - CI 中签名时，证书与口令必须放在 GitHub Secrets，**绝不能提交进仓库**

5. **提供源码运行方式作为兜底** — 被误杀的用户可以直接 `pip install -r requirements.txt && python main.py`。

---

## 📝 Release 说明模板

每次发布会自动生成以下内容的 Release 说明（CI 已内置杀软声明、使用限制与 SHA-256 校验块）：

```markdown
## 🎉 自动点击器 Pro v2.0.1

### ✨ 功能
- 🖱️ 鼠标连点（左/右/中键，固定坐标）
- 🔴 宏录制（鼠标点击 + 键盘按键），毫秒级回放，支持指定次数/时长
- ⌨️ 键盘连点 / 录制（回放时按"轻点"语义自动按下并释放）
- 🔐 本地 Fernet 加密存储（本地混淆级保护）
- 🔧 全局快捷键：F8 启停连点 / F10 开始录制 / F11 停止录制 / ESC 一键全停（窗口失焦时同样生效）
- 🎨 Win11 风格界面（Segoe UI + 蓝强调色主题）
- 🚀 单文件 EXE，无需安装 Python

### 🧪 质量
- 单元测试 64 项，覆盖引擎、加密、校验、快捷键、键盘录制/回放
- CI/CD 自动化构建（Windows + Linux），构建前跑测试
- 线程安全：状态加锁，后台线程经队列回主线程更新 UI

### ⌨️ 快捷键（全局生效）
- `F8`: 开始/停止连点
- `F10`: 开始录制
- `F11`: 停止录制
- `ESC`: 一键全停
- 录制时也会捕获键盘按键（F8/F10/F11/ESC 等控制键除外）

### ⚠️ 关于杀毒软件报毒
本程序需注册全局键盘钩子并模拟鼠标/键盘输入，可能被启发式引擎误报，
详见源码与 README「合法使用与免责声明」。也可不使用 EXE，直接：
`pip install -r requirements.txt && python main.py` 从源码运行。
本次发布文件 SHA-256 见 `SHA256SUMS.txt`。若不放心，请勿运行本程序。

### ⚖️ 使用限制
禁止用于违反目标平台服务条款的自动化（游戏外挂、刷单刷量等）。
```

---

## ❓ 常见问题

### Q1: 构建失败怎么办？
查看 Actions 页面的详细日志，常见原因：
- 依赖安装失败 → 检查 `requirements.txt`
- PyInstaller 打包错误 → 确认 `AutoClickerPro.spec` 中没有引用本机绝对路径（如 `C:\Users\...\`）
- 权限问题 → 确保有写入权限

### Q2: 如何自定义发布说明？
编辑 `.github/workflows/build.yml` 中的 `Generate changelog` 步骤（heredoc 需保持正确缩进，正文顶格会提前终止 `run: |` 块标量导致 YAML 非法）。

### Q3: 可以只构建一个平台吗？
可以，注释掉不需要的 job 即可：
```yaml
# build-linux:
#   ...
```

### Q4: 如何添加图标？
1. 准备 `.ico`（Windows）或 `.png`（Linux）图标文件
2. 修改 build.yml 中的 `--icon=NONE` 为 `--icon=path/to/icon.ico`
3. 将图标文件添加到仓库

### Q5: 如何设置预发布版本？
```yaml
- name: Create Release
  uses: softprops/action-gh-release@v1
  with:
    prerelease: true
```

---

## 🔐 安全提示

- ✅ 构建过程在 GitHub 官方服务器上进行，安全可靠
- ✅ 使用 `GITHUB_TOKEN` 自动授权，无需手动配置密钥
- ✅ 所有构建产物公开透明，可审查
- ⚠️ 若后续引入代码签名，证书与口令必须放在 **GitHub Secrets**，严禁提交进仓库

---

**祝发布顺利！🎉**
