"""
配额API路由模块

实现配额管理功能端点，包括查询配额和管理员更新配额。

需求引用:
    - 需求11.7: 返回当月已使用token数、剩余token数和配额重置日期
    - 需求11.5: 管理员更新用户配额
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_admin_user, get_current_user
from app.models.user import User
from app.schemas.quota import (QuotaResponse, QuotaUpdateRequest,
                               QuotaUpdateResponse)
from app.services.quota import InvalidQuotaValueError, QuotaNotFoundError, QuotaService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quota", tags=["配额管理"])


@router.get(
    "", response_model=QuotaResponse, summary="获取配额信息", description="获取当前用户的配额使用情况。"
)
async def get_quota(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> QuotaResponse:
    """
    获取当前用户的配额信息

    返回月度配额上限、已使用配额、剩余配额、重置日期和使用百分比。

    需求引用:
        - 需求11.7: 返回当月已使用token数、剩余token数和配额重置日期

    Args:
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        QuotaResponse: 配额信息
    """
    quota_service = QuotaService(db)

    try:
        quota_info = quota_service.get_quota_info(current_user.id)

        return QuotaResponse(
            monthly_quota=quota_info["monthly_quota"],
            used_quota=quota_info["used_quota"],
            remaining_quota=quota_info["remaining_quota"],
            reset_date=quota_info["reset_date"],
            usage_percentage=quota_info["usage_percentage"],
        )
    except Exception as e:
        logger.error(f"获取配额信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取配额信息失败"
        )


@router.put(
    "",
    response_model=QuotaUpdateResponse,
    summary="更新用户配额（管理员）",
    description="管理员更新指定用户的月度配额上限。需要管理员权限。",
)
async def update_quota(
    request: QuotaUpdateRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> QuotaUpdateResponse:
    """
    更新用户配额（管理员功能）

    更新指定用户的月度配额上限。

    需求引用:
        - 需求11.5: 管理员更新用户配额

    Args:
        request: 配额更新请求
        current_user: 当前管理员用户
        db: 数据库会话

    Returns:
        QuotaUpdateResponse: 更新后的配额信息

    Raises:
        HTTPException 400: 配额值无效
        HTTPException 403: 无管理员权限
        HTTPException 404: 用户不存在
        HTTPException 500: 更新失败
    """
    quota_service = QuotaService(db)

    try:
        quota = quota_service.update_quota(
            user_id=request.user_id, new_quota=request.monthly_quota
        )

        logger.info(
            f"管理员 {current_user.username} 更新用户 {request.user_id} 的配额为 {request.monthly_quota}"
        )

        return QuotaUpdateResponse(
            user_id=quota.user_id,
            monthly_quota=quota.monthly_quota,
            used_quota=quota.used_quota,
            remaining_quota=quota.remaining_quota,
            reset_date=quota.reset_date.isoformat(),
            updated_at=quota.updated_at.isoformat()
            if quota.updated_at
            else datetime.utcnow().isoformat(),
        )

    except InvalidQuotaValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except QuotaNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"更新配额失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新配额失败"
        )


@router.post(
    "/reset",
    response_model=QuotaResponse,
    summary="重置配额（管理员）",
    description="管理员重置指定用户的配额。需要管理员权限。",
)
async def reset_quota(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> QuotaResponse:
    """
    重置用户配额（管理员功能）

    将指定用户的已使用配额清零，更新重置日期。

    Args:
        user_id: 要重置配额的用户ID
        current_user: 当前管理员用户
        db: 数据库会话

    Returns:
        QuotaResponse: 重置后的配额信息

    Raises:
        HTTPException 403: 无管理员权限
        HTTPException 404: 用户不存在
        HTTPException 500: 重置失败
    """
    quota_service = QuotaService(db)

    try:
        quota = quota_service.reset_monthly_quota(user_id)

        logger.info(f"管理员 {current_user.username} 重置用户 {user_id} 的配额")

        return QuotaResponse(
            monthly_quota=quota.monthly_quota,
            used_quota=quota.used_quota,
            remaining_quota=quota.remaining_quota,
            reset_date=quota.reset_date.isoformat(),
            usage_percentage=quota.usage_percentage,
        )

    except QuotaNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"重置配额失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="重置配额失败"
        )


# 导出
__all__ = ["router"]
