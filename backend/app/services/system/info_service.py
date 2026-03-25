"""
System 信息服务模块

实现系统信息查询功能。
"""

import platform
import sys
from datetime import date, datetime
from typing import Any, Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.api_usage import APIUsage
from app.models.user import User


class InfoService:
    """
    系统信息服务类

    提供系统基本信息查询功能。

    使用方式:
        service = InfoService(db)
        info = service.get_system_info()
    """

    def __init__(self, db: Session):
        """
        初始化信息服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db

    def get_system_info(self) -> Dict[str, Any]:
        """
        获取系统信息

        返回系统的基本信息和运行状态。

        Returns:
            Dict[str, Any]: 系统信息字典
        """
        # 获取用户统计
        total_users = self.db.query(User).count()
        active_users = self.db.query(User).filter(User.is_active == True).count()

        # 获取今日统计
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_usage = (
            self.db.query(APIUsage)
            .filter(APIUsage.created_at >= today_start)
            .with_entities(
                func.count(APIUsage.id).label("calls"),
                func.sum(APIUsage.tokens_used).label("tokens"),
            )
            .first()
        )

        return {
            "system": {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "python_version": sys.version,
                "app_name": settings.app.app_name,
                "app_version": settings.app.app_version,
                "environment": settings.app.environment,
            },
            "statistics": {
                "total_users": total_users,
                "active_users": active_users,
                "today_api_calls": today_usage[0] if today_usage else 0,
                "today_tokens_used": int(today_usage[1])
                if today_usage and today_usage[1]
                else 0,
            },
            "uptime": {
                "started_at": datetime.utcnow().isoformat(),
            },
        }


__all__ = [
    "InfoService",
]
