"""
Web Scraper 日志服务模块

实现 Web Scraper 任务日志的管理功能。
"""

import logging
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from app.core.cache import cache_result, CacheKeys
from app.models.web_scraper_log import WebScraperLog, LogStatus
from app.models.web_scraper_task import WebScraperTask
from app.repositories.web_scraper_log_repository import WebScraperLogRepository
from app.repositories.web_scraper_task_repository import WebScraperTaskRepository
from app.services.web_scraper.exceptions import (
    KnowledgeBaseAccessError,
    TaskNotFoundError,
)

logger = logging.getLogger(__name__)


class LogService:
    """
    Web Scraper 日志服务类

    提供任务日志管理功能。

    使用方式:
        service = LogService(db)
        logs = service.get_task_logs(task_id=1, user_id=1)
        stats = service.get_log_statistics(task_id=1, user_id=1)
    """

    def __init__(self, db: Session):
        """
        初始化日志服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self.log_repo = WebScraperLogRepository(db)
        self.task_repo = WebScraperTaskRepository(db)

    def get_task_logs(
        self,
        task_id: int,
        user_id: int,
        status: Optional[LogStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WebScraperLog]:
        """
        获取任务执行日志

        Args:
            task_id: 任务ID
            user_id: 用户ID
            status: 状态过滤
            skip: 跳过数量
            limit: 返回数量

        Returns:
            List[WebScraperLog]: 日志列表

        Raises:
            TaskNotFoundError: 任务不存在
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"任务不存在: {task_id}")

        # 验证权限
        if task.created_by != user_id:
            raise KnowledgeBaseAccessError("无权限访问此任务的日志")

        return self.log_repo.get_by_task(
            task_id=task_id,
            status=status,
            skip=skip,
            limit=limit,
        )

    @cache_result(CacheKeys.LOG_STATS, ttl=300)
    def get_log_statistics(self, task_id: int, user_id: int) -> Dict[str, Any]:
        """
        获取任务日志统计信息（带缓存，TTL: 300秒）

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            Dict[str, Any]: 统计信息

        Raises:
            TaskNotFoundError: 任务不存在
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"任务不存在: {task_id}")

        # 验证权限
        if task.created_by != user_id:
            raise KnowledgeBaseAccessError("无权限访问此任务的统计信息")

        return self.log_repo.get_statistics_by_task(task_id)


__all__ = [
    "LogService",
]
