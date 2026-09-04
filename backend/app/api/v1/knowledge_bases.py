"""
知识库API路由

提供知识库的CRUD操作端点。

需求引用:
    - 需求3.1: 用户创建知识库且提供名称和描述
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.knowledge_base import (KnowledgeBaseCreate,
                                        KnowledgeBaseListResponse,
                                        KnowledgeBaseResponse,
                                        KnowledgeBaseUpdate, MessageResponse)
from app.services.rag_service import KnowledgeBaseNotFoundError, RAGService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-bases", tags=["知识库管理"])


@router.post(
    "",
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建知识库",
    description="创建新的知识库，用于存储和管理文档。",
)
def create_knowledge_base(
    request: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    创建知识库

    需求引用:
        - 需求3.1: 用户创建知识库且提供名称和描述
    """
    service = RAGService(db)

    kb = service.create_knowledge_base(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        category=request.category,
    )

    logger.info(f"用户 {current_user.id} 创建知识库: id={kb.id}, name={kb.name}")

    return KnowledgeBaseResponse(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        category=kb.category,
        document_count=0,
        created_at=kb.created_at,
        updated_at=kb.updated_at,
    )


@router.get(
    "",
    response_model=KnowledgeBaseListResponse,
    summary="获取知识库列表",
    description="获取当前用户的所有知识库列表，支持分页。",
)
def get_knowledge_bases(
    skip: int = Query(default=0, ge=0, description="跳过的记录数"),
    limit: int = Query(default=20, ge=1, le=100, description="返回的最大记录数"),
    keyword: str = Query(default="", max_length=100, description="按名称搜索"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取知识库列表"""
    service = RAGService(db)

    knowledge_bases, total = service.get_knowledge_bases(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        keyword=keyword,
    )

    items = []
    for kb in knowledge_bases:
        items.append(
            KnowledgeBaseResponse(
                id=kb.id,
                name=kb.name,
                description=kb.description,
                category=kb.category,
                document_count=len(kb.documents),
                created_at=kb.created_at,
                updated_at=kb.updated_at,
            )
        )

    return KnowledgeBaseListResponse(total=total, items=items)


@router.get(
    "/{kb_id}",
    response_model=KnowledgeBaseResponse,
    summary="获取知识库详情",
    description="获取指定知识库的详细信息。",
)
def get_knowledge_base(
    kb_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取知识库详情"""
    service = RAGService(db)

    try:
        kb = service.get_knowledge_base(kb_id, current_user.id)
    except KnowledgeBaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库不存在",
        )

    return KnowledgeBaseResponse(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        category=kb.category,
        document_count=len(kb.documents),
        created_at=kb.created_at,
        updated_at=kb.updated_at,
    )


@router.put(
    "/{kb_id}",
    response_model=KnowledgeBaseResponse,
    summary="更新知识库",
    description="更新指定知识库的信息。",
)
def update_knowledge_base(
    kb_id: int,
    request: KnowledgeBaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新知识库"""
    service = RAGService(db)

    try:
        kb = service.update_knowledge_base(
            kb_id=kb_id,
            user_id=current_user.id,
            name=request.name,
            description=request.description,
            category=request.category,
        )
    except KnowledgeBaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库不存在",
        )

    logger.info(f"用户 {current_user.id} 更新知识库: id={kb_id}")

    return KnowledgeBaseResponse(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        category=kb.category,
        document_count=len(kb.documents),
        created_at=kb.created_at,
        updated_at=kb.updated_at,
    )


@router.delete(
    "/{kb_id}",
    response_model=MessageResponse,
    summary="删除知识库",
    description="删除指定知识库及其所有文档和向量数据。",
)
def delete_knowledge_base(
    kb_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除知识库"""
    service = RAGService(db)

    try:
        success = service.delete_knowledge_base(kb_id, current_user.id)
    except KnowledgeBaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库不存在",
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除知识库失败",
        )

    logger.info(f"用户 {current_user.id} 删除知识库: id={kb_id}")

    return MessageResponse(message="知识库删除成功")


# 导出
__all__ = ["router"]
