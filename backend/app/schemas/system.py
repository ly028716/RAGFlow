"""
系统管理相关Pydantic模型

定义系统配置、使用统计和健康检查的数据模型。

需求引用:
    - 需求7.1, 需求7.2: 系统配置管理
    - 需求8.2: 使用统计
    - 需求8.4: 健康检查
"""

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ============ 系统配置相关 ============


class SystemConfigResponse(BaseModel):
    """
    系统配置响应模型

    返回系统配置信息，敏感字段已脱敏。

    需求引用:
        - 需求7.5: 查询系统配置时对敏感字段进行脱敏处理
    """

    app: Dict[str, Any] = Field(..., description="应用配置")
    database: Dict[str, Any] = Field(..., description="数据库配置")
    redis: Dict[str, Any] = Field(..., description="Redis配置")
    tongyi: Dict[str, Any] = Field(..., description="通义千问配置")
    vector_db: Dict[str, Any] = Field(..., description="向量数据库配置")
    file_storage: Dict[str, Any] = Field(..., description="文件存储配置")
    document_processing: Dict[str, Any] = Field(..., description="文档处理配置")
    rag: Dict[str, Any] = Field(..., description="RAG配置")
    quota: Dict[str, Any] = Field(..., description="配额配置")
    rate_limit: Dict[str, Any] = Field(..., description="速率限制配置")
    security: Dict[str, Any] = Field(..., description="安全配置")
    jwt: Dict[str, Any] = Field(..., description="JWT配置")

    class Config:
        json_schema_extra = {
            "example": {
                "app": {
                    "name": "AI智能助手系统",
                    "version": "0.1.0",
                    "environment": "development",
                    "debug": False,
                },
                "tongyi": {
                    "api_key": "sk-a****",
                    "llm_provider": "dashscope",
                    "model_name": "qwen-plus",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "embedding_provider": "dashscope",
                    "embedding_model": "text-embedding-v3",
                },
            }
        }


class SystemConfigUpdateRequest(BaseModel):
    """
    系统配置更新请求模型（管理员）

    用于管理员更新系统配置。

    需求引用:
        - 需求7.1: 配置通义千问API密钥
        - 需求7.2: 更新模型参数
    """

    tongyi: Optional[Dict[str, Any]] = Field(None, description="通义千问配置更新")
    rag: Optional[Dict[str, Any]] = Field(None, description="RAG配置更新")
    quota: Optional[Dict[str, Any]] = Field(None, description="配额配置更新")

    class Config:
        json_schema_extra = {
            "example": {
                "tongyi": {"temperature": 0.8, "max_tokens": 3000},
                "rag": {"top_k": 10, "similarity_threshold": 0.75},
            }
        }


# ============ 使用统计相关 ============


class UsageStatsPeriod(BaseModel):
    """统计周期"""

    start_date: str = Field(..., description="开始日期（ISO格式）")
    end_date: str = Field(..., description="结束日期（ISO格式）")


class UsageStatsSummary(BaseModel):
    """使用统计摘要"""

    total_tokens: int = Field(..., description="总token消耗")
    total_calls: int = Field(..., description="总API调用次数")
    total_cost: float = Field(..., description="总费用")
    active_users: int = Field(..., description="活跃用户数")
    average_tokens_per_call: int = Field(..., description="平均每次调用token数")


class APITypeStats(BaseModel):
    """API类型统计"""

    api_type: str = Field(..., description="API类型")
    call_count: int = Field(..., description="调用次数")
    total_tokens: int = Field(..., description="总token消耗")


class DailyStats(BaseModel):
    """每日统计"""

    date: str = Field(..., description="日期（ISO格式）")
    call_count: int = Field(..., description="调用次数")
    total_tokens: int = Field(..., description="总token消耗")


class UserQuotaInfo(BaseModel):
    """用户配额信息"""

    monthly_quota: int = Field(..., description="月度配额")
    used_quota: int = Field(..., description="已使用配额")
    remaining_quota: int = Field(..., description="剩余配额")
    usage_percentage: float = Field(..., description="使用百分比")
    reset_date: str = Field(..., description="重置日期")


class UsageStatsResponse(BaseModel):
    """
    使用统计响应模型

    返回系统或用户的使用统计信息。

    需求引用:
        - 需求8.2: 返回总token消耗、API调用次数、活跃用户数和功能使用热度
        - 需求8.3: 按用户维度统计token消耗并支持按时间范围筛选
    """

    period: UsageStatsPeriod = Field(..., description="统计周期")
    summary: UsageStatsSummary = Field(..., description="统计摘要")
    api_type_breakdown: List[APITypeStats] = Field(..., description="按API类型分类统计")
    daily_breakdown: List[DailyStats] = Field(..., description="每日统计")
    user_quota: Optional[UserQuotaInfo] = Field(None, description="用户配额信息（仅用户统计时返回）")

    class Config:
        json_schema_extra = {
            "example": {
                "period": {"start_date": "2025-01-01", "end_date": "2025-01-31"},
                "summary": {
                    "total_tokens": 500000,
                    "total_calls": 1000,
                    "total_cost": 50.0,
                    "active_users": 50,
                    "average_tokens_per_call": 500,
                },
                "api_type_breakdown": [
                    {"api_type": "chat", "call_count": 600, "total_tokens": 300000},
                    {"api_type": "rag", "call_count": 300, "total_tokens": 150000},
                ],
                "daily_breakdown": [
                    {"date": "2025-01-01", "call_count": 50, "total_tokens": 25000}
                ],
            }
        }


