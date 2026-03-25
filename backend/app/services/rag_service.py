"""
RAG服务模块 (Facade)

此模块现在作为 Facade，内部委托给子服务。
所有实际功能已迁移到 app.services.rag 包中的子服务。

推荐使用方式:
    from app.services.rag import KnowledgeBaseService, DocumentService
    kb_service = KnowledgeBaseService(db)
    doc_service = DocumentService(db)

向后兼容用法:
    from app.services.rag_service import RAGService
    service = RAGService(db)  # 内部委托给子服务
"""

import logging
from typing import List, Optional, Tuple

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase

# 导入子服务
from app.services.rag.document_service import DocumentService
from app.services.rag.exceptions import (
    DocumentNotFoundError,
    FileUploadError,
    KnowledgeBaseNotFoundError,
    RAGServiceError,
)
from app.services.rag.knowledge_base_service import KnowledgeBaseService
from app.services.rag.responses import DocumentStatusResponse
from app.services.rag.utils import (
    normalize_display_filename,
    sanitize_filename,
)

logger = logging.getLogger(__name__)

# 导出异常以保持向后兼容
__all__ = [
    "RAGService",
    "RAGServiceError",
    "KnowledgeBaseNotFoundError",
    "DocumentNotFoundError",
    "FileUploadError",
    "DocumentStatusResponse",
    "sanitize_filename",
    "normalize_display_filename",
]


class RAGService:
    """
    RAG服务类 (Facade)

    提供知识库管理、文档上传和RAG问答功能。
    此类现在作为 Facade，内部委托给 KnowledgeBaseService 和 DocumentService。

    向后兼容用法:
        service = RAGService(db)
        kb = service.create_knowledge_base(user_id=1, name="技术文档")

    推荐新用法:
        from app.services.rag import KnowledgeBaseService, DocumentService
        kb_service = KnowledgeBaseService(db)
        doc_service = DocumentService(db)
    """

    def __init__(self, db: Session):
        """
        初始化RAG服务

        Args:
            db: 数据库会话
        """
        self.db = db
        # 初始化子服务
        self._kb_service = KnowledgeBaseService(db)
        self._doc_service = DocumentService(db)

    # ==================== 知识库管理 (委托给 KnowledgeBaseService) ====================

    def create_knowledge_base(
        self,
        user_id: int,
        name: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
    ) -> KnowledgeBase:
        """创建知识库"""
        return self._kb_service.create(
            user_id=user_id,
            name=name,
            description=description,
            category=category,
        )

    def get_knowledge_bases(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[KnowledgeBase], int]:
        """获取用户的知识库列表"""
        return self._kb_service.get_list(user_id, skip, limit)

    def get_knowledge_base(
        self,
        kb_id: int,
        user_id: int,
    ) -> KnowledgeBase:
        """获取知识库详情"""
        return self._kb_service.get_by_id(kb_id, user_id)

    def get_knowledge_base_for_edit(
        self,
        kb_id: int,
        user_id: int,
    ) -> KnowledgeBase:
        """获取可编辑的知识库"""
        return self._kb_service.get_for_edit(kb_id, user_id)

    def update_knowledge_base(
        self,
        kb_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
    ) -> KnowledgeBase:
        """更新知识库信息"""
        return self._kb_service.update(
            kb_id=kb_id,
            user_id=user_id,
            name=name,
            description=description,
            category=category,
        )

    def delete_knowledge_base(
        self,
        kb_id: int,
        user_id: int,
    ) -> bool:
        """
        删除知识库

        删除知识库及其所有文档和向量数据。
        """
        import os
        from app.config import settings
        from app.core.vector_store import get_vector_store_manager

        # 获取知识库以删除其文档
        kb = self._kb_service.get_raw(kb_id)
        if not kb:
            raise KnowledgeBaseNotFoundError(f"知识库不存在: id={kb_id}")

        # 删除向量数据
        try:
            vector_store_manager = get_vector_store_manager()
            vector_store_manager.delete_collection(kb_id)
        except Exception as e:
            logger.warning(f"删除向量集合失败: {str(e)}")

        # 删除文档文件
        for doc in kb.documents:
            try:
                if os.path.exists(doc.file_path):
                    os.remove(doc.file_path)
            except Exception as e:
                logger.warning(f"删除文件失败: {doc.file_path}, error={str(e)}")

        # 删除数据库记录
        return self._kb_service.delete(kb_id, user_id)

    # ==================== 文档管理 (委托给 DocumentService) ====================

    async def upload_document(
        self,
        kb_id: int,
        user_id: int,
        file: UploadFile,
        background_tasks: BackgroundTasks,
    ) -> Document:
        """上传文档"""
        return await self._doc_service.upload(
            kb_id=kb_id,
            user_id=user_id,
            file=file,
            background_tasks=background_tasks,
        )

    async def upload_documents_batch(
        self,
        kb_id: int,
        user_id: int,
        files: List[UploadFile],
        background_tasks: BackgroundTasks,
    ) -> List[Document]:
        """批量上传文档"""
        return await self._doc_service.upload_batch(
            kb_id=kb_id,
            user_id=user_id,
            files=files,
            background_tasks=background_tasks,
        )

    def get_document_status(
        self,
        document_id: int,
        user_id: int,
    ) -> DocumentStatusResponse:
        """获取文档处理状态"""
        return self._doc_service.get_status(document_id, user_id)

    def get_documents(
        self,
        kb_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Document], int]:
        """获取知识库的文档列表"""
        return self._doc_service.get_list(kb_id, user_id, skip, limit)

    def get_document_preview(
        self,
        document_id: int,
        user_id: int,
        max_chars: int = 1000,
    ) -> str:
        """获取文档预览"""
        return self._doc_service.get_preview(document_id, user_id, max_chars)

    def get_document_preview_with_length(
        self,
        document_id: int,
        user_id: int,
        max_chars: int = 1000,
    ) -> Tuple[str, int]:
        """获取文档预览和长度"""
        return self._doc_service.get_preview_with_length(
            document_id, user_id, max_chars
        )

    def get_document_file(
        self,
        document_id: int,
        user_id: int,
    ) -> Tuple[str, str]:
        """获取文档文件路径"""
        return self._doc_service.get_file_path(document_id, user_id)

    async def retry_document_processing(
        self,
        document_id: int,
        user_id: int,
        background_tasks: BackgroundTasks,
    ) -> Document:
        """重试文档处理"""
        return await self._doc_service.retry_processing(
            document_id, user_id, background_tasks
        )

    async def delete_document(
        self,
        document_id: int,
        user_id: int,
    ) -> bool:
        """删除文档"""
        return await self._doc_service.delete(document_id, user_id)
