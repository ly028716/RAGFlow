"""
配额消费服务模块

实现配额消耗和API使用记录功能。
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.core.redis import RedisKeys, get_redis_client
from app.models.api_usage import APIUsage
from app.models.user_quota import UserQuota
from app.repositories.quota_repository import QuotaRepository
from app.services.quota.exceptions import InsufficientQuotaError
from app.websocket.connection_manager import connection_manager


class QuotaConsumptionService:
    """
    配额消费服务类

    提供配额消耗和API使用记录功能。
    """

    def __init__(self, db: Session):
        """
        初始化配额消费服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self.quota_repo = QuotaRepository(db)
        self.default_quota = settings.quota.default_monthly_quota

    def consume_quota(
        self,
        user_id: int,
        tokens_used: int,
        api_type: str = "chat",
        cost: Decimal = Decimal("0.0000"),
    ) -> Tuple[UserQuota, APIUsage]:
        """
        消耗用户配额（扣除token）

        使用Redis原子操作确保并发安全，同时记录API使用情况。

        Args:
            user_id: 用户ID
            tokens_used: 消耗的token数量
            api_type: API类型（chat/rag/agent等）
            cost: 调用费用（可选）

        Returns:
            Tuple[UserQuota, APIUsage]: (更新后的配额对象, API使用记录)

        Raises:
            InsufficientQuotaError: 配额不足
        """
        # 获取当前配额
        from app.services.quota.quota_query_service import QuotaQueryService
        query_service = QuotaQueryService(self.db)
        quota = query_service.get_user_quota(user_id)

        # 检查配额是否充足
        if not quota.has_sufficient_quota(tokens_used):
            raise InsufficientQuotaError(
                f"配额不足，剩余 {quota.remaining_quota} tokens，需要 {tokens_used} tokens",
                remaining=quota.remaining_quota,
                required=tokens_used,
            )

        # 使用Redis原子操作扣除配额
        try:
            redis_client = get_redis_client()
            used_key = RedisKeys.format_key(RedisKeys.USER_QUOTA_USED, user_id=user_id)

            # 原子递增
            redis_client.incrby(used_key, tokens_used)

            # 设置过期时间（到下个月1日）
            from dateutil.relativedelta import relativedelta
            from datetime import date

            today = date.today()
            next_month = today + relativedelta(months=1)
            next_reset = date(next_month.year, next_month.month, 1)
            ttl = int(
                (
                    datetime.combine(next_reset, datetime.min.time()) - datetime.now()
                ).total_seconds()
            )
            if ttl > 0:
                redis_client.expire(used_key, ttl)
        except Exception:
            # Redis不可用时，仅使用数据库
            pass

        # 更新数据库中的配额
        quota = self.quota_repo.consume_quota(user_id, tokens_used)

        # 检查配额警告阈值（剩余10%时发送警告）
        self._send_quota_warnings(user_id, quota)

        # 记录API使用情况
        api_usage = APIUsage(
            user_id=user_id, api_type=api_type, tokens_used=tokens_used, cost=cost
        )
        self.db.add(api_usage)
        self.db.commit()
        self.db.refresh(api_usage)

        return quota, api_usage

    def _send_quota_warnings(self, user_id: int, quota: UserQuota) -> None:
        """
        发送配额警告通知

        Args:
            user_id: 用户ID
            quota: 配额对象
        """
        usage_percentage = quota.usage_percentage

        if usage_percentage >= 90 and usage_percentage < 95:
            self._send_warning(
                user_id, quota, usage_percentage, "low",
                f"配额即将用尽，剩余 {quota.remaining_quota} tokens ({100-usage_percentage:.1f}%)"
            )
        elif usage_percentage >= 95:
            self._send_warning(
                user_id, quota, usage_percentage, "critical",
                f"配额严重不足，剩余 {quota.remaining_quota} tokens ({100-usage_percentage:.1f}%)"
            )

    def _send_warning(
        self, user_id: int, quota: UserQuota, usage_percentage: float,
        level: str, message: str
    ) -> None:
        """
        发送配额警告

        Args:
            user_id: 用户ID
            quota: 配额对象
            usage_percentage: 使用百分比
            level: 警告级别
            message: 警告消息
        """
        try:
            asyncio.create_task(
                connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "quota_warning",
                        "data": {
                            "level": level,
                            "remaining_quota": quota.remaining_quota,
                            "usage_percentage": usage_percentage,
                            "message": message,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    },
                )
            )
        except Exception:
            # WebSocket通知失败不影响主流程
            pass


__all__ = ["QuotaConsumptionService"]
