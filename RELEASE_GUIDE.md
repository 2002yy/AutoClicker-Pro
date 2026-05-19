# 自动发布指南

## 🚀 CI/CD 自动打包

本项目已配置 GitHub Actions 自动构建和发布流程。

### 触发方式

#### 1. 推送标签（推荐）
```bash
# 提交代码
git add .
git commit -m "发布新版本"

# 创建版本标签
git tag v1.0.0

# 推送到 GitHub（同时推送标签）
git push origin main --tags
```

#### 2. 手动触发
1. 进入仓库的 **Actions** 标签页
2. 选择 **Build and Release** 工作流
3. 点击 **Run workflow** 按钮
4. 选择分支后运行

### 构建产物

成功执行后，GitHub 会自动：

✅ **Windows**: 生成 `AutoClickerPro_Windows.zip` (包含 .exe)  
✅ **Linux**: 生成 `AutoClickerPro_Linux.tar.gz` (包含可执行文件)  
✅ **Release**: 在 Releases 页面创建新版本并上传两个压缩包

### 查看结果

1. 访问 https://github.com/你的用户名/你的仓库/releases
2. 找到最新版本的 Release
3. 下载对应系统的安装包

### 构建时间

通常 3-5 分钟即可完成 Windows 和 Linux 双平台构建。

---

## 📦 本地手动打包

### Windows
```bash
pip install -r requirements.txt
pyinstaller --onefile --name "AutoClickerPro" main.py
```
输出：`dist/AutoClickerPro.exe`

### Linux
```bash
pip install -r requirements.txt
pyinstaller --onefile --name "AutoClickerPro" main.py
chmod +x dist/AutoClickerPro
```
输出：`dist/AutoClickerPro`

---

## ⚠️ 注意事项

1. **首次使用**需要在 GitHub 仓库启用 Actions
2. 确保 `requirements.txt` 包含所有依赖
3. 版本号遵循语义化版本规范 (v1.0.0, v1.0.1, v2.0.0 等)
