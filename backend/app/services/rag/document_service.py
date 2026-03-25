"""
文档服务模块 (Facade)

此模块现在作为 Facade，内部委托给子服务。
所有实际功能已迁移到 app.services.rag 包中的子服务。

推荐使用方式:
    from app.services.rag import (
        DocumentUploadService,
        DocumentQueryService,
        DocumentActionService,
    )
    upload_service = DocumentUploadService(db)
    query_service = DocumentQueryService(db)
    action_service = DocumentActionService(db)

向后兼容用法:
    from app.services.rag import DocumentService
    service = DocumentService(db)  # 内部委托给子服务
"""

from typing import List, Tuple

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.orm import Session

from app.models.document import Document
from app.services.rag.document_action_service import DocumentActionService
from app.services.rag.document_query_service import DocumentQueryService
from app.services.rag.document_upload_service import DocumentUploadService
from app.services.rag.responses import DocumentStatusResponse


class DocumentService:
    """
    文档服务类 (Facade)

    此服务现在作为 Facade，内部委托给子服务：
    - DocumentUploadService - 负责上传相关功能
    - DocumentQueryService - 负责查询相关功能
    - DocumentActionService - 负责操作相关功能

    向后兼容用法:
        service = DocumentService(db)
        doc = await service.upload(...)

    推荐新用法:
        from app.services.rag import DocumentUploadService, DocumentQueryService
        upload_service = DocumentUploadService(db)
        query_service = DocumentQueryService(db)
    """

    def __init__(self, db: Session):
        """
        初始化文档服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        # 初始化子服务
        self._upload_service = DocumentUploadService(db)
        self._query_service = DocumentQueryService(db)
        self._action_service = DocumentActionService(db)

    # ==================== 上传相关 (委托给 DocumentUploadService) ====================

    async def upload(
        self,
        kb_id: int,
        user_id: int,
        file: UploadFile,
        background_tasks: BackgroundTasks,
    ) -> Document:
        """上传文档"""
        return await self._upload_service.upload(
            kb_id=kb_id,
            user_id=user_id,
            file=file,
            background_tasks=background_tasks,
        )

    async def upload_batch(
        self,
        kb_id: int,
        user_id: int,
        files: List[UploadFile],
        background_tasks: BackgroundTasks,
    ) -> List[Document]:
        """批量上传文档"""
        return await self._upload_service.upload_batch(
            kb_id=kb_id,
            user_id=user_id,
            files=files,
            background_tasks=background_tasks,
        )

    # ==================== 查询相关 (委托给 DocumentQueryService) ====================

    def get_status(
        self,
        document_id: int,
        user_id: int,
    ) -> DocumentStatusResponse:
        """获取文档处理状态"""
        return self._query_service.get_status(document_id, user_id)

    def get_list(
        self,
        kb_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Document], int]:
        """获取知识库的文档列表"""
        return self._query_service.get_list(kb_id, user_id, skip, limit)

    def get_preview(
        self,
        document_id: int,
        user_id: int,
        max_chars: int = 1000,
    ) -> str:
        """获取文档预览"""
        return self._query_service.get_preview(document_id, user_id, max_chars)

    def get_preview_with_length(
        self,
        document_id: int,
        user_id: int,
        max_chars: int = 1000,
    ) -> Tuple[str, int]:
        """获取文档预览和长度"""
        return self._query_service.get_preview_with_length(
            document_id, user_id, max_chars
        )

    def get_file_path(
        self,
        document_id: int,
        user_id: int,
    ) -> Tuple[str, str]:
        """获取文档文件路径"""
        return self._query_service.get_file_path(document_id, user_id)

    def get_by_id(
        self,
        document_id: int,
        user_id: int,
    ) -> Document:
        """获取文档详情"""
        return self._query_service.get_by_id(document_id, user_id)

    # ==================== 操作相关 (委托给 DocumentActionService) ====================

    async def retry_processing(
        self,
        document_id: int,
        user_id: int,
        background_tasks: BackgroundTasks,
    ) -> Document:
        """重试文档处理"""
        return await self._action_service.retry_processing(
            document_id, user_id, background_tasks
        )

    async def delete(
        self,
        document_id: int,
        user_id: int,
    ) -> bool:
        """删除文档"""
        return await self._action_service.delete(document_id, user_id)


__all__ = [
    "DocumentService",
]
