"""
Agent 执行查询服务模块

实现 Agent 执行记录的查询功能。
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.agent_execution import ExecutionStatus
from app.repositories.agent_repository import AgentExecutionRepository

logger = logging.getLogger(__name__)


class ExecutionQueryService:
    """
    Agent 执行查询服务类

    提供执行记录的查询功能。

    使用方式:
        service = ExecutionQueryService(db)
        execution = service.get_by_id(execution_id=1, user_id=1)
        executions = service.get_user_executions(user_id=1)
    """

    def __init__(self, db: Session):
        """
        初始化执行查询服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self.execution_repo = AgentExecutionRepository(db)

    def get_by_id(
        self, execution_id: int, user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        获取执行记录

        Args:
            execution_id: 执行记录ID
            user_id: 用户ID（用于权限验证）

        Returns:
            执行记录字典，不存在或无权限则返回None
        """
        execution = self.execution_repo.get_by_id_and_user(execution_id, user_id)
        if not execution:
            return None

        return {
            "execution_id": execution.id,
            "task": execution.task,
            "result": execution.result,
            "steps": execution.steps or [],
            "status": execution.status.value,
            "error_message": execution.error_message,
            "created_at": execution.created_at.isoformat(),
            "completed_at": execution.completed_at.isoformat()
            if execution.completed_at
            else None,
        }

    def get_user_executions(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        status: Optional[ExecutionStatus] = None,
    ) -> Dict[str, Any]:
        """
        获取用户的执行历史

        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            status: 状态过滤（pending/running/completed/failed）

        Returns:
            包含执行记录列表和总数的字典
        """
        # 获取执行记录
        executions, total = self.execution_repo.get_user_executions(
            user_id=user_id, skip=skip, limit=limit, status=status
        )

        # 转换为字典格式
        executions_list = []
        for execution in executions:
            executions_list.append(
                {
                    "execution_id": execution.id,
                    "task": execution.task,
                    "result": execution.result,
                    "status": execution.status.value,
                    "error_message": execution.error_message,
                    "step_count": len(execution.steps) if execution.steps else 0,
                    "created_at": execution.created_at.isoformat(),
                    "completed_at": execution.completed_at.isoformat()
                    if execution.completed_at
                    else None,
                }
            )

        return {"total": total, "items": executions_list}


__all__ = [
    "ExecutionQueryService",
]
