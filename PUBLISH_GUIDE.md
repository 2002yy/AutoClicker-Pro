# 🚀 自动点击器专业版 - 发布指南

## 📋 目录
- [快速开始](#快速开始)
- [CI/CD 工作流说明](#cicd-工作流说明)
- [手动触发构建](#手动触发构建)
- [自动发布流程](#自动发布流程)
- [常见问题](#常见问题)

---

## ⚡ 快速开始

### 方式一：推送标签自动发布（推荐）

```bash
# 1. 提交所有更改
git add .
git commit -m "准备发布 v1.0.0"

# 2. 创建版本标签（格式：v主版本。次版本.修订号）
git tag v1.0.0

# 3. 推送到 GitHub（包含标签）
git push origin main --tags
```

推送后，GitHub Actions 会自动：
1. ✅ 在 Windows 环境编译 `.exe` 文件
2. ✅ 在 Linux 环境编译可执行文件
3. ✅ 创建 GitHub Release 并上传两个平台的安装包
4. ✅ 生成精美的发布说明（含中文）

### 方式二：手动触发构建

1. 进入仓库 **Actions** 标签页
2. 选择 **Build and Release** 工作流
3. 点击 **Run workflow** 按钮
4. 输入版本号（如 `v1.0.0`）
5. 点击绿色 **Run workflow** 按钮

---

## 🔄 CI/CD 工作流说明

### 工作流程图

```
推送标签 v* 或 手动触发
         ↓
    ┌────────────┐
    │ 构建阶段   │
    ├────────────┤
    │ Windows    │──→ AutoClickerPro_Windows.zip
    │ (windows-latest) │
    │            │
    │ Linux      │──→ AutoClickerPro_Linux.tar.gz
    │ (ubuntu-latest) │
    └────────────┘
         ↓
    ┌────────────┐
    │ 发布阶段   │
    │ create-release │
    └────────────┘
         ↓
    GitHub Release
    - 精美发布说明
    - Windows 安装包
    - Linux 安装包
```

### 构建产物

| 平台 | 文件名 | 内容 |
|------|--------|------|
| **Windows** | `AutoClickerPro_Windows.zip` | `AutoClickerPro.exe` + README + LICENSE |
| **Linux** | `AutoClickerPro_Linux.tar.gz` | `AutoClickerPro` + README + LICENSE |

### 预计时间
- Windows 构建：~2 分钟
- Linux 构建：~1.5 分钟
- 发布创建：~30 秒
- **总计：约 3-5 分钟**

---

## 📝 自动发布说明模板

每次发布会自动生成以下内容的 Release 说明：

```markdown
## 🎉 自动点击器专业版 v1.0.0

### ✨ 新特性
- 🔐 **加密存储**: 宏录制文件采用 Fernet 对称加密
- 🧩 **模块化架构**: UI 与业务逻辑完全解耦
- ⚡ **高性能**: 优化的线程管理，低延迟响应
- 🛡️ **安全防护**: 完整的输入验证和防滥用机制
- 🎨 **现代化界面**: 简洁直观的用户体验

### 🔧 技术改进
- 分离配置文件 (constants/encryption/validation)
- 新增宏管理模块 (macros.py)
- 快捷键管理器 (hotkey_manager.py)
- 完整的单元测试覆盖 (36+ 测试用例)
- CI/CD 自动化构建

### 📦 安装说明
#### Windows
1. 下载 `AutoClickerPro_Windows.zip`
2. 解压到任意目录
3. 双击运行 `AutoClickerPro.exe`

#### Linux
1. 下载 `AutoClickerPro_Linux.tar.gz`
2. 解压：`tar -xzvf AutoClickerPro_Linux.tar.gz`
3. 运行：`./AutoClickerPro`

### ⌨️ 快捷键
- `F8`: 开始/停止连点
- `F9`: 开始/停止录制
- `F10`: 播放宏
- `ESC`: 停止当前操作
```

---

## ❓ 常见问题

### Q1: 构建失败怎么办？
**A:** 查看 Actions 页面的详细日志，常见原因：
- 依赖安装失败 → 检查 `requirements.txt`
- PyInstaller 打包错误 → 检查 `--add-data` 路径
- 权限问题 → 确保有写入权限

### Q2: 如何自定义发布说明？
**A:** 编辑 `.github/workflows/build.yml` 中的 `Generate changelog` 步骤，修改 heredoc 内容。

### Q3: 可以只构建一个平台吗？
**A:** 可以，注释掉不需要的 job 即可：
```yaml
# 注释掉 Linux 构建
# build-linux:
#   ...
```

### Q4: 如何添加图标？
**A:** 
1. 准备 `.ico` (Windows) 或 `.png` (Linux) 图标文件
2. 修改 build.yml 中的 `--icon=NONE` 为 `--icon=path/to/icon.ico`
3. 将图标文件添加到仓库

### Q5: 如何设置预发布版本？
**A:** 使用 `prerelease: true`：
```yaml
- name: Create Release
  uses: softprops/action-gh-release@v1
  with:
    prerelease: true  # 设置为预发布
```

---

## 🔐 安全提示

- ✅ 构建过程在 GitHub 官方服务器上进行，安全可靠
- ✅ 使用 `GITHUB_TOKEN` 自动授权，无需手动配置密钥
- ✅ 所有构建产物公开透明，可审查

---

## 📞 技术支持

如有问题，请提交 Issue 或联系维护者。

**祝发布顺利！🎉**
