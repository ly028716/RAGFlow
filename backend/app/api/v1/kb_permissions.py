"""
知识库权限API路由

提供知识库权限管理端点。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.knowledge_base_permission import PermissionType
from app.models.user import User
from app.schemas.knowledge_base_permission import (PermissionCreate,
                                                   PermissionListResponse,
                                                   PermissionResponse,
                                                   PermissionUpdate,
                                                   ShareKnowledgeBaseRequest,
                                                   VisibilityResponse,
                                                   VisibilityUpdate)
from app.services.knowledge_base_permission import KnowledgeBasePermissionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-bases", tags=["知识库权限"])


@router.get(
    "/{kb_id}/permissions",
    response_model=PermissionListResponse,
    summary="获取权限列表",
    description="获取知识库的权限列表。所有者可以看到所有权限，其他用户只能看到自己的权限。",
)
def get_permissions(
    kb_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PermissionListResponse:
    """获取权限列表"""
    service = KnowledgeBasePermissionService(db)
    permissions, total = service.get_permissions(kb_id, current_user.id)

    return PermissionListResponse(
        items=[PermissionResponse(**p) for p in permissions], total=total
    )


@router.post(
    "/{kb_id}/permissions",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="添加权限",
    description="为知识库添加用户权限（仅所有者可操作）。",
)
def add_permission(
    kb_id: int,
    data: PermissionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PermissionResponse:
    """添加权限"""
    service = KnowledgeBasePermissionService(db)
    permission = service.add_permission(kb_id, current_user.id, data)

    if not permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作或用户不存在")

    # 获取用户名
    user = (
        db.query(User).filter(User.id == permission.user_id).first()
        if permission.user_id
        else None
    )

    return PermissionResponse(
        id=permission.id,
        knowledge_base_id=permission.knowledge_base_id,
        user_id=permission.user_id,
        username=user.username if user else None,
        permission_type=permission.permission_type,
        is_public=permission.is_public,
        created_at=permission.created_at,
    )


@router.put(
    "/{kb_id}/permissions/{permission_id}",
    response_model=PermissionResponse,
    summary="更新权限",
    description="更新知识库的用户权限（仅所有者可操作）。",
)
def update_permission(
    kb_id: int,
    permission_id: int,
    data: PermissionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PermissionResponse:
    """更新权限"""
    service = KnowledgeBasePermissionService(db)
    permission = service.update_permission(kb_id, permission_id, current_user.id, data)

    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="权限不存在或无权操作")

    # 获取用户名
    user = (
        db.query(User).filter(User.id == permission.user_id).first()
        if permission.user_id
        else None
    )

    return PermissionResponse(
        id=permission.id,
        knowledge_base_id=permission.knowledge_base_id,
        user_id=permission.user_id,
        username=user.username if user else None,
        permission_type=permission.permission_type,
        is_public=permission.is_public,
        created_at=permission.created_at,
    )


@router.delete(
    "/{kb_id}/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除权限",
    description="删除知识库的用户权限（仅所有者可操作）。",
)
def delete_permission(
    kb_id: int,
    permission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除权限"""
    service = KnowledgeBasePermissionService(db)
    success = service.delete_permission(kb_id, permission_id, current_user.id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="权限不存在或无权操作")


@router.post(
    "/{kb_id}/share",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="分享知识库",
    description="通过用户名分享知识库（仅所有者可操作）。",
)
def share_knowledge_base(
    kb_id: int,
    data: ShareKnowledgeBaseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PermissionResponse:
    """分享知识库"""
    service = KnowledgeBasePermissionService(db)
    permission = service.share_by_username(
        kb_id=kb_id,
        owner_id=current_user.id,
        username=data.username,
        permission_type=data.permission_type,
    )

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="用户不存在或无权操作"
        )

    return PermissionResponse(
        id=permission.id,
        knowledge_base_id=permission.knowledge_base_id,
        user_id=permission.user_id,
        username=data.username,
        permission_type=permission.permission_type,
        is_public=permission.is_public,
        created_at=permission.created_at,
    )


__all__ = ["router"]
