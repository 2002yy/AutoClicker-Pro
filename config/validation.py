"""
验证模块
提供输入数据验证功能
"""

from typing import Tuple, Dict, Any, Optional, List
from .constants import VALIDATION_RULES, ERROR_VALIDATION_FAILED

# 修饰键前缀（pynput 键名：ctrl / ctrl_l / ctrl_r / alt / alt_gr / shift_l / cmd ...）
MODIFIER_PREFIXES = ('ctrl', 'alt', 'shift', 'cmd')


def is_modifier_name(name: Any) -> bool:
    """判断规范键名是否为修饰键（供录制器与校验共用）"""
    if not isinstance(name, str) or not name:
        return False
    return name in MODIFIER_PREFIXES or name.startswith(
        tuple(prefix + '_' for prefix in MODIFIER_PREFIXES)
    )


def validate_modifier_list(modifiers: Any) -> Tuple[bool, str]:
    """校验修饰键列表：非空、元素均为合法修饰键名"""
    if not isinstance(modifiers, (list, tuple)) or len(modifiers) == 0:
        return False, "组合键缺少修饰键列表 (modifiers)"
    for mod in modifiers:
        if not is_modifier_name(mod):
            return False, f"非法的修饰键名：{mod}"
    return True, ""


class ValidationError(Exception):
    """验证异常"""
    pass


def validate_number(value: Any, field_name: str, 
                    min_val: Optional[int] = None, 
                    max_val: Optional[int] = None,
                    required: bool = True) -> Tuple[bool, str]:
    """
    验证数值类型
    
    Args:
        value: 要验证的值
        field_name: 字段名称（用于错误消息）
        min_val: 最小值（None 表示无限制）
        max_val: 最大值（None 表示无限制）
        required: 是否必填
        
    Returns:
        (是否有效，错误消息)
    """
    # 检查是否为空
    if value is None or value == '':
        if required:
            return False, f"{field_name} 不能为空"
        else:
            return True, ""
    
    # 尝试转换为整数
    try:
        num_value = int(value)
    except (ValueError, TypeError):
        return False, f"{field_name} 必须是有效的数字"
    
    # 检查最小值
    if min_val is not None and num_value < min_val:
        return False, f"{field_name} 不能小于 {min_val}"
    
    # 检查最大值
    if max_val is not None and num_value > max_val:
        return False, f"{field_name} 不能大于 {max_val}"
    
    return True, ""


def validate_string(value: Any, field_name: str, 
                    min_length: int = 0, 
                    max_length: Optional[int] = None,
                    required: bool = True,
                    allowed_values: Optional[list] = None) -> Tuple[bool, str]:
    """
    验证字符串类型
    
    Args:
        value: 要验证的值
        field_name: 字段名称
        min_length: 最小长度
        max_length: 最大长度
        required: 是否必填
        allowed_values: 允许的值的列表
        
    Returns:
        (是否有效，错误消息)
    """
    # 检查是否为空
    if value is None or value == '':
        if required:
            return False, f"{field_name} 不能为空"
        else:
            return True, ""
    
    # 转换为字符串
    str_value = str(value)
    
    # 检查长度
    if len(str_value) < min_length:
        return False, f"{field_name} 长度不能小于 {min_length}"
    
    if max_length is not None and len(str_value) > max_length:
        return False, f"{field_name} 长度不能大于 {max_length}"
    
    # 检查允许的值
    if allowed_values is not None and str_value not in allowed_values:
        return False, f"{field_name} 必须是以下值之一：{', '.join(allowed_values)}"
    
    return True, ""


def validate_coordinate(x: Any, y: Any) -> Tuple[bool, str]:
    """
    验证坐标值
    
    Args:
        x: X 坐标
        y: Y 坐标
        
    Returns:
        (是否有效，错误消息)
    """
    # 验证 X 坐标
    is_valid, error_msg = validate_number(
        x, "X 坐标", 
        min_val=VALIDATION_RULES['coordinate_x']['min'],
        max_val=VALIDATION_RULES['coordinate_x']['max'],
        required=VALIDATION_RULES['coordinate_x']['required']
    )
    if not is_valid:
        return False, error_msg
    
    # 验证 Y 坐标
    is_valid, error_msg = validate_number(
        y, "Y 坐标",
        min_val=VALIDATION_RULES['coordinate_y']['min'],
        max_val=VALIDATION_RULES['coordinate_y']['max'],
        required=VALIDATION_RULES['coordinate_y']['required']
    )
    if not is_valid:
        return False, error_msg
    
    return True, ""


