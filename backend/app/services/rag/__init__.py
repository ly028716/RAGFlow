"""
RAG 服务包

提供知识库管理和文档管理功能。

使用方式:
    from app.services.rag import RAGService, KnowledgeBaseService, DocumentService
    from app.services.rag.exceptions import RAGServiceError

    # 使用 Facade（向后兼容）
    service = RAGService(db)
    kb = service.create_knowledge_base(user_id=1, name="技术文档")

    # 直接使用子服务（推荐）
    kb_service = KnowledgeBaseService(db)
    doc_service = DocumentService(db)
"""

# 子服务
from app.services.rag.document_action_service import DocumentActionService
from app.services.rag.document_query_service import DocumentQueryService
from app.services.rag.document_service import DocumentService
from app.services.rag.document_upload_service import DocumentUploadService
from app.services.rag.knowledge_base_service import KnowledgeBaseService

# 异常
from app.services.rag.exceptions import (
    DocumentNotFoundError,
    FileUploadError,
    KnowledgeBaseNotFoundError,
    RAGServiceError,
)

# 响应类
from app.services.rag.responses import DocumentStatusResponse

# 工具函数
from app.services.rag.utils import (
    normalize_display_filename,
    sanitize_filename,
)

# Facade（从原文件导入以保持向后兼容）
from app.services.rag_service import RAGService

__all__ = [
    # 服务类
    "RAGService",
    "KnowledgeBaseService",
    "DocumentService",
    "DocumentUploadService",
    "DocumentQueryService",
    "DocumentActionService",
    # 异常
    "RAGServiceError",
    "KnowledgeBaseNotFoundError",
    "DocumentNotFoundError",
    "FileUploadError",
    # 响应类
    "DocumentStatusResponse",
    # 工具函数
    "sanitize_filename",
    "normalize_display_filename",
]
