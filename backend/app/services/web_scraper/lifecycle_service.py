"""
Web Scraper 任务生命周期服务模块

实现 Web Scraper 任务的生命周期管理（启动、停止、暂停、恢复）。
"""

import logging
from sqlalchemy.orm import Session

from app.core.cache import CacheManager, CacheKeys
from app.core.scheduler import get_scheduler
from app.models.web_scraper_task import WebScraperTask, TaskStatus, ScheduleType
from app.repositories.web_scraper_task_repository import WebScraperTaskRepository
from app.services.web_scraper.exceptions import (
    KnowledgeBaseAccessError,
    TaskNotFoundError,
)

logger = logging.getLogger(__name__)


class LifecycleService:
    """
    Web Scraper 任务生命周期服务类

    提供任务生命周期管理功能（启动、停止、暂停、恢复）。

    使用方式:
        service = LifecycleService(db)
        task = service.start(task_id=1, user_id=1)
        task = service.stop(task_id=1, user_id=1)
    """

    def __init__(self, db: Session):
        """
        初始化生命周期服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self.task_repo = WebScraperTaskRepository(db)

    def start(self, task_id: int, user_id: int) -> WebScraperTask:
        """
        启动任务

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            WebScraperTask: 更新后的任务

        Raises:
            TaskNotFoundError: 任务不存在
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"任务不存在: {task_id}")

        # 验证权限
        if task.created_by != user_id:
            raise KnowledgeBaseAccessError("无权限启动此任务")

        # 更新状态
        updated_task = self.task_repo.update(task_id, {"status": TaskStatus.ACTIVE})

        # 清除相关缓存
        CacheManager.invalidate_pattern(f"{CacheKeys.TASK_LIST}:*")
        CacheManager.invalidate_key(f"{CacheKeys.TASK_DETAIL}:{task_id}")

        logger.info(f"启动任务成功: {task_id}")
        return updated_task

    def stop(self, task_id: int, user_id: int) -> WebScraperTask:
        """
        停止任务

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            WebScraperTask: 更新后的任务

        Raises:
            TaskNotFoundError: 任务不存在
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"任务不存在: {task_id}")

        # 验证权限
        if task.created_by != user_id:
            raise KnowledgeBaseAccessError("无权限停止此任务")

        # 更新状态
        updated_task = self.task_repo.update(task_id, {"status": TaskStatus.STOPPED})

        # 清除相关缓存
        CacheManager.invalidate_pattern(f"{CacheKeys.TASK_LIST}:*")
        CacheManager.invalidate_key(f"{CacheKeys.TASK_DETAIL}:{task_id}")

        logger.info(f"停止任务成功: {task_id}")
        return updated_task

    def pause(self, task_id: int, user_id: int) -> WebScraperTask:
        """
        暂停任务

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            WebScraperTask: 更新后的任务

        Raises:
            TaskNotFoundError: 任务不存在
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"任务不存在: {task_id}")

        # 验证权限
        if task.created_by != user_id:
            raise KnowledgeBaseAccessError("无权限暂停此任务")

        # 更新状态
        updated_task = self.task_repo.update(task_id, {"status": TaskStatus.PAUSED})

        # 清除相关缓存
        CacheManager.invalidate_pattern(f"{CacheKeys.TASK_LIST}:*")
        CacheManager.invalidate_key(f"{CacheKeys.TASK_DETAIL}:{task_id}")

        logger.info(f"暂停任务成功: {task_id}")
        return updated_task

    def resume(self, task_id: int, user_id: int) -> WebScraperTask:
        """
        恢复任务

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            WebScraperTask: 更新后的任务

        Raises:
            TaskNotFoundError: 任务不存在
        """
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"任务不存在: {task_id}")

        # 验证权限
        if task.created_by != user_id:
            raise KnowledgeBaseAccessError("无权限恢复此任务")

        # 更新状态
        updated_task = self.task_repo.update(task_id, {"status": TaskStatus.ACTIVE})

        # 清除相关缓存
        CacheManager.invalidate_pattern(f"{CacheKeys.TASK_LIST}:*")
        CacheManager.invalidate_key(f"{CacheKeys.TASK_DETAIL}:{task_id}")

        logger.info(f"恢复任务成功: {task_id}")
        return updated_task

    def _schedule_task(self, task: WebScraperTask):
        """
        将任务添加到调度器

        Args:
            task: 任务对象
        """
        try:
            scheduler = get_scheduler()

            # 创建任务执行回调
            async def task_callback(task_id: int):
                # 重新获取任务（确保使用最新状态）
                task = self.task_repo.get_by_id(task_id)
                if task and task.status == TaskStatus.ACTIVE:
                    # 这里需要导入 ExecutionService
                    from app.services.web_scraper.execution_service import ExecutionService
                    execution_service = ExecutionService(self.db)
                    await execution_service._execute_task(task)

            # 添加到调度器
            success = scheduler.add_job(
                job_id=f"scraper_task_{task.id}",
                cron_expression=task.cron_expression,
                callback=task_callback,
                task_id=task.id
            )

            if success:
                logger.info(f"任务已添加到调度器: {task.id}, Cron: {task.cron_expression}")
            else:
                logger.error(f"添加任务到调度器失败: {task.id}")

        except Exception as e:
            logger.error(f"调度任务失败: {task.id}, 错误: {str(e)}")

    def _unschedule_task(self, task_id: int):
        """
        从调度器移除任务

        Args:
            task_id: 任务ID
        """
        try:
            scheduler = get_scheduler()
            success = scheduler.remove_job(f"scraper_task_{task_id}")

            if success:
                logger.info(f"任务已从调度器移除: {task_id}")
            else:
                logger.warning(f"从调度器移除任务失败（可能不存在）: {task_id}")

        except Exception as e:
            logger.error(f"取消调度任务失败: {task_id}, 错误: {str(e)}")


__all__ = [
    "LifecycleService",
]
