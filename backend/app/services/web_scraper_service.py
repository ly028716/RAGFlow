"""
Web Scraper 服务层

协调网页采集任务的执行，整合调度器、采集器和知识库
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from app.config import settings
from app.core.cache import cache_result, CacheManager, CacheKeys
from app.core.scheduler import get_scheduler, ScraperScheduler
from app.core.web_scraper import (
    WebScraper,
    ScraperConfig,
    SelectorConfig,
    ScrapedContent,
    WebScraperError,
    PageLoadError,
    ContentExtractionError,
)
from app.core.url_validator import validate_scraper_url, URLValidationError
from app.models.web_scraper_task import WebScraperTask, TaskStatus, ScheduleType
from app.models.web_scraper_log import WebScraperLog, LogStatus
from app.models.document import Document, DocumentStatus
from app.models.knowledge_base import KnowledgeBase
from app.repositories.web_scraper_task_repository import WebScraperTaskRepository
from app.repositories.web_scraper_log_repository import WebScraperLogRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository

logger = logging.getLogger(__name__)


class WebScraperServiceError(Exception):
    """Web Scraper服务异常基类"""
    pass


class TaskNotFoundError(WebScraperServiceError):
    """任务不存在异常"""
    pass


class TaskAlreadyRunningError(WebScraperServiceError):
    """任务已在运行中异常"""
    pass


class InvalidTaskConfigError(WebScraperServiceError):
    """任务配置无效异常"""
    pass


class KnowledgeBaseAccessError(WebScraperServiceError):
    """知识库访问异常"""
    pass


class WebScraperService:
    """
    网页采集服务

    协调任务调度、网页采集和知识库集成，提供：
    - 任务CRUD操作
    - 任务执行和调度
    - 任务生命周期管理
    - 执行日志管理
    """

    def __init__(self, db: Session):
        """
        初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.task_repo = WebScraperTaskRepository(db)
        self.log_repo = WebScraperLogRepository(db)
        self.doc_repo = DocumentRepository(db)
        self.kb_repo = KnowledgeBaseRepository(db)

    # ==================== 任务CRUD操作 ====================

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
            # TODO: 验证Cron表达式格式

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

        # 如果是定时任务且状态为活跃，添加到调度器
        if schedule_type == ScheduleType.CRON and task.status == TaskStatus.ACTIVE:
            self._schedule_task(task)

        return task

    def update_task(
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

        # 验证Cron表达式（如果更新）
        if "cron_expression" in update_data and update_data["cron_expression"]:
            # TODO: 验证Cron表达式格式
            pass

        # 更新任务
        updated_task = self.task_repo.update(task_id, update_data)
        logger.info(f"更新采集任务成功: {task_id}")

        # 清除相关缓存
        CacheManager.invalidate_pattern(f"{CacheKeys.TASK_LIST}:*")
        CacheManager.invalidate_key(f"{CacheKeys.TASK_DETAIL}:{task_id}")

        # 如果是定时任务，更新调度器
        if updated_task.schedule_type == ScheduleType.CRON:
            if updated_task.status == TaskStatus.ACTIVE:
                self._schedule_task(updated_task)
            else:
                self._unschedule_task(task_id)

        return updated_task

    def delete_task(self, task_id: int, user_id: int) -> bool:
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

        # 从调度器移除
        if task.schedule_type == ScheduleType.CRON:
            self._unschedule_task(task_id)

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

    def get_task(self, task_id: int, user_id: int) -> WebScraperTask:
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

    @cache_result(CacheKeys.TASK_LIST, ttl=60)
    def list_tasks(
        self,
        user_id: int,
        status: Optional[TaskStatus] = None,
        knowledge_base_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WebScraperTask]:
        """
        获取任务列表（带缓存，TTL: 60秒）

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
        # 转换为可序列化的字典列表
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

    # ==================== 任务生命周期管理 ====================

    def start_task(self, task_id: int, user_id: int) -> WebScraperTask:
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

        # 如果是定时任务，添加到调度器
        if updated_task.schedule_type == ScheduleType.CRON:
            self._schedule_task(updated_task)

        logger.info(f"启动任务成功: {task_id}")
        return updated_task

    def stop_task(self, task_id: int, user_id: int) -> WebScraperTask:
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

        # 从调度器移除
        if task.schedule_type == ScheduleType.CRON:
            self._unschedule_task(task_id)

        # 更新状态
        updated_task = self.task_repo.update(task_id, {"status": TaskStatus.STOPPED})

        # 清除相关缓存
        CacheManager.invalidate_pattern(f"{CacheKeys.TASK_LIST}:*")
        CacheManager.invalidate_key(f"{CacheKeys.TASK_DETAIL}:{task_id}")

        logger.info(f"停止任务成功: {task_id}")
        return updated_task

    def pause_task(self, task_id: int, user_id: int) -> WebScraperTask:
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

        # 从调度器移除
        if task.schedule_type == ScheduleType.CRON:
            self._unschedule_task(task_id)

        # 更新状态
        updated_task = self.task_repo.update(task_id, {"status": TaskStatus.PAUSED})

        # 清除相关缓存
        CacheManager.invalidate_pattern(f"{CacheKeys.TASK_LIST}:*")
        CacheManager.invalidate_key(f"{CacheKeys.TASK_DETAIL}:{task_id}")

        logger.info(f"暂停任务成功: {task_id}")
        return updated_task

    def resume_task(self, task_id: int, user_id: int) -> WebScraperTask:
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

        # 如果是定时任务，添加到调度器
        if updated_task.schedule_type == ScheduleType.CRON:
            self._schedule_task(updated_task)

        logger.info(f"恢复任务成功: {task_id}")
        return updated_task

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

    # ==================== 任务执行 ====================

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

    # ==================== 调度器集成 ====================

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
                    await self._execute_task(task)

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

    # ==================== 日志管理 ====================

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

