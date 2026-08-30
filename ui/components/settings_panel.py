"""
设置面板组件
包含所有时间间隔、重复次数等配置输入框
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Optional, Tuple

from config.constants import (
    FONT_FAMILY, FONT_SIZE_NORMAL,
    DEFAULT_INTERVAL_MS, DEFAULT_RECORD_INTERVAL,
    DEFAULT_HOLD_DURATION, DEFAULT_REPEAT_COUNT, DEFAULT_REPEAT_INTERVAL,
    DEFAULT_START_DELAY_S, DEFAULT_AUTO_STOP_S,
    CLICK_TYPE_CHOICES, CLICK_TYPE_CODES, DEFAULT_CLICK_TYPE_LABEL,
    POSITION_MODE_CHOICES, DEFAULT_POSITION_MODE_LABEL,
    PADDING_STANDARD, PADDING_SMALL,
    GRID_STICKY_W, GRID_STICKY_E
)


class SettingsPanel(ttk.LabelFrame):
    """设置面板组件，包含所有配置输入框（标题框样式，与宏库/快捷键区统一）"""

    def __init__(self, parent):
        super().__init__(parent, text="点击参数", padding=PADDING_STANDARD)
        
        # 存储所有变量的字典（数值型，随 get_values 整数化）
        self.variables: Dict[str, tk.StringVar] = {}

        # 非数值型控件变量（不进入 get_values 的整数化流程）
        self.click_type_var = tk.StringVar(master=self,
                                           value=DEFAULT_CLICK_TYPE_LABEL)
        self.position_var = tk.StringVar(master=self,
                                         value=DEFAULT_POSITION_MODE_LABEL)
        self.fixed_x_var = tk.StringVar(master=self, value="0")
        self.fixed_y_var = tk.StringVar(master=self, value="0")

        # 拾取坐标回调（由主窗口注入倒计时逻辑）
        self._pick_handler: Optional[Callable[[], None]] = None
        
        # 创建所有输入字段
        self._create_inputs()
    
    def _create_inputs(self):
        """创建所有输入字段"""
        # 点击间隔
        self._create_input_row(0, "点击间隔 (毫秒):", "interval_ms", 
                               str(DEFAULT_INTERVAL_MS))
        
        # 录制间隔
        self._create_input_row(1, "录制间隔 (毫秒):", "record_interval",
                               str(DEFAULT_RECORD_INTERVAL))
        
        # 按住持续时间
        self._create_input_row(2, "按住持续时间 (毫秒):", "hold_duration",
                               str(DEFAULT_HOLD_DURATION))
        
        # 重复次数
        self._create_input_row(3, "重复次数 (0=不限):", "repeat_count",
                               str(DEFAULT_REPEAT_COUNT))
        
        # 重复间隔
        self._create_input_row(4, "重复间隔 (毫秒):", "repeat_interval",
                               str(DEFAULT_REPEAT_INTERVAL))

        # 延迟启动（秒）
        self._create_input_row(5, "延迟启动 (秒):", "start_delay_s",
                               str(DEFAULT_START_DELAY_S))

        # 自动停止（秒）
        self._create_input_row(6, "自动停止 (秒, 0不限):", "auto_stop_s",
                               str(DEFAULT_AUTO_STOP_S))

        # 点击类型（单击/双击/三击）—— 内置连点模式生效
        type_label = ttk.Label(self, text="点击类型:",
                               font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        type_label.grid(row=7, column=0, sticky=GRID_STICKY_W,
                        pady=PADDING_SMALL)
        self.click_type_combo = ttk.Combobox(
            self, textvariable=self.click_type_var,
            values=list(CLICK_TYPE_CHOICES), state="readonly", width=8)
        self.click_type_combo.grid(row=7, column=1, sticky=GRID_STICKY_W,
                                   pady=PADDING_SMALL,
                                   padx=(PADDING_STANDARD, 0))

        # 点击位置（跟随光标/固定位置 + 拾取坐标）
        pos_label = ttk.Label(self, text="点击位置:",
                              font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        pos_label.grid(row=8, column=0, sticky=GRID_STICKY_W,
                       pady=PADDING_SMALL)
        self.position_combo = ttk.Combobox(
            self, textvariable=self.position_var,
            values=list(POSITION_MODE_CHOICES), state="readonly", width=8)
        self.position_combo.grid(row=8, column=1, sticky=GRID_STICKY_W,
                                 pady=PADDING_SMALL,
                                 padx=(PADDING_STANDARD, 0))
        self.position_combo.bind('<<ComboboxSelected>>',
                                 lambda _e: self._sync_position_state())

        # 固定位置子区：X/Y 输入框 + 拾取按钮（仅"固定位置"时可用）
        self.fixed_frame = ttk.Frame(self)
        self.fixed_frame.grid(row=9, column=0, columnspan=2, sticky=GRID_STICKY_E,
                              pady=(0, PADDING_SMALL))
        x_label = ttk.Label(self.fixed_frame, text="X:")
        x_label.grid(row=0, column=0, padx=(0, 2))
        self.x_entry = ttk.Entry(self.fixed_frame, textvariable=self.fixed_x_var,
                                 width=6)
        self.x_entry.grid(row=0, column=1, padx=(0, PADDING_STANDARD))
        y_label = ttk.Label(self.fixed_frame, text="Y:")
        y_label.grid(row=0, column=2, padx=(0, 2))
        self.y_entry = ttk.Entry(self.fixed_frame, textvariable=self.fixed_y_var,
                                 width=6)
        self.y_entry.grid(row=0, column=3, padx=(0, PADDING_STANDARD))
        self.pick_button = ttk.Button(self.fixed_frame, text="拾取坐标",
                                      command=self._on_pick)
        self.pick_button.grid(row=0, column=4)

        # X/Y 只允许数字输入
        for var in (self.fixed_x_var, self.fixed_y_var):
            var.trace_add('write', lambda *a, v=var: self._filter_digits(v))

        self._sync_position_state()

    def _filter_digits(self, var: tk.StringVar):
        """过滤非数字字符"""
        value = var.get()
        cleaned = ''.join(c for c in value if c.isdigit())
        if cleaned != value:
            var.set(cleaned)

    def _on_pick(self):
        if self._pick_handler is not None:
            self._pick_handler()

    def set_pick_handler(self, handler: Callable[[], None]):
        """注入拾取坐标回调（主窗口实现倒计时抓取光标位置）"""
        self._pick_handler = handler

    def _sync_position_state(self):
        """固定位置模式下启用 X/Y 输入与拾取按钮"""
        fixed = self.get_position_mode() == 'fixed'
        state = "normal" if fixed else "disabled"
        for w in (self.x_entry, self.y_entry, self.pick_button):
            w.config(state=state)

    def get_click_type(self) -> str:
        """获取点击类型代码：single / double / triple"""
        return CLICK_TYPE_CODES.get(self.click_type_var.get(), 'single')

    def set_click_type(self, code: str):
        """按代码设置点击类型"""
        for label, val in CLICK_TYPE_CODES.items():
            if val == code:
                self.click_type_var.set(label)
                return

    def get_position_mode(self) -> str:
        """获取位置模式：cursor（跟随光标）/ fixed（固定位置）"""
        return 'fixed' if self.position_var.get() == '固定位置' else 'cursor'

    def set_position_mode(self, mode: str):
        """设置位置模式：'cursor' / 'fixed'"""
        self.position_var.set('固定位置' if mode == 'fixed' else '跟随光标')
        self._sync_position_state()

    def get_fixed_xy(self) -> Optional[Tuple[int, int]]:
        """获取固定坐标；非法或空输入返回 None"""
        try:
            return int(self.fixed_x_var.get()), int(self.fixed_y_var.get())
        except ValueError:
            return None

    def set_fixed_xy(self, x: int, y: int):
        """写入拾取/恢复的固定坐标"""
        self.fixed_x_var.set(str(int(x)))
        self.fixed_y_var.set(str(int(y)))
    
    def _create_input_row(self, row: int, label_text: str,
                          var_name: str, default_value: str):
        """
        创建一行输入控件

        Args:
            row: 行号
            label_text: 标签文本
            var_name: 变量名称（用于存储）
            default_value: 默认值
        """
        # 标签
        label = ttk.Label(self, text=label_text, font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        label.grid(row=row, column=0, sticky=GRID_STICKY_W, pady=PADDING_SMALL)

        # 变量（显式绑定到本组件，避免残留至解释器退出期）
        var = tk.StringVar(master=self, value=default_value)
        self.variables[var_name] = var

        # 输入框（只允许输入数字；sticky=ew 填满列宽，避免标签和输入框之间出现大片空白）
        entry = ttk.Entry(self, textvariable=var)
        entry.grid(row=row, column=1, sticky="ew",
                   pady=PADDING_SMALL, padx=(PADDING_STANDARD, 0))
        # 绑定输入校验：只允许数字和退格键
        var.trace_add('write', lambda *args: self._validate_input(var_name))

        # 配置列权重使输入框可以扩展
        self.columnconfigure(1, weight=1)

    def _validate_input(self, var_name: str):
        """输入校验：自动过滤非数字字符"""
        var = self.variables[var_name]
        value = var.get()
        # 移除所有非数字字符（保留空字符串）
        cleaned = ''.join(c for c in value if c.isdigit())
        if cleaned != value:
            var.set(cleaned)
    
    def get_values(self) -> Dict[str, int]:
        """
        获取所有输入值
        
        Returns:
            包含所有配置值的字典
        """
        values = {}
        for name, var in self.variables.items():
            try:
                values[name] = int(var.get())
            except ValueError:
                values[name] = 0  # 无效输入时返回 0
        return values
    
    def set_values(self, values: Dict[str, int]):
        """
        批量设置输入值
        
        Args:
            values: 包含配置值的字典
        """
        for name, value in values.items():
            if name in self.variables:
                self.variables[name].set(str(value))
    
    def get_value(self, name: str) -> int:
        """
        获取单个输入值
        
        Args:
            name: 变量名称
            
        Returns:
            输入值（整数）
        """
        if name not in self.variables:
            raise KeyError(f"未知的配置项：{name}")
        
        try:
            return int(self.variables[name].get())
        except ValueError:
            return 0
    
    def set_value(self, name: str, value: int):
        """
        设置单个输入值
        
        Args:
            name: 变量名称
            value: 值
        """
        if name not in self.variables:
            raise KeyError(f"未知的配置项：{name}")
        
        self.variables[name].set(str(value))
    
    def validate(self) -> tuple:
        """
        验证所有输入

        Returns:
            (是否有效，错误消息)
        """
        from config.validation import validate_time_inputs

        # 检查是否有空输入
        for name, var in self.variables.items():
            value = var.get()
            if not value or value.strip() == '':
                return False, f"{name} 不能为空"

        values = self.get_values()

        ok, error_msg = validate_time_inputs(
            interval_ms=values.get('interval_ms', 0),
            record_interval=values.get('record_interval', 0),
            hold_duration=values.get('hold_duration', 0),
            repeat_count=values.get('repeat_count', 0),
            repeat_interval=values.get('repeat_interval', 0),
            start_delay_s=values.get('start_delay_s', 0),
            auto_stop_s=values.get('auto_stop_s', 0)
        )
        if not ok:
            return False, error_msg

        # 固定位置模式下校验 X/Y 坐标
        if self.get_position_mode() == 'fixed':
            if not self.fixed_x_var.get().strip():
                return False, "X 坐标不能为空"
            if not self.fixed_y_var.get().strip():
                return False, "Y 坐标不能为空"
            if self.get_fixed_xy() is None:
                return False, "X/Y 坐标需为整数"

        return True, ""

    def reset_to_defaults(self):
        """重置为默认值"""
        self.set_values({
            'interval_ms': DEFAULT_INTERVAL_MS,
            'record_interval': DEFAULT_RECORD_INTERVAL,
            'hold_duration': DEFAULT_HOLD_DURATION,
            'repeat_count': DEFAULT_REPEAT_COUNT,
            'repeat_interval': DEFAULT_REPEAT_INTERVAL,
            'start_delay_s': DEFAULT_START_DELAY_S,
            'auto_stop_s': DEFAULT_AUTO_STOP_S,
        })
        self.set_click_type('single')
        self.set_position_mode('cursor')
        self.set_fixed_xy(0, 0)
