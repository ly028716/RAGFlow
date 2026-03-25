"""
System 统计服务模块

实现系统使用统计功能。
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.api_usage import APIUsage
from app.models.user_quota import UserQuota


class StatisticsService:
    """
    系统统计服务类

    提供系统使用统计功能。

    使用方式:
        service = StatisticsService(db)
        stats = service.get_usage_stats(start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))
    """

    def __init__(self, db: Session):
        """
        初始化统计服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db

    def get_usage_stats(
        self,
        user_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        获取使用统计

        聚合统计API使用情况，包括token消耗、调用次数、活跃用户等。

        Args:
            user_id: 用户ID（可选，指定则返回该用户的统计）
            start_date: 开始日期（可选，默认为当月1日）
            end_date: 结束日期（可选，默认为今天）

        Returns:
            Dict[str, Any]: 使用统计字典
        """
        # 设置默认日期范围（当月）
        if not start_date:
            today = date.today()
            start_date = date(today.year, today.month, 1)

        if not end_date:
            end_date = date.today()

        # 转换为datetime用于查询
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        # 构建基础查询
        query = self.db.query(APIUsage).filter(
            and_(
                APIUsage.created_at >= start_datetime,
                APIUsage.created_at <= end_datetime,
            )
        )

        # 如果指定用户，添加用户过滤
        if user_id:
            query = query.filter(APIUsage.user_id == user_id)

        # 总token消耗
        total_tokens = query.with_entities(func.sum(APIUsage.tokens_used)).scalar() or 0

        # API调用次数
        total_calls = query.count()

        # 总费用
        total_cost = query.with_entities(func.sum(APIUsage.cost)).scalar() or Decimal(
            "0.0000"
        )

        # 活跃用户数（仅在未指定用户时统计）
        active_users = 0
        if not user_id:
            active_users = (
                query.with_entities(
                    func.count(func.distinct(APIUsage.user_id))
                ).scalar()
                or 0
            )

        # 按API类型统计（功能使用热度）
        api_type_stats = (
            query.with_entities(
                APIUsage.api_type,
                func.count(APIUsage.id).label("call_count"),
                func.sum(APIUsage.tokens_used).label("total_tokens"),
            )
            .group_by(APIUsage.api_type)
            .all()
        )

        api_type_breakdown = [
            {"api_type": stat[0], "call_count": stat[1], "total_tokens": stat[2] or 0}
            for stat in api_type_stats
        ]

        # 按日期统计（趋势分析）
        daily_stats = (
            query.with_entities(
                func.date(APIUsage.created_at).label("date"),
                func.count(APIUsage.id).label("call_count"),
                func.sum(APIUsage.tokens_used).label("total_tokens"),
            )
            .group_by(func.date(APIUsage.created_at))
            .order_by("date")
            .all()
        )

        daily_breakdown = [
            {
                "date": stat[0].isoformat() if stat[0] else None,
                "call_count": stat[1],
                "total_tokens": stat[2] or 0,
            }
            for stat in daily_stats
        ]

        # 如果指定用户，获取用户配额信息
        user_quota_info = None
        if user_id:
            user_quota = (
                self.db.query(UserQuota).filter(UserQuota.user_id == user_id).first()
            )

            if user_quota:
                user_quota_info = {
                    "monthly_quota": user_quota.monthly_quota,
                    "used_quota": user_quota.used_quota,
                    "remaining_quota": user_quota.remaining_quota,
                    "usage_percentage": user_quota.usage_percentage,
                    "reset_date": user_quota.reset_date.isoformat(),
                }

        # 构建统计结果
        stats = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "summary": {
                "total_tokens": int(total_tokens),
                "total_calls": total_calls,
                "total_cost": float(total_cost),
                "active_users": active_users,
                "average_tokens_per_call": int(total_tokens / total_calls)
                if total_calls > 0
                else 0,
            },
            "api_type_breakdown": api_type_breakdown,
            "daily_breakdown": daily_breakdown,
        }

        # 添加用户配额信息（如果有）
        if user_quota_info:
            stats["user_quota"] = user_quota_info

        return stats


__all__ = [
    "StatisticsService",
]
