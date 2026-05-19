"""
加密模块
提供宏数据的加密和解密功能
"""

import os
import base64
import json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
from typing import Optional, List, Dict, Any

from .constants import (
    CONFIG_DIR, KEY_FILE, SALT_FILE, ENCRYPTED_CONFIG_FILE,
    ENCRYPTION_ALGORITHM, ENCRYPTION_ITERATIONS, ENCRYPTION_KEY_LENGTH
)


class EncryptionManager:
    """加密管理器，负责密钥生成、加载和数据加解密"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._cipher = None
        self._key_dir = None
        self._ensure_config_dir()
        self._load_or_create_key()
        self._initialized = True
    
    def _ensure_config_dir(self):
        """确保配置目录存在"""
        home_dir = os.path.expanduser("~")
        self._key_dir = os.path.join(home_dir, CONFIG_DIR)
        
        if not os.path.exists(self._key_dir):
            os.makedirs(self._key_dir, mode=0o700)  # 仅所有者可读写执行
    
    def _generate_salt(self) -> bytes:
        """生成随机盐"""
        return os.urandom(16)
    
    def _load_or_create_salt(self) -> bytes:
        """加载或创建盐值"""
        salt_path = os.path.join(self._key_dir, SALT_FILE)
        
        if os.path.exists(salt_path):
            with open(salt_path, 'rb') as f:
                return f.read()
        else:
            salt = self._generate_salt()
            with open(salt_path, 'wb') as f:
                f.write(salt)
            # 设置文件权限为仅所有者可读写
            os.chmod(salt_path, 0o600)
            return salt
    
    def _create_key_from_password(self, password: str, salt: bytes) -> bytes:
        """从密码和盐生成加密密钥"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=ENCRYPTION_KEY_LENGTH,
            salt=salt,
            iterations=ENCRYPTION_ITERATIONS,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def _load_or_create_key(self):
        """加载或生成加密密钥"""
        key_path = os.path.join(self._key_dir, KEY_FILE)
        salt = self._load_or_create_salt()
        
        if os.path.exists(key_path):
            # 加载现有密钥
            with open(key_path, 'rb') as f:
                stored_data = json.load(f)
                password = stored_data.get('password')
                
                if password:
                    key = self._create_key_from_password(password, salt)
                    self._cipher = Fernet(key)
        else:
            # 生成新密钥（使用随机密码）
            import secrets
            password = secrets.token_urlsafe(32)
            key = self._create_key_from_password(password, salt)
            self._cipher = Fernet(key)
            
            # 保存密钥信息
            with open(key_path, 'w') as f:
                json.dump({'password': password}, f)
            
            # 设置文件权限为仅所有者可读写
            os.chmod(key_path, 0o600)
    
    def encrypt(self, data: Any, password: Optional[str] = None) -> str:
        """
        加密数据
        
        Args:
            data: 要加密的数据（将被转换为 JSON 字符串）
            password: 可选的密码。如果提供，将使用 PBKDF2 从密码派生密钥；
                     否则使用预生成的密钥
                     
        Returns:
            加密后的 Base64 字符串
        """
        # 将数据转换为 JSON 字符串
        json_str = json.dumps(data, ensure_ascii=False)
        json_bytes = json_str.encode('utf-8')
        
        if password:
            # 使用提供的密码生成密钥
            salt = self._load_or_create_salt()
            key = self._create_key_from_password(password, salt)
            cipher = Fernet(key)
            encrypted_bytes = cipher.encrypt(json_bytes)
        else:
            # 使用预生成的密钥
            if self._cipher is None:
                raise RuntimeError("加密器未初始化")
            encrypted_bytes = self._cipher.encrypt(json_bytes)
        
        # 转换为 Base64 字符串
        return base64.b64encode(encrypted_bytes).decode('utf-8')
    
    def decrypt(self, encrypted_data: str, password: Optional[str] = None) -> Any:
        """
        解密数据
        
        Args:
            encrypted_data: 加密的 Base64 字符串
            password: 可选的密码。如果提供，将使用 PBKDF2 从密码派生密钥；
                     否则使用预生成的密钥
                     
        Returns:
            解密后的 Python 对象
        """
        # 从 Base64 转换为字节
        encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        
        if password:
            # 使用提供的密码生成密钥
            salt = self._load_or_create_salt()
            key = self._create_key_from_password(password, salt)
            cipher = Fernet(key)
            decrypted_bytes = cipher.decrypt(encrypted_bytes)
        else:
            # 使用预生成的密钥
            if self._cipher is None:
                raise RuntimeError("加密器未初始化")
            decrypted_bytes = self._cipher.decrypt(encrypted_bytes)
        
        # 解析 JSON
        json_str = decrypted_bytes.decode('utf-8')
        return json.loads(json_str)
    
    def encrypt_file(self, data: Any, filepath: str):
        """
        加密并保存到文件
        
        Args:
            data: 要加密的数据
            filepath: 输出文件路径
        """
        encrypted_data = self.encrypt(data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(encrypted_data)
    
    def decrypt_file(self, filepath: str) -> Any:
        """
        从文件读取并解密
        
        Args:
            filepath: 输入文件路径
            
        Returns:
            解密后的 Python 对象
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            encrypted_data = f.read().strip()
        
        return self.decrypt(encrypted_data)
    
    def reset_key(self):
        """重置密钥（会删除旧密钥并生成新密钥）"""
        key_path = os.path.join(self._key_dir, KEY_FILE)
        salt_path = os.path.join(self._key_dir, SALT_FILE)
        
        # 删除旧文件
        if os.path.exists(key_path):
            os.remove(key_path)
        if os.path.exists(salt_path):
            os.remove(salt_path)
        
        # 重新初始化
        self._cipher = None
        self._load_or_create_key()


def encrypt_macro(macro_data: List[Dict[str, Any]], filepath: str):
    """
    加密宏数据并保存到文件
    
    Args:
        macro_data: 宏动作列表
        filepath: 输出文件路径
    """
    manager = EncryptionManager()
    manager.encrypt_file(macro_data, filepath)


def decrypt_macro(filepath: str) -> List[Dict[str, Any]]:
    """
    从文件读取并解密宏数据
    
    Args:
        filepath: 输入文件路径
        
    Returns:
        宏动作列表
    """
    manager = EncryptionManager()
    return manager.decrypt_file(filepath)
