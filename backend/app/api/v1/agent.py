"""
Agent API路由模块

实现Agent工具管理和任务执行端点。

需求引用:
    - 需求5.2: 用户创建自定义工具且提供工具名称、描述和配置参数
    - 需求5.3: 用户更新工具配置
    - 需求5.4: 用户禁用工具
    - 需求6.1: 用户提交Agent任务
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.middleware.rate_limiter import rate_limit_api, rate_limit_llm
from app.models.agent_execution import ExecutionStatus
from app.models.agent_tool import ToolType
from app.models.user import User
from app.schemas.agent import (DeleteResponse, ExecutionListItem,
                               ExecutionListResponse, ExecutionResponse,
                               TaskExecuteRequest, ToolCreate,
                               ToolListResponse, ToolResponse, ToolUpdate)
from app.services.agent import AgentService

router = APIRouter(prefix="/agent", tags=["Agent智能代理"])
logger = logging.getLogger(__name__)


# ==================== 工具管理端点 ====================


@router.get(
    "/tools",
    response_model=ToolListResponse,
    summary="获取工具列表",
    description="获取所有可用的Agent工具，包括内置工具和自定义工具。",
)
@rate_limit_api()
def get_tools(
    request: Request,
    response: Response,
    skip: int = Query(default=0, ge=0, description="跳过的记录数"),
    limit: int = Query(default=100, ge=1, le=200, description="返回的最大记录数"),
    tool_type: Optional[ToolType] = Query(
        default=None, description="工具类型过滤（builtin/custom）"
    ),
    is_enabled: Optional[bool] = Query(default=None, description="启用状态过滤"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ToolListResponse:
    """
    获取工具列表端点

    需求引用:
        - 需求5.1: 返回工具列表时包含工具名称、描述、类型和启用状态

    Args:
        skip: 跳过的记录数
        limit: 返回的最大记录数
        tool_type: 工具类型过滤
        is_enabled: 启用状态过滤
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        ToolListResponse: 工具列表和总数
    """
    service = AgentService(db)

    result = service.get_tools_with_total(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        tool_type=tool_type,
        is_enabled=is_enabled,
    )

    return ToolListResponse(
        total=result["total"],
        items=[ToolResponse(**tool) for tool in result["items"]],
    )


@router.get(
    "/tools/{tool_id}",
    response_model=ToolResponse,
    summary="获取工具详情",
    description="获取指定工具的详细信息。",
)
@rate_limit_api()
def get_tool(
    tool_id: int,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ToolResponse:
    """
    获取工具详情端点

    Args:
        tool_id: 工具ID
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        ToolResponse: 工具详细信息

    Raises:
        HTTPException 404: 工具不存在
    """
    service = AgentService(db)

    tool = service.get_tool(tool_id=tool_id, user_id=current_user.id)

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"工具 {tool_id} 不存在"
        )

    return ToolResponse(**tool)


@router.post(
    "/tools",
    response_model=ToolResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建自定义工具",
    description="创建新的自定义工具，提供工具名称、描述和配置参数。",
)
@rate_limit_api()
def create_tool(
    tool_data: ToolCreate,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ToolResponse:
    """
    创建自定义工具端点

    需求引用:
        - 需求5.2: 用户创建自定义工具且提供工具名称、描述和配置参数，
                   在数据库中创建工具记录并设置工具类型为"自定义"

    Args:
        tool_data: 工具创建信息
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        ToolResponse: 创建的工具信息

    Raises:
        HTTPException 400: 工具名称已存在
    """
    service = AgentService(db)

    try:
        tool = service.create_tool(
            user_id=current_user.id,
            name=tool_data.name,
            description=tool_data.description,
            config=tool_data.config,
        )

        return ToolResponse(**tool)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/tools/{tool_id}",
    response_model=ToolResponse,
    summary="更新工具配置",
    description="更新工具的名称、描述、配置参数或启用状态。",
)
@rate_limit_api()
def update_tool(
    tool_id: int,
    tool_data: ToolUpdate,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ToolResponse:
    """
    更新工具配置端点

    需求引用:
        - 需求5.3: 用户更新工具配置，验证配置格式的有效性并更新数据库记录

    Args:
        tool_id: 工具ID
        tool_data: 更新数据
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        ToolResponse: 更新后的工具信息

    Raises:
        HTTPException 404: 工具不存在
        HTTPException 400: 工具名称已被其他工具使用或不能修改内置工具
    """
    service = AgentService(db)

    try:
        tool = service.update_tool(
            tool_id=tool_id,
            user_id=current_user.id,
            name=tool_data.name,
            description=tool_data.description,
            config=tool_data.config,
            is_enabled=tool_data.is_enabled,
        )

        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"工具 {tool_id} 不存在"
            )

        return ToolResponse(**tool)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/tools/{tool_id}",
    response_model=DeleteResponse,
    summary="删除工具",
    description="删除自定义工具（不能删除内置工具）。",
)
@rate_limit_api()
def delete_tool(
    tool_id: int,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    """
    删除工具端点

    Args:
        tool_id: 工具ID
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        DeleteResponse: 删除成功消息

    Raises:
        HTTPException 404: 工具不存在
        HTTPException 400: 不能删除内置工具
    """
    service = AgentService(db)

    try:
        success = service.delete_tool(tool_id=tool_id, user_id=current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"工具 {tool_id} 不存在"
            )

        return DeleteResponse(message="工具删除成功")

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==================== 任务执行端点 ====================


@router.post(
    "/execute",
    response_model=ExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="执行Agent任务",
    description="提交任务给Agent执行，Agent将使用ReAct模式分析任务并调用工具完成任务。",
)
@rate_limit_llm()
async def execute_task(
    task_data: TaskExecuteRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExecutionResponse:
    """
    执行Agent任务端点

    需求引用:
        - 需求6.1: 用户提交Agent任务，Agent服务使用ReAct模式分析任务并生成执行计划
        - 需求6.2: Agent执行计划生成完成后创建执行记录并设置状态为"执行中"
        - 需求6.3: Agent任务执行中，根据推理结果自动选择并调用相应的工具
        - 需求6.4: 记录每个执行步骤的工具名称、输入参数、输出结果和推理过程
        - 需求6.5: Agent任务执行完成，更新执行记录状态为"已完成"并记录最终结果和完成时间
        - 需求6.6: Agent任务执行失败，更新执行记录状态为"失败"并记录错误信息

    Args:
        task_data: 任务执行请求
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        ExecutionResponse: 执行结果

    Raises:
        HTTPException 500: 任务执行失败
    """
    service = AgentService(db)

    try:
        result = await service.execute_task(
            user_id=current_user.id,
            task=task_data.task,
            tool_ids=task_data.tool_ids,
            max_iterations=task_data.max_iterations,
        )

        return ExecutionResponse(**result)

    except Exception as e:
        logger.error(f"任务执行失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="任务执行失败",
        )


@router.post(
    "/execute/stream", summary="流式执行Agent任务", description="流式执行Agent任务，实时返回执行步骤和结果。"
)
@rate_limit_llm()
async def stream_execute_task(
    task_data: TaskExecuteRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    流式执行Agent任务端点

    需求引用:
        - 需求6.7: Agent服务在任务执行过程中实时返回中间步骤信息以支持前端可视化展示

    Args:
        task_data: 任务执行请求
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        StreamingResponse: SSE流式响应
    """
    service = AgentService(db)

    async def event_generator():
        """生成SSE事件"""
        try:
            async for event in service.stream_execute_task(
                user_id=current_user.id,
                task=task_data.task,
                tool_ids=task_data.tool_ids,
                max_iterations=task_data.max_iterations,
            ):
                # 格式化为SSE事件
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"流式任务执行失败: {str(e)}")
            error_event = {"type": "error", "data": {"message": "任务执行失败"}}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ==================== 执行历史查询端点 ====================


