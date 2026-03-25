"""
RAG 服务异常模块

定义 RAG 相关的所有异常类。
"""


class RAGServiceError(Exception):
    """RAG服务异常基类"""

    pass


class KnowledgeBaseNotFoundError(RAGServiceError):
    """知识库不存在异常"""

    pass


class DocumentNotFoundError(RAGServiceError):
    """文档不存在异常"""

    pass


class FileUploadError(RAGServiceError):
    """文件上传异常"""

    pass


__all__ = [
    "RAGServiceError",
    "KnowledgeBaseNotFoundError",
    "DocumentNotFoundError",
    "FileUploadError",
]
