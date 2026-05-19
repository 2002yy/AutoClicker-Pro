# 自动点击器 Pro

一个功能强大的自动点击器和宏录制工具，具有加密存储、模块化设计和完整的单元测试。

## 项目结构

```
/workspace/
├── main.py              # 程序入口
├── config/              # 配置模块
│   ├── constants.py     # 常量定义
│   ├── encryption.py    # 加密功能
│   └── validation.py    # 输入验证
├── core/                # 核心业务逻辑
│   ├── engine.py        # 主引擎（需要 X server）
│   └── macros.py        # 宏录制与播放
├── ui/                  # UI 层
│   ├── app.py           # 主应用窗口
│   └── components/      # UI 组件
│       ├── settings_panel.py
│       ├── action_list.py
│       ├── control_buttons.py
│       └── status_bar.py
├── utils/               # 工具模块
│   └── hotkey_manager.py # 快捷键管理
└── tests/               # 单元测试
    ├── test_encryption.py
    ├── test_validation.py
    ├── test_macros.py
    └── test_hotkey_manager.py
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行程序

```bash
python main.py
```

## 运行测试

```bash
# 运行所有测试
python -m unittest discover tests -v

# 运行特定测试模块
python -m unittest tests.test_encryption -v
python -m unittest tests.test_validation -v
python -m unittest tests.test_macros -v
```

## 主要功能

### 1. 加密存储
- 宏数据支持 Fernet 对称加密
- 可选择使用密码保护
- 密钥安全存储在 `~/.autoclicker_pro/`

### 2. 模块化设计
- UI 与业务逻辑完全解耦
- 配置信息集中管理
- 组件化 UI 设计

### 3. 线程安全
- 所有共享状态使用锁保护
- UI 更新在主线程执行
- 避免竞态条件

### 4. 输入验证
- 完整的时间输入验证
- 坐标验证
- 宏序列验证

### 5. 快捷键支持
- 全局快捷键注册
- 可自定义快捷键组合
- 线程安全的快捷键处理

## 测试结果

当前通过 **36 个单元测试**：
- ✅ 加密/解密测试 (6 个)
- ✅ 输入验证测试 (15 个)
- ✅ 宏模块测试 (15 个)

注意：`test_hotkey_manager.py` 需要 X server 环境才能运行。

## 安全性改进

1. **宏录制加密存储** - 使用 Fernet 对称加密
2. **权限控制** - 配置文件权限设置为 600
3. **防滥用机制** - 最小间隔限制
4. **资源正确释放** - 确保监听器和线程正确清理

## 代码质量

- ✅ 消除所有魔法值
- ✅ 方法职责单一
- ✅ 代码复用率高
- ✅ 完整的类型注解
- ✅ 详细的文档字符串
