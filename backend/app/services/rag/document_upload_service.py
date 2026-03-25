"""
文档上传服务模块

实现文档上传相关业务逻辑，包括单文件上传和批量上传。
"""

import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.langchain_integration.document_loaders import (
    DocumentLoaderFactory,
    UnsupportedFileTypeError,
)
from app.models.document import Document, DocumentStatus
from app.models.knowledge_base_permission import PermissionType
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.services.knowledge_base_permission import KnowledgeBasePermissionService
from app.services.rag.base import BaseRAGService
from app.services.rag.exceptions import FileUploadError, KnowledgeBaseNotFoundError
from app.services.rag.utils import normalize_display_filename, sanitize_filename
from app.tasks.document_tasks import process_document_task

logger = logging.getLogger(__name__)


class DocumentUploadService(BaseRAGService):
    """
    文档上传服务类

    提供文档上传和批量上传功能。

    使用方式:
        service = DocumentUploadService(db)
        doc = await service.upload(kb_id=1, user_id=1, file=upload_file, background_tasks=tasks)
        docs = await service.upload_batch(kb_id=1, user_id=1, files=files, background_tasks=tasks)
    """

    def __init__(self, db: Session):
        """
        初始化上传服务

        Args:
            db: SQLAlchemy数据库会话
        """
        super().__init__(db)
        self.doc_repo = DocumentRepository(db)
        self.kb_repo = KnowledgeBaseRepository(db)
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

    async def upload(
        self,
        kb_id: int,
        user_id: int,
        file: UploadFile,
        background_tasks: BackgroundTasks,
    ) -> Document:
        """
        上传文档

        保存文件并创建后台处理任务。

        Args:
            kb_id: 知识库ID
            user_id: 用户ID
            file: 上传的文件
            background_tasks: FastAPI后台任务

        Returns:
            Document: 创建的文档记录

        Raises:
            KnowledgeBaseNotFoundError: 知识库不存在
            FileUploadError: 文件上传失败
            UnsupportedFileTypeError: 不支持的文件类型
        """
        # 验证知识库
        self._require_kb_permission(kb_id, user_id, PermissionType.EDITOR.value)

        # 获取文件类型
        display_filename = normalize_display_filename(file.filename)
        file_type = DocumentLoaderFactory.get_file_type_from_extension(display_filename)

        logger.info(f"开始处理文件上传: filename={display_filename}, type={file_type}")

        if not file_type:
            logger.warning(f"文件类型不支持: {display_filename}")
            raise UnsupportedFileTypeError(
                f"不支持的文件类型: {display_filename}。"
                f"支持的类型: {', '.join(DocumentLoaderFactory.get_supported_types())}"
            )

        # 验证文件大小
        try:
            file_content = await file.read()
            file_size = len(file_content)
            max_size = settings.file_storage.max_upload_size_bytes

            logger.info(f"文件大小: {file_size} bytes, 最大允许: {max_size} bytes")

            if file_size > max_size:
                max_size_mb = max_size / (1024 * 1024)
                file_size_mb = file_size / (1024 * 1024)
                logger.warning(f"文件大小超出限制: {file_size_mb:.2f}MB > {max_size_mb:.2f}MB")
                raise FileUploadError(
                    f"文件大小超出限制: {file_size_mb:.2f}MB > {max_size_mb:.2f}MB"
                )
        except Exception as e:
            if isinstance(e, FileUploadError):
                raise
            logger.error(f"读取文件失败: {str(e)}")
            raise FileUploadError(f"读取文件失败: {str(e)}")

        try:
            file_path = await self._save_file(
                kb_id=kb_id,
                content=file_content,
                display_filename=display_filename,
            )
            logger.info(f"文件保存成功: {file_path}")
        except Exception as e:
            logger.error(f"保存文件失败: {str(e)}")
            raise FileUploadError(f"保存文件失败: {str(e)}")

        try:
            # 创建文档记录
            document = self.doc_repo.create(
                knowledge_base_id=kb_id,
                filename=display_filename,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type,
            )

            # 更新知识库更新时间
            self.kb_repo.touch(kb_id)

            # 添加后台处理任务
            background_tasks.add_task(
                self._process_document_background,
                document.id,
            )

            logger.info(
                f"文档上传成功: id={document.id}, "
                f"filename={document.filename}, kb_id={kb_id}"
            )

            return document

        except Exception as e:
            # 清理已保存的文件
            if os.path.exists(file_path):
                os.remove(file_path)
            raise

    async def upload_batch(
        self,
        kb_id: int,
        user_id: int,
        files: List[UploadFile],
        background_tasks: BackgroundTasks,
    ) -> List[Document]:
        """
        批量上传文档

        Args:
            kb_id: 知识库ID
            user_id: 用户ID
            files: 上传的文件列表
            background_tasks: FastAPI后台任务

        Returns:
            List[Document]: 创建的文档记录列表
        """
        documents = []
        errors = []

        for file in files:
            try:
                doc = await self.upload(
                    kb_id=kb_id,
                    user_id=user_id,
                    file=file,
                    background_tasks=background_tasks,
                )
                documents.append(doc)
            except Exception as e:
                errors.append(
                    {
                        "filename": file.filename,
                        "error": str(e),
                    }
                )
                logger.warning(f"批量上传文件失败: {file.filename}, error={str(e)}")

        if errors:
            logger.warning(f"批量上传部分失败: {len(errors)}/{len(files)}")

        return documents

    async def _save_file(
        self,
        kb_id: int,
        content: bytes,
        display_filename: str,
    ) -> str:
        """
        保存上传的文件

        Args:
            kb_id: 知识库ID
            content: 文件内容
            display_filename: 显示文件名

        Returns:
            str: 保存的文件路径
        """
        # 生成唯一文件名
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        safe_original = sanitize_filename(display_filename)
        safe_filename = f"{timestamp}_{unique_id}_{safe_original}"

        # 创建知识库目录
        kb_dir = os.path.join(settings.file_storage.upload_dir, f"kb_{kb_id}")
        if not os.path.exists(kb_dir):
            os.makedirs(kb_dir, exist_ok=True)

        # 保存文件
        file_path = os.path.join(kb_dir, safe_filename)

        try:
            with open(file_path, "wb") as buffer:
                buffer.write(content)

            logger.debug(f"文件保存成功: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"文件保存失败: {str(e)}")
            raise FileUploadError(f"文件保存失败: {str(e)}")

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


__all__ = [
    "DocumentUploadService",
]
