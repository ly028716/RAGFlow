"""
Web Scraper API 端点

提供网页采集任务管理的REST API接口
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.web_scraper_task import TaskStatus, ScheduleType
from app.models.web_scraper_log import LogStatus
from app.schemas.web_scraper import (
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskResponse,
    TaskListResponse,
    LogResponse,
    LogListResponse,
    LogStatisticsResponse,
    TaskExecuteResponse,
)
from app.services.web_scraper_service import (
    WebScraperService,
    TaskNotFoundError,
    InvalidTaskConfigError,
    KnowledgeBaseAccessError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/web-scraper", tags=["web-scraper"])


# ==================== 任务管理端点 ====================

@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: TaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    创建网页采集任务

    创建一个新的网页采集任务，支持一次性执行或定时执行。

    **权限要求**: 已认证用户

    **参数说明**:
    - name: 任务名称（必需）
    - url: 目标URL（必需）
    - knowledge_base_id: 目标知识库ID（必需）
    - schedule_type: 调度类型，once-一次性，cron-定时（默认once）
    - cron_expression: Cron表达式（定时任务必需）
    - selector_config: 选择器配置（必需）
    - scraper_config: 采集器配置（可选）

    **返回**: 创建的任务信息
    """
    try:
        service = WebScraperService(db)
        task = service.create_task(
            name=request.name,
            url=request.url,
            knowledge_base_id=request.knowledge_base_id,
            user_id=current_user.id,
            description=request.description,
            url_pattern=request.url_pattern,
            schedule_type=request.schedule_type,
            cron_expression=request.cron_expression,
            selector_config=request.selector_config.model_dump(),
            scraper_config=request.scraper_config.model_dump() if request.scraper_config else None,
        )

        logger.info(f"用户 {current_user.id} 创建采集任务: {task.id}")
        return task

    except InvalidTaskConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except KnowledgeBaseAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"创建采集任务失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建任务失败"
        )


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    status_filter: Optional[TaskStatus] = Query(None, alias="status", description="任务状态过滤"),
    knowledge_base_id: Optional[int] = Query(None, description="知识库ID过滤"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取任务列表

    获取当前用户的网页采集任务列表，支持分页和过滤。

    **权限要求**: 已认证用户

    **查询参数**:
    - status: 任务状态过滤（active/paused/stopped）
    - knowledge_base_id: 知识库ID过滤
    - skip: 跳过数量（分页）
    - limit: 返回数量（分页，最大1000）

    **返回**: 任务列表和总数
    """
    try:
        service = WebScraperService(db)
        tasks = service.list_tasks(
            user_id=current_user.id,
            status=status_filter,
            knowledge_base_id=knowledge_base_id,
            skip=skip,
            limit=limit,
        )

        # 获取总数
        total = service.task_repo.count(
            status=status_filter,
            knowledge_base_id=knowledge_base_id,
            created_by=current_user.id,
        )

        return TaskListResponse(total=total, items=tasks)

    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取任务列表失败"
        )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取任务详情

    获取指定任务的详细信息。

    **权限要求**: 已认证用户，且为任务创建者

    **路径参数**:
    - task_id: 任务ID

    **返回**: 任务详细信息
    """
    try:
        service = WebScraperService(db)
        task = service.get_task(task_id, current_user.id)
        return task

    except TaskNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except KnowledgeBaseAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取任务详情失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取任务详情失败"
        )


@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    request: TaskUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新任务

    更新指定任务的配置信息。

    **权限要求**: 已认证用户，且为任务创建者

    **路径参数**:
    - task_id: 任务ID

    **请求体**: 要更新的字段（所有字段可选）

    **返回**: 更新后的任务信息
    """
    try:
        service = WebScraperService(db)

        # 构建更新数据
        update_data = request.model_dump(exclude_unset=True)

        # 转换嵌套对象为字典
        if "selector_config" in update_data and update_data["selector_config"]:
            update_data["selector_config"] = update_data["selector_config"].model_dump()
        if "scraper_config" in update_data and update_data["scraper_config"]:
            update_data["scraper_config"] = update_data["scraper_config"].model_dump()

        task = service.update_task(task_id, current_user.id, **update_data)

        logger.info(f"用户 {current_user.id} 更新采集任务: {task_id}")
        return task

    except TaskNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InvalidTaskConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except KnowledgeBaseAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"更新任务失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新任务失败"
        )


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    删除任务

    删除指定的网页采集任务。

    **权限要求**: 已认证用户，且为任务创建者

    **路径参数**:
    - task_id: 任务ID

    **返回**: 无内容（204）
    """
    try:
        service = WebScraperService(db)
        success = service.delete_task(task_id, current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除任务失败"
            )

        logger.info(f"用户 {current_user.id} 删除采集任务: {task_id}")
        return None

    except TaskNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except KnowledgeBaseAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"删除任务失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除任务失败"
        )


# ==================== 任务控制端点 ====================

