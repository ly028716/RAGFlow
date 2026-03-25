"""
Web Scraper 任务服务模块

实现 Web Scraper 任务的 CRUD 操作。
"""

import logging
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from app.core.cache import CacheManager, CacheKeys
from app.core.url_validator import validate_scraper_url, URLValidationError
from app.models.web_scraper_task import WebScraperTask, TaskStatus, ScheduleType
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.repositories.web_scraper_task_repository import WebScraperTaskRepository
from app.services.web_scraper.exceptions import (
    InvalidTaskConfigError,
    KnowledgeBaseAccessError,
    TaskNotFoundError,
)

logger = logging.getLogger(__name__)


class TaskService:
    """
    Web Scraper 任务服务类

    提供任务的 CRUD 操作。

    使用方式:
        service = TaskService(db)
        task = service.create(name="任务", url="https://example.com", ...)
        tasks = service.list_tasks(user_id=1)
    """

    def __init__(self, db: Session):
        """
        初始化任务服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self.task_repo = WebScraperTaskRepository(db)
        self.kb_repo = KnowledgeBaseRepository(db)

    def create(
        self,
        name: str,
        url: str,
        knowledge_base_id: int,
        user_id: int,
        description: Optional[str] = None,
        url_pattern: Optional[str] = None,
        schedule_type: ScheduleType = ScheduleType.ONCE,
        cron_expression: Optional[str] = None,
        selector_config: Optional[Dict[str, Any]] = None,
        scraper_config: Optional[Dict[str, Any]] = None,
    ) -> WebScraperTask:
        """
        创建采集任务

        Args:
            name: 任务名称
            url: 目标URL
            knowledge_base_id: 知识库ID
            user_id: 创建者用户ID
            description: 任务描述
            url_pattern: URL匹配模式
            schedule_type: 调度类型
            cron_expression: Cron表达式（定时任务必需）
            selector_config: 选择器配置
            scraper_config: 采集器配置

        Returns:
            WebScraperTask: 创建的任务

        Raises:
            InvalidTaskConfigError: 配置无效
            KnowledgeBaseAccessError: 知识库不存在或无权限
        """
        # 验证URL
        try:
            validate_scraper_url(url)
        except URLValidationError as e:
            raise InvalidTaskConfigError(f"URL验证失败: {str(e)}")

        # 验证知识库
        kb = self.kb_repo.get_by_id(knowledge_base_id)
        if not kb:
            raise KnowledgeBaseAccessError(f"知识库不存在: {knowledge_base_id}")

        # 验证Cron表达式
        if schedule_type == ScheduleType.CRON:
            if not cron_expression:
                raise InvalidTaskConfigError("定时任务必须提供Cron表达式")

        # 验证选择器配置
        if selector_config:
            required_fields = ["title", "content"]
            for field in required_fields:
                if field not in selector_config:
                    raise InvalidTaskConfigError(f"选择器配置缺少必需字段: {field}")

        # 创建任务
        task_data = {
            "name": name,
            "description": description,
            "url": url,
            "url_pattern": url_pattern,
            "knowledge_base_id": knowledge_base_id,
            "schedule_type": schedule_type,
            "cron_expression": cron_expression,
            "selector_config": selector_config or {},
            "scraper_config": scraper_config or {},
            "status": TaskStatus.ACTIVE if schedule_type == ScheduleType.CRON else TaskStatus.PAUSED,
            "created_by": user_id,
        }

        task = self.task_repo.create(task_data)
        logger.info(f"创建采集任务成功: {task.id}, 名称: {name}")

        # 清除任务列表缓存
        CacheManager.invalidate_pattern(f"{CacheKeys.TASK_LIST}:*")

        return task

    def update(
        self,
        task_id: int,
        user_id: int,
        **update_data
    ) -> WebScraperTask:
        """
        更新采集任务

        Args:
            task_id: 任务ID
            user_id: 用户ID
            **update_data: 更新数据

        Returns:
            WebScraperTask: 更新后的任务

        Raises:
            TaskNotFoundError: 任务不存在
            InvalidTaskConfigError: 配置无效
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"任务不存在: {task_id}")

        # 验证权限
        if task.created_by != user_id:
            raise KnowledgeBaseAccessError("无权限修改此任务")

        # 验证URL（如果更新）
        if "url" in update_data:
            try:
                validate_scraper_url(update_data["url"])
            except URLValidationError as e:
                raise InvalidTaskConfigError(f"URL验证失败: {str(e)}")

        # 更新任务
        updated_task = self.task_repo.update(task_id, update_data)
        logger.info(f"更新采集任务成功: {task_id}")

        # 清除相关缓存
        CacheManager.invalidate_pattern(f"{CacheKeys.TASK_LIST}:*")
        CacheManager.invalidate_key(f"{CacheKeys.TASK_DETAIL}:{task_id}")

        return updated_task

    def delete(self, task_id: int, user_id: int) -> bool:
        """
        删除采集任务

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            bool: 是否成功删除

        Raises:
            TaskNotFoundError: 任务不存在
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"任务不存在: {task_id}")

        # 验证权限
        if task.created_by != user_id:
            raise KnowledgeBaseAccessError("无权限删除此任务")

        # 删除任务
        success = self.task_repo.delete(task_id)
        if success:
            logger.info(f"删除采集任务成功: {task_id}")
            # 清除相关缓存
            CacheManager.invalidate_pattern(f"{CacheKeys.TASK_LIST}:*")
            CacheManager.invalidate_key(f"{CacheKeys.TASK_DETAIL}:{task_id}")
            CacheManager.invalidate_key(f"{CacheKeys.TASK_STATS}:{task_id}")
            CacheManager.invalidate_key(f"{CacheKeys.LOG_STATS}:{task_id}")

        return success

    def get_by_id(self, task_id: int, user_id: int) -> WebScraperTask:
        """
        获取任务详情

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            WebScraperTask: 任务对象

        Raises:
            TaskNotFoundError: 任务不存在
        """
        task = self.task_repo.get_by_id_with_relations(task_id)
        if not task:
            raise TaskNotFoundError(f"任务不存在: {task_id}")

        # 验证权限
        if task.created_by != user_id:
            raise KnowledgeBaseAccessError("无权限访问此任务")

        return task

    def list_tasks(
        self,
        user_id: int,
        status: Optional[TaskStatus] = None,
        knowledge_base_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WebScraperTask]:
        """
        获取任务列表

        Args:
            user_id: 用户ID
            status: 任务状态过滤
            knowledge_base_id: 知识库ID过滤
            skip: 跳过数量
            limit: 返回数量

        Returns:
            List[WebScraperTask]: 任务列表
        """
        tasks = self.task_repo.get_all_with_relations(
            status=status,
            knowledge_base_id=knowledge_base_id,
            created_by=user_id,
            skip=skip,
            limit=limit,
        )
        return [self._task_to_dict(task) for task in tasks]

    def _task_to_dict(self, task: WebScraperTask) -> dict:
        """将任务对象转换为字典（用于缓存）"""
        return {
            "id": task.id,
            "name": task.name,
            "description": task.description,
            "url": task.url,
            "url_pattern": task.url_pattern,
            "knowledge_base_id": task.knowledge_base_id,
            "schedule_type": task.schedule_type.value if task.schedule_type else None,
            "cron_expression": task.cron_expression,
            "status": task.status.value if task.status else None,
            "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
            "next_run_at": task.next_run_at.isoformat() if task.next_run_at else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "created_by": task.created_by,
        }


__all__ = [
    "TaskService",
]
