"""
聊天API路由模块

实现聊天功能端点，支持流式和非流式响应。

需求引用:
    - 需求2.2: 调用通义千问API生成回复并存储消息
    - 需求2.3: 使用SSE协议实时推送AI生成的文本片段，首字响应时间小于3秒
    - 需求2.7: 记录消耗的token数量
    - 需求11.2: 检查用户的剩余配额是否足够
    - 需求11.3: 配额不足返回403错误
    - 需求11.4: 调用后扣除token并记录到api_usage表
"""

import json
import logging
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import get_db
from app.dependencies import get_current_user
from app.langchain_integration.chains import (ChatConfig, ConversationManager,
                                              get_conversation_manager)
from app.langchain_integration.rag_chain import get_rag_manager
from app.services.enhanced_conversation_service import get_enhanced_conversation_service
from app.middleware.rate_limiter import rate_limit_llm
from app.models.knowledge_base_permission import PermissionType
from app.models.message import MessageRole
from app.models.user import User
from app.schemas.conversation import ChatConfig as ChatConfigSchema
from app.schemas.conversation import ChatRequest, ChatResponse
from app.services.conversation_service import (ConversationNotFoundError,
                                               ConversationService)
from app.services.knowledge_base_permission_service import \
    KnowledgeBasePermissionService
from app.services.quota_service import InsufficientQuotaError, QuotaService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["聊天"])


def _convert_chat_config(config: Optional[ChatConfigSchema]) -> ChatConfig:
    """
    转换ChatConfig schema到ChatConfig对象

    Args:
        config: ChatConfig schema对象

    Returns:
        ChatConfig: 对话配置对象
    """
    if config is None:
        return ChatConfig()

    return ChatConfig(
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        mode=config.mode.value,
    )


def _get_message_history(
    service: ConversationService, conversation_id: int, user_id: int, limit: int = 10
) -> list[dict]:
    """
    获取对话历史消息

    Args:
        service: 对话服务
        conversation_id: 对话ID
        user_id: 用户ID
        limit: 最大消息数

    Returns:
        list[dict]: 消息历史列表
    """
    messages = service.get_recent_messages(
        conversation_id=conversation_id, user_id=user_id, limit=limit
    )

    return [{"role": msg.role.value, "content": msg.content} for msg in messages]


@router.post(
    "", response_model=ChatResponse, summary="发送消息（非流式）", description="发送消息到对话，返回AI回复。"
)
@rate_limit_llm()
async def chat(
    chat_request: ChatRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    """
    非流式聊天端点

    需求引用:
        - 需求2.2: 调用通义千问API生成回复并将用户消息和AI回复存储到消息表
        - 需求2.7: 记录消耗的token数量到消息表
        - 需求11.2: 检查用户的剩余配额是否足够
        - 需求11.3: 配额不足返回403错误
        - 需求11.4: 调用后扣除token并记录到api_usage表

    Args:
        chat_request: 聊天请求
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        ChatResponse: AI回复

    Raises:
        HTTPException 403: 配额不足
        HTTPException 404: 对话不存在或无权访问
        HTTPException 500: LLM调用失败
    """
    service = ConversationService(db)
    quota_service = QuotaService(db)
    manager = get_conversation_manager()

    try:
        # 检查用户配额（预估需要一定的token）
        # 使用配置的max_tokens作为预估值
        estimated_tokens = (
            chat_request.config.max_tokens if chat_request.config else 2000
        )
        if not quota_service.check_quota(current_user.id, estimated_tokens):
            quota_info = quota_service.get_quota_info(current_user.id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "配额不足，无法进行对话",
                    "remaining_quota": quota_info["remaining_quota"],
                    "reset_date": quota_info["reset_date"],
                },
            )

        # 验证对话存在
        conversation = service.get_conversation(
            conversation_id=chat_request.conversation_id, user_id=current_user.id
        )

        # 获取历史消息
        history = _get_message_history(
            service=service,
            conversation_id=chat_request.conversation_id,
            user_id=current_user.id,
        )

        # 保存用户消息
        user_message = service.add_message(
            conversation_id=chat_request.conversation_id,
            user_id=current_user.id,
            role=MessageRole.USER,
            content=chat_request.content,
            tokens=0,
        )

        # 转换配置
        config = _convert_chat_config(chat_request.config)

        # 调用LLM、RAG或增强型对话
        if chat_request.config and chat_request.config.mode.value == "enhanced":
            # 使用增强型对话服务（结合OpenClaw Agent和RAG）
            enhanced_service = get_enhanced_conversation_service()
            enhanced_response = await enhanced_service.chat(
                question=chat_request.content,
                knowledge_base_ids=chat_request.knowledge_base_ids,
                conversation_id=str(chat_request.conversation_id),
                chat_history=history,
            )
            response_content = enhanced_response.get("answer", "")
            tokens_used = enhanced_response.get("tokens_used", 0)
        elif chat_request.knowledge_base_ids:
            # 批量验证知识库权限
            kb_permission_service = KnowledgeBasePermissionService(db)
            has_permission, failed_ids = kb_permission_service.check_permissions_batch(
                chat_request.knowledge_base_ids, current_user.id, PermissionType.VIEWER.value
            )
            
            if not has_permission:
                # detail中的消息会被error_handler处理
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": f"知识库不存在或无权访问: ids={failed_ids}"},
                )

            rag_manager = get_rag_manager()
            rag_response = await rag_manager.query(
                knowledge_base_ids=chat_request.knowledge_base_ids,
                question=chat_request.content,
                conversation_id=str(chat_request.conversation_id)
                if chat_request.conversation_id
                else None,
                chat_history=history,
            )
            response_content = rag_response.answer
            tokens_used = rag_response.tokens_used
        else:
            response_content, tokens_used = await manager.chat(
                conversation_id=chat_request.conversation_id,
                message=chat_request.content,
                config=config,
                history=history,
            )

        # 保存AI回复
        ai_message = service.add_message(
            conversation_id=chat_request.conversation_id,
            user_id=current_user.id,
            role=MessageRole.ASSISTANT,
            content=response_content,
            tokens=tokens_used,
        )

        # 扣除配额并记录API使用
        try:
            quota_service.consume_quota(
                user_id=current_user.id, tokens_used=tokens_used, api_type="chat"
            )
        except InsufficientQuotaError:
            # 如果在调用后配额不足，仍然返回结果，但记录警告
            logger.warning(f"用户 {current_user.id} 配额不足，但已完成本次调用")

        return ChatResponse(
            message_id=ai_message.id, content=response_content, tokens_used=tokens_used
        )

    except ConversationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException:
        # 重新抛出HTTP异常（如403配额不足）
        raise
    except Exception as e:
        logger.exception(f"聊天失败: {str(e)}")
        error_message = "聊天服务暂时不可用"
        if settings.debug:
            msg = str(e).strip()
            if msg:
                api_key = settings.tongyi.dashscope_api_key
                if api_key and api_key in msg:
                    msg = msg.replace(api_key, "***")
                error_message = msg
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_message,
        )


