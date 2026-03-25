"""
对话API路由模块

实现对话的CRUD操作端点。

需求引用:
    - 需求2.1: 创建对话并返回唯一对话ID
    - 需求2.4: 查询对话历史，按更新时间倒序排列，支持分页
    - 需求2.5: 软删除对话
    - 需求2.6: 导出对话内容为Markdown或JSON格式
    - 需求2.8: 自动根据消息内容生成对话标题
"""

from datetime import datetime
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.middleware.rate_limiter import rate_limit_api, rate_limit_llm
from app.models.user import User
from app.schemas.conversation import (ConversationCreate,
                                      ConversationDetailResponse,
                                      ConversationListItem,
                                      ConversationListResponse,
                                      ConversationResponse, ConversationUpdate,
                                      DeleteResponse, ExportFormatEnum,
                                      ExportResponse, MessageResponse,
                                      TitleGenerateRequest,
                                      TitleGenerateResponse)
from app.services.conversation import (ConversationNotFoundError,
                                               ConversationService)

router = APIRouter(prefix="/conversations", tags=["对话管理"])
logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建对话",
    description="创建新的对话会话，返回对话ID和基本信息。",
)
@rate_limit_api()
def create_conversation(
    conversation_data: ConversationCreate,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """
    创建对话端点

    需求引用:
        - 需求2.1: 创建对话记录并返回唯一对话ID，默认标题为"新对话"

    Args:
        conversation_data: 对话创建信息
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        ConversationResponse: 创建的对话信息
    """
    service = ConversationService(db)

    conversation = service.create_conversation(
        user_id=current_user.id, title=conversation_data.title
    )

    return ConversationResponse.model_validate(conversation)


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="获取对话列表",
    description="获取当前用户的对话列表，按更新时间倒序排列，支持分页。",
)
@rate_limit_api()
def get_conversations(
    request: Request,
    response: Response,
    skip: int = Query(default=0, ge=0, description="跳过的记录数"),
    limit: int = Query(default=20, ge=1, le=100, description="返回的最大记录数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationListResponse:
    """
    获取对话列表端点

    需求引用:
        - 需求2.4: 返回用户所有未删除的对话列表，按更新时间倒序排列，支持分页查询

    Args:
        skip: 跳过的记录数
        limit: 返回的最大记录数
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        ConversationListResponse: 对话列表和总数
    """
    service = ConversationService(db)

    conversations, total = service.get_conversations(
        user_id=current_user.id, skip=skip, limit=limit
    )

    items = [ConversationListItem(**conv) for conv in conversations]

    return ConversationListResponse(total=total, items=items)


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="获取对话详情",
    description="获取指定对话的详细信息，包括所有消息。",
)
@rate_limit_api()
def get_conversation(
    request: Request,
    response: Response,
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetailResponse:
    """
    获取对话详情端点

    Args:
        conversation_id: 对话ID
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        ConversationDetailResponse: 对话详情，包括消息列表

    Raises:
        HTTPException 404: 对话不存在或无权访问
    """
    service = ConversationService(db)

    try:
        conversation = service.get_conversation(
            conversation_id=conversation_id, user_id=current_user.id
        )

        messages = service.get_messages(
            conversation_id=conversation_id, user_id=current_user.id
        )

        message_responses = [MessageResponse.model_validate(msg) for msg in messages]

        return ConversationDetailResponse(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=message_responses,
        )

    except ConversationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="更新对话",
    description="更新对话标题。",
)
@rate_limit_api()
def update_conversation(
    request: Request,
    response: Response,
    conversation_id: int,
    conversation_data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """
    更新对话端点

    Args:
        conversation_id: 对话ID
        conversation_data: 更新数据
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        ConversationResponse: 更新后的对话信息

    Raises:
        HTTPException 404: 对话不存在或无权访问
    """
    service = ConversationService(db)

    try:
        conversation = service.update_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id,
            title=conversation_data.title,
        )

        return ConversationResponse.model_validate(conversation)

    except ConversationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/{conversation_id}",
    response_model=DeleteResponse,
    summary="删除对话",
    description="软删除对话，将is_deleted标记为true。",
)
@rate_limit_api()
def delete_conversation(
    request: Request,
    response: Response,
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    """
    删除对话端点

    需求引用:
        - 需求2.5: 将对话记录的is_deleted字段标记为true而非物理删除

    Args:
        conversation_id: 对话ID
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        DeleteResponse: 删除成功消息

    Raises:
        HTTPException 404: 对话不存在或无权访问
    """
    service = ConversationService(db)

    try:
        service.delete_conversation(
            conversation_id=conversation_id, user_id=current_user.id
        )

        return DeleteResponse(message="对话删除成功")

    except ConversationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageResponse],
    summary="获取对话消息",
    description="获取指定对话的所有消息，按时间正序排列。",
)
@rate_limit_api()
def get_messages(
    request: Request,
    response: Response,
    conversation_id: int,
    skip: int = Query(default=0, ge=0, description="跳过的记录数"),
    limit: Optional[int] = Query(default=None, ge=1, le=1000, description="返回的最大记录数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MessageResponse]:
    """
    获取对话消息端点

    Args:
        conversation_id: 对话ID
        skip: 跳过的记录数
        limit: 返回的最大记录数
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        list[MessageResponse]: 消息列表

    Raises:
        HTTPException 404: 对话不存在或无权访问
    """
    service = ConversationService(db)

    try:
        messages = service.get_messages(
            conversation_id=conversation_id,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
        )

        return [MessageResponse.model_validate(msg) for msg in messages]

    except ConversationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/{conversation_id}/export",
    response_model=ExportResponse,
    summary="导出对话",
    description="导出对话内容为Markdown或JSON格式。",
)
@rate_limit_api()
def export_conversation(
    request: Request,
    response: Response,
    conversation_id: int,
    format: ExportFormatEnum = Query(
        default=ExportFormatEnum.MARKDOWN, description="导出格式"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExportResponse:
    """
    导出对话端点

    需求引用:
        - 需求2.6: 生成包含所有消息的Markdown或JSON格式文件

    Args:
        conversation_id: 对话ID
        format: 导出格式（markdown或json）
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        ExportResponse: 导出的内容和建议文件名

    Raises:
        HTTPException 404: 对话不存在或无权访问
        HTTPException 400: 不支持的导出格式
    """
    service = ConversationService(db)

    try:
        # 导出对话
        content = service.export_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id,
            format=format.value,
        )

        # 获取对话信息以生成文件名
        conversation = service.get_conversation(
            conversation_id=conversation_id, user_id=current_user.id
        )

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(
            c for c in conversation.title if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        safe_title = safe_title[:50]  # 限制文件名长度

        if format == ExportFormatEnum.MARKDOWN:
            filename = f"{safe_title}_{timestamp}.md"
        else:
            filename = f"{safe_title}_{timestamp}.json"

        return ExportResponse(content=content, format=format.value, filename=filename)

    except ConversationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{conversation_id}/generate-title",
    response_model=TitleGenerateResponse,
    summary="生成对话标题",
    description="使用LLM根据消息内容生成对话标题。",
)
@rate_limit_llm()
async def generate_title(
    conversation_id: int,
    title_request: TitleGenerateRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TitleGenerateResponse:
    """
    生成对话标题端点

    需求引用:
        - 需求2.8: 自动根据消息内容生成对话标题（最多20个字符）

    Args:
        conversation_id: 对话ID
        title_request: 标题生成请求
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        TitleGenerateResponse: 生成的标题

    Raises:
        HTTPException 404: 对话不存在或无权访问
        HTTPException 500: 标题生成失败
    """
    service = ConversationService(db)

    try:
        # 验证对话存在且属于当前用户
        conversation = service.get_conversation(
            conversation_id=conversation_id, user_id=current_user.id
        )

        # 生成标题
        title = await service.generate_title(
            first_message=title_request.message, max_length=20
        )

        # 更新对话标题
        service.update_conversation_title(conversation_id=conversation_id, title=title)

        return TitleGenerateResponse(title=title)

    except ConversationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"标题生成失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="标题生成失败",
        )


# 导出
__all__ = ["router"]
