"""
System 服务加密工具模块

提供加密、解密和脱敏功能。
"""

import base64
from typing import Optional

from cryptography.fernet import Fernet

from app.config import settings


def get_or_create_encryption_key() -> bytes:
    """
    获取或创建加密密钥

    从环境变量读取加密密钥，如果不存在则生成新密钥。
    注意：生产环境必须配置固定的加密密钥。

    Returns:
        bytes: Fernet加密密钥
    """
    # 从配置读取加密密钥（应该是32字节的base64编码字符串）
    key_str = getattr(settings.app, "encryption_key", None)

    if key_str:
        try:
            # 确保密钥是有效的Fernet密钥格式
            return base64.urlsafe_b64decode(key_str)
        except Exception:
            pass

    # 如果没有配置或配置无效，生成新密钥（仅用于开发环境）
    return Fernet.generate_key()


def encrypt_value(value: str, encryption_key: bytes) -> str:
    """
    加密敏感值

    使用AES-256加密算法（通过Fernet）加密敏感配置。

    Args:
        value: 要加密的明文值
        encryption_key: 加密密钥

    Returns:
        str: 加密后的值（base64编码）
    """
    if not value:
        return value

    try:
        fernet = Fernet(encryption_key)
        encrypted = fernet.encrypt(value.encode("utf-8"))
        return encrypted.decode("utf-8")
    except Exception as e:
        print(f"加密失败: {e}")
        return value


def decrypt_value(encrypted_value: str, encryption_key: bytes) -> str:
    """
    解密敏感值

    Args:
        encrypted_value: 加密的值
        encryption_key: 加密密钥

    Returns:
        str: 解密后的明文值
    """
    if not encrypted_value:
        return encrypted_value

    try:
        fernet = Fernet(encryption_key)
        decrypted = fernet.decrypt(encrypted_value.encode("utf-8"))
        return decrypted.decode("utf-8")
    except Exception as e:
        print(f"解密失败: {e}")
        return encrypted_value


def mask_sensitive_value(value: str, show_chars: int = 4) -> str:
    """
    脱敏敏感值

    显示前几个字符，其余用星号替换。

    Args:
        value: 要脱敏的值
        show_chars: 显示的字符数

    Returns:
        str: 脱敏后的值
    """
    if not value or len(value) <= show_chars:
        return "*" * len(value) if value else ""

    return value[:show_chars] + "*" * (len(value) - show_chars)


__all__ = [
    "get_or_create_encryption_key",
    "encrypt_value",
    "decrypt_value",
    "mask_sensitive_value",
]
