"""
知识库权限常量模块

定义权限相关的常量和映射。
"""

from app.models.knowledge_base_permission import PermissionType


# 权限等级映射
PERMISSION_LEVELS = {
    PermissionType.VIEWER.value: 1,
    PermissionType.EDITOR.value: 2,
    PermissionType.OWNER.value: 3,
}


__all__ = ["PERMISSION_LEVELS"]
