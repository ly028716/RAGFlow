"""
Web Scraper 执行日志模型

记录每次采集任务的执行情况
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class LogStatus(str, Enum):
    """执行状态枚举"""

    RUNNING = "running"  # 运行中
    SUCCESS = "success"  # 成功
    FAILED = "failed"  # 失败


class WebScraperLog(Base):
    """
    网页采集执行日志表

    记录每次采集任务的执行情况，包括状态、统计信息和错误信息
    """

    __tablename__ = "web_scraper_logs"

    id = Column(Integer, primary_key=True, index=True, comment="日志ID")
    task_id = Column(
        Integer,
        ForeignKey("web_scraper_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="任务ID"
    )
    status = Column(
        SQLEnum(LogStatus),
        nullable=False,
        default=LogStatus.RUNNING,
        index=True,
        comment="执行状态"
    )
    start_time = Column(DateTime, nullable=False, index=True, comment="开始时间")
    end_time = Column(DateTime, nullable=True, comment="结束时间")
    pages_scraped = Column(Integer, nullable=False, default=0, comment="抓取页面数")
    documents_created = Column(Integer, nullable=False, default=0, comment="创建文档数")
    error_message = Column(Text, nullable=True, comment="错误信息")
    execution_details = Column(JSON, nullable=True, comment="执行详情（JSON格式）")
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="创建时间"
    )

    # 关系：任务
    task = relationship("WebScraperTask", back_populates="logs")

    def __repr__(self):
        return f"<WebScraperLog(id={self.id}, task_id={self.task_id}, status={self.status})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "status": self.status.value if self.status else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "pages_scraped": self.pages_scraped,
            "documents_created": self.documents_created,
            "error_message": self.error_message,
            "execution_details": self.execution_details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
