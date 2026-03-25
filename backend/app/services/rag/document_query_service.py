"""
文档查询服务模块

实现文档查询相关业务逻辑，包括状态查询、列表查询、预览等。
"""

import logging
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.langchain_integration.document_loaders import DocumentLoaderFactory
from app.models.document import Document, DocumentStatus
from app.models.knowledge_base_permission import PermissionType
from app.repositories.document_repository import DocumentRepository
from app.services.knowledge_base_permission import KnowledgeBasePermissionService
from app.services.rag.base import BaseRAGService
from app.services.rag.exceptions import DocumentNotFoundError, KnowledgeBaseNotFoundError
from app.services.rag.responses import DocumentStatusResponse

logger = logging.getLogger(__name__)


class DocumentQueryService(BaseRAGService):
    """
    文档查询服务类

    提供文档查询功能，包括状态查询、列表查询、预览等。

    使用方式:
        service = DocumentQueryService(db)
        status = service.get_status(document_id=1, user_id=1)
        docs, total = service.get_list(kb_id=1, user_id=1)
        preview = service.get_preview(document_id=1, user_id=1)
    """

    def __init__(self, db: Session):
        """
        初始化查询服务

        Args:
            db: SQLAlchemy数据库会话
        """
        super().__init__(db)
        self.doc_repo = DocumentRepository(db)
        self.kb_permission_service = KnowledgeBasePermissionService(db)

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

    def get_status(
        self,
        document_id: int,
        user_id: int,
    ) -> DocumentStatusResponse:
        """
        获取文档处理状态

        Args:
            document_id: 文档ID
            user_id: 用户ID

        Returns:
            DocumentStatusResponse: 文档状态响应

        Raises:
            DocumentNotFoundError: 文档不存在
        """
        document = self.doc_repo.get_by_id(document_id)

        if not document:
            raise DocumentNotFoundError(f"文档不存在: id={document_id}")

        # 验证用户权限
        try:
            self._require_kb_permission(
                document.knowledge_base_id, user_id, PermissionType.VIEWER.value
            )
        except KnowledgeBaseNotFoundError as e:
            raise DocumentNotFoundError(f"文档不存在: id={document_id}") from e

        # 计算进度
        progress = self._calculate_progress(document.status)

        return DocumentStatusResponse(
            document_id=document.id,
            status=document.status.value,
            progress=progress,
            chunk_count=document.chunk_count,
            error_message=document.error_message,
        )

    def _calculate_progress(self, status: DocumentStatus) -> int:
        """
        根据状态计算进度百分比

        Args:
            status: 文档状态

        Returns:
            int: 进度百分比
        """
        progress_map = {
            DocumentStatus.PROCESSING: 50,
            DocumentStatus.COMPLETED: 100,
            DocumentStatus.FAILED: 0,
        }
        return progress_map.get(status, 0)

    def get_list(
        self,
        kb_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Document], int]:
        """
        获取知识库的文档列表

        Args:
            kb_id: 知识库ID
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            Tuple[List[Document], int]: (文档列表, 总数)

        Raises:
            KnowledgeBaseNotFoundError: 知识库不存在
        """
        # 验证知识库
        self._require_kb_permission(kb_id, user_id, PermissionType.VIEWER.value)

        return self.doc_repo.get_by_knowledge_base(kb_id, skip, limit)

    def get_preview(
        self,
        document_id: int,
        user_id: int,
        max_chars: int = 1000,
    ) -> str:
        """
        获取文档预览

        Args:
            document_id: 文档ID
            user_id: 用户ID
            max_chars: 最大字符数

        Returns:
            str: 文档预览文本

        Raises:
            DocumentNotFoundError: 文档不存在
        """
        document = self.doc_repo.get_by_id(document_id)

        if not document:
            raise DocumentNotFoundError(f"文档不存在: id={document_id}")

        # 验证用户权限
        try:
            self._require_kb_permission(
                document.knowledge_base_id, user_id, PermissionType.VIEWER.value
            )
        except KnowledgeBaseNotFoundError as e:
            raise DocumentNotFoundError(f"文档不存在: id={document_id}") from e

        # 获取预览
        return DocumentLoaderFactory.get_document_preview(
            file_path=document.file_path,
            file_type=document.file_type,
            max_chars=max_chars,
        )

    def get_preview_with_length(
        self,
        document_id: int,
        user_id: int,
        max_chars: int = 1000,
    ) -> Tuple[str, int]:
        """
        获取文档预览和长度

        Args:
            document_id: 文档ID
            user_id: 用户ID
            max_chars: 最大字符数

        Returns:
            Tuple[str, int]: (预览文本, 总长度)

        Raises:
            DocumentNotFoundError: 文档不存在
        """
        document = self.doc_repo.get_by_id(document_id)
        if not document:
            raise DocumentNotFoundError(f"文档不存在: id={document_id}")

        try:
            self._require_kb_permission(
                document.knowledge_base_id, user_id, PermissionType.VIEWER.value
            )
        except KnowledgeBaseNotFoundError as e:
            raise DocumentNotFoundError(f"文档不存在: id={document_id}") from e

        return DocumentLoaderFactory.get_document_preview_with_length(
            file_path=document.file_path,
            file_type=document.file_type,
            max_chars=max_chars,
        )

    def get_file_path(
        self,
        document_id: int,
        user_id: int,
    ) -> Tuple[str, str]:
        """
        获取文档文件路径

        Args:
            document_id: 文档ID
            user_id: 用户ID

        Returns:
            Tuple[str, str]: (文件路径, 文件名)

        Raises:
            DocumentNotFoundError: 文档不存在或文件不存在
        """
        import os

        document = self.doc_repo.get_by_id(document_id)
        if not document:
            raise DocumentNotFoundError(f"文档不存在: id={document_id}")

        try:
            self._require_kb_permission(
                document.knowledge_base_id, user_id, PermissionType.VIEWER.value
            )
        except KnowledgeBaseNotFoundError as e:
            raise DocumentNotFoundError(f"文档不存在: id={document_id}") from e

        if not os.path.exists(document.file_path):
            raise DocumentNotFoundError(f"文件不存在: path={document.file_path}")

        return document.file_path, document.filename

    def get_by_id(
        self,
        document_id: int,
        user_id: int,
    ) -> Document:
        """
        获取文档详情

        Args:
            document_id: 文档ID
            user_id: 用户ID

        Returns:
            Document: 文档对象

        Raises:
            DocumentNotFoundError: 文档不存在
        """
        document = self.doc_repo.get_by_id(document_id)
        if not document:
            raise DocumentNotFoundError(f"文档不存在: id={document_id}")

        try:
            self._require_kb_permission(
                document.knowledge_base_id, user_id, PermissionType.VIEWER.value
            )
        except KnowledgeBaseNotFoundError as e:
            raise DocumentNotFoundError(f"文档不存在: id={document_id}") from e

        return document


__all__ = [
    "DocumentQueryService",
]
