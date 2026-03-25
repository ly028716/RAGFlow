"""
Web Scraper 服务模块 (Facade)

此模块现在作为 Facade，内部委托给子服务。
所有实际功能已迁移到 app.services.web_scraper 包中的子服务。

推荐使用方式:
    from app.services.web_scraper import (
        TaskService,
        LifecycleService,
        ExecutionService,
        LogService,
    )

向后兼容用法:
    from app.services.web_scraper import WebScraperService
    service = WebScraperService(db)  # 内部委托给子服务
"""

from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from app.models.web_scraper_log import WebScraperLog, LogStatus
from app.models.web_scraper_task import WebScraperTask, TaskStatus, ScheduleType

from app.services.web_scraper.execution_service import ExecutionService
from app.services.web_scraper.lifecycle_service import LifecycleService
from app.services.web_scraper.log_service import LogService
from app.services.web_scraper.task_service import TaskService


class WebScraperService:
    """
    Web Scraper 服务类 (Facade)

    协调任务调度、网页采集和知识库集成。
    此服务现在作为 Facade，内部委托给子服务。

    向后兼容用法:
        service = WebScraperService(db)
        task = service.create_task(...)

    推荐新用法:
        from app.services.web_scraper import TaskService, ExecutionService
        task_service = TaskService(db)
        execution_service = ExecutionService(db)
    """

    def __init__(self, db: Session):
        """
        初始化 Web Scraper 服务

        Args:
            db: 数据库会话
        """
        self.db = db
        # 初始化子服务
        self._task_service = TaskService(db)
        self._lifecycle_service = LifecycleService(db)
        self._execution_service = ExecutionService(db)
        self._log_service = LogService(db)

    # ==================== 任务CRUD (委托给 TaskService) ====================

    def create_task(
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
        """创建采集任务"""
        return self._task_service.create(
            name=name,
            url=url,
            knowledge_base_id=knowledge_base_id,
            user_id=user_id,
            description=description,
            url_pattern=url_pattern,
            schedule_type=schedule_type,
            cron_expression=cron_expression,
            selector_config=selector_config,
            scraper_config=scraper_config,
        )

    def update_task(
        self,
        task_id: int,
        user_id: int,
        **update_data
    ) -> WebScraperTask:
        """更新采集任务"""
        return self._task_service.update(task_id, user_id, **update_data)

    def delete_task(self, task_id: int, user_id: int) -> bool:
        """删除采集任务"""
        return self._task_service.delete(task_id, user_id)

    def get_task(self, task_id: int, user_id: int) -> WebScraperTask:
        """获取任务详情"""
        return self._task_service.get_by_id(task_id, user_id)

    def list_tasks(
        self,
        user_id: int,
        status: Optional[TaskStatus] = None,
        knowledge_base_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WebScraperTask]:
        """获取任务列表"""
        return self._task_service.list_tasks(
            user_id=user_id,
            status=status,
            knowledge_base_id=knowledge_base_id,
            skip=skip,
            limit=limit,
        )

    # ==================== 任务生命周期 (委托给 LifecycleService) ====================

    def start_task(self, task_id: int, user_id: int) -> WebScraperTask:
        """启动任务"""
        return self._lifecycle_service.start(task_id, user_id)

    def stop_task(self, task_id: int, user_id: int) -> WebScraperTask:
        """停止任务"""
        return self._lifecycle_service.stop(task_id, user_id)

    def pause_task(self, task_id: int, user_id: int) -> WebScraperTask:
        """暂停任务"""
        return self._lifecycle_service.pause(task_id, user_id)

    def resume_task(self, task_id: int, user_id: int) -> WebScraperTask:
        """恢复任务"""
        return self._lifecycle_service.resume(task_id, user_id)

    # ==================== 任务执行 (委托给 ExecutionService) ====================

    async def execute_once(self, task_id: int, user_id: int) -> WebScraperLog:
        """立即执行任务一次"""
        return await self._execution_service.execute_once(task_id, user_id)

    # ==================== 日志管理 (委托给 LogService) ====================

    def get_task_logs(
        self,
        task_id: int,
        user_id: int,
        status: Optional[LogStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WebScraperLog]:
        """获取任务执行日志"""
        return self._log_service.get_task_logs(
            task_id=task_id,
            user_id=user_id,
            status=status,
            skip=skip,
            limit=limit,
        )

    def get_log_statistics(self, task_id: int, user_id: int) -> Dict[str, Any]:
        """获取任务日志统计信息"""
        return self._log_service.get_log_statistics(task_id, user_id)


__all__ = [
    "WebScraperService",
]
