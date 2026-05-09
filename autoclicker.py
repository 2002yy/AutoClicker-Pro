import customtkinter as ctk
import threading
import time
import webbrowser
from datetime import datetime, timedelta
from pynput.mouse import Button, Controller as MouseController, Listener as MouseListener
from pynput.keyboard import Key, Controller as KeyboardController, Listener as KeyListener

# --- 全局配置 ---
ctk.set_appearance_mode("Light") 
ctk.set_default_color_theme("blue")

# ==========================================
# 弹窗类定义
# ==========================================

class HelpWindow(ctk.CTkToplevel):
    """帮助文档弹窗"""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("使用说明 & 常见问题")
        self.geometry("600x500") 
        self.resizable(False, False)
        
        textbox = ctk.CTkTextbox(self, width=560, height=450, corner_radius=10, font=("Microsoft YaHei UI", 12))
        textbox.pack(padx=20, pady=20)
        
        info_text = """【常见问题 Q&A】

Q: 目前算是“后台运行”吗？
A: 严格来说，不是（或者说是“全局模拟”，而非“句柄后台”）。

1. 当前状态（前台/全局模拟）：
   目前的原理是利用 pynput 调用操作系统的底层接口，模拟真实的物理鼠标/键盘信号。
   • 特点：鼠标指针会真的移动，键盘会真的按下。
   • 限制：当你开启连点时，你不能同时用鼠标去做别的事，因为鼠标被程序占用了。

2. 你可能想要的“后台连点”：
   这是指向某个特定的窗口句柄发送消息。
   • 特点：可以最小化游戏挂机。
   • 实现难度：容易被游戏反作弊系统（如TP、VAC）检测封号，且对部分现代游戏无效。

3. 结论：
   目前的版本是全局兼容性最强的版本（能点动99%的软件），但它会独占你的鼠标。

------------------------------------------------

【功能说明】
1. 鼠标/键盘连点
   - 间隔时间：设置为0则为极速模式。
   - 停止条件：支持无限循环、指定次数、指定时间。

2. 键鼠录制 (宏)
   - 按 F10 开始录制 -> 做动作 -> 按 F10 结束 -> 按 F11 回放。
"""
        textbox.insert("0.0", info_text)
        textbox.configure(state="disabled")

class ContactWindow(ctk.CTkToplevel):
    """[新增] 联系作者小方格弹窗"""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("关于作者")
        self.geometry("300x200")
        self.resizable(False, False)
        
        # 居中显示
        self.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self, text="全能连点器 Pro", font=("Microsoft YaHei UI", 16, "bold")).pack(pady=(20, 5))
        ctk.CTkLabel(self, text="Version 1.0.0", text_color="gray").pack(pady=(0, 20))
        
        ctk.CTkLabel(self, text="作者: 2002yy").pack(pady=5)
        
        # 跳转按钮
        btn = ctk.CTkButton(self, text="前往 GitHub 主页", command=self.open_github, width=150)
        btn.pack(pady=20)

    def open_github(self):
        webbrowser.open("https://github.com/2002yy")
        self.destroy() # 点击后关闭弹窗

# ==========================================
# 主程序
# ==========================================

class AutoClickerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. 窗口基础
        self.title("全能连点器 Pro - 1.0.0 版")
        self.geometry("820x620") # 稍微加大一点尺寸，让布局更舒展
        self.resizable(False, False)
        
        # 2. 核心对象
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self.is_running = False
        self.is_playing_macro = False
        
        # 录制相关
        self.recorded_events = []
        self.is_recording = False
        self.start_record_time = 0
        self.rec_mouse_listener = None
        self.rec_key_listener = None

        # 3. 变量初始化
        self.current_mode = "mouse"
        
        # 鼠标变量
        self.mouse_btn_var = ctk.StringVar(value="左键")
        self.click_type_var = ctk.StringVar(value="单击")
        self.location_mode_var = ctk.StringVar(value="当前位置")
        self.fixed_x_var = ctk.StringVar(value="0")
        self.fixed_y_var = ctk.StringVar(value="0")
        
        # 键盘变量
        self.key_value_var = ctk.StringVar(value="Space")
        self.target_key_code = Key.space
        
        # 通用变量
        self.h_var = ctk.StringVar(value="0")
        self.m_var = ctk.StringVar(value="0")
        self.s_var = ctk.StringVar(value="0")
        self.ms_var = ctk.StringVar(value="100")
        
        self.stop_mode_var = ctk.StringVar(value="无限循环")
        self.entry_stop_val_var = ctk.StringVar(value="1000")
        
        # 辅助状态
        self.picking_location = False
        self.setting_single_key = False

        # 4. 界面构建
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.create_sidebar()
        self.create_main_area()
        
        # 5. 启动监听
        self.listener = KeyListener(on_press=self.on_global_key_press)
        self.listener.start()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_sidebar(self):
        """左侧导航栏"""
        self.sidebar = ctk.CTkFrame(self, width=180, corner_radius=0, fg_color=("gray90", "gray15")) # 稍微加宽
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)

        # Title
        ctk.CTkLabel(self.sidebar, text="连点器 Pro", font=("Microsoft YaHei UI", 22, "bold")).grid(row=0, column=0, padx=20, pady=(30, 30))

        # Buttons (增加 padx 让文字不靠边，视觉更一致)
        self.btn_nav_mouse = self.create_nav_btn("🖱️鼠标连点", 1, "mouse")
        self.btn_nav_key = self.create_nav_btn("⌨️     键盘连点", 2, "key")
        self.btn_nav_rec = self.create_nav_btn("🔴     键鼠录制", 3, "record")

        # 底部按钮
        self.btn_contact = ctk.CTkButton(
            self.sidebar, text="🔗  联系作者", fg_color="transparent", 
            border_width=0, text_color="gray", 
            hover_color=("gray85", "gray25"),
            anchor="w",
            command=lambda: ContactWindow(self) # [修改] 打开弹窗
        )
        self.btn_contact.grid(row=11, column=0, padx=20, pady=(0, 5), sticky="ew")

        self.btn_help = ctk.CTkButton(
            self.sidebar, text="❓  使用帮助", fg_color="transparent", 
            border_width=1, text_color="gray", 
            anchor="w",
            command=lambda: HelpWindow(self)
        )
        self.btn_help.grid(row=12, column=0, padx=20, pady=(0, 20), sticky="ew")

    def create_nav_btn(self, text, row, mode):
        btn = ctk.CTkButton(
            self.sidebar, text=text, height=45, corner_radius=8,
            fg_color="transparent", text_color=("gray10", "gray90"), 
            hover_color=("gray80", "gray25"),
            anchor="w", font=("Microsoft YaHei UI", 14),
            command=lambda: self.switch_mode(mode)
        )
        btn.grid(row=row, column=0, padx=15, pady=5, sticky="ew")
        return btn

    def create_main_area(self):
        """右侧主区域"""
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray98", "gray10"))
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # 1. 顶部栏
        self.top_bar = ctk.CTkFrame(self.main_frame, height=50, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 0))
        
        self.lbl_mode_title = ctk.CTkLabel(self.top_bar, text="鼠标连点配置", font=("Microsoft YaHei UI", 20, "bold"))
        self.lbl_mode_title.pack(side="left")
        
        ctk.CTkButton(self.top_bar, text="💾 保存配置", width=100, height=32, fg_color="#4a90e2").pack(side="right")

        # 2. 核心内容区 (Scrollable)
        self.scroll_frame = ctk.CTkScrollableFrame(self.main_frame, corner_radius=10, fg_color="transparent")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=10)
        
        self.create_mouse_panel()
        self.create_key_panel()
        self.create_record_panel()
        
        # 3. 底部栏
        self.bottom_bar = ctk.CTkFrame(self.main_frame, fg_color=("white", "gray15"), height=100, corner_radius=0)
        self.bottom_bar.grid(row=2, column=0, sticky="ew")
        
        self.btn_start = ctk.CTkButton(
            self.bottom_bar, text="开始运行 (F8)", command=self.toggle_running,
            height=55, font=("Microsoft YaHei UI", 22, "bold"),
            fg_color="#00C853", hover_color="#009624", corner_radius=28
        )
        self.btn_start.pack(fill="x", padx=50, pady=(20, 5))
        
        self.lbl_status = ctk.CTkLabel(self.bottom_bar, text="就绪 - 按 F8 启动", text_color="gray")
        self.lbl_status.pack(pady=(0, 15))

        self.switch_mode("mouse")

    # --- 面板构建 (重点修改：整齐化) ---

    def create_mouse_panel(self):
        self.panel_mouse = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.create_section_label(self.panel_mouse, "1. 动作设置")
        
        # [修改] 使用 Grid 布局卡片，确保每行高度一致，文字左对齐
        card = self.create_card(self.panel_mouse)
        
        # 创建内部 Grid 容器
        grid_frame = ctk.CTkFrame(card, fg_color="transparent")
        grid_frame.pack(fill="x", padx=20, pady=20)
        grid_frame.grid_columnconfigure(0, minsize=100) # 标签列定宽
        
        # Row 1: 鼠标按键
        ctk.CTkLabel(grid_frame, text="鼠标按键:", font=("Microsoft YaHei UI", 14), anchor="w").grid(row=0, column=0, sticky="w", pady=12)
        ctk.CTkSegmentedButton(grid_frame, values=["左键", "右键", "中键"], variable=self.mouse_btn_var, width=220).grid(row=0, column=1, sticky="w", padx=10)
        
        # Row 2: 点击类型
        ctk.CTkLabel(grid_frame, text="点击类型:", font=("Microsoft YaHei UI", 14), anchor="w").grid(row=1, column=0, sticky="w", pady=12)
        f_click = ctk.CTkFrame(grid_frame, fg_color="transparent")
        f_click.grid(row=1, column=1, sticky="w", padx=10)
        ctk.CTkRadioButton(f_click, text="单击", variable=self.click_type_var, value="单击").pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(f_click, text="双击", variable=self.click_type_var, value="双击").pack(side="left")

        # Row 3: 点击位置
        ctk.CTkLabel(grid_frame, text="点击位置:", font=("Microsoft YaHei UI", 14), anchor="w").grid(row=2, column=0, sticky="w", pady=12)
        f_loc = ctk.CTkFrame(grid_frame, fg_color="transparent")
        f_loc.grid(row=2, column=1, sticky="w", padx=10)
        
        ctk.CTkOptionMenu(f_loc, variable=self.location_mode_var, values=["当前位置", "固定坐标"], width=120, command=self.toggle_loc_inputs).pack(side="left")
        
        # 坐标输入区域
        self.f_loc_coords = ctk.CTkFrame(f_loc, fg_color="transparent")
        ctk.CTkLabel(self.f_loc_coords, text="X:").pack(side="left", padx=(15, 2))
        ctk.CTkEntry(self.f_loc_coords, width=60, textvariable=self.fixed_x_var).pack(side="left")
        ctk.CTkLabel(self.f_loc_coords, text="Y:").pack(side="left", padx=(10, 2))
        ctk.CTkEntry(self.f_loc_coords, width=60, textvariable=self.fixed_y_var).pack(side="left")
        ctk.CTkButton(self.f_loc_coords, text="抓取 (F9)", width=80, fg_color="gray", command=self.start_pick_location).pack(side="left", padx=15)
        self.f_loc_coords.pack(side="left") # 初始pack

        # 通用设置
        self.create_common_settings(self.panel_mouse)

    def create_key_panel(self):
        self.panel_key = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.create_section_label(self.panel_key, "1. 按键设置")
        card = self.create_card(self.panel_key)
        
        # 同样使用 Grid 保持对齐
        grid_frame = ctk.CTkFrame(card, fg_color="transparent")
        grid_frame.pack(fill="x", padx=20, pady=20)
        grid_frame.grid_columnconfigure(0, minsize=100)

        ctk.CTkLabel(grid_frame, text="目标按键:", font=("Microsoft YaHei UI", 14), anchor="w").grid(row=0, column=0, sticky="w", pady=10)
        
        f_k = ctk.CTkFrame(grid_frame, fg_color="transparent")
        f_k.grid(row=0, column=1, sticky="w", padx=10)
        
        ctk.CTkEntry(f_k, textvariable=self.key_value_var, width=140, state="disabled", justify="center", font=("Arial", 14, "bold")).pack(side="left")
        self.btn_set_key = ctk.CTkButton(f_k, text="设置按键 (点击录入)", command=self.start_set_single_key, fg_color="#FBC02D", text_color="black", hover_color="#F9A825", width=160)
        self.btn_set_key.pack(side="left", padx=15)

        self.create_common_settings(self.panel_key)

    def create_record_panel(self):
        self.panel_record = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        
        info_card = ctk.CTkFrame(self.panel_record, fg_color=("white", "gray20"), corner_radius=10)
        info_card.pack(fill="x", pady=10)
        ctk.CTkLabel(info_card, text="💡 键鼠录制 (宏)", font=("Microsoft YaHei UI", 16, "bold")).pack(anchor="w", padx=25, pady=(20, 5))
        ctk.CTkLabel(info_card, text="记录并无限循环回放你的所有操作。\n提示：播放时请勿触碰鼠标键盘，以免干扰。", justify="left", text_color="gray50", font=("Microsoft YaHei UI", 13)).pack(anchor="w", padx=25, pady=(0, 20))

        status_card = self.create_card(self.panel_record)
        
        self.lbl_rec_status = ctk.CTkLabel(status_card, text="当前状态: 空闲", font=("Microsoft YaHei UI", 18))
        self.lbl_rec_status.pack(pady=(30, 20))
        
        btn_box = ctk.CTkFrame(status_card, fg_color="transparent")
        btn_box.pack(pady=(0, 30))
        self.btn_rec_start = ctk.CTkButton(btn_box, text="开始录制 (F10)", fg_color="#D32F2F", hover_color="#B71C1C", width=160, height=45, font=("Microsoft YaHei UI", 14, "bold"), command=self.toggle_recording)
        self.btn_rec_start.pack(side="left", padx=20)
        self.btn_rec_play = ctk.CTkButton(btn_box, text="播放宏 (F11)", fg_color="#1976D2", hover_color="#0D47A1", width=160, height=45, font=("Microsoft YaHei UI", 14, "bold"), command=self.toggle_playing_macro)
        self.btn_rec_play.pack(side="left", padx=20)

    def create_common_settings(self, parent):
        self.create_section_label(parent, "2. 运行参数")
        card = self.create_card(parent)
        
        # 也是 Grid 布局
        grid_frame = ctk.CTkFrame(card, fg_color="transparent")
        grid_frame.pack(fill="x", padx=20, pady=20)
        grid_frame.grid_columnconfigure(0, minsize=100)

        # 间隔
        ctk.CTkLabel(grid_frame, text="间隔时间:", font=("Microsoft YaHei UI", 14), anchor="w").grid(row=0, column=0, sticky="w", pady=12)
        f_int = ctk.CTkFrame(grid_frame, fg_color="transparent")
        f_int.grid(row=0, column=1, sticky="w", padx=10)
        self.create_time_input(f_int, self.h_var, "时")
        self.create_time_input(f_int, self.m_var, "分")
        self.create_time_input(f_int, self.s_var, "秒")
        self.create_time_input(f_int, self.ms_var, "毫秒")

        # 停止条件
        ctk.CTkLabel(grid_frame, text="停止条件:", font=("Microsoft YaHei UI", 14), anchor="w").grid(row=1, column=0, sticky="w", pady=12)
        f_stop = ctk.CTkFrame(grid_frame, fg_color="transparent")
        f_stop.grid(row=1, column=1, sticky="w", padx=10)
        ctk.CTkOptionMenu(f_stop, variable=self.stop_mode_var, values=["无限循环", "指定次数", "指定时间"], width=120).pack(side="left")
        ctk.CTkEntry(f_stop, width=100, textvariable=self.entry_stop_val_var).pack(side="left", padx=15)
        ctk.CTkLabel(f_stop, text="(次/秒)").pack(side="left")

    # --- UI 辅助 ---
    def create_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=("white", "gray20"), corner_radius=12)
        card.pack(fill="x", pady=8)
        return card

    def create_section_label(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=("Microsoft YaHei UI", 15, "bold"), text_color="gray").pack(anchor="w", pady=(20, 8))

    def create_time_input(self, parent, var, label):
        ctk.CTkEntry(parent, width=55, textvariable=var, justify="center").pack(side="left", padx=(0, 5))
        ctk.CTkLabel(parent, text=label).pack(side="left", padx=(0, 10))

    def toggle_loc_inputs(self, value):
        if value == "固定坐标": self.f_loc_coords.pack(side="left", padx=10)
        else: self.f_loc_coords.pack_forget()

    def switch_mode(self, mode):
        self.current_mode = mode
        # 按钮样式切换
        for btn, m in [(self.btn_nav_mouse, "mouse"), (self.btn_nav_key, "key"), (self.btn_nav_rec, "record")]:
            if m == mode:
                btn.configure(fg_color=("gray85", "gray30"), text_color=("#1a73e8", "white"))
            else:
                btn.configure(fg_color="transparent", text_color=("gray10", "gray90"))

        self.panel_mouse.pack_forget(); self.panel_key.pack_forget(); self.panel_record.pack_forget()
        
        if mode == "mouse":
            self.lbl_mode_title.configure(text="鼠标连点配置")
            self.panel_mouse.pack(fill="x")
            self.bottom_bar.grid(row=2, column=0, sticky="ew")
        elif mode == "key":
            self.lbl_mode_title.configure(text="键盘连点配置")
            self.panel_key.pack(fill="x")
            self.bottom_bar.grid(row=2, column=0, sticky="ew")
        elif mode == "record":
            self.lbl_mode_title.configure(text="宏录制模式")
            self.panel_record.pack(fill="x")
            self.bottom_bar.grid_forget()

    # --- 逻辑 (保持不变) ---
    def on_global_key_press(self, key):
        if self.setting_single_key:
            name = str(key).replace("Key.", "").upper()
            try: name = key.char.upper()
            except: pass
            self.key_value_var.set(name)
            self.target_key_code = key
            self.setting_single_key = False
            self.btn_set_key.configure(text="设置按键 (点击录入)", fg_color="#FBC02D")
            return
            
        if self.current_mode == "record":
            if key == Key.f10: self.after(0, self.toggle_recording)
            elif key == Key.f11: self.after(0, self.toggle_playing_macro)
        else:
            if key == Key.f8: self.after(0, self.toggle_running)
            elif key == Key.f9 and self.current_mode == "mouse":
                if not self.picking_location: self.after(0, self.start_pick_location)

    def start_pick_location(self):
        self.picking_location = True
        self.lbl_status.configure(text="3秒后自动捕获...", text_color="orange")
        self.after(3000, self.get_mouse_pos)

    def get_mouse_pos(self):
        x, y = self.mouse.position
        self.fixed_x_var.set(str(x)); self.fixed_y_var.set(str(y))
        self.location_mode_var.set("固定坐标")
        self.toggle_loc_inputs("固定坐标")
        self.picking_location = False
        self.lbl_status.configure(text=f"已捕获坐标: {x}, {y}", text_color="green")

    def start_set_single_key(self):
        self.setting_single_key = True
        self.btn_set_key.configure(text="请按下键盘...", fg_color="#FF5252")

    def toggle_running(self):
        if self.is_running: self.stop_running()
        else: self.start_running()

    def start_running(self):
        try:
            h=int(self.h_var.get()); m=int(self.m_var.get())
            s=int(self.s_var.get()); ms=int(self.ms_var.get())
            total_ms = (h*3600 + m*60 + s)*1000 + ms
            if total_ms < 0: raise ValueError
        except:
            self.lbl_status.configure(text="错误: 时间格式不正确", text_color="red")
            return

        self.is_running = True
        self.btn_start.configure(text="停止运行 (F8)", fg_color="#D32F2F", hover_color="#B71C1C")
        self.lbl_status.configure(text="运行中...", text_color="green")
        
        threading.Thread(target=self.run_loop, args=(total_ms, self.current_mode), daemon=True).start()

    def stop_running(self):
        self.is_running = False
        self.btn_start.configure(text="开始运行 (F8)", fg_color="#00C853", hover_color="#009624")
        self.lbl_status.configure(text="已停止", text_color="gray")

    def run_loop(self, interval_ms, mode):
        interval_sec = interval_ms / 1000.0
        stop_mode = self.stop_mode_var.get()
        stop_val = float(self.entry_stop_val_var.get()) if stop_mode != "无限循环" else 0
        start_time = time.time()
        count = 0
        
        btn_map = {"左键": Button.left, "右键": Button.right, "中键": Button.middle}
        mouse_btn = btn_map.get(self.mouse_btn_var.get(), Button.left)
        clicks = 2 if self.click_type_var.get() == "双击" else 1
        
        while self.is_running:
            if mode == "mouse":
                if self.location_mode_var.get() == "固定坐标":
                    try: self.mouse.position = (int(self.fixed_x_var.get()), int(self.fixed_y_var.get()))
                    except: pass
                self.mouse.click(mouse_btn, clicks)
            elif mode == "key":
                self.keyboard.press(self.target_key_code)
                time.sleep(0.02)
                self.keyboard.release(self.target_key_code)
            count += 1
            if stop_mode == "指定次数" and count >= int(stop_val): break
            if stop_mode == "指定时间" and (time.time() - start_time) >= stop_val: break
            time.sleep(interval_sec)
        self.after(0, self.stop_running)

    def toggle_recording(self):
        if self.is_recording: self.stop_recording()
        else: self.start_recording()

    def start_recording(self):
        self.is_recording = True
        self.recorded_events = []
        self.start_record_time = time.time()
        self.btn_rec_start.configure(text="停止录制 (F10)", fg_color="gray")
        self.lbl_rec_status.configure(text="正在录制... 按 F10 停止", text_color="red")
        self.rec_mouse_listener = MouseListener(on_click=self.on_rec_mouse); self.rec_mouse_listener.start()
        self.rec_key_listener = KeyListener(on_press=self.on_rec_key); self.rec_key_listener.start()

    def stop_recording(self):
        self.is_recording = False
        if self.rec_mouse_listener: self.rec_mouse_listener.stop()
        if self.rec_key_listener: self.rec_key_listener.stop()
        self.btn_rec_start.configure(text="重新录制 (F10)", fg_color="#D32F2F")
        self.lbl_rec_status.configure(text=f"录制完成: 共 {len(self.recorded_events)} 步", text_color="green")

    def on_rec_mouse(self, x, y, button, pressed):
        if pressed and self.is_recording:
            delay = time.time() - self.start_record_time
            self.recorded_events.append({"type": "mouse", "x": x, "y": y, "btn": str(button), "delay": delay})
            self.start_record_time = time.time()

    def on_rec_key(self, key):
        if self.is_recording and key != Key.f10:
            delay = time.time() - self.start_record_time
            k_val = getattr(key, 'vk', None) or str(key)
            self.recorded_events.append({"type": "key", "key": k_val, "delay": delay})
            self.start_record_time = time.time()

    def toggle_playing_macro(self):
        if self.is_playing_macro:
            self.is_playing_macro = False
            self.btn_rec_play.configure(text="播放宏 (F11)", fg_color="#1976D2")
            self.lbl_rec_status.configure(text="播放停止", text_color="gray")
        else:
            if not self.recorded_events: return
            self.is_playing_macro = True
            self.btn_rec_play.configure(text="停止播放 (F11)", fg_color="#D32F2F")
            self.lbl_rec_status.configure(text="宏运行中...", text_color="green")
            threading.Thread(target=self.play_macro, daemon=True).start()

    def play_macro(self):
        while self.is_playing_macro:
            for ev in self.recorded_events:
                if not self.is_playing_macro: break
                time.sleep(ev["delay"])
                if ev["type"] == "mouse":
                    self.mouse.position = (ev["x"], ev["y"])
                    btn = Button.left if "left" in ev["btn"] else Button.right if "right" in ev["btn"] else Button.middle
                    self.mouse.click(btn)
                elif ev["type"] == "key":
                    try:
                        from pynput.keyboard import KeyCode
                        k = KeyCode.from_vk(ev["key"]) if isinstance(ev["key"], int) else None
                        if not k and "Key." in ev["key"]: k = getattr(Key, ev["key"].split(".")[1])
                        if not k: k = ev["key"].replace("'", "")
                        self.keyboard.press(k); time.sleep(0.01); self.keyboard.release(k)
                    except: pass
            time.sleep(0.1)
        self.after(0, self.toggle_playing_macro)

    def on_close(self):
        self.is_running = False; self.is_playing_macro = False; self.is_recording = False
        self.listener.stop()
        self.destroy()

if __name__ == "__main__":
    app = AutoClickerApp()
    app.mainloop()