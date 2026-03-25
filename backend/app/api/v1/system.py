"""
系统管理API路由模块

实现系统配置管理、使用统计和健康检查功能端点。

需求引用:
    - 需求7.1, 需求7.2: 系统配置管理
    - 需求8.2: 使用统计
    - 需求8.4: 健康检查
"""

import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import get_db
from app.dependencies import get_current_admin_user, get_current_user
from app.models.user import User
from app.schemas.system import (HealthCheckResponse, SystemConfigResponse,
                                SystemConfigUpdateRequest, SystemInfoResponse,
                                UsageStatsResponse)
from app.services.system import SystemService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["系统管理"])


# ============ 系统配置管理 ============


@router.get(
    "/config",
    response_model=SystemConfigResponse,
    summary="获取系统配置（管理员）",
    description="获取系统配置信息，敏感字段已脱敏。需要管理员权限。",
)
async def get_system_config(
    current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)
) -> SystemConfigResponse:
    """
    获取系统配置

    返回系统配置信息，敏感字段（如API密钥）进行脱敏处理。

    需求引用:
        - 需求7.5: 查询系统配置时对敏感字段进行脱敏处理

    Args:
        current_user: 当前管理员用户
        db: 数据库会话

    Returns:
        SystemConfigResponse: 系统配置信息

    Raises:
        HTTPException 403: 无管理员权限
        HTTPException 500: 获取配置失败
    """
    system_service = SystemService(db)

    try:
        config = system_service.get_config()
        logger.info(f"管理员 {current_user.username} 查询系统配置")
        return SystemConfigResponse(**config)
    except Exception as e:
        logger.error(f"获取系统配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取系统配置失败"
        )


@router.put(
    "/config",
    response_model=SystemConfigResponse,
    summary="更新系统配置（管理员）",
    description="更新系统配置项。需要管理员权限。",
)
async def update_system_config(
    request: SystemConfigUpdateRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> SystemConfigResponse:
    """
    更新系统配置

    更新系统配置项，敏感字段自动加密存储。

    注意：配置更新仅影响运行时配置，重启后会恢复为环境变量配置

    需求引用:
        - 需求7.1: 配置通义千问API密钥时验证有效性并加密存储
        - 需求7.2: 更新模型参数时验证参数范围的合法性

    Args:
        request: 配置更新请求
        current_user: 当前管理员用户
        db: 数据库会话

    Returns:
        SystemConfigResponse: 更新后的系统配置

    Raises:
        HTTPException 400: 配置值无效
        HTTPException 403: 无管理员权限
        HTTPException 500: 更新失败
    """
    system_service = SystemService(db)

    try:
        # 构建配置更新字典
        config_updates = {}

        if request.tongyi is not None:
            config_updates["tongyi"] = request.tongyi

        if request.rag is not None:
            config_updates["rag"] = request.rag

        if request.quota is not None:
            config_updates["quota"] = request.quota

        # 更新配置
        updated_config = system_service.update_config(config_updates)

        logger.info(f"管理员 {current_user.username} 更新系统配置")

        return SystemConfigResponse(**updated_config)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"更新系统配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新系统配置失败"
        )


# ============ 使用统计 ============


