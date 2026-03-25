"""
Web Scraper 任务执行服务模块

实现 Web Scraper 任务的执行功能。
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.cache import CacheKeys, CacheManager
from app.core.scheduler import get_scheduler
from app.core.web_scraper import (
    WebScraper,
    ScraperConfig,
    SelectorConfig,
    ScrapedContent,
    WebScraperError,
)
from app.models.document import Document, DocumentStatus
from app.models.web_scraper_log import WebScraperLog, LogStatus
from app.models.web_scraper_task import WebScraperTask, TaskStatus
from app.repositories.document_repository import DocumentRepository
from app.repositories.web_scraper_log_repository import WebScraperLogRepository
from app.repositories.web_scraper_task_repository import WebScraperTaskRepository
from app.services.web_scraper.exceptions import KnowledgeBaseAccessError, TaskNotFoundError

logger = logging.getLogger(__name__)


class ExecutionService:
    """
    Web Scraper 任务执行服务类

    提供任务执行功能。

    使用方式:
        service = ExecutionService(db)
        log = await service.execute_once(task_id=1, user_id=1)
    """

    def __init__(self, db: Session):
        """
        初始化执行服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self.task_repo = WebScraperTaskRepository(db)
        self.log_repo = WebScraperLogRepository(db)
        self.doc_repo = DocumentRepository(db)

    async def execute_once(self, task_id: int, user_id: int) -> WebScraperLog:
        """
        立即执行任务一次

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            WebScraperLog: 执行日志

        Raises:
            TaskNotFoundError: 任务不存在
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"任务不存在: {task_id}")

        # 验证权限
        if task.created_by != user_id:
            raise KnowledgeBaseAccessError("无权限执行此任务")

        logger.info(f"立即执行任务: {task_id}")
        return await self._execute_task(task)

    async def _execute_task(self, task: WebScraperTask) -> WebScraperLog:
        """
        执行采集任务（内部方法）

        Args:
            task: 任务对象

        Returns:
            WebScraperLog: 执行日志
        """
        # 创建执行日志
        log = self.log_repo.create({
            "task_id": task.id,
            "status": LogStatus.RUNNING,
            "start_time": datetime.utcnow(),
            "pages_scraped": 0,
            "documents_created": 0,
        })

        try:
            logger.info(f"开始执行采集任务: {task.id}, 名称: {task.name}")

            # 构建采集器配置
            scraper_config = ScraperConfig(
                wait_for_selector=task.scraper_config.get("wait_for_selector", "body"),
                wait_timeout=task.scraper_config.get("wait_timeout", 30000),
                screenshot=task.scraper_config.get("screenshot", False),
                user_agent=task.scraper_config.get("user_agent"),
                headers=task.scraper_config.get("headers"),
                retry_times=task.scraper_config.get("retry_times", 3),
                retry_delay=task.scraper_config.get("retry_delay", 5),
            )

            # 构建选择器配置
            selector_config = SelectorConfig(
                title=task.selector_config.get("title", "title"),
                content=task.selector_config.get("content", "body"),
                author=task.selector_config.get("author"),
                publish_date=task.selector_config.get("publish_date"),
                exclude=task.selector_config.get("exclude", []),
            )

            # 执行采集
            async with WebScraper(scraper_config, selector_config) as scraper:
                scraped_content = await scraper.scrape_url(task.url)

            # 创建文档
            document = await self._create_document_from_content(
                scraped_content,
                task.knowledge_base_id,
                task.created_by
            )

            # 更新日志状态
            self.log_repo.update(log.id, {
                "status": LogStatus.SUCCESS,
                "end_time": datetime.utcnow(),
                "pages_scraped": 1,
                "documents_created": 1,
                "execution_details": {
                    "url": scraped_content.url,
                    "title": scraped_content.title,
                    "document_id": document.id,
                    "content_length": len(scraped_content.content),
                }
            })

            # 更新任务最后执行时间
            self.task_repo.update(task.id, {"last_run_at": datetime.utcnow()})

            # 清除统计缓存（日志已更新）
            CacheManager.invalidate_key(f"{CacheKeys.LOG_STATS}:{task.id}")

            logger.info(f"采集任务执行成功: {task.id}, 文档ID: {document.id}")
            return self.log_repo.get_by_id(log.id)

        except WebScraperError as e:
            # 采集失败
            error_message = f"采集失败: {str(e)}"
            logger.error(f"任务 {task.id} 执行失败: {error_message}")

            self.log_repo.update(log.id, {
                "status": LogStatus.FAILED,
                "end_time": datetime.utcnow(),
                "error_message": error_message,
            })

            return self.log_repo.get_by_id(log.id)

        except Exception as e:
            # 其他异常
            error_message = f"未知错误: {str(e)}"
            logger.error(f"任务 {task.id} 执行失败: {error_message}", exc_info=True)

            self.log_repo.update(log.id, {
                "status": LogStatus.FAILED,
                "end_time": datetime.utcnow(),
                "error_message": error_message,
            })

            return self.log_repo.get_by_id(log.id)

    async def _create_document_from_content(
        self,
        content: ScrapedContent,
        knowledge_base_id: int,
        user_id: int
    ) -> Document:
        """
        从采集内容创建文档

        Args:
            content: 采集的内容
            knowledge_base_id: 知识库ID
            user_id: 用户ID

        Returns:
            Document: 创建的文档
        """
        # 创建文档记录
        document = self.doc_repo.create({
            "knowledge_base_id": knowledge_base_id,
            "filename": f"{content.title}.md",
            "file_type": "text/markdown",
            "file_size": len(content.content.encode('utf-8')),
            "status": DocumentStatus.COMPLETED,
            "chunk_count": 0,  # 暂时设为0，后续处理时更新
            "uploaded_by": user_id,
            "metadata": {
                "source": "web_scraper",
                "url": content.url,
                "author": content.author,
                "publish_date": content.publish_date,
                "scraped_at": datetime.utcnow().isoformat(),
            }
        })

        logger.info(f"从采集内容创建文档: {document.id}, 标题: {content.title}")
        return document


__all__ = [
    "ExecutionService",
]