def validate_time_inputs(interval_ms: Any, record_interval: Any,
                         hold_duration: Any, repeat_count: Any,
                         repeat_interval: Any,
                         start_delay_s: Any = 0,
                         auto_stop_s: Any = 0) -> Tuple[bool, str]:
    """
    验证时间相关的输入

    Args:
        interval_ms: 点击间隔（毫秒）
        record_interval: 录制间隔（毫秒）
        hold_duration: 按住持续时间（毫秒）
        repeat_count: 重复次数
        repeat_interval: 重复间隔（毫秒）
        start_delay_s: 延迟启动（秒），0 = 立即开始
        auto_stop_s: 自动停止（秒），0 = 不限时

    Returns:
        (是否有效，错误消息)
    """
    # 验证点击间隔
    is_valid, error_msg = validate_number(
        interval_ms, "点击间隔",
        min_val=VALIDATION_RULES['interval_ms']['min'],
        max_val=VALIDATION_RULES['interval_ms']['max'],
        required=VALIDATION_RULES['interval_ms']['required']
    )
    if not is_valid:
        return False, error_msg

    # 验证录制间隔
    is_valid, error_msg = validate_number(
        record_interval, "录制间隔",
        min_val=VALIDATION_RULES['record_interval']['min'],
        max_val=VALIDATION_RULES['record_interval']['max'],
        required=VALIDATION_RULES['record_interval']['required']
    )
    if not is_valid:
        return False, error_msg

    # 验证按住持续时间
    is_valid, error_msg = validate_number(
        hold_duration, "按住持续时间",
        min_val=VALIDATION_RULES['hold_duration']['min'],
        max_val=VALIDATION_RULES['hold_duration']['max'],
        required=VALIDATION_RULES['hold_duration']['required']
    )
    if not is_valid:
        return False, error_msg

    # 验证重复次数（0 表示无限循环直到手动停止）
    is_valid, error_msg = validate_number(
        repeat_count, "重复次数",
        min_val=VALIDATION_RULES['repeat_count']['min'],
        max_val=VALIDATION_RULES['repeat_count']['max'],
        required=VALIDATION_RULES['repeat_count']['required']
    )
    if not is_valid:
        return False, error_msg

    # 验证重复间隔
    is_valid, error_msg = validate_number(
        repeat_interval, "重复间隔",
        min_val=VALIDATION_RULES['repeat_interval']['min'],
        max_val=VALIDATION_RULES['repeat_interval']['max'],
        required=VALIDATION_RULES['repeat_interval']['required']
    )
    if not is_valid:
        return False, error_msg

    # 验证延迟启动 / 自动停止
    for field_name in ('start_delay_s', 'auto_stop_s'):
        rules = VALIDATION_RULES[field_name]
        label = "延迟启动" if field_name == 'start_delay_s' else "自动停止"
        value = start_delay_s if field_name == 'start_delay_s' else auto_stop_s
        is_valid, error_msg = validate_number(
            value, label,
            min_val=rules['min'], max_val=rules['max'],
            required=rules['required']
        )
        if not is_valid:
            return False, error_msg

    return True, ""


def _validate_anchor_fields(action: Dict[str, Any]) -> Tuple[bool, str]:
    """窗口锚定可选字段：要么全缺省，要么 title + 双偏移齐全且类型正确"""
    anchor_title = action.get('anchor_title')
    rel_x = action.get('win_rel_x')
    rel_y = action.get('win_rel_y')
    has_anchor = any(v is not None for v in (anchor_title, rel_x, rel_y))
    if not has_anchor:
        return True, ""
    if not isinstance(anchor_title, str) or not anchor_title.strip():
        return False, "窗口锚定缺少有效标题 (anchor_title)"
    for field_name, value in (('win_rel_x', rel_x), ('win_rel_y', rel_y)):
        if not isinstance(value, int) or isinstance(value, bool):
            return False, f"窗口相对坐标 {field_name} 必须是整数"
    return True, ""


