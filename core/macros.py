"""
宏录制与播放核心逻辑模块
负责处理点击序列的录制、存储、回放和编辑
"""

import time
import json
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path

from config.encryption import EncryptionManager


@dataclass
class ClickAction:
    """表示一个点击动作"""
    x: int
    y: int
    button: str  # 'left', 'right', 'middle'
    action_type: str  # 'press' 或 'release'
    timestamp: float  # 相对于序列开始的时间戳
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ClickAction':
        """从字典创建实例"""
        return cls(**data)


class MacroRecorder:
    """宏录制器，负责录制鼠标点击序列"""
    
    def __init__(self):
        self.click_sequence: List[ClickAction] = []
        self.is_recording = False
        self.recording_start_time: float = 0
        self.on_action_recorded: Optional[Callable[[ClickAction], None]] = None
    
    def start_recording(self):
        """开始录制"""
        self.click_sequence = []
        self.is_recording = True
        self.recording_start_time = time.time()
    
    def stop_recording(self):
        """停止录制"""
        self.is_recording = False
    
    def record_action(self, x: int, y: int, button: str, action_type: str):
        """记录一个点击动作"""
        if not self.is_recording:
            return
        
        timestamp = time.time() - self.recording_start_time
        action = ClickAction(x, y, button, action_type, timestamp)
        self.click_sequence.append(action)
        
        if self.on_action_recorded:
            self.on_action_recorded(action)
    
    def get_sequence(self) -> List[ClickAction]:
        """获取录制的序列"""
        return self.click_sequence.copy()
    
    def clear_sequence(self):
        """清空序列"""
        self.click_sequence = []


class MacroPlayer:
    """宏播放器，负责回放点击序列"""
    
    def __init__(self):
        self.is_playing = False
        self.should_stop = False
        self.on_playback_complete: Optional[Callable[[], None]] = None
    
    def play_sequence(
        self,
        sequence: List[ClickAction],
        mouse_controller,
        interval_ms: int = 100,
        hold_duration: int = 100,
        repeat_count: int = 1,
        repeat_interval: int = 1000
    ):
        """
        播放点击序列
        
        Args:
            sequence: 点击动作序列
            mouse_controller: 鼠标控制器实例
            interval_ms: 动作间隔（毫秒）
            hold_duration: 按住持续时间（毫秒）
            repeat_count: 重复次数
            repeat_interval: 重复间隔（毫秒）
        """
        self.is_playing = True
        self.should_stop = False
        
        try:
            for i in range(repeat_count):
                if self.should_stop:
                    break
                
                for j, action in enumerate(sequence):
                    if self.should_stop:
                        break
                    
                    # 移动鼠标到指定位置
                    mouse_controller.position = (action.x, action.y)
                    
                    # 执行点击动作
                    from pynput.mouse import Button
                    button_map = {
                        'left': Button.left,
                        'right': Button.right,
                        'middle': Button.middle
                    }
                    button = button_map.get(action.button, Button.left)
                    
                    if action.action_type == 'press':
                        mouse_controller.press(button)
                        
                        # 如果是按下动作，等待指定的持续时间后释放
                        if hold_duration > 0:
                            time.sleep(hold_duration / 1000.0)
                            mouse_controller.release(button)
                    elif action.action_type == 'release':
                        mouse_controller.release(button)
                    
                    # 根据间隔等待（最后一个动作不需要等待）
                    if j < len(sequence) - 1:
                        time.sleep(interval_ms / 1000.0)
                
                # 如果不是最后一次重复，则等待重复间隔
                if i < repeat_count - 1 and not self.should_stop:
                    time.sleep(repeat_interval / 1000.0)
        finally:
            self.is_playing = False
            if self.on_playback_complete:
                self.on_playback_complete()
    
    def stop(self):
        """停止播放"""
        self.should_stop = True


class MacroStorage:
    """宏存储管理器，负责宏的保存和加载（支持加密）"""
    
    def __init__(self, storage_dir: str = "./macros"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.encryption_manager = EncryptionManager()
    
    def save_macro(self, name: str, sequence: List[ClickAction], password: Optional[str] = None):
        """
        保存宏到文件
        
        Args:
            name: 宏名称
            sequence: 点击动作序列
            password: 可选的加密密码
        """
        # 转换为字典列表
        data = [action.to_dict() for action in sequence]
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        
        # 确定文件路径
        file_path = self.storage_dir / f"{name}.macro"
        
        if password:
            # 加密保存（encrypt 返回的是字符串）
            encrypted_data = self.encryption_manager.encrypt(json_str, password)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
        else:
            # 明文保存
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
    
    def load_macro(self, name: str, password: Optional[str] = None) -> List[ClickAction]:
        """
        从文件加载宏
        
        Args:
            name: 宏名称
            password: 可选的解密密码
            
        Returns:
            点击动作序列
        """
        file_path = self.storage_dir / f"{name}.macro"
        
        if not file_path.exists():
            raise FileNotFoundError(f"宏文件不存在：{name}")
        
        # 如果提供了密码，直接使用密码解密
        if password:
            with open(file_path, 'r', encoding='utf-8') as f:
                encrypted_data = f.read().strip()
            
            json_str = self.encryption_manager.decrypt(encrypted_data, password)
        else:
            # 没有密码，尝试检测是否加密（通过读取前几个字节判断）
            with open(file_path, 'rb') as f:
                first_bytes = f.read(10)
            
            # 简单的加密检测：加密数据通常包含特殊字符
            is_encrypted = any(b > 127 or b < 32 for b in first_bytes if b not in (ord('\n'), ord('\r')))
            
            if is_encrypted:
                raise ValueError("该宏文件已加密，需要提供密码")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                json_str = f.read()
        
        # 解析 JSON 并转换为 ClickAction 列表
        data = json.loads(json_str)
        return [ClickAction.from_dict(item) for item in data]
    
    def list_macros(self) -> List[str]:
        """列出所有可用的宏名称"""
        macros = []
        for file_path in self.storage_dir.glob("*.macro"):
            macros.append(file_path.stem)
        return macros
    
    def delete_macro(self, name: str) -> bool:
        """删除指定宏"""
        file_path = self.storage_dir / f"{name}.macro"
        if file_path.exists():
            file_path.unlink()
            return True
        return False
