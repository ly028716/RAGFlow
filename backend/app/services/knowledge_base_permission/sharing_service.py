"""
知识库分享服务模块

实现知识库分享功能。
"""

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.knowledge_base import KnowledgeBase
from app.models.knowledge_base_permission import KnowledgeBasePermission
from app.models.user import User
from app.schemas.knowledge_base_permission import PermissionCreate
from app.services.knowledge_base_permission.constants import PERMISSION_LEVELS
from app.services.knowledge_base_permission.permission_management_service import \
    PermissionManagementService


class SharingService:
    """知识库分享服务"""

    def __init__(self, db: Session):
        self.db = db
        self._management_service = PermissionManagementService(db)

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
        # 查找用户
        user = self.db.query(User).filter(User.username == username).first()
        if not user:
            return None

        # 使用add_permission添加权限
        data = PermissionCreate(user_id=user.id, permission_type=permission_type)
        return self._management_service.add_permission(kb_id, owner_id, data)

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
        # 查询用户有权限的知识库（非自己创建的）
        query = (
            self.db.query(KnowledgeBase)
            .join(
                KnowledgeBasePermission,
                KnowledgeBase.id == KnowledgeBasePermission.knowledge_base_id,
            )
            .filter(
                KnowledgeBasePermission.user_id == user_id,
                KnowledgeBase.user_id != user_id,  # 排除自己创建的
            )
        )

        total = query.count()
        knowledge_bases = query.offset(skip).limit(limit).all()

        return knowledge_bases, total


__all__ = ["SharingService"]
