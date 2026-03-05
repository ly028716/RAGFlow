"""
Web Scraper 任务模型

存储网页采集任务的配置信息
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class ScheduleType(str, Enum):
    """调度类型枚举"""

    ONCE = "once"  # 一次性任务
    CRON = "cron"  # 定时任务


class TaskStatus(str, Enum):
    """任务状态枚举"""

    ACTIVE = "active"  # 活跃
    PAUSED = "paused"  # 暂停
    STOPPED = "stopped"  # 停止


class WebScraperTask(Base):
    """
    网页采集任务表

    存储网页采集任务的配置信息，支持一次性和定时采集
    """

    __tablename__ = "web_scraper_tasks"

    id = Column(Integer, primary_key=True, index=True, comment="任务ID")
    name = Column(String(200), nullable=False, comment="任务名称")
    description = Column(Text, nullable=True, comment="任务描述")
    url = Column(String(500), nullable=False, comment="目标URL")
    url_pattern = Column(String(500), nullable=True, comment="URL匹配模式（支持通配符）")
    knowledge_base_id = Column(
        Integer,
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="目标知识库ID"
    )
    schedule_type = Column(
        SQLEnum(ScheduleType),
        nullable=False,
        default=ScheduleType.ONCE,
        comment="调度类型：once-一次性，cron-定时"
    )
    cron_expression = Column(String(100), nullable=True, comment="Cron表达式")
    selector_config = Column(JSON, nullable=True, comment="选择器配置（JSON格式）")
    scraper_config = Column(JSON, nullable=True, comment="采集器配置（JSON格式）")
    status = Column(
        SQLEnum(TaskStatus),
        nullable=False,
        default=TaskStatus.ACTIVE,
        index=True,
        comment="任务状态"
    )
    last_run_at = Column(DateTime, nullable=True, comment="最后执行时间")
    next_run_at = Column(DateTime, nullable=True, index=True, comment="下次执行时间")
    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="创建者用户ID"
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间"
    )

    # 关系：知识库
    knowledge_base = relationship("KnowledgeBase", back_populates="scraper_tasks")

    # 关系：创建者
    creator = relationship("User", foreign_keys=[created_by])

    # 关系：执行日志
    logs = relationship(
        "WebScraperLog",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="WebScraperLog.created_at.desc()"
    )

    def __repr__(self):
        return f"<WebScraperTask(id={self.id}, name={self.name}, status={self.status})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "url_pattern": self.url_pattern,
            "knowledge_base_id": self.knowledge_base_id,
            "schedule_type": self.schedule_type.value if self.schedule_type else None,
            "cron_expression": self.cron_expression,
            "selector_config": self.selector_config,
            "scraper_config": self.scraper_config,
            "status": self.status.value if self.status else None,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
