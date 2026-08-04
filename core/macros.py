"""
宏数据模型模块
定义点击动作的数据结构。

说明：早期版本这里还有 MacroRecorder / MacroPlayer / MacroStorage 三个类，
但录制、回放、存盘能力已全部由 core.engine.ClickerEngine 实现，
那三个类没有任何调用方，属于死代码，已于 v2.0.1 移除。
"""

from typing import Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class ClickAction:
    """表示一个动作（鼠标点击或键盘按键）

    kind='mouse' 时 button 取 'left'/'right'/'middle'/'x1'/'x2'，x/y 为目标坐标；
    kind='key'   时 key 取规范键名（如 'a'、'enter'、'ctrl_l'），x/y 不使用（置 0）。
    """
    x: int
    y: int
    button: str  # 鼠标：'left'/'right'/'middle'/'x1'/'x2'；键盘：留空
    action_type: str  # 'press' 或 'release'
    timestamp: float  # 相对于序列开始的时间戳（秒）
    kind: str = 'mouse'          # 'mouse' | 'key'
    key: Optional[str] = None    # 键盘动作的规范键名（kind='key' 时有效）

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ClickAction':
        """从字典创建实例（兼容旧版无 kind/key 字段的数据）"""
        return cls(
            x=data.get('x', 0),
            y=data.get('y', 0),
            button=data.get('button', 'left'),
            action_type=data.get('action_type', 'press'),
            timestamp=data.get('timestamp', 0.0),
            kind=data.get('kind', 'mouse'),
            key=data.get('key'),
        )
