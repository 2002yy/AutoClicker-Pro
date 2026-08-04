"""
常量定义模块
集中管理应用程序的所有常量配置
"""

# ==================== 应用程序基础配置 ====================
APP_NAME = "自动点击器 Pro"
APP_VERSION = "2.0.0"
APP_WIDTH = 450
APP_HEIGHT = 650
APP_MIN_WIDTH = 400
APP_MIN_HEIGHT = 550

# ==================== 颜色定义 ====================
COLOR_PRIMARY = "#4A90E2"
COLOR_SUCCESS = "#5CB85C"
COLOR_WARNING = "#F0AD4E"
COLOR_DANGER = "#D9534F"
COLOR_INFO = "#5BC0DE"
COLOR_LIGHT = "#F8F9FA"
COLOR_DARK = "#343A40"
COLOR_WHITE = "#FFFFFF"
COLOR_BLACK = "#000000"
COLOR_DISABLED = "#6C757D"
COLOR_BACKGROUND = "#F5F5F5"

# ==================== 字体配置 ====================
FONT_FAMILY = "微软雅黑"
FONT_SIZE_NORMAL = 10
FONT_SIZE_LARGE = 12
FONT_SIZE_TITLE = 14
FONT_SIZE_SMALL = 9

# ==================== 默认设置 ====================
DEFAULT_MOUSE_BUTTON = 'left'
DEFAULT_INTERVAL_MS = 100
DEFAULT_RECORD_INTERVAL = 100
DEFAULT_HOLD_DURATION = 100
DEFAULT_REPEAT_COUNT = 1
DEFAULT_REPEAT_INTERVAL = 1000

# ==================== 时间单位换算 ====================
MS_PER_SECOND = 1000
MS_PER_MINUTE = 60000
MS_PER_HOUR = 3600000

# ==================== 全局快捷键定义 ====================
# 注意：这里使用 pynput 的按键名（小写），由 utils.hotkey_manager 注册为全局热键，
# 窗口失焦时同样生效。组合键写法示例：'ctrl+shift+s'。
HOTKEY_START_STOP = 'f8'          # 开始 / 停止连点
HOTKEY_START_RECORDING = 'f10'    # 开始录制
HOTKEY_STOP_RECORDING = 'f11'     # 停止录制
HOTKEY_CANCEL = 'esc'             # 取消（停止录制 / 停止连点）

# 展示给用户的快捷键说明
HOTKEY_HINT = "F8 启停连点 | F10 录制 | F11 停止录制 | ESC 全部停止"

# ==================== 文件路径配置 ====================
CONFIG_DIR = ".autoclicker_pro"
KEY_FILE = ".key"
SALT_FILE = "salt.key"

# ==================== 加密配置 ====================
ENCRYPTION_ITERATIONS = 100000
ENCRYPTION_KEY_LENGTH = 32

# ==================== 验证规则 ====================
VALIDATION_RULES = {
    'interval_ms': {'min': 1, 'max': 60000, 'required': True},
    'record_interval': {'min': 1, 'max': 10000, 'required': True},
    'hold_duration': {'min': 0, 'max': 5000, 'required': False},
    'repeat_count': {'min': 1, 'max': 10000, 'required': True},
    'repeat_interval': {'min': 0, 'max': 3600000, 'required': False},
    'coordinate_x': {'min': 0, 'max': None, 'required': True},  # None 表示无上限
    'coordinate_y': {'min': 0, 'max': None, 'required': True},
}

# ==================== UI 布局配置 ====================
PADDING_STANDARD = 10
PADDING_LARGE = 20
PADDING_SMALL = 5
GRID_STICKY_ALL = "nsew"
GRID_STICKY_W = "w"
GRID_STICKY_E = "e"
GRID_STICKY_N = "n"
GRID_STICKY_S = "s"

# ==================== 列表框配置 ====================
LISTBOX_HEIGHT = 10
LISTBOX_WIDTH = 50

# ==================== 按钮样式 ====================
STYLE_DANGER = "Danger.TButton"
STYLE_PRIMARY = "Primary.TButton"
STYLE_SUCCESS = "Success.TButton"

# ==================== 状态消息 ====================
STATUS_READY = "就绪"
STATUS_RUNNING = "正在点击..."
STATUS_STOPPED = "已停止"
STATUS_RECORDING = "正在录制鼠标/键盘... 按 ESC 停止"
STATUS_RECORDING_STOPPED = "录制已停止"
STATUS_LOADING = "加载中..."
STATUS_SAVING = "保存中..."

# ==================== 错误消息 ====================
ERROR_INVALID_INPUT = "输入错误"
ERROR_FILE_NOT_FOUND = "文件未找到"
ERROR_SAVE_FAILED = "保存失败"
ERROR_LOAD_FAILED = "加载失败"
ERROR_VALIDATION_FAILED = "验证失败"
