"""
配额服务包

提供用户配额管理的所有服务。

导出:
    - QuotaService: 配额服务 Facade
    - QuotaQueryService: 配额查询服务
    - QuotaManagementService: 配额管理服务
    - QuotaConsumptionService: 配额消费服务
    - 异常类: QuotaServiceError, QuotaNotFoundError, etc.

使用示例:
    from app.services.quota import QuotaService
    from app.services.quota.exceptions import InsufficientQuotaError

    service = QuotaService(db)
    try:
        quota, usage = service.consume_quota(user_id, tokens_used=100)
    except InsufficientQuotaError:
        print("配额不足")
"""

from app.services.quota.exceptions import (
    InsufficientQuotaError,
    InvalidQuotaValueError,
    QuotaNotFoundError,
    QuotaServiceError,
)
from app.services.quota.quota_consumption_service import QuotaConsumptionService
from app.services.quota.quota_management_service import QuotaManagementService
from app.services.quota.quota_query_service import QuotaQueryService
from app.services.quota.quota_service import QuotaService

__all__ = [
    # Facade
    "QuotaService",
    # Sub-services
    "QuotaQueryService",
    "QuotaManagementService",
    "QuotaConsumptionService",
    # Exceptions
    "QuotaServiceError",
    "QuotaNotFoundError",
    "InsufficientQuotaError",
    "InvalidQuotaValueError",
]
