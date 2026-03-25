"""
System 服务包

提供系统配置管理、使用统计和健康检查功能。

使用方式:
    from app.services.system import SystemService
    service = SystemService(db)
    config = service.get_config()

或者使用子服务:
    from app.services.system import ConfigService, StatisticsService, HealthService
    config_service = ConfigService()
    stats_service = StatisticsService(db)
"""

# 子服务
from app.services.system.config_service import ConfigService
from app.services.system.health_service import HealthService
from app.services.system.info_service import InfoService
from app.services.system.statistics_service import StatisticsService

# Facade
from app.services.system.system_service import SystemService

# 工具函数
from app.services.system.crypto_utils import (
    decrypt_value,
    encrypt_value,
    get_or_create_encryption_key,
    mask_sensitive_value,
)

__all__ = [
    # 服务类
    "SystemService",
    "ConfigService",
    "StatisticsService",
    "HealthService",
    "InfoService",
    # 工具函数
    "get_or_create_encryption_key",
    "encrypt_value",
    "decrypt_value",
    "mask_sensitive_value",
]
