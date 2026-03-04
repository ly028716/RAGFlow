"""
OpenClaw API 端点

提供 OpenClaw Gateway 的健康检查、消息发送和工具管理接口
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.openclaw_client import (
    OpenClawAPIError,
    OpenClawTimeoutError,
    get_openclaw_client,
)
from app.dependencies import get_current_admin_user, get_current_user, get_db
from app.models.user import User
from app.schemas.openclaw import (
    OpenClawHealthResponse,
    OpenClawMessageRequest,
    OpenClawMessageResponse,
    ToolListResponse,
    ToolRegisterRequest,
    ToolResponse,
)
from app.services.openclaw_tool_service import OpenClawToolService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/openclaw", tags=["openclaw"])


@router.get(
    "/health",
    response_model=OpenClawHealthResponse,
    summary="OpenClaw 健康检查",
    description="检查 OpenClaw Gateway 的连接状态和健康信息，无需认证",
)
async def check_openclaw_health() -> OpenClawHealthResponse:
    """
    检查 OpenClaw Gateway 健康状态

    无需认证，任何人都可以调用此接口查看 OpenClaw 的连接状态
    """
    openclaw_client = get_openclaw_client()
    health_info = await openclaw_client.health_check()
    return OpenClawHealthResponse(**health_info)


@router.post(
    "/message",
    response_model=OpenClawMessageResponse,
    summary="发送消息到 OpenClaw Agent",
    description="向 OpenClaw Agent 发送消息并获取响应，需要用户认证",
)
async def send_message_to_openclaw(
    request: OpenClawMessageRequest,
    current_user: User = Depends(get_current_user),
) -> OpenClawMessageResponse:
    """
    发送消息到 OpenClaw Agent

    需要用户认证。消息将被发送到指定的 Agent 进行处理。

    Args:
        request: 消息请求，包含消息内容、Agent ID、上下文等
        current_user: 当前登录用户

    Returns:
        OpenClawMessageResponse: Agent 的响应结果

    Raises:
        HTTPException: 503 - OpenClaw 服务不可用
    """
    logger.info(
        f"用户 {current_user.id} 发送消息到 OpenClaw: "
        f"agent_id={request.agent_id}, message_length={len(request.message)}"
    )

    openclaw_client = get_openclaw_client()

    try:
        response = await openclaw_client.send_message(
            message=request.message,
            agent_id=request.agent_id,
            context=request.context,
            stream=request.stream,
        )
        return OpenClawMessageResponse(**response)

    except OpenClawTimeoutError as e:
        logger.error(f"OpenClaw 请求超时: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"OpenClaw 请求超时: {str(e)}",
        )

    except OpenClawAPIError as e:
        logger.error(f"OpenClaw API 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OpenClaw 服务不可用: {str(e)}",
        )

    except Exception as e:
        logger.error(f"OpenClaw 调用失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"服务器内部错误: {str(e)}",
        )


# ============================================================================
# 工具管理端点
# ============================================================================


@router.post(
    "/tools/register",
    response_model=ToolResponse,
    status_code=status.HTTP_201_CREATED,
    summary="注册OpenClaw工具",
    description="注册新的工具到OpenClaw Gateway，需要管理员权限",
)
async def register_tool(
    request: ToolRegisterRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> ToolResponse:
    """
    注册OpenClaw工具

    将自定义工具注册到系统，供OpenClaw Agent调用。

    Args:
        request: 工具注册请求
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        ToolResponse: 注册的工具信息

    Raises:
        HTTPException 400: 工具名称已存在
        HTTPException 500: 注册失败
    """
    logger.info(f"用户 {current_user.id} 注册工具: {request.name}")

    try:
        tool_service = OpenClawToolService(db)
        tool = tool_service.register_tool(
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            endpoint_url=request.endpoint_url,
            method=request.method,
            auth_type=request.auth_type,
            auth_config=request.auth_config,
            parameters_schema=request.parameters_schema,
            response_schema=request.response_schema,
            created_by=current_user.id,
        )

        return ToolResponse.model_validate(tool)

    except ValueError as e:
        logger.error(f"工具注册失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"工具注册失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"工具注册失败: {str(e)}",
        )


@router.get(
    "/tools",
    response_model=ToolListResponse,
    summary="获取工具列表",
    description="获取已注册的OpenClaw工具列表",
)
async def list_tools(
    status_filter: Optional[str] = None,
    is_builtin: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ToolListResponse:
    """
    获取工具列表

    Args:
        status_filter: 状态过滤（active/inactive/deleted）
        is_builtin: 是否为内置工具
        skip: 跳过数量
        limit: 返回数量
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        ToolListResponse: 工具列表
    """
    try:
        tool_service = OpenClawToolService(db)
        tools = tool_service.list_tools(
            status=status_filter,
            is_builtin=is_builtin,
            skip=skip,
            limit=limit,
        )

        tool_responses = [ToolResponse.model_validate(tool) for tool in tools]
        total = tool_service.tool_repo.count(status=status_filter)

        return ToolListResponse(total=total, items=tool_responses)

    except Exception as e:
        logger.error(f"获取工具列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取工具列表失败: {str(e)}",
        )


@router.get(
    "/tools/{tool_id}",
    response_model=ToolResponse,
    summary="获取工具详情",
    description="获取指定工具的详细信息",
)
async def get_tool(
    tool_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ToolResponse:
    """
    获取工具详情

    Args:
        tool_id: 工具ID
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        ToolResponse: 工具详情

    Raises:
        HTTPException 404: 工具不存在
    """
    try:
        tool_service = OpenClawToolService(db)
        tool = tool_service.get_tool(tool_id)

        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"工具 {tool_id} 不存在",
            )

        return ToolResponse.model_validate(tool)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工具详情失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取工具详情失败: {str(e)}",
        )
