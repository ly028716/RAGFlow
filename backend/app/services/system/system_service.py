"""
System 服务模块 (Facade)

此模块现在作为 Facade，内部委托给子服务。
所有实际功能已迁移到 app.services.system 包中的子服务。

推荐使用方式:
    from app.services.system import ConfigService, StatisticsService, HealthService, InfoService

向后兼容用法:
    from app.services.system import SystemService
    service = SystemService(db)  # 内部委托给子服务
"""

from datetime import date
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.services.system.config_service import ConfigService
from app.services.system.health_service import HealthService
from app.services.system.info_service import InfoService
from app.services.system.statistics_service import StatisticsService


class SystemService:
    """
    系统服务类 (Facade)

    提供系统配置管理、使用统计和健康检查功能。
    此服务现在作为 Facade，内部委托给子服务。

    向后兼容用法:
        service = SystemService(db)
        config = service.get_config()

    推荐新用法:
        from app.services.system import ConfigService, StatisticsService
        config_service = ConfigService()
        stats_service = StatisticsService(db)
    """

    def __init__(self, db: Session):
        """
        初始化系统服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        # 初始化子服务
        self._config_service = ConfigService()
        self._statistics_service = StatisticsService(db)
        self._health_service = HealthService(db)
        self._info_service = InfoService(db)

    # ==================== 配置管理 (委托给 ConfigService) ====================

    def get_config(self) -> Dict[str, Any]:
        """获取系统配置"""
        return self._config_service.get_config()

    def update_config(self, config_updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新系统配置"""
        return self._config_service.update_config(config_updates)

    # ==================== 使用统计 (委托给 StatisticsService) ====================

    def get_usage_stats(
        self,
        user_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """获取使用统计"""
        return self._statistics_service.get_usage_stats(user_id, start_date, end_date)

    # ==================== 健康检查 (委托给 HealthService) ====================

    def health_check(self, detailed: bool = True) -> Dict[str, Any]:
        """系统健康检查"""
        return self._health_service.health_check(detailed)

    # ==================== 系统信息 (委托给 InfoService) ====================

    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return self._info_service.get_system_info()


__all__ = [
    "SystemService",
]