def validate_macro_action(action: Dict[str, Any]) -> Tuple[bool, str]:
    """
    验证宏动作数据

    支持四种动作：
    - 鼠标动作（kind 缺省或为 'mouse'）：需 x/y/button/action_type；
      可选 modifiers（组合键点击）、可选窗口锚定字段
    - 键盘单键（kind='key'）：需 key（规范键名）/action_type，x/y 不使用
    - 键盘组合键（kind='chord'）：需 key + 非空合法的 modifiers 列表
    - 鼠标移动（kind='move'）：需 x/y；无 button 要求，可携带锚定字段

    Args:
        action: 宏动作字典

    Returns:
        (是否有效，错误消息)
    """
    if not isinstance(action, dict):
        return False, "宏动作数据必须是字典格式"

    kind = action.get('kind', 'mouse')

    # 鼠标移动轨迹点：仅坐标（+可选锚定）
    if kind == 'move':
        if 'x' not in action or 'y' not in action:
            return False, "移动动作缺少必需字段：x/y"
        is_valid, error_msg = validate_coordinate(action['x'], action['y'])
        if not is_valid:
            return False, error_msg
        return _validate_anchor_fields(action)

    # 键盘组合键：action_type + key + modifiers
    if kind == 'chord':
        is_valid, error_msg = validate_string(
            action.get('action_type', ''), "动作类型",
            required=True, allowed_values=['press']
        )
        if not is_valid:
            return False, error_msg
        if not action.get('key'):
            return False, "键盘组合键缺少触发键 (key)"
        is_valid, error_msg = validate_modifier_list(action.get('modifiers'))
        if not is_valid:
            return False, error_msg
        return True, ""

    # 键盘单键：只需 action_type + key（x/y/button 不使用）
    if kind == 'key':
        is_valid, error_msg = validate_string(
            action.get('action_type', ''), "动作类型",
            required=True, allowed_values=['press', 'release']
        )
        if not is_valid:
            return False, error_msg
        key = action.get('key')
        if not key:
            return False, "键盘动作缺少键名 (key)"
        return True, ""

    # 鼠标动作：先检查必需字段（保持旧版报错文案），再逐项校验
    for field in ('x', 'y', 'button'):
        if field not in action:
            return False, f"宏动作缺少必需字段：{field}"

    is_valid, error_msg = validate_string(
        action.get('action_type', ''), "动作类型",
        required=True, allowed_values=['press', 'release']
    )
    if not is_valid:
        return False, error_msg

    is_valid, error_msg = validate_coordinate(action['x'], action['y'])
    if not is_valid:
        return False, error_msg

    is_valid, error_msg = validate_string(
        action['button'], "按钮类型",
        required=True,
        allowed_values=['left', 'right', 'middle', 'x1', 'x2']
    )
    if not is_valid:
        return False, error_msg

    # 可选修饰键（组合键点击）
    if action.get('modifiers'):
        is_valid, error_msg = validate_modifier_list(action['modifiers'])
        if not is_valid:
            return False, error_msg

    # 可选窗口锚定字段（鼠标动作）
    is_valid, error_msg = _validate_anchor_fields(action)
    if not is_valid:
        return False, error_msg

    # 验证时间戳（可选）
    if 'timestamp' in action:
        is_valid, error_msg = validate_number(
            action['timestamp'], "时间戳",
            min_val=0,
            required=False
        )
        if not is_valid:
            return False, error_msg

    return True, ""


def validate_macro_sequence(actions: list) -> Tuple[bool, str]:
    """
    验证宏动作序列
    
    Args:
        actions: 宏动作列表
        
    Returns:
        (是否有效，错误消息)
    """
    if not isinstance(actions, list):
        return False, "宏数据必须是列表格式"
    
    if len(actions) == 0:
        return False, "宏动作序列不能为空"
    
    # 验证每个动作
    for i, action in enumerate(actions):
        is_valid, error_msg = validate_macro_action(action)
        if not is_valid:
            return False, f"第 {i+1} 个动作无效：{error_msg}"
    
    return True, ""


def validate_input(field_name: str, value: Any, 
                   input_type: str = 'number') -> Tuple[bool, str]:
    """
    通用输入验证函数
    
    Args:
        field_name: 字段名称
        value: 要验证的值
        input_type: 输入类型 ('number' 或 'string')
        
    Returns:
        (是否有效，错误消息)
    """
    if field_name not in VALIDATION_RULES:
        return True, ""  # 没有规则则默认通过
    
    rules = VALIDATION_RULES[field_name]
    
    if input_type == 'number':
        return validate_number(
            value, field_name,
            min_val=rules.get('min'),
            max_val=rules.get('max'),
            required=rules.get('required', True)
        )
    elif input_type == 'string':
        return validate_string(
            value, field_name,
            required=rules.get('required', True)
        )
    else:
        return False, f"未知的输入类型：{input_type}"
