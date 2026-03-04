"""
工具 API 路由模块

提供供外部系统（如 OpenClaw）调用的工具端点。

架构说明:
    飞书 -> OpenClaw (WSL:18789) -> AI智能助手 (FastAPI:8000) -> RAG知识库

    OpenClaw 作为主入口，接收飞书消息
    AI智能助手作为工具服务，提供知识库查询功能
"""

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field
import time

from app.core.database import get_db
from app.services.rag_service import RAGService
from app.services.openclaw_tool_service import OpenClawToolService
from app.models.openclaw_tool_call import CallStatus
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["Tools"])


# ============================================================================
# Pydantic 模型
# ============================================================================

class QueryKnowledgeBaseRequest(BaseModel):
    """知识库查询请求"""
    query: str = Field(..., min_length=1, max_length=1000, description="查询内容")
    knowledge_base_ids: Optional[List[int]] = Field(None, description="知识库ID列表，为空则查询所有")
    top_k: int = Field(5, ge=1, le=20, description="返回结果数量")
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="相似度阈值")

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "什么是 Python？",
                "knowledge_base_ids": [1, 2],
                "top_k": 5,
                "similarity_threshold": 0.7
            }
        }
    }


class DocumentChunk(BaseModel):
    """文档片段"""
    content: str = Field(..., description="文档内容")
    similarity_score: float = Field(..., description="相似度分数")
    document_id: int = Field(..., description="文档ID")
    document_name: str = Field(..., description="文档名称")
    knowledge_base_id: int = Field(..., description="知识库ID")
    knowledge_base_name: str = Field(..., description="知识库名称")


class QueryKnowledgeBaseResponse(BaseModel):
    """知识库查询响应"""
    success: bool = Field(..., description="是否成功")
    query: str = Field(..., description="查询内容")
    results: List[DocumentChunk] = Field(..., description="检索结果")
    total_results: int = Field(..., description="结果总数")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "query": "什么是 Python？",
                "results": [
                    {
                        "content": "Python 是一种高级编程语言...",
                        "similarity_score": 0.92,
                        "document_id": 1,
                        "document_name": "Python 教程.pdf",
                        "knowledge_base_id": 1,
                        "knowledge_base_name": "技术文档"
                    }
                ],
                "total_results": 5
            }
        }
    }


# ============================================================================
# 认证函数
# ============================================================================

def verify_api_token(x_api_token: Optional[str] = Header(None)) -> bool:
    """
    验证 API Token

    用于 OpenClaw 调用时的身份验证

    Args:
        x_api_token: API Token (从请求头获取)

    Returns:
        bool: 验证是否通过

    Raises:
        HTTPException: Token 无效或缺失
    """
    if not x_api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 API Token，请在请求头中提供 X-API-Token"
        )

    # 从配置中获取有效的 API Token
    # 可以配置多个 Token，用逗号分隔
    valid_tokens = settings.openclaw.api_tokens.split(",") if hasattr(settings.openclaw, 'api_tokens') else []

    if not valid_tokens or x_api_token not in valid_tokens:
        logger.warning(f"无效的 API Token: {x_api_token[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Token"
        )

    return True


# ============================================================================
# API 端点
# ============================================================================

@router.post(
    "/query-kb",
    response_model=QueryKnowledgeBaseResponse,
    summary="查询知识库",
    description="供 OpenClaw 调用的知识库查询接口。使用 RAG 检索相关文档片段。"
)
async def query_knowledge_base(
    request: QueryKnowledgeBaseRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_api_token)
) -> QueryKnowledgeBaseResponse:
    """
    查询知识库

    供 OpenClaw Agent 调用的工具端点。
    根据查询内容，从指定的知识库中检索相关文档片段。

    认证方式:
        在请求头中提供 X-API-Token

    Args:
        request: 查询请求
        db: 数据库会话
        _: API Token 验证结果

    Returns:
        QueryKnowledgeBaseResponse: 查询结果

    Raises:
        HTTPException 401: API Token 无效
        HTTPException 404: 知识库不存在
        HTTPException 500: 查询失败
    """
    logger.info(
        f"OpenClaw 调用知识库查询: query='{request.query}', "
        f"kb_ids={request.knowledge_base_ids}, top_k={request.top_k}"
    )

    start_time = time.time()
    tool_service = OpenClawToolService(db)

    # 获取知识库查询工具
    tool = tool_service.get_tool_by_name("query_knowledge_base")
    if not tool:
        logger.warning("知识库查询工具未注册，跳过调用记录")
        tool_id = None
    else:
        tool_id = tool.id

    try:
        # 创建 RAG 服务
        rag_service = RAGService(db)

        # 执行检索
        results = await rag_service.retrieve_documents(
            query=request.query,
            knowledge_base_ids=request.knowledge_base_ids,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold
        )

        # 转换结果格式
        document_chunks = []
        for result in results:
            chunk = DocumentChunk(
                content=result.get("content", ""),
                similarity_score=result.get("similarity_score", 0.0),
                document_id=result.get("document_id", 0),
                document_name=result.get("document_name", ""),
                knowledge_base_id=result.get("knowledge_base_id", 0),
                knowledge_base_name=result.get("knowledge_base_name", "")
            )
            document_chunks.append(chunk)

        execution_time = time.time() - start_time
        logger.info(f"知识库查询成功: 返回 {len(document_chunks)} 个结果, 耗时 {execution_time:.2f}s")

        # 记录工具调用
        if tool_id:
            tool_service.record_tool_call(
                tool_id=tool_id,
                request_params=request.model_dump(),
                response_data={"total_results": len(document_chunks)},
                status=CallStatus.SUCCESS,
                execution_time=execution_time,
            )

        return QueryKnowledgeBaseResponse(
            success=True,
            query=request.query,
            results=document_chunks,
            total_results=len(document_chunks)
        )

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"知识库查询失败: {str(e)}", exc_info=True)

        # 记录失败的工具调用
        if tool_id:
            tool_service.record_tool_call(
                tool_id=tool_id,
                request_params=request.model_dump(),
                status=CallStatus.FAILED,
                error_message=str(e),
                execution_time=execution_time,
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"知识库查询失败: {str(e)}"
        )


__all__ = ["router"]
