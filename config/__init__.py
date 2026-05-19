"""
配置模块初始化文件
"""

from .constants import *
from .encryption import EncryptionManager, encrypt_macro, decrypt_macro
from .validation import (
    ValidationError,
    validate_number,
    validate_string,
    validate_coordinate,
    validate_time_inputs,
    validate_macro_action,
    validate_macro_sequence,
    validate_input
)

__all__ = [
    # 常量
    'APP_NAME', 'APP_VERSION', 'APP_WIDTH', 'APP_HEIGHT',
    'COLOR_PRIMARY', 'COLOR_SUCCESS', 'COLOR_DANGER',
    'FONT_FAMILY', 'FONT_SIZE_NORMAL',
    'DEFAULT_INTERVAL_MS', 'DEFAULT_RECORD_INTERVAL',
    'KEY_MAP', 'BUTTON_MAP_REVERSE',
    'VALIDATION_RULES',
    
    # 加密
    'EncryptionManager',
    'encrypt_macro',
    'decrypt_macro',
    
    # 验证
    'ValidationError',
    'validate_number',
    'validate_string',
    'validate_coordinate',
    'validate_time_inputs',
    'validate_macro_action',
    'validate_macro_sequence',
    'validate_input',
]
