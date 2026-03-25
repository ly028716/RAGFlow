"""
权限管理服务模块

实现权限的CRUD管理功能。
"""

import logging
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from app.models.knowledge_base import KnowledgeBase
from app.models.knowledge_base_permission import KnowledgeBasePermission, PermissionType
from app.models.user import User
from app.schemas.knowledge_base_permission import PermissionCreate, PermissionUpdate
from app.services.knowledge_base_permission.permission_check_service import \
    PermissionCheckService

logger = logging.getLogger(__name__)


class PermissionManagementService:
    """权限管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self._check_service = PermissionCheckService(db)

    def get_permissions(self, kb_id: int, user_id: int) -> Tuple[List[dict], int]:
        """
        获取知识库的权限列表

        Args:
            kb_id: 知识库ID
            user_id: 当前用户ID（用于权限检查）

        Returns:
            (权限列表, 总数)
        """
        # 检查是否有权限查看
        has_permission, kb = self._check_service.check_permission(
            kb_id, user_id, PermissionType.OWNER.value
        )
        if not has_permission:
            # 非所有者只能看到自己的权限
            permission = (
                self.db.query(KnowledgeBasePermission)
                .filter(
                    KnowledgeBasePermission.knowledge_base_id == kb_id,
                    KnowledgeBasePermission.user_id == user_id,
                )
                .first()
            )

            if permission:
                user = self.db.query(User).filter(User.id == user_id).first()
                return [
                    {
                        "id": permission.id,
                        "knowledge_base_id": permission.knowledge_base_id,
                        "user_id": permission.user_id,
                        "username": user.username if user else None,
                        "permission_type": permission.permission_type,
                        "is_public": permission.is_public,
                        "created_at": permission.created_at,
                    }
                ], 1
            return [], 0

        # 所有者可以看到所有权限 - 使用JOIN优化查询
        permissions = (
            self.db.query(KnowledgeBasePermission)
            .options(joinedload(KnowledgeBasePermission.user))
            .filter(KnowledgeBasePermission.knowledge_base_id == kb_id)
            .all()
        )

        result = []
        for perm in permissions:
            result.append(
                {
                    "id": perm.id,
                    "knowledge_base_id": perm.knowledge_base_id,
                    "user_id": perm.user_id,
                    "username": perm.user.username if perm.user else None,
                    "permission_type": perm.permission_type,
                    "is_public": perm.is_public,
                    "created_at": perm.created_at,
                }
            )

        return result, len(result)

    def add_permission(
        self, kb_id: int, owner_id: int, data: PermissionCreate
    ) -> Optional[KnowledgeBasePermission]:
        """
        添加权限

        Args:
            kb_id: 知识库ID
            owner_id: 所有者ID
            data: 权限数据

        Returns:
            创建的权限对象或None
        """
        # 检查是否为所有者
        kb = (
            self.db.query(KnowledgeBase)
            .filter(KnowledgeBase.id == kb_id, KnowledgeBase.user_id == owner_id)
            .first()
        )

        if not kb:
            return None

        # 不能给自己添加权限
        if data.user_id == owner_id:
            return None

        # 检查用户是否存在
        if data.user_id:
            user = self.db.query(User).filter(User.id == data.user_id).first()
            if not user:
                return None

        # 检查是否已存在权限
        existing = (
            self.db.query(KnowledgeBasePermission)
            .filter(
                KnowledgeBasePermission.knowledge_base_id == kb_id,
                KnowledgeBasePermission.user_id == data.user_id,
            )
            .first()
        )

        if existing:
            # 更新现有权限
            existing.permission_type = data.permission_type
            self.db.commit()
            self.db.refresh(existing)
            return existing

        # 创建新权限
        permission = KnowledgeBasePermission(
            knowledge_base_id=kb_id,
            user_id=data.user_id,
            permission_type=data.permission_type,
            is_public=data.user_id is None,
        )

        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)

        logger.info(
            f"添加权限成功: kb_id={kb_id}, user_id={data.user_id}, type={data.permission_type}"
        )
        return permission

    def update_permission(
        self, kb_id: int, permission_id: int, owner_id: int, data: PermissionUpdate
    ) -> Optional[KnowledgeBasePermission]:
        """
        更新权限

        Args:
            kb_id: 知识库ID
            permission_id: 权限ID
            owner_id: 所有者ID
            data: 更新数据

        Returns:
            更新后的权限对象或None
        """
        # 检查是否为所有者
        kb = (
            self.db.query(KnowledgeBase)
            .filter(KnowledgeBase.id == kb_id, KnowledgeBase.user_id == owner_id)
            .first()
        )

        if not kb:
            return None

        permission = (
            self.db.query(KnowledgeBasePermission)
            .filter(
                KnowledgeBasePermission.id == permission_id,
                KnowledgeBasePermission.knowledge_base_id == kb_id,
            )
            .first()
        )

        if not permission:
            return None

        permission.permission_type = data.permission_type
        self.db.commit()
        self.db.refresh(permission)

        logger.info(
            f"更新权限成功: permission_id={permission_id}, type={data.permission_type}"
        )
        return permission

    def delete_permission(self, kb_id: int, permission_id: int, owner_id: int) -> bool:
        """
        删除权限

        Args:
            kb_id: 知识库ID
            permission_id: 权限ID
            owner_id: 所有者ID

        Returns:
            是否删除成功
        """
        # 检查是否为所有者
        kb = (
            self.db.query(KnowledgeBase)
            .filter(KnowledgeBase.id == kb_id, KnowledgeBase.user_id == owner_id)
            .first()
        )

        if not kb:
            return False

        permission = (
            self.db.query(KnowledgeBasePermission)
            .filter(
                KnowledgeBasePermission.id == permission_id,
                KnowledgeBasePermission.knowledge_base_id == kb_id,
            )
            .first()
        )

        if not permission:
            return False

        self.db.delete(permission)
        self.db.commit()

        logger.info(f"删除权限成功: permission_id={permission_id}")
        return True


__all__ = ["PermissionManagementService"]
