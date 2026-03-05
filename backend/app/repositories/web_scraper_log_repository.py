"""
Web Scraper 执行日志 Repository

处理网页采集执行日志的数据访问操作
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.web_scraper_log import WebScraperLog, LogStatus


class WebScraperLogRepository:
    """网页采集执行日志数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, log_data: dict) -> WebScraperLog:
        """创建执行日志"""
        log = WebScraperLog(**log_data)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_by_id(self, log_id: int, with_task: bool = False) -> Optional[WebScraperLog]:
        """根据ID获取日志（可选预加载任务数据）"""
        query = self.db.query(WebScraperLog)

        if with_task:
            query = query.options(joinedload(WebScraperLog.task))

        return query.filter(WebScraperLog.id == log_id).first()

    def get_by_task(
        self,
        task_id: int,
        status: Optional[LogStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WebScraperLog]:
        """根据任务ID获取日志列表"""
        query = self.db.query(WebScraperLog).filter(WebScraperLog.task_id == task_id)

        if status:
            query = query.filter(WebScraperLog.status == status)
        if start_date:
            query = query.filter(WebScraperLog.start_time >= start_date)
        if end_date:
            query = query.filter(WebScraperLog.start_time <= end_date)

        return query.order_by(WebScraperLog.created_at.desc()).offset(skip).limit(limit).all()

    def get_latest_by_task(self, task_id: int) -> Optional[WebScraperLog]:
        """获取任务的最新日志"""
        return (
            self.db.query(WebScraperLog)
            .filter(WebScraperLog.task_id == task_id)
            .order_by(WebScraperLog.created_at.desc())
            .first()
        )

    def get_running_logs(self) -> List[WebScraperLog]:
        """获取所有运行中的日志"""
        return (
            self.db.query(WebScraperLog)
            .filter(WebScraperLog.status == LogStatus.RUNNING)
            .all()
        )

    def get_all(
        self,
        status: Optional[LogStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WebScraperLog]:
        """获取日志列表"""
        query = self.db.query(WebScraperLog)

        if status:
            query = query.filter(WebScraperLog.status == status)
        if start_date:
            query = query.filter(WebScraperLog.start_time >= start_date)
        if end_date:
            query = query.filter(WebScraperLog.start_time <= end_date)

        return query.order_by(WebScraperLog.created_at.desc()).offset(skip).limit(limit).all()

    def update(self, log_id: int, update_data: dict) -> Optional[WebScraperLog]:
        """更新日志"""
        ALLOWED_UPDATE_FIELDS = {
            'status', 'end_time', 'pages_scraped',
            'documents_created', 'error_message', 'execution_details'
        }

        log = self.get_by_id(log_id)
        if not log:
            return None

        for key, value in update_data.items():
            if key in ALLOWED_UPDATE_FIELDS and hasattr(log, key):
                setattr(log, key, value)

        self.db.commit()
        self.db.refresh(log)
        return log

    def delete(self, log_id: int) -> bool:
        """删除日志"""
        log = self.get_by_id(log_id)
        if not log:
            return False

        self.db.delete(log)
        self.db.commit()
        return True

    def delete_old_logs(self, days: int = 30) -> int:
        """删除指定天数之前的日志"""
        cutoff_date = datetime.utcnow() - datetime.timedelta(days=days)
        deleted_count = (
            self.db.query(WebScraperLog)
            .filter(WebScraperLog.created_at < cutoff_date)
            .delete()
        )
        self.db.commit()
        return deleted_count

    def count_by_task(
        self,
        task_id: int,
        status: Optional[LogStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """统计任务的日志数量"""
        query = self.db.query(WebScraperLog).filter(WebScraperLog.task_id == task_id)

        if status:
            query = query.filter(WebScraperLog.status == status)
        if start_date:
            query = query.filter(WebScraperLog.start_time >= start_date)
        if end_date:
            query = query.filter(WebScraperLog.start_time <= end_date)

        return query.count()

    def get_statistics_by_task(self, task_id: int) -> dict:
        """获取任务的统计信息（优化版：单次查询）"""
        from sqlalchemy import func, case

        result = self.db.query(
            func.count(WebScraperLog.id).label('total'),
            func.sum(case((WebScraperLog.status == LogStatus.SUCCESS, 1), else_=0)).label('success'),
            func.sum(case((WebScraperLog.status == LogStatus.FAILED, 1), else_=0)).label('failed'),
            func.sum(case((WebScraperLog.status == LogStatus.RUNNING, 1), else_=0)).label('running')
        ).filter(WebScraperLog.task_id == task_id).first()

        total = result.total or 0
        success = result.success or 0
        failed = result.failed or 0
        running = result.running or 0

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "running": running,
            "success_rate": (success / total * 100) if total > 0 else 0,
        }