# ============ 健康检查相关 ============


class ComponentHealth(BaseModel):
    """组件健康状态"""

    status: str = Field(..., description="状态（healthy/unhealthy/degraded/unknown）")
    message: str = Field(..., description="状态消息")
    type: Optional[str] = Field(None, description="组件类型")
    version: Optional[str] = Field(None, description="版本信息")
    connected_clients: Optional[int] = Field(None, description="连接客户端数（Redis）")
    used_memory_human: Optional[str] = Field(None, description="已用内存（Redis）")
    persist_directory: Optional[str] = Field(None, description="持久化目录（Chroma）")
    free_space_gb: Optional[int] = Field(None, description="可用磁盘空间（GB）")


class HealthCheckResponse(BaseModel):
    """
    健康检查响应模型

    返回系统各组件的健康状态。

    需求引用:
        - 需求8.4: 提供健康检查接口，返回数据库、Redis和向量数据库连接状态
    """

    status: str = Field(..., description="整体状态（healthy/unhealthy/degraded）")
    timestamp: str = Field(..., description="检查时间戳（ISO格式）")
    components: Dict[str, ComponentHealth] = Field(..., description="各组件健康状态")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-01-08T10:00:00Z",
                "components": {
                    "database": {
                        "status": "healthy",
                        "type": "mysql",
                        "message": "数据库连接正常",
                    },
                    "redis": {
                        "status": "healthy",
                        "message": "Redis连接正常",
                        "version": "7.0.0",
                        "connected_clients": 5,
                        "used_memory_human": "1.5M",
                    },
                    "vector_db": {
                        "status": "healthy",
                        "type": "chroma",
                        "message": "向量数据库连接正常",
                        "persist_directory": "./data/chroma",
                    },
                    "disk": {
                        "status": "healthy",
                        "free_space_gb": 50,
                        "message": "可用磁盘空间: 50GB",
                    },
                },
            }
        }


# ============ 系统信息相关 ============


class SystemInfoSystem(BaseModel):
    """系统基本信息"""

    platform: str = Field(..., description="操作系统平台")
    platform_version: str = Field(..., description="平台版本")
    python_version: str = Field(..., description="Python版本")
    app_name: str = Field(..., description="应用名称")
    app_version: str = Field(..., description="应用版本")
    environment: str = Field(..., description="运行环境")


class SystemInfoStatistics(BaseModel):
    """系统统计信息"""

    total_users: int = Field(..., description="总用户数")
    active_users: int = Field(..., description="活跃用户数")
    today_api_calls: int = Field(..., description="今日API调用次数")
    today_tokens_used: int = Field(..., description="今日token消耗")


class SystemInfoUptime(BaseModel):
    """系统运行时间"""

    started_at: str = Field(..., description="启动时间（ISO格式）")


class SystemInfoResponse(BaseModel):
    """
    系统信息响应模型

    返回系统的基本信息和运行状态。
    """

    system: SystemInfoSystem = Field(..., description="系统基本信息")
    statistics: SystemInfoStatistics = Field(..., description="统计信息")
    uptime: SystemInfoUptime = Field(..., description="运行时间")

    class Config:
        json_schema_extra = {
            "example": {
                "system": {
                    "platform": "Linux",
                    "platform_version": "5.10.0",
                    "python_version": "3.11.0",
                    "app_name": "AI智能助手系统",
                    "app_version": "0.1.0",
                    "environment": "production",
                },
                "statistics": {
                    "total_users": 100,
                    "active_users": 80,
                    "today_api_calls": 500,
                    "today_tokens_used": 250000,
                },
                "uptime": {"started_at": "2025-01-08T00:00:00Z"},
            }
        }


# 导出
__all__ = [
    # 配置相关
    "SystemConfigResponse",
    "SystemConfigUpdateRequest",
    # 使用统计相关
    "UsageStatsPeriod",
    "UsageStatsSummary",
    "APITypeStats",
    "DailyStats",
    "UserQuotaInfo",
    "UsageStatsResponse",
    # 健康检查相关
    "ComponentHealth",
    "HealthCheckResponse",
    # 系统信息相关
    "SystemInfoSystem",
    "SystemInfoStatistics",
    "SystemInfoUptime",
    "SystemInfoResponse",
]
