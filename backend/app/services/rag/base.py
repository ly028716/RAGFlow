"""
RAG 服务基类模块

定义 RAG 服务的抽象基类和共享功能。
"""

import logging
import os
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.config import settings

if TYPE_CHECKING:
    from app.models.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)


class BaseRAGService:
    """
    RAG服务基类

    提供共享的初始化和工具方法。
    """

    def __init__(self, db: Session):
        """
        初始化服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self._ensure_upload_dir()

    def _ensure_upload_dir(self) -> None:
        """确保上传目录存在"""
        upload_dir = settings.file_storage.upload_dir
        abs_path = os.path.abspath(upload_dir)
        if not os.path.exists(abs_path):
            os.makedirs(abs_path, exist_ok=True)
            logger.info(f"创建上传目录: {abs_path}")
        else:
            logger.debug(f"上传目录已存在: {abs_path}")


__all__ = [
    "BaseRAGService",
]
