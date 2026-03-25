"""
配额管理服务模块

实现配额更新和重置功能。
"""

from datetime import date
from typing import Optional

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.config import settings
from app.core.redis import RedisKeys, get_redis_client
from app.models.user_quota import UserQuota
from app.repositories.quota_repository import QuotaRepository
from app.services.quota.exceptions import InvalidQuotaValueError, QuotaNotFoundError


class QuotaManagementService:
    """
    配额管理服务类

    提供配额更新和重置功能。
    """

    def __init__(self, db: Session):
        """
        初始化配额管理服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self.quota_repo = QuotaRepository(db)
        self.default_quota = settings.quota.default_monthly_quota

    def update_quota(self, user_id: int, new_quota: int) -> UserQuota:
        """
        更新用户的月度配额上限（管理员功能）

        Args:
            user_id: 用户ID
            new_quota: 新的月度配额上限

        Returns:
            UserQuota: 更新后的配额对象

        Raises:
            InvalidQuotaValueError: 配额值无效
            QuotaNotFoundError: 用户配额记录不存在
        """
        # 验证配额值
        if new_quota < 0:
            raise InvalidQuotaValueError("配额值不能为负数")

        if new_quota < 1000:
            raise InvalidQuotaValueError("配额值不能小于1000")

        # 确保用户有配额记录
        from app.services.quota.quota_query_service import QuotaQueryService
        query_service = QuotaQueryService(self.db)
        quota = query_service.get_user_quota(user_id)

        # 更新配额
        quota = self.quota_repo.update_monthly_quota(user_id, new_quota)

        if not quota:
            raise QuotaNotFoundError(f"用户 {user_id} 的配额记录不存在")

        # 同步到Redis
        self._sync_quota_to_redis(user_id, quota)

        return quota

    def reset_monthly_quota(self, user_id: int) -> UserQuota:
        """
        重置用户的月度配额

        将已使用配额清零，更新重置日期到下个月1日。

        Args:
            user_id: 用户ID

        Returns:
            UserQuota: 重置后的配额对象

        Raises:
            QuotaNotFoundError: 用户配额记录不存在
        """
        quota = self.quota_repo.reset_quota(user_id)

        if not quota:
            raise QuotaNotFoundError(f"用户 {user_id} 的配额记录不存在")

        # 清除Redis缓存
        self._clear_quota_from_redis(user_id)

        # 同步新配额到Redis
        self._sync_quota_to_redis(user_id, quota)

        return quota

    def reset_all_quotas(self) -> int:
        """
        重置所有过期的用户配额

        用于定时任务，在每月1日执行。

        Returns:
            int: 重置的配额数量
        """
        count = self.quota_repo.reset_all_expired_quotas()

        # 清除所有Redis配额缓存
        try:
            redis_client = get_redis_client()
            # 使用SCAN命令查找所有配额相关的键
            cursor = 0
            while True:
                cursor, keys = redis_client.scan(cursor, match="quota:*", count=100)
                if keys:
                    redis_client.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            # Redis不可用时忽略
            pass

        return count

    def _sync_quota_to_redis(self, user_id: int, quota: UserQuota) -> None:
        """
        同步配额信息到Redis缓存

        Args:
            user_id: 用户ID
            quota: 配额对象
        """
        try:
            from datetime import datetime

            redis_client = get_redis_client()
            quota_key = RedisKeys.format_key(RedisKeys.USER_QUOTA, user_id=user_id)
            used_key = RedisKeys.format_key(RedisKeys.USER_QUOTA_USED, user_id=user_id)

            # 计算到下个月1日的TTL
            next_reset = self._get_next_reset_date()
            ttl = int(
                (
                    datetime.combine(next_reset, datetime.min.time()) - datetime.now()
                ).total_seconds()
            )

            if ttl > 0:
                redis_client.setex(quota_key, ttl, str(quota.monthly_quota))
                redis_client.setex(used_key, ttl, str(quota.used_quota))
        except Exception:
            # Redis不可用时忽略
            pass

    def _clear_quota_from_redis(self, user_id: int) -> None:
        """
        清除Redis中的配额缓存

        Args:
            user_id: 用户ID
        """
        try:
            redis_client = get_redis_client()
            quota_key = RedisKeys.format_key(RedisKeys.USER_QUOTA, user_id=user_id)
            used_key = RedisKeys.format_key(RedisKeys.USER_QUOTA_USED, user_id=user_id)

            redis_client.delete(quota_key, used_key)
        except Exception:
            # Redis不可用时忽略
            pass

    def _get_next_reset_date(self) -> date:
        """
        获取下一个配额重置日期（下个月1日）

        Returns:
            date: 下个月1日的日期
        """
        today = date.today()
        next_month = today + relativedelta(months=1)
        return date(next_month.year, next_month.month, 1)


__all__ = ["QuotaManagementService"]
