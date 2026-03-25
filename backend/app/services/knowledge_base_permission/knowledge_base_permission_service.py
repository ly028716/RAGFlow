"""
知识库权限服务 Facade

提供统一的知识库权限服务接口，委托给各子服务处理。
"""

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.knowledge_base import KnowledgeBase
from app.models.knowledge_base_permission import KnowledgeBasePermission
from app.schemas.knowledge_base_permission import PermissionCreate, PermissionUpdate
from app.services.knowledge_base_permission.permission_check_service import \
    PermissionCheckService
from app.services.knowledge_base_permission.permission_management_service import \
    PermissionManagementService
from app.services.knowledge_base_permission.sharing_service import SharingService


class KnowledgeBasePermissionService:
    """
    知识库权限服务 Facade 类

    提供知识库权限的管理功能。
    内部委托给各子服务处理，保持向后兼容。
    """

    def __init__(self, db: Session):
        """
        初始化权限服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self._check_service = PermissionCheckService(db)
        self._management_service = PermissionManagementService(db)
        self._sharing_service = SharingService(db)

    def check_permission(
        self,
        kb_id: int,
        user_id: int,
        required_permission: str = "viewer",
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
        return self._check_service.check_permission(kb_id, user_id, required_permission)

    def check_permissions_batch(
        self,
        kb_ids: List[int],
        user_id: int,
        required_permission: str = "viewer",
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
        return self._check_service.check_permissions_batch(kb_ids, user_id, required_permission)

    def get_permissions(self, kb_id: int, user_id: int) -> Tuple[List[dict], int]:
        """
        获取知识库的权限列表

        Args:
            kb_id: 知识库ID
            user_id: 当前用户ID（用于权限检查）

        Returns:
            (权限列表, 总数)
        """
        return self._management_service.get_permissions(kb_id, user_id)

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
        return self._management_service.add_permission(kb_id, owner_id, data)

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
        return self._management_service.update_permission(kb_id, permission_id, owner_id, data)

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
        return self._management_service.delete_permission(kb_id, permission_id, owner_id)

    def share_by_username(
        self,
        kb_id: int,
        owner_id: int,
        username: str,
        permission_type: str = "viewer",
    ) -> Optional[KnowledgeBasePermission]:
        """
        通过用户名分享知识库

        Args:
            kb_id: 知识库ID
            owner_id: 所有者ID
            username: 目标用户名
            permission_type: 权限类型

        Returns:
            创建的权限对象或None
        """
        return self._sharing_service.share_by_username(kb_id, owner_id, username, permission_type)

    def get_shared_knowledge_bases(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> Tuple[List[KnowledgeBase], int]:
        """
        获取分享给用户的知识库列表

        Args:
            user_id: 用户ID
            skip: 跳过数量
            limit: 返回数量

        Returns:
            (知识库列表, 总数)
        """
        return self._sharing_service.get_shared_knowledge_bases(user_id, skip, limit)


__all__ = ["KnowledgeBasePermissionService"]
