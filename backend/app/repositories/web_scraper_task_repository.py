"""
Web Scraper 任务 Repository

处理网页采集任务的数据访问操作
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.models.web_scraper_task import WebScraperTask, TaskStatus, ScheduleType


class WebScraperTaskRepository:
    """网页采集任务数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, task_data: dict) -> WebScraperTask:
        """创建采集任务"""
        task = WebScraperTask(**task_data)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_by_id(self, task_id: int, with_relations: bool = False) -> Optional[WebScraperTask]:
        """根据ID获取任务（可选预加载关联数据）"""
        query = self.db.query(WebScraperTask)

        if with_relations:
            query = query.options(
                joinedload(WebScraperTask.knowledge_base),
                joinedload(WebScraperTask.creator)
            )

        return query.filter(WebScraperTask.id == task_id).first()

    def get_by_id_with_relations(self, task_id: int) -> Optional[WebScraperTask]:
        """根据ID获取任务（包含关联数据）"""
        return (
            self.db.query(WebScraperTask)
            .options(
                joinedload(WebScraperTask.knowledge_base),
                joinedload(WebScraperTask.creator)
            )
            .filter(WebScraperTask.id == task_id)
            .first()
        )

    def get_all(
        self,
        status: Optional[TaskStatus] = None,
        schedule_type: Optional[ScheduleType] = None,
        knowledge_base_id: Optional[int] = None,
        created_by: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WebScraperTask]:
        """获取任务列表"""
        query = self.db.query(WebScraperTask)

        if status:
            query = query.filter(WebScraperTask.status == status)
        if schedule_type:
            query = query.filter(WebScraperTask.schedule_type == schedule_type)
        if knowledge_base_id:
            query = query.filter(WebScraperTask.knowledge_base_id == knowledge_base_id)
        if created_by:
            query = query.filter(WebScraperTask.created_by == created_by)

        return query.order_by(WebScraperTask.created_at.desc()).offset(skip).limit(limit).all()

    def get_all_with_relations(
        self,
        status: Optional[TaskStatus] = None,
        schedule_type: Optional[ScheduleType] = None,
        knowledge_base_id: Optional[int] = None,
        created_by: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WebScraperTask]:
        """获取任务列表（包含关联数据）"""
        query = (
            self.db.query(WebScraperTask)
            .options(
                joinedload(WebScraperTask.knowledge_base),
                joinedload(WebScraperTask.creator)
            )
        )

        if status:
            query = query.filter(WebScraperTask.status == status)
        if schedule_type:
            query = query.filter(WebScraperTask.schedule_type == schedule_type)
        if knowledge_base_id:
            query = query.filter(WebScraperTask.knowledge_base_id == knowledge_base_id)
        if created_by:
            query = query.filter(WebScraperTask.created_by == created_by)

        return query.order_by(WebScraperTask.created_at.desc()).offset(skip).limit(limit).all()

    def get_active_tasks(self) -> List[WebScraperTask]:
        """获取所有活跃的任务"""
        return (
            self.db.query(WebScraperTask)
            .filter(WebScraperTask.status == TaskStatus.ACTIVE)
            .all()
        )

    def get_pending_scheduled_tasks(self, current_time: datetime) -> List[WebScraperTask]:
        """获取待执行的定时任务"""
        return (
            self.db.query(WebScraperTask)
            .filter(
                and_(
                    WebScraperTask.status == TaskStatus.ACTIVE,
                    WebScraperTask.schedule_type == ScheduleType.CRON,
                    or_(
                        WebScraperTask.next_run_at.is_(None),
                        WebScraperTask.next_run_at <= current_time
                    )
                )
            )
            .all()
        )

    def get_by_knowledge_base(self, knowledge_base_id: int) -> List[WebScraperTask]:
        """根据知识库ID获取任务列表"""
        return (
            self.db.query(WebScraperTask)
            .filter(WebScraperTask.knowledge_base_id == knowledge_base_id)
            .order_by(WebScraperTask.created_at.desc())
            .all()
        )

    def get_by_user(self, user_id: int, skip: int = 0, limit: int = 100) -> List[WebScraperTask]:
        """根据用户ID获取任务列表"""
        return (
            self.db.query(WebScraperTask)
            .filter(WebScraperTask.created_by == user_id)
            .order_by(WebScraperTask.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update(self, task_id: int, update_data: dict) -> Optional[WebScraperTask]:
        """更新任务"""
        ALLOWED_UPDATE_FIELDS = {
            'name', 'description', 'url', 'url_pattern',
            'schedule_type', 'cron_expression',
            'selector_config', 'scraper_config',
            'status', 'last_run_at', 'next_run_at'
        }

        task = self.get_by_id(task_id)
        if not task:
            return None

        for key, value in update_data.items():
            if key in ALLOWED_UPDATE_FIELDS and hasattr(task, key):
                setattr(task, key, value)

        self.db.commit()
        self.db.refresh(task)
        return task

    def delete(self, task_id: int) -> bool:
        """删除任务（硬删除）"""
        task = self.get_by_id(task_id)
        if not task:
            return False

        self.db.delete(task)
        self.db.commit()
        return True

    def count(
        self,
        status: Optional[TaskStatus] = None,
        schedule_type: Optional[ScheduleType] = None,
        knowledge_base_id: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> int:
        """统计任务数量"""
        query = self.db.query(WebScraperTask)

        if status:
            query = query.filter(WebScraperTask.status == status)
        if schedule_type:
            query = query.filter(WebScraperTask.schedule_type == schedule_type)
        if knowledge_base_id:
            query = query.filter(WebScraperTask.knowledge_base_id == knowledge_base_id)
        if created_by:
            query = query.filter(WebScraperTask.created_by == created_by)

        return query.count()

    def count_by_user(self, user_id: int) -> int:
        """统计用户的任务数量"""
        return (
            self.db.query(WebScraperTask)
            .filter(WebScraperTask.created_by == user_id)
            .count()
        )