@router.get(
    "/stats",
    response_model=UsageStatsResponse,
    summary="获取使用统计",
    description="获取系统或用户的使用统计信息。管理员可查看所有用户统计，普通用户只能查看自己的统计。",
)
async def get_usage_stats(
    user_id: Optional[int] = Query(None, description="用户ID（管理员可指定，普通用户自动使用当前用户）"),
    start_date: Optional[date] = Query(None, description="开始日期（默认为当月1日）"),
    end_date: Optional[date] = Query(None, description="结束日期（默认为今天）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsageStatsResponse:
    """
    获取使用统计

    聚合统计API使用情况，包括token消耗、调用次数、活跃用户等。

    权限说明:
    - 管理员：可以查看所有用户的统计或指定用户的统计
    - 普通用户：只能查看自己的统计

    需求引用:
        - 需求8.2: 返回总token消耗、API调用次数、活跃用户数和功能使用热度
        - 需求8.3: 按用户维度统计token消耗并支持按时间范围筛选

    Args:
        user_id: 用户ID（可选）
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        UsageStatsResponse: 使用统计信息

    Raises:
        HTTPException 403: 权限不足
        HTTPException 500: 获取统计失败
    """
    system_service = SystemService(db)

    # 权限检查
    if not current_user.is_admin:
        # 普通用户只能查看自己的统计
        if user_id is not None and user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="只能查看自己的统计信息"
            )
        user_id = current_user.id
    elif user_id is None:
        # 管理员未指定用户ID时，查看全部统计
        user_id = None

    try:
        stats = system_service.get_usage_stats(
            user_id=user_id, start_date=start_date, end_date=end_date
        )

        return UsageStatsResponse(**stats)

    except Exception as e:
        logger.error(f"获取使用统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取使用统计失败"
        )


@router.get(
    "/stats/all",
    response_model=UsageStatsResponse,
    summary="获取全局使用统计（管理员）",
    description="获取所有用户的使用统计信息。需要管理员权限。",
)
async def get_all_usage_stats(
    start_date: Optional[date] = Query(None, description="开始日期（默认为当月1日）"),
    end_date: Optional[date] = Query(None, description="结束日期（默认为今天）"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> UsageStatsResponse:
    """
    获取全局使用统计（管理员）

    获取所有用户的聚合统计信息。

    需求引用:
        - 需求8.2: 返回总token消耗、API调用次数、活跃用户数和功能使用热度

    Args:
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
        current_user: 当前管理员用户
        db: 数据库会话

    Returns:
        UsageStatsResponse: 全局使用统计信息

    Raises:
        HTTPException 403: 无管理员权限
        HTTPException 500: 获取统计失败
    """
    system_service = SystemService(db)

    try:
        # user_id=None 表示查询所有用户的统计
        stats = system_service.get_usage_stats(
            user_id=None, start_date=start_date, end_date=end_date
        )

        logger.info(f"管理员 {current_user.username} 查询全局使用统计")

        return UsageStatsResponse(**stats)

    except Exception as e:
        logger.error(f"获取全局使用统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取全局使用统计失败"
        )


# ============ 健康检查 ============


@router.get(
    "/ping",
    summary="系统快速存活探针",
    description="不依赖数据库/Redis/向量库的快速存活检查。无需认证。",
)
async def ping() -> dict:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="系统健康检查",
    description="检查系统各组件的健康状态。无需认证。",
)
async def health_check(db: Session = Depends(get_db)) -> HealthCheckResponse:
    """
    系统健康检查

    检查各个组件的连接状态和健康状况，包括：
    - MySQL数据库
    - Redis缓存
    - Chroma向量数据库
    - 磁盘空间

    此端点无需认证，用于监控系统和负载均衡器健康检查。

    需求引用:
        - 需求8.4: 提供健康检查接口，返回数据库、Redis和向量数据库连接状态

    Args:
        db: 数据库会话

    Returns:
        HealthCheckResponse: 健康检查结果
    """
    system_service = SystemService(db)

    try:
        detailed = settings.app.environment not in ("staging", "production")
        health_status = system_service.health_check(detailed=detailed)
        return HealthCheckResponse(**health_status)
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        # 即使检查失败，也返回unhealthy状态而不是抛出异常
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.utcnow().isoformat(),
            components={"error": {"status": "unhealthy", "message": "健康检查失败"}},
        )


# ============ 系统信息 ============


@router.get(
    "/info",
    response_model=SystemInfoResponse,
    summary="获取系统信息",
    description="获取系统的基本信息和运行状态。",
)
async def get_system_info(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> SystemInfoResponse:
    """
    获取系统信息

    返回系统的基本信息和运行状态，包括：
    - 操作系统信息
    - Python版本
    - 应用版本
    - 用户统计
    - 今日使用统计
    - 运行时间

    Args:
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        SystemInfoResponse: 系统信息

    Raises:
        HTTPException 500: 获取信息失败
    """
    system_service = SystemService(db)

    try:
        system_info = system_service.get_system_info()
        return SystemInfoResponse(**system_info)
    except Exception as e:
        logger.error(f"获取系统信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取系统信息失败"
        )


# 导出
__all__ = ["router"]
