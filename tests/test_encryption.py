"""
测试加密模块
"""

import unittest
import sys
import os
import tempfile
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.encryption import EncryptionManager, encrypt_macro, decrypt_macro


class TestEncryption(unittest.TestCase):
    """测试加密功能"""
    
    def setUp(self):
        """测试前准备"""
        self.manager = EncryptionManager()
        self.test_data = [
            {'x': 100, 'y': 200, 'button': 'left', 'action_type': 'press'},
            {'x': 100, 'y': 200, 'button': 'left', 'action_type': 'release'}
        ]
    
    def test_encrypt_decrypt_string(self):
        """测试字符串加解密"""
        original = "Hello, World!"
        encrypted = self.manager.encrypt(original)
        
        # 加密后的数据应该不同
        self.assertNotEqual(original, encrypted)
        
        # 解密后应该恢复原始数据
        decrypted = self.manager.decrypt(encrypted)
        self.assertEqual(original, decrypted)
    
    def test_encrypt_decrypt_dict(self):
        """测试字典加解密"""
        original = {'key': 'value', 'number': 42}
        encrypted = self.manager.encrypt(original)
        decrypted = self.manager.decrypt(encrypted)
        
        self.assertEqual(original, decrypted)
    
    def test_encrypt_decrypt_list(self):
        """测试列表加解密"""
        original = self.test_data
        encrypted = self.manager.encrypt(original)
        decrypted = self.manager.decrypt(encrypted)
        
        self.assertEqual(original, decrypted)
    
    def test_encrypt_file_and_decrypt_file(self):
        """测试文件加解密"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.enc', delete=False) as f:
            temp_path = f.name
        
        try:
            # 加密保存到文件
            self.manager.encrypt_file(self.test_data, temp_path)
            
            # 从文件解密
            decrypted = self.manager.decrypt_file(temp_path)
            
            self.assertEqual(self.test_data, decrypted)
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_encrypt_macro_function(self):
        """测试 encrypt_macro 辅助函数"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.enc', delete=False) as f:
            temp_path = f.name
        
        try:
            # 使用辅助函数加密
            encrypt_macro(self.test_data, temp_path)
            
            # 使用辅助函数解密
            decrypted = decrypt_macro(temp_path)
            
            self.assertEqual(self.test_data, decrypted)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_invalid_encrypted_data(self):
        """测试无效加密数据"""
        with self.assertRaises(Exception):
            self.manager.decrypt("invalid_encrypted_data")


if __name__ == '__main__':
    unittest.main()