@router.post("/tasks/{task_id}/start", response_model=TaskResponse)
async def start_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    启动任务

    启动指定的网页采集任务。对于定时任务，将添加到调度器。

    **权限要求**: 已认证用户，且为任务创建者

    **路径参数**:
    - task_id: 任务ID

    **返回**: 更新后的任务信息
    """
    try:
        service = WebScraperService(db)
        task = service.start_task(task_id, current_user.id)

        logger.info(f"用户 {current_user.id} 启动采集任务: {task_id}")
        return task

    except TaskNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except KnowledgeBaseAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"启动任务失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="启动任务失败"
        )


@router.post("/tasks/{task_id}/stop", response_model=TaskResponse)
async def stop_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    停止任务

    停止指定的网页采集任务。对于定时任务，将从调度器移除。

    **权限要求**: 已认证用户，且为任务创建者

    **路径参数**:
    - task_id: 任务ID

    **返回**: 更新后的任务信息
    """
    try:
        service = WebScraperService(db)
        task = service.stop_task(task_id, current_user.id)

        logger.info(f"用户 {current_user.id} 停止采集任务: {task_id}")
        return task

    except TaskNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except KnowledgeBaseAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"停止任务失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="停止任务失败"
        )


@router.post("/tasks/{task_id}/pause", response_model=TaskResponse)
async def pause_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    暂停任务

    暂停指定的网页采集任务。对于定时任务，将从调度器移除。

    **权限要求**: 已认证用户，且为任务创建者

    **路径参数**:
    - task_id: 任务ID

    **返回**: 更新后的任务信息
    """
    try:
        service = WebScraperService(db)
        task = service.pause_task(task_id, current_user.id)

        logger.info(f"用户 {current_user.id} 暂停采集任务: {task_id}")
        return task

    except TaskNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except KnowledgeBaseAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"暂停任务失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="暂停任务失败"
        )


@router.post("/tasks/{task_id}/resume", response_model=TaskResponse)
async def resume_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    恢复任务

    恢复指定的网页采集任务。对于定时任务，将重新添加到调度器。

    **权限要求**: 已认证用户，且为任务创建者

    **路径参数**:
    - task_id: 任务ID

    **返回**: 更新后的任务信息
    """
    try:
        service = WebScraperService(db)
        task = service.resume_task(task_id, current_user.id)

        logger.info(f"用户 {current_user.id} 恢复采集任务: {task_id}")
        return task

    except TaskNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except KnowledgeBaseAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"恢复任务失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="恢复任务失败"
        )


@router.post("/tasks/{task_id}/execute", response_model=TaskExecuteResponse)
async def execute_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    立即执行任务

    立即执行指定的网页采集任务一次，不影响定时调度。

    **权限要求**: 已认证用户，且为任务创建者

    **路径参数**:
    - task_id: 任务ID

    **返回**: 执行响应信息
    """
    try:
        service = WebScraperService(db)
        log = await service.execute_once(task_id, current_user.id)

        logger.info(f"用户 {current_user.id} 立即执行采集任务: {task_id}")
        return TaskExecuteResponse(
            task_id=task_id,
            log_id=log.id,
            status=log.status.value,
            message="任务执行完成" if log.status == LogStatus.SUCCESS else "任务执行失败"
        )

    except TaskNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except KnowledgeBaseAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"执行任务失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="执行任务失败"
        )


# ==================== 日志管理端点 ====================

@router.get("/tasks/{task_id}/logs", response_model=LogListResponse)
async def get_task_logs(
    task_id: int,
    status_filter: Optional[LogStatus] = Query(None, alias="status", description="日志状态过滤"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取任务执行日志

    获取指定任务的执行日志列表，支持分页和过滤。

    **权限要求**: 已认证用户，且为任务创建者

    **路径参数**:
    - task_id: 任务ID

    **查询参数**:
    - status: 日志状态过滤（running/success/failed）
    - skip: 跳过数量（分页）
    - limit: 返回数量（分页，最大1000）

    **返回**: 日志列表和总数
    """
    try:
        service = WebScraperService(db)
        logs = service.get_task_logs(
            task_id=task_id,
            user_id=current_user.id,
            status=status_filter,
            skip=skip,
            limit=limit,
        )

        # 获取总数
        total = service.log_repo.count_by_task(
            task_id=task_id,
            status=status_filter,
        )

        return LogListResponse(total=total, items=logs)

    except TaskNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except KnowledgeBaseAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取任务日志失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取任务日志失败"
        )


@router.get("/tasks/{task_id}/statistics", response_model=LogStatisticsResponse)
async def get_task_statistics(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取任务统计信息

    获取指定任务的执行统计信息，包括总执行次数、成功率等。

    **权限要求**: 已认证用户，且为任务创建者

    **路径参数**:
    - task_id: 任务ID

    **返回**: 统计信息
    """
    try:
        service = WebScraperService(db)
        statistics = service.get_log_statistics(task_id, current_user.id)

        return LogStatisticsResponse(**statistics)

    except TaskNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except KnowledgeBaseAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取任务统计信息失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取任务统计信息失败"
        )
