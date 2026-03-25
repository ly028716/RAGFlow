"""
Web Scraper 服务包

提供网页采集任务管理功能。

使用方式:
    from app.services.web_scraper import WebScraperService
    service = WebScraperService(db)
    task = service.create_task(...)

或者使用子服务:
    from app.services.web_scraper import (
        TaskService,
        LifecycleService,
        ExecutionService,
        LogService,
    )
"""

# 子服务
from app.services.web_scraper.execution_service import ExecutionService
from app.services.web_scraper.lifecycle_service import LifecycleService
from app.services.web_scraper.log_service import LogService
from app.services.web_scraper.task_service import TaskService

# 异常
from app.services.web_scraper.exceptions import (
    InvalidTaskConfigError,
    KnowledgeBaseAccessError,
    TaskAlreadyRunningError,
    TaskNotFoundError,
    WebScraperServiceError,
)

# Facade
from app.services.web_scraper.web_scraper_service import WebScraperService

__all__ = [
    # 服务类
    "WebScraperService",
    "TaskService",
    "LifecycleService",
    "ExecutionService",
    "LogService",
    # 异常
    "WebScraperServiceError",
    "TaskNotFoundError",
    "TaskAlreadyRunningError",
    "InvalidTaskConfigError",
    "KnowledgeBaseAccessError",
]
