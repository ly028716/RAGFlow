"""
权限检查服务模块

实现权限检查功能。
"""

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.knowledge_base import KnowledgeBase
from app.models.knowledge_base_permission import KnowledgeBasePermission, PermissionType
from app.models.user import User
from app.services.knowledge_base_permission.constants import PERMISSION_LEVELS


class PermissionCheckService:
    """权限检查服务"""

    def __init__(self, db: Session):
        self.db = db

    def check_permission(
        self,
        kb_id: int,
        user_id: int,
        required_permission: str = PermissionType.VIEWER.value,
    ) -> Tuple[bool, Optional[KnowledgeBase]]:
        """
        检查用户对知识库的权限

        Args:
            kb_id: 知识库ID
            user_id: 用户ID
            required_permission: 所需权限级别

        Returns:
            (是否有权限, 知识库对象)
        """
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            return False, None

        # 检查是否为超级管理员
        user = self.db.query(User).filter(User.id == user_id).first()
        if user and user.is_admin:
            return True, kb

        # 所有者拥有所有权限
        if kb.user_id == user_id:
            return True, kb

        # 检查公开知识库（仅查看权限）
        if hasattr(kb, "visibility") and kb.visibility == "public":
            if required_permission == PermissionType.VIEWER.value:
                return True, kb

        # 检查用户权限
        permission = (
            self.db.query(KnowledgeBasePermission)
            .filter(
                KnowledgeBasePermission.knowledge_base_id == kb_id,
                KnowledgeBasePermission.user_id == user_id,
            )
            .first()
        )

        if not permission:
            return False, kb

        # 权限等级检查
        user_level = PERMISSION_LEVELS.get(permission.permission_type, 0)
        required_level = PERMISSION_LEVELS.get(required_permission, 0)

        return user_level >= required_level, kb

    def check_permissions_batch(
        self,
        kb_ids: List[int],
        user_id: int,
        required_permission: str = PermissionType.VIEWER.value,
    ) -> Tuple[bool, List[int]]:
        """
        批量检查用户对知识库的权限

        Args:
            kb_ids: 知识库ID列表
            user_id: 用户ID
            required_permission: 所需权限级别

        Returns:
            (是否全部有权限, 无权限的知识库ID列表)
        """
        if not kb_ids:
            return True, []

        # 检查是否为超级管理员
        user = self.db.query(User).filter(User.id == user_id).first()
        if user and user.is_admin:
            return True, []

        # 查询所有涉及的知识库
        kbs = self.db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(kb_ids)).all()
        kb_map = {kb.id: kb for kb in kbs}

        # 检查不存在的知识库
        found_ids = set(kb_map.keys())
        missing_ids = [kb_id for kb_id in kb_ids if kb_id not in found_ids]
        if missing_ids:
            return False, missing_ids

        # 查询用户的权限记录
        permissions = (
            self.db.query(KnowledgeBasePermission)
            .filter(
                KnowledgeBasePermission.knowledge_base_id.in_(kb_ids),
                KnowledgeBasePermission.user_id == user_id,
            )
            .all()
        )
        perm_map = {p.knowledge_base_id: p for p in permissions}

        required_level = PERMISSION_LEVELS.get(required_permission, 0)
        failed_ids = []

        for kb_id in kb_ids:
            kb = kb_map[kb_id]

            # 1. 所有者拥有所有权限
            if kb.user_id == user_id:
                continue

            # 2. 公开知识库（仅查看权限）
            if (
                hasattr(kb, "visibility")
                and kb.visibility == "public"
                and required_permission == PermissionType.VIEWER.value
            ):
                continue

            # 3. 检查权限记录
            permission = perm_map.get(kb_id)
            if not permission:
                failed_ids.append(kb_id)
                continue

            user_level = PERMISSION_LEVELS.get(permission.permission_type, 0)
            if user_level < required_level:
                failed_ids.append(kb_id)

        return len(failed_ids) == 0, failed_ids


__all__ = ["PermissionCheckService"]
