"""
知识库服务模块

实现知识库管理相关业务逻辑。
"""

import logging
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.knowledge_base import KnowledgeBase
from app.models.knowledge_base_permission import PermissionType
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.services.knowledge_base_permission import KnowledgeBasePermissionService
from app.services.rag.base import BaseRAGService
from app.services.rag.exceptions import KnowledgeBaseNotFoundError

logger = logging.getLogger(__name__)


class KnowledgeBaseService(BaseRAGService):
    """
    知识库服务类

    提供知识库的CRUD操作。

    使用方式:
        service = KnowledgeBaseService(db)
        kb = service.create(user_id=1, name="技术文档", description="技术相关文档")
        kbs, total = service.get_list(user_id=1, skip=0, limit=20)
    """

    def __init__(self, db: Session):
        """
        初始化知识库服务

        Args:
            db: SQLAlchemy数据库会话
        """
        super().__init__(db)
        self.kb_repo = KnowledgeBaseRepository(db)
        self.kb_permission_service = KnowledgeBasePermissionService(db)

    def _require_permission(
        self,
        kb_id: int,
        user_id: int,
        required_permission: str,
    ) -> KnowledgeBase:
        """
        检查用户是否有权限访问知识库

        Args:
            kb_id: 知识库ID
            user_id: 用户ID
            required_permission: 所需权限

        Returns:
            KnowledgeBase: 知识库对象

        Raises:
            KnowledgeBaseNotFoundError: 知识库不存在或无权限
        """
        has_permission, kb = self.kb_permission_service.check_permission(
            kb_id, user_id, required_permission
        )
        if not has_permission or kb is None:
            raise KnowledgeBaseNotFoundError(f"知识库不存在: id={kb_id}")
        return kb

    def create(
        self,
        user_id: int,
        name: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
    ) -> KnowledgeBase:
        """
        创建知识库

        Args:
            user_id: 用户ID
            name: 知识库名称
            description: 知识库描述
            category: 知识库分类

        Returns:
            KnowledgeBase: 创建的知识库对象

        需求引用:
            - 需求3.1: 用户创建知识库且提供名称和描述
        """
        logger.info(f"创建知识库: user_id={user_id}, name={name}")

        kb = self.kb_repo.create(
            user_id=user_id,
            name=name,
            description=description,
            category=category,
        )

        logger.info(f"知识库创建成功: id={kb.id}, name={kb.name}")
        return kb

    def get_list(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[KnowledgeBase], int]:
        """
        获取用户的知识库列表

        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            Tuple[List[KnowledgeBase], int]: (知识库列表, 总数)
        """
        return self.kb_repo.get_by_user(user_id, skip, limit)

    def get_by_id(
        self,
        kb_id: int,
        user_id: int,
    ) -> KnowledgeBase:
        """
        获取知识库详情

        Args:
            kb_id: 知识库ID
            user_id: 用户ID

        Returns:
            KnowledgeBase: 知识库对象

        Raises:
            KnowledgeBaseNotFoundError: 知识库不存在
        """
        return self._require_permission(kb_id, user_id, PermissionType.VIEWER.value)

    def get_for_edit(
        self,
        kb_id: int,
        user_id: int,
    ) -> KnowledgeBase:
        """
        获取可编辑的知识库

        Args:
            kb_id: 知识库ID
            user_id: 用户ID

        Returns:
            KnowledgeBase: 知识库对象

        Raises:
            KnowledgeBaseNotFoundError: 知识库不存在或无编辑权限
        """
        return self._require_permission(kb_id, user_id, PermissionType.EDITOR.value)

    def update(
        self,
        kb_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
    ) -> KnowledgeBase:
        """
        更新知识库信息

        Args:
            kb_id: 知识库ID
            user_id: 用户ID
            name: 新名称
            description: 新描述
            category: 新分类

        Returns:
            KnowledgeBase: 更新后的知识库对象

        Raises:
            KnowledgeBaseNotFoundError: 知识库不存在
        """
        kb = self.kb_repo.update(kb_id, user_id, name, description, category)
        if not kb:
            raise KnowledgeBaseNotFoundError(f"知识库不存在: id={kb_id}")

        logger.info(f"知识库更新成功: id={kb_id}")
        return kb

    def delete(
        self,
        kb_id: int,
        user_id: int,
    ) -> bool:
        """
        删除知识库

        删除知识库及其所有文档和向量数据。

        Args:
            kb_id: 知识库ID
            user_id: 用户ID

        Returns:
            bool: 是否删除成功

        Raises:
            KnowledgeBaseNotFoundError: 知识库不存在
        """
        # 检查知识库是否存在
        kb = self.kb_repo.get_by_id_and_user(kb_id, user_id)
        if not kb:
            raise KnowledgeBaseNotFoundError(f"知识库不存在: id={kb_id}")

        # 删除数据库记录
        success = self.kb_repo.delete(kb_id, user_id)

        if success:
            logger.info(f"知识库删除成功: id={kb_id}")

        return success

    def get_raw(self, kb_id: int) -> Optional[KnowledgeBase]:
        """
        直接获取知识库（不检查权限）

        Args:
            kb_id: 知识库ID

        Returns:
            Optional[KnowledgeBase]: 知识库对象或None
        """
        return self.kb_repo.get_by_id(kb_id)


__all__ = [
    "KnowledgeBaseService",
]
