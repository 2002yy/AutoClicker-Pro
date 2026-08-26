# AutoClickerPro 原型软件审计报告

> 审计对象：`C:\Users\Zhang\Desktop\连点器`（连点器 Pro，v2.0.0）
> 审计范围：全部源码（`main.py` / `config/` / `core/` / `ui/` / `utils/`）、构建脚本、测试、文档（README / PRIVACY / SECURITY / PACKAGING）
> 审计方式：静态代码审查 + 文档声明一致性比对 + 测试覆盖评估

---

## 一、总体结论

| 维度 | 评级 | 说明 |
|---|---|---|
| 安全（机密性/完整性） | 🟡 中低 | 无网络、无遥测，加载外部宏有校验；但"加密存储"实为本地混淆，密钥明文落盘 |
| 隐私 | 🟢 良好 | PRIVACY 核心声明（无网络/无遥测）属实 |
| 功能完整性 | 🔴 较差 | README 宣传的"键盘连点""录制键鼠""F8–F11 全局快捷键""Win11 风格 UI"均未实现 |
| 代码质量 | 🟡 中 | 存在双重宏实现（死代码）与大量未使用代码，模块分层清晰是亮点 |
| 构建/发布 | 🔴 严重 | `AutoClickerPro.spec` 硬编码他人机器路径，在本机**构建必失败**且泄露他人主目录 |
| 测试 | 🟡 中 | 测试覆盖的是**未使用的死代码**，真实核心 `ClickerEngine` **零测试** |
| 合规/可接受使用 | 🟡 提示 | 连点器可能违反部分平台 ToS，缺少免责声明 |

