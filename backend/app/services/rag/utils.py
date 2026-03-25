"""
RAG 服务工具函数模块

提供文件处理相关的工具函数。
"""

import os
import re


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除不安全字符

    Args:
        filename: 原始文件名

    Returns:
        str: 清理后的文件名
    """
    base = os.path.basename(filename or "").strip() or "upload"
    base = base.replace("\x00", "")
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base)
    if len(base) > 180:
        root, ext = os.path.splitext(base)
        base = f"{root[:160]}{ext[:20]}"
    return base


def normalize_display_filename(filename: str) -> str:
    """
    规范化显示文件名

    Args:
        filename: 原始文件名

    Returns:
        str: 规范化后的文件名
    """
    base = os.path.basename(filename or "").strip() or "upload"
    base = base.replace("\x00", "")
    base = re.sub(r"[\r\n\t]+", " ", base).strip()
    if len(base) > 180:
        root, ext = os.path.splitext(base)
        base = f"{root[:160]}{ext[:20]}"
    return base


__all__ = [
    "sanitize_filename",
    "normalize_display_filename",
]
