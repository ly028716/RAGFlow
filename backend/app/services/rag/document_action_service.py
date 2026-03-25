"""
文档操作服务模块

实现文档操作相关业务逻辑，包括删除、重试处理等。
"""

import logging
import os

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.vector_store import get_vector_store_manager
from app.models.document import Document, DocumentStatus
from app.models.knowledge_base_permission import PermissionType
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.services.knowledge_base_permission import KnowledgeBasePermissionService
from app.services.rag.base import BaseRAGService
from app.services.rag.exceptions import DocumentNotFoundError, KnowledgeBaseNotFoundError
from app.tasks.document_tasks import process_document_task

logger = logging.getLogger(__name__)


class DocumentActionService(BaseRAGService):
    """
    文档操作服务类

    提供文档操作功能，包括删除、重试处理等。

    使用方式:
        service = DocumentActionService(db)
        success = await service.delete(document_id=1, user_id=1)
        doc = await service.retry_processing(document_id=1, user_id=1, background_tasks=tasks)
    """

    def __init__(self, db: Session):
        """
        初始化操作服务

        Args:
            db: SQLAlchemy数据库会话
        """
        super().__init__(db)
        self.doc_repo = DocumentRepository(db)
        self.kb_repo = KnowledgeBaseRepository(db)
        self.kb_permission_service = KnowledgeBasePermissionService(db)
        self.vector_store_manager = get_vector_store_manager()

    def _require_kb_permission(
        self,
        kb_id: int,
        user_id: int,
        required_permission: str,
    ):
        """
        检查用户是否有权限访问知识库

        Args:
            kb_id: 知识库ID
            user_id: 用户ID
            required_permission: 所需权限

        Raises:
            KnowledgeBaseNotFoundError: 知识库不存在或无权限
        """
        has_permission, kb = self.kb_permission_service.check_permission(
            kb_id, user_id, required_permission
        )
        if not has_permission or kb is None:
            raise KnowledgeBaseNotFoundError(f"知识库不存在: id={kb_id}")
        return kb

    async def retry_processing(
        self,
        document_id: int,
        user_id: int,
        background_tasks: BackgroundTasks,
    ) -> Document:
        """
        重试文档处理

        Args:
            document_id: 文档ID
            user_id: 用户ID
            background_tasks: FastAPI后台任务

        Returns:
            Document: 更新后的文档对象

        Raises:
            DocumentNotFoundError: 文档不存在
        """
        document = self.doc_repo.get_by_id(document_id)
        if not document:
            raise DocumentNotFoundError(f"文档不存在: id={document_id}")

        try:
            self._require_kb_permission(
                document.knowledge_base_id, user_id, PermissionType.EDITOR.value
            )
        except KnowledgeBaseNotFoundError as e:
            raise DocumentNotFoundError(f"文档不存在: id={document_id}") from e

        try:
            await self.vector_store_manager.delete_by_document_id(
                document.knowledge_base_id, document_id
            )
        except Exception as e:
            logger.warning(f"重试前删除向量数据失败: {str(e)}")

        document = self.doc_repo.update_status(
            document_id,
            DocumentStatus.PROCESSING,
            chunk_count=0,
        )
        if document:
            document.error_message = None
            self.db.commit()
            self.db.refresh(document)

        background_tasks.add_task(self._process_document_background, document.id)
        return document

    async def _process_document_background(self, document_id: int) -> None:
        """
        后台处理文档

        Args:
            document_id: 文档ID
        """
        try:
            await process_document_task(document_id)
        except Exception as e:
            logger.error(f"后台处理文档失败: document_id={document_id}, error={str(e)}")

    async def delete(
        self,
        document_id: int,
        user_id: int,
    ) -> bool:
        """
        删除文档

        删除文档文件、数据库记录和向量数据。

        Args:
            document_id: 文档ID
            user_id: 用户ID

        Returns:
            bool: 是否删除成功

        Raises:
            DocumentNotFoundError: 文档不存在
        """
        document = self.doc_repo.get_by_id(document_id)

        if not document:
            raise DocumentNotFoundError(f"文档不存在: id={document_id}")

        # 验证用户权限
        try:
            self._require_kb_permission(
                document.knowledge_base_id, user_id, PermissionType.EDITOR.value
            )
        except KnowledgeBaseNotFoundError as e:
            raise DocumentNotFoundError(f"文档不存在: id={document_id}") from e

        kb_id = document.knowledge_base_id
        file_path = document.file_path

        try:
            await self.vector_store_manager.delete_by_document_id(kb_id, document_id)
        except Exception as e:
            logger.warning(f"删除向量数据失败: {str(e)}")

        # 删除文件
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.warning(f"删除文件失败: {file_path}, error={str(e)}")

        # 删除数据库记录
        success = self.doc_repo.delete(document_id)

        if success:
            logger.info(f"文档删除成功: id={document_id}")

        return success


__all__ = [
    "DocumentActionService",
]