> ⚠️ **上表为初次审计时（修复前）的评级，请勿据此判断当前状态。**
> 两批修复已完成，最新进展见 [第十章](#十修复进度2026-08-04) 与 [第十一章](#十一第二批修复2026-08-04p2p3)。
> 截至第二批修复后：构建/发布已由 🔴 转 🟢（spec 与 CI 均可用），测试由 🟡 转 🟢（51 项覆盖真实核心），
> 合规已由 🟡 转 🟢（免责声明落地）；功能完整性仍为 🟡（键盘连点/键盘录制/Win11 UI 未实现，但文档已如实标注）。

**一句话结论**：代码本身干净、无恶意行为、无远程通信，可以作为本地原型使用；但**文档严重夸大功能**（多处宣传特性根本没写），构建脚本含致命硬编码路径，测试覆盖名不副实。在对外发布前必须修正功能声明、修复 spec、并补齐核心测试。

---

## 二、安全与隐私

### ✅ S1【正面】无网络、无遥测（PRIVACY 声明属实）
代码中没有任何 `socket` / `requests` / `urllib` 等网络引用。`pynput` 仅通过 ctypes 注册全局钩子，不产生网络通信。PRIVACY.md 的"Zero Data Collection / No network requests"**准确**。
- 证据：`core/engine.py`、`utils/hotkey_manager.py` 均无网络调用。

### 🟡 S2【中】"加密存储"实为混淆，密钥以明文落盘
`EncryptionManager` 生成一个随机口令并**明文**写入 `~/.autoclicker_pro/.key`（`{'password': ...}`）。在 Windows 上 `os.chmod(0o600)` 实际无效，任何能读取该用户目录的人都能直接解密全部 `.enc` 宏文件。
- 对"窃取宏文件但拿不到密钥"的威胁模型几乎不成立（同一账号下两者都可读）。
- 证据：`config/encryption.py:94-105`（`_load_or_create_key` 保存明文口令）、`config/constants.py:72-74`。
- 建议：要么**由用户口令派生密钥**（不落盘），要么在文档中明确"仅本地混淆、非机密保护"，避免给用户错误的安全感。
- 备注：PBKDF2(100000 次, SHA256, 32 字节) 的参数本身合理。

### 🟡 S3【低】SECURITY.md 称"整个工具是单文件 Python"——不实
实际为多模块项目（`config/` `core/` `ui/` `utils/`）。虽仍可审查，但表述误导。
- 证据：`SECURITY.md:23` vs 项目结构。

### 🟡 S4【低】PRIVACY.md 称 UI 框架为 customtkinter——不实
应用实际用标准 `tkinter.ttk`，全代码无 `customtkinter` 导入。
- 证据：`PRIVACY.md:25` vs `ui/app.py:6`（`import tkinter as tk`）。

### ✅ S5【正面】加载外部宏有严格校验，无反序列化/代码执行风险
`engine.load_sequence` → `decrypt_macro` → `json.loads` → `validate_macro_sequence` 逐字段校验 `x/y/button/action_type` 与取值范围，`button_map.get(..., left)` 兜底。即便加载恶意 `.enc`，也只会得到合法动作或抛验证错误，不会执行任意代码。
- 证据：`config/validation.py:202-276`、`core/engine.py:282-293`。

---

## 三、功能完整性（与 README 声明逐项比对）

### 🔴 F1【高】"键盘连点"功能完全未实现
- `engine` 实例化了 `self.keyboard_controller = keyboard.Controller()`（`core/engine.py:27`），但**从未调用**其 `.press()`。
- 点击核心 `_execute_clicking` 只移动鼠标、做鼠标按下/释放（`core/engine.py:127-169`）。
- 设置面板只有时间间隔/次数，**没有"选择按键"的控件**（`ui/components/settings_panel.py`）。
- README 却明确写："⌨️ 键盘连点 — 支持任意键盘按键的自动连按"。
- 影响：核心宣传功能缺失。

### 🔴 F2【高】"录制键鼠操作"——实际只录鼠标，键盘不录制
- 录制时键盘监听器 `_on_key_press` 仅处理 ESC 停止（`core/engine.py:257-266`），不记录任何按键。
- `ClickAction` 数据类只有 `x/y/button/action_type`，**没有 key 字段**（`core/macros.py:16-22`）。
- README 写："🔴 宏录制 — 录制键鼠操作并以毫秒精度回放"。
- 影响：宏是"纯鼠标"宏，与宣传不符。

### 🟡 F3【中】全局快捷键 F8–F11 未接线
- `constants.py:65-69` 定义了 `HOTKEY_START_STOP='<F8>'` 等，并写好了完整的 `HotkeyManager`（`utils/hotkey_manager.py`），但**该类从未被 import 或实例化**。
- 应用仅用 tkinter 绑定 `Escape`，且只用于"停止录制"（`ui/app.py:103-110`）。**无法用快捷键启停点击**。
- 影响：内部状态（常量/类）与真实行为不一致；用户无法在窗口失焦时控制程序。

### 🟡 F4【中】"Win11 风格界面 / customtkinter"未实现
实际是原生 `ttk` 控件，无 customtkinter、无主题/圆角/阴影等 Win11 风格。README 曾围绕 customtkinter 描述（已于第三批修复中改用 ttk 自定义 Win11 主题），相关打包说明已并入 `PUBLISHING.md`。

---

## 四、代码质量

### 🟡 C1【中】双重宏实现，一半是死代码
- 应用真正走的是：`ClickerEngine`（`core/engine.py`）+ `encrypt_macro/decrypt_macro`（`config/encryption.py`）。
- `core/macros.py` 里的 `MacroRecorder` / `MacroPlayer` / `MacroStorage` **完全没有被任何代码引用**（UI 只用 `ClickerEngine`）。
- 两套实现并存，维护者易混淆，且其中一套带 bug（见 C2）。

### 🟡 C2【中】`MacroStorage.load_macro` 的加密检测启发式错误
- 判断逻辑：`any(b > 127 or b < 32 for b in first_bytes)`（`core/macros.py:211-221`）。
- Fernet 输出是 Base64（ASCII 可打印，字节全在 32–126），该条件**永远为假** → 把真加密文件误判为明文 → `json.loads(base64垃圾)` 崩。
- 反过来，含中文的明文宏（UTF-8 字节 >127）会被**误判为加密**。
- 该路径当前未被使用，但逻辑本身错误，且被测试"伪装通过"（见 T2）。

### 🟡 C3【低】大量未使用代码/常量
`KEY_MAP`（engine 导入但未用）、`BUTTON_MAP_REVERSE`、`HotkeyManager`、`keyboard_controller`、`MACROS_DIR`、`DEFAULT_MACRO_FILE`、`ENCRYPTED_CONFIG_FILE` 等。建议清理以降低认知负担。

### 🟡 C4【低】录制会捕获自身 UI 按钮点击
录制期间全局监听鼠标，点"停止录制"按钮本身也会被录成一次动作，回放时会在按钮位置多发一次点击。
- 证据：`core/engine.py:_on_mouse_click`（全局监听）。
- 建议：录制时忽略本应用窗口区域的点击，或提供"排除 UI"开关。

### ✅ 正面：线程与回调设计合理
`is_running`/`is_recording` 用锁保护；后台线程通过 `root.after(0, ...)` 回到主线程更新 UI（`ui/app.py:209,231`），避免了 Tkinter 跨线程崩溃。模块分层（配置/核心/UI/工具）清晰、UI 与逻辑解耦良好。

---

## 五、构建与发布

### 🔴 B1【严重·构建阻断】`AutoClickerPro.spec` 硬编码他人机器路径
- `AutoClickerPro.spec:8`：`datas=[('C:\\Users\\96967\\AppData\\Local\\Programs\\Python\\Python312\\Lib\\site-packages\\customtkinter', 'customtkinter')]`
- 在 Zhang 的机器上该路径不存在 → **用 spec 构建必然失败**。
- 同时**泄露了另一用户（96967）的主目录路径**，属于信息泄露。
- `build/` 目录下的 `Analysis-00.toc` 同样写死了 `96967` 的路径，说明该构建产物来自他人环境并被提交。
- 建议：删除硬编码绝对路径，改用 `customtkinter.__file__` 动态获取（正如 `pack.py` 所做的），或直接用 `pack.py`；**不要提交含他人路径的构建产物**。

### 🟡 B2【中】customtkinter 是"幽灵依赖"
`pack.py:16-52` 与 `requirements.txt:1` 都把 customtkinter 列为依赖/打包内容，但代码未使用 → 徒增 EXE 体积并误导贡献者。
- 建议：从 `requirements.txt`、`pack.py`、`PRIVACY.md` 移除 customtkinter（已完成；`PACKAGING.md` 已并入 `PUBLISHING.md`）。

### 🟡 B3【低】仓库提交了二进制与缓存
`dist/AutoClickerPro.exe`（二进制）与 `build/`（`.pyc`/`.toc`/`.pkg`/`.zip`）被提交进仓库。建议加入 `.gitignore`，仅保留源码与 `pack.py`。

### 🟡 B4【信息】杀软误报与 SmartScreen 风险
PyInstaller `--onefile` + `pynput` 全局键盘/鼠标钩子，极易触发杀软"键盘记录器/远控"启发式告警；未签名 EXE 会触发 Windows SmartScreen。发布前建议：代码签名、在文档中说明、并保留"源码运行"入口。

---

## 六、测试

### 🔴 T1【高】测试覆盖的是死代码，核心 `ClickerEngine` 零测试
- `tests/test_macros.py` 测的是 `MacroRecorder/MacroPlayer/MacroStorage`（`core/macros.py`）——这些**应用根本不用**。
- 实际应用核心 `core/engine.py` 的 `ClickerEngine` **没有任何测试文件**。
- README 称"43 个测试全部通过"——真实但不具价值。
- 建议：为 `ClickerEngine` 补单测（用 mock 的 `mouse.Controller`/`keyboard.Controller`，重点测配置更新、序列校验、save/load 路径）。

### 🟡 T2【中】`test_save_and_load_encrypted_macro` 靠异常继承"蒙混过关"
该测试对"无密码加载加密宏"断言 `assertRaises(ValueError)`。实际因 C2 的检测启发式失效，抛出的是 `json.JSONDecodeError`——而它**恰好是 `ValueError` 的子类**，于是测试通过，却掩盖了真实 bug。
- 建议：修正 C2 的检测逻辑后，断言具体异常类型/消息。

---

## 七、合规与可接受使用

### 🟡 L1【提示】缺少 ToS / 合法使用免责声明
连点器类工具常被游戏或应用的服务条款禁止。软件本身合法，但 README 未说明"仅用于已授权/合法的场景，请遵守目标平台 ToS"。建议补充，降低法律风险与用户误解。

---

## 八、优先修复清单（建议顺序）

| 优先级 | 项 | 动作 |
|---|---|---|
| P0 | B1 | 删除/修复 `AutoClickerPro.spec` 硬编码路径，清理泄露他人路径的 `build/` 产物 |
| P0 | F1/F2/F4 | 要么实现键盘连点/键盘录制/Win11 UI，要么**如实修改 README**（推荐先改文档，再排期开发） |
| P1 | B2 | 移除 customtkinter 幽灵依赖（requirements/pack.py/文档） |
| P1 | T1 | 为 `ClickerEngine` 补真正的核心测试 |
| P1 | C1/C2 | 删除 `core/macros.py` 未使用类，或统一到 engine；修复加密检测启发式 |
| P2 | S2 | 加密改由用户口令派生密钥，或文档明确"仅本地混淆" |
| P2 | F3 | 接线 `HotkeyManager` 实现 F8–F11，或删除相关常量 |
| P2 | C3/C4 | 清理死代码；录制时排除自身 UI 点击 |
| P3 | S3/S4/L1 | 修正 SECURITY/PRIVACY 文档误述，补充 ToS 免责声明 |
| P3 | B3/B4 | 加 `.gitignore`；发布前代码签名并说明杀软误报 |

---

## 九、审计未发现的问题（正面小结）
- 无恶意代码、无后门、无隐蔽网络回传。
- 隐私声明（无网络/无遥测）基本属实。
- 外部宏加载有输入校验，无 RCE/反序列化风险。
- 线程与 UI 更新设计正确，模块解耦清晰。
- 代码注释与文档（除功能夸大外）较规范。

> 本审计基于静态审查，未执行动态运行；如需，我可以进一步：修复 `AutoClickerPro.spec` 与清理幽灵依赖、为 `ClickerEngine` 补充单元测试、或按你选择的方向（实现功能 / 收敛文档）落地修改。

---

## 十、修复进度（2026-08-04）

用户确认"开始修复"，已落地以下 P0/P1 项（全部通过 `python -m unittest discover tests`，共 52 项）：

| 状态 | 项 | 改动 |
|---|---|---|
| ✅ 已修复 | B1 | `AutoClickerPro.spec` 移除硬编码 `C:\Users\96967\...` 路径与未使用的 customtkinter `datas`，重写为干净 onefile/windowed spec |
| ✅ 已修复 | B2 | `pack.py` 移除 customtkinter 安装与 `--add-data`；`requirements.txt` 删除 customtkinter 行 |
| ✅ 已修复 | B3 | 新增 `.gitignore`（忽略 `build/` `dist/` `__pycache__/` `.workbuddy/` 等） |
| ✅ 已修复 | F1/F2/F4/S3/S4 | README 新增"规划中"区块，如实标注键盘连点/键盘录制/全局快捷键/Win11 UI 未实现；SECURITY 改为"多模块项目"；PRIVACY 与 PACKAGING 的 customtkinter → tkinter；PACKAGING 修正 `SOURCE_FILE=main.py` 与手动命令 |
| ✅ 已修复 | C2 | `core/macros.py` 的 `load_macro` 加密检测改为基于 `json.loads` 判定，修正此前对 Base64 误判为明文、对中文误判为加密的 bug |
| ✅ 已修复 | T1 | 新增 `tests/test_engine.py`，用 mock 控制器测试 `ClickerEngine` 配置/线程安全/点击调用/ save-load 往返/非法文件拒绝；原死代码测试仍保留 |

### 首批修复时尚未处理（规划为下一批，已于第十一章完成大部分）

> 以下为第一批修复时的待办计划。**其中 F3 全局快捷键、C1/C3 死代码、C4 录制排除自身点击、L1 合规免责、B4 签名说明 已在「第十一章 · 第二批修复」全部落地**；键盘连点/键盘录制（F1/F2）、Win11 UI（F4）、口令派生加密（S2）仍未实现，见第十一章末尾「仍未处理」。

- **P2 功能实现**：键盘连点、键盘录制、Win11 UI —— 当前按"文档收敛"处理，未实际开发（F3 全局快捷键已在本批完成）。
- **P2 加密**：S2 建议改为"用户口令派生密钥"或文档明确"仅本地混淆"；本次仅文档标注，未改机制。
- **清理**：`build/`、`dist/` 含旧构建产物（部分仍带 `96967` 路径），已 gitignore；可手动删除后重新构建。

---

## 十一、第二批修复（2026-08-04，P2/P3）

用户确认"下一批"，已落地以下内容（`python -m unittest discover tests` 共 **51 项全部通过**，另加一次真实 GUI 冒烟测试）。

### 已修复

| 状态 | 项 | 改动 |
|---|---|---|
| ✅ | **F3** 全局快捷键 | `HotkeyManager` 正式接入 `ui/app.py`：`F8` 启停连点、`F10` 开始录制、`F11` 停止录制、`ESC` 一键全停，**窗口失焦时同样生效**。`constants.py` 的快捷键由 Tk 风格 `'<F8>'` 改为 pynput 风格 `'f8'`（原格式根本无法被 `HotkeyManager` 匹配），删除未实现的 `HOTKEY_PICK_LOCATION`(F9)。注册失败时（远程桌面/安全软件拦截）状态栏提示并降级为界面按钮，不崩溃 |
| ✅ | **F3-bug** 按键去抖 | `HotkeyManager._on_press` 原先没有去重，长按 F8 时操作系统的按键重复事件会在一秒内触发几十次回调（连点会被反复启停）。现按"键已在按下集合中则忽略"处理，并为 `_pressed_keys` 补齐线程锁 |
| ✅ | **C4** 排除自身点击 | 引擎新增可选钩子 `ignore_click_predicate`；`ui/app.py` 通过 `<Configure>` 事件缓存本窗口屏幕矩形（含边框/标题栏），录制时落在窗口内的点击直接丢弃。**避免"点停止录制按钮"这一动作被录进宏**。引擎不反向依赖 Tk，分层未被破坏 |
| ✅ | **C1/C3** 死代码清理 | 删除 `core/macros.py` 中零调用的 `MacroRecorder` / `MacroPlayer` / `MacroStorage`（仅保留 `ClickAction` 数据模型）；`core/__init__.py` 同步收敛导出；`tests/test_macros.py` 移除对应测试。删除未使用常量 `KEY_MAP` / `BUTTON_MAP_REVERSE` / `MACROS_DIR` / `DEFAULT_MACRO_FILE` / `ENCRYPTED_CONFIG_FILE` / `ENCRYPTION_ALGORITHM` 及 `engine.py` 中实例化后从未调用的 `keyboard_controller` |
| ✅ | **L1** 合规免责 | README 新增「⚖️ 合法使用与免责声明」：明确允许用途（办公自动化 / UI 测试 / 无障碍辅助）与禁止用途（违反平台 ToS 的游戏外挂、刷单刷量、绕过人机验证、未授权设备），并声明使用者自负后果 |
| ✅ | **B4** 签名与误报 | `RELEASE_GUIDE.md` 新增「代码签名与杀毒软件误报」章节：解释三重可疑特征（键盘钩子 / 输入注入 / PyInstaller 加壳）为何必然触发启发式误报，给出按性价比排序的五级处理方案（SHA-256 → 主动声明 → 厂商申诉 → OV/EV 证书 → 源码兜底）与 `signtool` 命令 |

### 本批新发现并顺手修复的问题

| 严重度 | 问题 | 说明与处理 |
|---|---|---|
| 🔴 **严重** | **`.github/workflows/build.yml` 本身是非法 YAML** | changelog 步骤的 heredoc 正文顶格书写，提前终止了 `run: \|` 块标量，导致整个 workflow 解析失败。**这条流水线从未成功运行过**，README 顶部的 build 徽章一直是摆设。已重写为正确缩进（YAML 剥离块缩进后 shell 仍收到顶格文本），并在本地实跑该步骤验证产出 |
| 🟠 高 | CI 打包漏了 `--windowed` | Windows 构建命令为 `pyinstaller --onefile ...`，缺 `--windowed`，发布出去的 EXE 会额外弹出黑色控制台窗口。已补齐；`RELEASE_GUIDE` 的手动命令同样修正 |
| 🟠 高 | CI 用 `--add-data` 重复打包源码 | `--add-data "config;config" ...` 把已被 import 分析收录的 Python 包又作为 data 复制一份，冗余且可能造成导入歧义。已移除 |
| 🟡 中 | CI 从不跑测试 | 构建前无任何测试步骤。已在 Windows job 增加 `python -m unittest discover tests -v`（Linux runner 无 X server，pynput 无法导入，故不在该侧执行） |
| 🟡 中 | 跨线程直接调用 `root.after()` | 引擎回调从 pynput 监听线程直接调 `root.after()`，Tkinter 并不保证该调用线程安全。已改为 `queue.Queue` + 主线程 50ms 轮询泵（`_dispatch_to_ui` / `_drain_ui_queue`），快捷键回调走同一通道 |
| 🟡 中 | 网格伸缩权重错位 | `main_frame.rowconfigure(4, weight=1)` 把伸缩权重给了状态栏而非动作列表，窗口拉高时列表不跟着变高。已随布局重排修正 |
| 🟡 中 | 发布说明与实际功能不符 | `build.yml` / `PUBLISH_GUIDE.md` 的 Release 模板仍写着 `F9 录制`、`F10 播放宏`、"36+ 测试用例"、"防滥用机制"、"支持键盘宏录制"。已全部按实际情况改写，并在 Release 说明中内置杀软误报声明、使用限制与自动生成的 SHA-256 校验块 |

### 验证方式
- `python -m unittest discover tests` → **51 tests, OK**（新增录制过滤 4 项、快捷键去抖 6 项、`ClickAction` 往返 1 项）
- 真实 GUI 冒烟：实例化 `AutoClickerApp` → 确认注册到 `['esc','f10','f11','f8']`、监听器 running、窗口矩形计算正确、内外点判定正确、UI 队列可被主线程消费、`on_close` 干净退出
- `python -m compileall ui core config utils main.py pack.py` → 全部通过
- `build.yml` 用 PyYAML 解析通过，并在本地 bash 实跑 changelog 生成步骤，确认 heredoc 与 SHA-256 追加均正常

### 仍未处理

> 以下项中的 F1/F2、F4、文档重复、构建产物均已在「第十二章 · 第三批修复」完成，**仅 S2 仍未处理**。

- ~~**F1/F2**：键盘连点、键盘录制（已在第十二章实现）~~
- ~~**F4**：Win11 风格 UI（已在第十二章实现 ttk 自定义主题）~~
- **S2**：加密仍为固定密钥的本地混淆，未改为用户口令派生（文档已明确说明其保护级别）
- ~~**文档重复**：`PUBLISH_GUIDE.md` 与 `RELEASE_GUIDE.md`（已合并为单一 `PUBLISHING.md`）~~
- ~~**构建产物**：`build/`、`dist/` 旧产物（已删除并重新验证构建）~~

---

## 十二、第三批修复（2026-08-04，F1/F2/F4 + 收尾）

用户确认推进 F1/F2（键盘连点/录制）、F4（Win11 UI）与收尾清理（合并发布文档 + 删旧构建产物）。`python -m unittest discover tests` 共 **64 项全部通过**，另加一次真实 GUI 冒烟测试。

### 已修复

| 状态 | 项 | 改动 |
|---|---|---|
| ✅ | **F2 键盘录制** | 引擎 `keyboard.Listener` 的 `_on_key_press` 现在把非 ESC、非全局快捷键的按键录为 `kind='key'` 动作（规范键名如 `'a'`、`'enter'`、`'ctrl_l'`）；ESC 仍停止录制。录制时落在本窗口的点击仍按 `ignore_click_predicate` 忽略 |
| ✅ | **F1 键盘连点** | `_execute_clicking` 新增键盘分支：key 动作按"轻点"语义执行——按下后若 `hold_duration<=0` 立即释放（避免按键卡住），否则按住指定时长再释放。与鼠标动作共用 repeat_count，因此"键盘宏重复播放"即实现键盘连点 |
| ✅ | **数据模型扩展** | `ClickAction` 增加 `kind`（`'mouse'`/`'key'`）与 `key`（规范键名）字段，均带默认值；`from_dict` 改为显式 `data.get` 容错，旧版无 `kind/key` 的 `.enc` 文件可正常加载（向后兼容） |
| ✅ | **校验扩展** | `validate_macro_action` 增加 `kind` 分支：键盘动作只校验 `key` 非空、`action_type` 合法，跳过坐标/按钮校验；旧数据无 `kind` 仍按鼠标校验 |
| ✅ | **F4 Win11 风格 UI** | 新增 `ui/theme.py` 的 `apply_win11_theme(root)`：基于 `clam` 的浅色主题（Segoe UI 字体、蓝 `#0067C0` 强调色主按钮、白底卡片、细边框）；在 `app.main()` 创建窗口后调用。"开始点击"按钮改用 `Accent.TButton` 强调样式。全部容错包裹，主题失败不影响功能 |
| ✅ | **UI 显示** | `ActionList._format_action` 区分键盘动作，显示为 `1. 按键 [enter] 按下 @ 1.23s`；录制状态文案更新为"正在录制鼠标/键盘..." |
| ✅ | **文档合并** | `PUBLISH_GUIDE.md` 与 `RELEASE_GUIDE.md` 合并为单一 `PUBLISHING.md`（含 CI/CD 流程、FAQ、本地打包、`--windowed`、签名/误报、Release 模板、安全提示），旧两文件已删除并移除交叉引用 |
| ✅ | **构建产物清理** | 删除 `build/`、`dist/` 下含旧 `96967` 路径的产物（已被 gitignore），并重新构建验证 |

### 关键设计点

- **统一动作序列**：键盘能力不另立一套，而是并入现有"录制→回放"模型。录制时鼠标与键盘动作混排进同一 `click_sequence`，回放时按 `kind` 分流到 `mouse_controller` / `keyboard_controller`。逻辑最少新增、分层不被破坏（引擎仍不依赖 Tk）。
- **录制去重控制键**：`_SKIP_KEY_NAMES` 跳过 F8/F10/F11/ESC，避免把全局快捷键本身录进宏。
- **轻点语义**：键盘录制只记 `press`，回放时自动补 `release`，天然避免"按住不松"卡键。
- **re-adding keyboard_controller**：第二批（C3）曾以"未使用"为由删除 `keyboard.Controller()`，本轮 F1 正式使用它，属有意回滚。

### 验证方式

- `python -m unittest discover tests -v` → **64 tests, OK**（新增：键盘录制 6 项、键盘回放 2 项、键盘动作校验 2 项、`ClickAction` 含 kind/key 往返 + 向后兼容 2 项）
- 真实 GUI 冒烟：实例化 `AutoClickerApp` → 确认 `Accent.TButton` 主题背景为 `#0067C0`、注册到 `['esc','f10','f11','f8']`、`ActionList` 键盘格式正确、引擎录制键盘动作（f8 被跳过）
- `python -m compileall ui core config utils main.py pack.py` → 全部通过

### 仍未处理

- **S2**：加密仍为固定密钥的本地混淆（Fernet + 固定派生参数），未改为"用户口令派生密钥"（PBKDF2/HKDF）。如需，需新增口令输入 UI 与降级逻辑，属独立功能开发。