@router.post(
    "/stream",
    summary="发送消息（流式）",
    description="发送消息到对话，使用SSE协议流式返回AI回复。如果conversation_id为null，将自动创建新对话。",
)
@rate_limit_llm()
async def stream_chat(
    chat_request: ChatRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    流式聊天端点

    使用Server-Sent Events (SSE)协议实时推送AI生成的文本片段。
    支持自动创建新对话（当conversation_id为null时）。

    需求引用:
        - 需求2.3: 使用SSE协议实时推送AI生成的文本片段，首字响应时间小于3秒
        - 需求2.7: 记录消耗的token数量到消息表
        - 需求11.2: 检查用户的剩余配额是否足够
        - 需求11.3: 配额不足返回403错误
        - 需求11.4: 调用后扣除token并记录到api_usage表

    事件格式:
        - conversation事件: data: {"type": "conversation", "conversation_id": 123}
        - token事件: data: {"type": "token", "content": "文本片段"}
        - 完成事件: data: {"type": "done", "message_id": 123, "tokens_used": 150}
        - 错误事件: data: {"type": "error", "error": "错误信息"}

    Args:
        chat_request: 聊天请求
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        StreamingResponse: SSE流式响应

    Raises:
        HTTPException 403: 配额不足
        HTTPException 404: 对话不存在或无权访问
    """
    service = ConversationService(db)
    quota_service = QuotaService(db)
    manager = get_conversation_manager()

    # 检查用户配额
    estimated_tokens = chat_request.config.max_tokens if chat_request.config else 2000
    if not quota_service.check_quota(current_user.id, estimated_tokens):
        quota_info = quota_service.get_quota_info(current_user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "配额不足，无法进行对话",
                "remaining_quota": quota_info["remaining_quota"],
                "reset_date": quota_info["reset_date"],
            },
        )

    # 如果指定了知识库，验证权限
    if chat_request.knowledge_base_ids:
        kb_permission_service = KnowledgeBasePermissionService(db)
        has_permission, failed_ids = kb_permission_service.check_permissions_batch(
            chat_request.knowledge_base_ids, current_user.id, PermissionType.VIEWER.value
        )
        if not has_permission:
            # detail中的消息会被error_handler处理
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": f"知识库不存在或无权访问: ids={failed_ids}"},
            )

    # 处理对话ID：如果为null则创建新对话
    conversation_id = chat_request.conversation_id
    is_new_conversation = False

    if conversation_id is None:
        # 创建新对话
        conversation = service.create_conversation(user_id=current_user.id, title="新对话")
        conversation_id = conversation.id
        is_new_conversation = True
        logger.info(f"自动创建新对话: {conversation_id}")
    else:
        # 验证对话存在
        try:
            conversation = service.get_conversation(
                conversation_id=conversation_id, user_id=current_user.id
            )
        except ConversationNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # 获取历史消息
    history = _get_message_history(
        service=service, conversation_id=conversation_id, user_id=current_user.id
    )

    # 检查是否是第一条用户消息（用于自动生成标题）
    is_first_message = is_new_conversation or service.is_first_user_message(
        conversation_id
    )

    # 保存用户消息
    user_message = service.add_message(
        conversation_id=conversation_id,
        user_id=current_user.id,
        role=MessageRole.USER,
        content=chat_request.content,
        tokens=0,
    )

    # 如果是第一条用户消息，自动生成标题
    if is_first_message:
        try:
            title = service.generate_title_sync(
                first_message=chat_request.content, max_length=20
            )
            service.update_conversation_title(
                conversation_id=conversation_id, title=title
            )
            logger.info(f"自动生成对话标题: {title}")
        except Exception as e:
            logger.error(f"自动生成标题失败: {str(e)}")
            # 标题生成失败不影响对话继续

    # 转换配置
    config = _convert_chat_config(chat_request.config)

    # 保存用户ID和对话ID用于流式响应中的配额扣除
    user_id = current_user.id
    final_conversation_id = conversation_id
    request_id = getattr(request.state, "request_id", None)

    async def generate_stream() -> AsyncGenerator[str, None]:
        """生成SSE流"""
        full_response = ""
        tokens_used = 0

        # 如果是新对话，先发送对话ID
        if is_new_conversation:
            yield f"data: {json.dumps({'type': 'conversation', 'conversation_id': final_conversation_id}, ensure_ascii=False)}\n\n"

        try:
            stream_generator = None
            if chat_request.config and chat_request.config.mode.value == "enhanced":
                # 使用增强型对话服务（结合OpenClaw Agent和RAG）
                enhanced_service = get_enhanced_conversation_service()
                stream_generator = enhanced_service.stream_chat(
                    question=chat_request.content,
                    knowledge_base_ids=chat_request.knowledge_base_ids,
                    conversation_id=str(final_conversation_id),
                    chat_history=history,
                )
            elif chat_request.knowledge_base_ids:
                rag_manager = get_rag_manager()
                stream_generator = rag_manager.stream_query(
                    knowledge_base_ids=chat_request.knowledge_base_ids,
                    question=chat_request.content,
                    conversation_id=str(final_conversation_id),
                    chat_history=history,
                )
            else:
                stream_generator = manager.stream_chat(
                    conversation_id=final_conversation_id,
                    message=chat_request.content,
                    config=config,
                    history=history,
                )

            async for event in stream_generator:
                event_type = event.get("type", "")

                if event_type == "sources":
                    # 发送引用源信息
                    sources = event.get("sources", [])
                    if sources:
                        yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"

                elif event_type == "token":
                    content = event.get("content", "")
                    full_response += content
                    yield f"data: {json.dumps({'type': 'token', 'content': content}, ensure_ascii=False)}\n\n"

                elif event_type == "done":
                    tokens_used = event.get("tokens_used", 0)

                    # 保存AI回复到数据库并扣除配额
                    # 注意：这里需要新的数据库会话，因为流式响应可能跨越多个请求周期
                    try:
                        from app.core.database import SessionLocal

                        with SessionLocal() as new_db:
                            new_service = ConversationService(new_db)
                            new_quota_service = QuotaService(new_db)

                            # 保存AI回复
                            ai_message = new_service.add_message(
                                conversation_id=final_conversation_id,
                                user_id=user_id,
                                role=MessageRole.ASSISTANT,
                                content=full_response,
                                tokens=tokens_used,
                            )
                            message_id = ai_message.id

                            # 扣除配额并记录API使用
                            try:
                                new_quota_service.consume_quota(
                                    user_id=user_id,
                                    tokens_used=tokens_used,
                                    api_type="chat",
                                )
                            except InsufficientQuotaError:
                                # 如果在调用后配额不足，仍然返回结果，但记录警告
                                logger.warning(f"用户 {user_id} 配额不足，但已完成本次调用")
                    except Exception as save_error:
                        logger.error(f"保存AI回复失败: {str(save_error)}")
                        message_id = 0

                    yield f"data: {json.dumps({'type': 'done', 'message_id': message_id, 'tokens_used': tokens_used, 'conversation_id': final_conversation_id}, ensure_ascii=False)}\n\n"

                elif event_type == "error":
                    error_message = event.get("error") or "聊天服务暂时不可用"
                    yield f"data: {json.dumps({'type': 'error', 'error': error_message, 'request_id': request_id}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.exception(f"流式聊天失败: {str(e)} [request_id={request_id}]")
            error_message = "聊天服务暂时不可用"
            if settings.debug:
                msg = str(e).strip()
                if msg:
                    api_key = settings.tongyi.dashscope_api_key
                    if api_key and api_key in msg:
                        msg = msg.replace(api_key, "***")
                    error_message = msg
            yield f"data: {json.dumps({'type': 'error', 'error': error_message, 'request_id': request_id}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用nginx缓冲
        },
    )


# 导出
__all__ = ["router"]
