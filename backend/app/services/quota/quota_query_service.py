"""
配额查询服务模块

实现配额查询和检查功能。
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.core.redis import RedisKeys, get_redis_client
from app.models.user_quota import UserQuota
from app.repositories.quota_repository import QuotaRepository


class QuotaQueryService:
    """
    配额查询服务类

    提供配额查询和检查功能。
    """

    def __init__(self, db: Session):
        """
        初始化配额查询服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self.quota_repo = QuotaRepository(db)
        self.default_quota = settings.quota.default_monthly_quota

    def get_user_quota(self, user_id: int) -> UserQuota:
        """
        获取用户配额信息

        如果用户没有配额记录，自动创建默认配额。

        Args:
            user_id: 用户ID

        Returns:
            UserQuota: 用户配额对象
        """
        quota = self.quota_repo.get_or_create(
            user_id=user_id, monthly_quota=self.default_quota
        )
        return quota

    def check_quota(self, user_id: int, tokens_required: int = 0) -> bool:
        """
        检查用户是否有足够的配额

        使用Redis缓存加速检查，同时确保数据一致性。

        Args:
            user_id: 用户ID
            tokens_required: 需要的token数量（默认为0，仅检查是否有剩余配额）

        Returns:
            bool: 配额充足返回True，否则返回False
        """
        try:
            # 首先尝试从Redis获取配额信息（快速路径）
            redis_client = get_redis_client()
            quota_key = RedisKeys.format_key(RedisKeys.USER_QUOTA, user_id=user_id)
            used_key = RedisKeys.format_key(RedisKeys.USER_QUOTA_USED, user_id=user_id)

            # 尝试从Redis获取
            monthly_quota = redis_client.get(quota_key)
            used_quota = redis_client.get(used_key)

            if monthly_quota is not None and used_quota is not None:
                remaining = int(monthly_quota) - int(used_quota)
                return remaining >= tokens_required
        except Exception:
            # Redis不可用时，回退到数据库
            pass

        # 从数据库获取配额
        quota = self.get_user_quota(user_id)
        return quota.has_sufficient_quota(tokens_required)

    def get_quota_info(self, user_id: int) -> dict:
        """
        获取用户配额详细信息

        返回格式化的配额信息，包括使用百分比和重置日期。

        Args:
            user_id: 用户ID

        Returns:
            dict: 配额信息字典
        """
        quota = self.get_user_quota(user_id)

        return {
            "monthly_quota": quota.monthly_quota,
            "used_quota": quota.used_quota,
            "remaining_quota": quota.remaining_quota,
            "reset_date": quota.reset_date.isoformat(),
            "usage_percentage": quota.usage_percentage,
        }


__all__ = ["QuotaQueryService"]
