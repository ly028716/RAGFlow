"""
RAG 服务响应模块

定义 RAG 相关的响应类。
"""

from typing import Optional


class DocumentStatusResponse:
    """文档状态响应"""

    def __init__(
        self,
        document_id: int,
        status: str,
        progress: int,
        chunk_count: int,
        error_message: Optional[str] = None,
    ):
        self.document_id = document_id
        self.status = status
        self.progress = progress
        self.chunk_count = chunk_count
        self.error_message = error_message

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "status": self.status,
            "progress": self.progress,
            "chunk_count": self.chunk_count,
            "error_message": self.error_message,
        }


__all__ = [
    "DocumentStatusResponse",
]
