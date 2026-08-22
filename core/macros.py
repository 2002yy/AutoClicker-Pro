"""
宏数据模型模块
定义动作的数据结构。

动作分三类：
- kind='mouse'  鼠标事件：x/y/button/action_type；可选 modifiers（组合键点击，
  如 Shift+单击——修饰键记录在按下侧与释放侧各一份，回放负责对称按下/释放）；
- kind='key'    单键轻点：key 为规范键名（如 'a'、'enter'）；
- kind='chord'  键盘组合键：modifiers 为按住顺序的修饰键名列表，
  key 为触发键（如 Ctrl+C -> modifiers=['ctrl_l'], key='c'），回放为整体轻点。

说明：早期版本这里还有 MacroRecorder / MacroPlayer / MacroStorage 三个类，
其能力已全部由 core.engine.ClickerEngine 实现，已于 v2.0.1 移除。
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


@dataclass
class ClickAction:
    """表示一个动作（鼠标事件 / 键盘按键 / 键盘组合键）"""
    x: int
    y: int
    button: str  # 鼠标：'left'/'right'/'middle'/'x1'/'x2'；键盘类留空
    action_type: str  # 'press' 或 'release'（chord 固定为 'press'）
    timestamp: float  # 相对于序列开始的时间戳（秒）
    kind: str = 'mouse'           # 'mouse' | 'key' | 'chord'
    key: Optional[str] = None     # key/chord 的触发键规范键名
    modifiers: List[str] = field(default_factory=list)  # 组合键修饰键（按下顺序）

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ClickAction':
        """从字典创建实例（兼容旧版无 kind/key/modifiers 字段的数据）"""
        raw_mods = data.get('modifiers') or []
        return cls(
            x=data.get('x', 0),
            y=data.get('y', 0),
            button=data.get('button', 'left'),
            action_type=data.get('action_type', 'press'),
            timestamp=data.get('timestamp', 0.0),
            kind=data.get('kind', 'mouse'),
            key=data.get('key'),
            modifiers=list(raw_mods),
        )