@router.get(
    "/executions",
    response_model=ExecutionListResponse,
    summary="获取执行历史",
    description="获取当前用户的Agent任务执行历史，按创建时间倒序排列。",
)
@rate_limit_api()
def get_executions(
    request: Request,
    response: Response,
    skip: int = Query(default=0, ge=0, description="跳过的记录数"),
    limit: int = Query(default=20, ge=1, le=100, description="返回的最大记录数"),
    status: Optional[ExecutionStatus] = Query(
        default=None, description="状态过滤（pending/running/completed/failed）"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExecutionListResponse:
    """
    获取执行历史端点

    Args:
        skip: 跳过的记录数
        limit: 返回的最大记录数
        status: 状态过滤
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        ExecutionListResponse: 执行记录列表和总数
    """
    service = AgentService(db)

    result = service.get_user_executions(
        user_id=current_user.id, skip=skip, limit=limit, status=status
    )

    return ExecutionListResponse(
        total=result["total"],
        items=[ExecutionListItem(**item) for item in result["items"]],
    )


@router.get(
    "/executions/{execution_id}",
    response_model=ExecutionResponse,
    summary="获取执行详情",
    description="获取指定执行记录的详细信息，包括所有执行步骤。",
)
@rate_limit_api()
def get_execution(
    execution_id: int,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExecutionResponse:
    """
    获取执行详情端点

    Args:
        execution_id: 执行记录ID
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        ExecutionResponse: 执行记录详情

    Raises:
        HTTPException 404: 执行记录不存在或无权访问
    """
    service = AgentService(db)

    execution = service.get_execution(
        execution_id=execution_id, user_id=current_user.id
    )

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"执行记录 {execution_id} 不存在或无权访问",
        )

    return ExecutionResponse(**execution)


# 导出
__all__ = ["router"]
