"""
配额服务 Facade

提供统一的配额服务接口，委托给各子服务处理。
"""

from decimal import Decimal
from typing import Tuple

from sqlalchemy.orm import Session

from app.models.api_usage import APIUsage
from app.models.user_quota import UserQuota
from app.services.quota.exceptions import (
    InsufficientQuotaError,
    InvalidQuotaValueError,
    QuotaNotFoundError,
)
from app.services.quota.quota_consumption_service import QuotaConsumptionService
from app.services.quota.quota_management_service import QuotaManagementService
from app.services.quota.quota_query_service import QuotaQueryService


class QuotaService:
    """
    配额服务 Facade 类

    提供用户配额管理功能，包括配额检查、消耗、更新和重置。
    内部委托给各子服务处理，保持向后兼容。

    使用方式:
        service = QuotaService(db)
        quota = service.get_user_quota(user_id=1)
        if service.check_quota(user_id=1, tokens_required=100):
            service.consume_quota(user_id=1, tokens_used=100, api_type="chat")
    """

    def __init__(self, db: Session):
        """
        初始化配额服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self._query_service = QuotaQueryService(db)
        self._management_service = QuotaManagementService(db)
        self._consumption_service = QuotaConsumptionService(db)

    def get_user_quota(self, user_id: int) -> UserQuota:
        """
        获取用户配额信息

        Args:
            user_id: 用户ID

        Returns:
            UserQuota: 用户配额对象
        """
        return self._query_service.get_user_quota(user_id)

    def check_quota(self, user_id: int, tokens_required: int = 0) -> bool:
        """
        检查用户是否有足够的配额

        Args:
            user_id: 用户ID
            tokens_required: 需要的token数量

        Returns:
            bool: 配额充足返回True，否则返回False
        """
        return self._query_service.check_quota(user_id, tokens_required)

    def consume_quota(
        self,
        user_id: int,
        tokens_used: int,
        api_type: str = "chat",
        cost: Decimal = Decimal("0.0000"),
    ) -> Tuple[UserQuota, APIUsage]:
        """
        消耗用户配额（扣除token）

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
        return self._consumption_service.consume_quota(user_id, tokens_used, api_type, cost)

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
        return self._management_service.update_quota(user_id, new_quota)

    def reset_monthly_quota(self, user_id: int) -> UserQuota:
        """
        重置用户的月度配额

        Args:
            user_id: 用户ID

        Returns:
            UserQuota: 重置后的配额对象

        Raises:
            QuotaNotFoundError: 用户配额记录不存在
        """
        return self._management_service.reset_monthly_quota(user_id)

    def reset_all_quotas(self) -> int:
        """
        重置所有过期的用户配额

        Returns:
            int: 重置的配额数量
        """
        return self._management_service.reset_all_quotas()

    def get_quota_info(self, user_id: int) -> dict:
        """
        获取用户配额详细信息

        Args:
            user_id: 用户ID

        Returns:
            dict: 配额信息字典
        """
        return self._query_service.get_quota_info(user_id)


__all__ = ["QuotaService"]
