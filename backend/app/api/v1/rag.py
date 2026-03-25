"""
RAG问答API路由

提供基于知识库的智能问答端点。

需求引用:
    - 需求4.1: 用户提交RAG查询请求且指定知识库ID
    - 需求4.2: 向量检索完成，将检索到的文档片段作为上下文传递给通义千问模型生成答案
    - 需求4.3: 在响应中返回生成的答案、相关文档片段、来源文档名称和相似度评分
    - 需求4.4: 用户指定多个知识库ID，在所有指定知识库中进行联合检索
"""

import json
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.langchain_integration.rag_chain import RAGManager, get_rag_manager
from app.middleware.rate_limiter import rate_limit_llm
from app.models.knowledge_base_permission import PermissionType
from app.models.user import User
from app.schemas.knowledge_base import (DocumentChunkResponse, RAGQueryRequest,
                                        RAGQueryResponse)
from app.services.knowledge_base_permission import KnowledgeBasePermissionService
from app.services.quota import QuotaService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG问答"])


@router.post(
    "/query",
    response_model=RAGQueryResponse,
    summary="RAG问答",
    description="基于知识库进行智能问答，支持单个或多个知识库联合检索。",
)
@rate_limit_llm()
async def rag_query(
    request: Request,
    rag_request: RAGQueryRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    RAG问答

    需求引用:
        - 需求4.1: 用户提交RAG查询请求且指定知识库ID
        - 需求4.2: 将检索到的文档片段作为上下文传递给通义千问模型生成答案
        - 需求4.3: 返回生成的答案、相关文档片段、来源文档名称和相似度评分
        - 需求4.4: 在所有指定知识库中进行联合检索
    """
    # 验证知识库权限
    kb_permission_service = KnowledgeBasePermissionService(db)
    for kb_id in rag_request.knowledge_base_ids:
        has_permission, kb = kb_permission_service.check_permission(
            kb_id, current_user.id, PermissionType.VIEWER.value
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库不存在或无权访问: id={kb_id}",
            )

    # 检查配额
    quota_service = QuotaService(db)
    if not quota_service.check_quota(current_user.id, 1000):  # 预估token
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="配额不足，请联系管理员",
        )

    # 执行RAG查询
    rag_manager = get_rag_manager()

    try:
        response = await rag_manager.query(
            knowledge_base_ids=rag_request.knowledge_base_ids,
            question=rag_request.question,
            top_k=rag_request.top_k,
            conversation_id=rag_request.conversation_id,
        )
    except Exception as e:
        logger.error(f"RAG查询失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG查询失败",
        )

    # 扣除配额
    quota_service.consume_quota(current_user.id, response.tokens_used)

    logger.info(
        f"用户 {current_user.id} RAG查询: "
        f"kb_ids={rag_request.knowledge_base_ids}, tokens={response.tokens_used}"
    )

    # 转换响应
    sources = [
        DocumentChunkResponse(
            content=s.content,
            document_name=s.document_name,
            similarity_score=s.similarity_score,
            document_id=s.document_id,
            chunk_index=s.chunk_index,
        )
        for s in response.sources
    ]

    return RAGQueryResponse(
        answer=response.answer,
        sources=sources,
        tokens_used=response.tokens_used,
    )


@router.post(
    "/query/stream",
    summary="RAG流式问答",
    description="基于知识库进行流式智能问答，实时返回生成的答案。",
)
@rate_limit_llm()
async def rag_query_stream(
    request: Request,
    rag_request: RAGQueryRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    RAG流式问答

    使用SSE协议实时推送生成的答案。
    """
    # 验证知识库权限
    kb_permission_service = KnowledgeBasePermissionService(db)
    for kb_id in rag_request.knowledge_base_ids:
        has_permission, kb = kb_permission_service.check_permission(
            kb_id, current_user.id, PermissionType.VIEWER.value
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库不存在或无权访问: id={kb_id}",
            )

    # 检查配额
    quota_service = QuotaService(db)
    if not quota_service.check_quota(current_user.id, 1000):  # 预估token
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="配额不足，请联系管理员",
        )

    async def generate():
        """生成SSE流"""
        rag_manager = get_rag_manager()
        tokens_used = 0

        try:
            async for event in rag_manager.stream_query(
                knowledge_base_ids=rag_request.knowledge_base_ids,
                question=rag_request.question,
                top_k=rag_request.top_k,
                conversation_id=rag_request.conversation_id,
            ):
                event_type = event.get("type")

                if event_type == "sources":
                    # 发送文档片段
                    data = {
                        "type": "sources",
                        "sources": event.get("sources", []),
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

                elif event_type == "token":
                    # 发送文本片段
                    data = {
                        "type": "token",
                        "content": event.get("content", ""),
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

                elif event_type == "done":
                    # 发送完成事件
                    tokens_used = event.get("tokens_used", 0)
                    data = {
                        "type": "done",
                        "content": event.get("content", ""),
                        "tokens_used": tokens_used,
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

                    # 扣除配额
                    quota_service.consume_quota(current_user.id, tokens_used)

                elif event_type == "error":
                    # 发送错误事件
                    data = {
                        "type": "error",
                        "error": "RAG查询失败",
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

            logger.info(
                f"用户 {current_user.id} RAG流式查询完成: "
                f"kb_ids={rag_request.knowledge_base_ids}, tokens={tokens_used}"
            )

        except Exception as e:
            logger.error(f"RAG流式查询失败: {str(e)}")
            error_data = {
                "type": "error",
                "error": "RAG查询失败",
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# 导出
__all__ = ["router"]
