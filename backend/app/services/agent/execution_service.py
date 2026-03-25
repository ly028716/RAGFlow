"""
Agent 任务执行服务模块

实现 Agent 任务的执行功能（普通执行和流式执行）。
"""

import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy.orm import Session

from app.langchain_integration.agent_executor import AgentManager
from app.models.agent_execution import AgentExecution, ExecutionStatus
from app.repositories.agent_repository import AgentExecutionRepository
from app.websocket.connection_manager import connection_manager

logger = logging.getLogger(__name__)


class TaskExecutionService:
    """
    Agent 任务执行服务类

    提供任务的执行功能（普通执行和流式执行）。

    使用方式:
        service = TaskExecutionService(db)
        result = await service.execute(user_id=1, task="计算 2+2")
        async for event in service.stream_execute(user_id=1, task="计算 2+2"):
            print(event)
    """

    def __init__(self, db: Session):
        """
        初始化任务执行服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self.execution_repo = AgentExecutionRepository(db)
        self.agent_manager = AgentManager()

    async def execute(
        self,
        user_id: int,
        task: str,
        tool_ids: Optional[List[int]] = None,
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
        """
        执行Agent任务

        Args:
            user_id: 用户ID
            task: 任务描述
            tool_ids: 要使用的工具ID列表（可选，默认使用所有启用的工具）
            max_iterations: 最大迭代次数

        Returns:
            执行结果字典
        """
        try:
            logger.info(f"用户 {user_id} 开始执行Agent任务: {task}")

            # 创建执行记录
            execution = self.execution_repo.create(
                user_id=user_id, task=task, status=ExecutionStatus.PENDING
            )

            # 通过WebSocket通知任务创建
            try:
                await connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "agent_task_created",
                        "data": {
                            "execution_id": execution.id,
                            "task": task,
                            "status": ExecutionStatus.PENDING.value,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    },
                )
            except Exception as e:
                logger.warning(f"WebSocket通知失败: {str(e)}")

            # 设置状态为执行中
            self.execution_repo.set_running(execution.id)

            # 通过WebSocket通知任务开始执行
            try:
                await connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "agent_task_started",
                        "data": {
                            "execution_id": execution.id,
                            "status": ExecutionStatus.RUNNING.value,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    },
                )
            except Exception as e:
                logger.warning(f"WebSocket通知失败: {str(e)}")

            # 执行任务
            result = await self.agent_manager.execute_task(
                task=task, tool_ids=tool_ids, max_iterations=max_iterations
            )

            # 更新执行记录
            if result["status"] == "completed":
                self.execution_repo.update(
                    execution.id,
                    status=ExecutionStatus.COMPLETED,
                    result=result["result"],
                    steps=result["steps"],
                    completed_at=datetime.utcnow(),
                )

                # 通过WebSocket通知任务完成
                try:
                    await connection_manager.send_personal_message(
                        user_id,
                        {
                            "type": "agent_task_completed",
                            "data": {
                                "execution_id": execution.id,
                                "result": result["result"],
                                "status": ExecutionStatus.COMPLETED.value,
                                "step_count": len(result["steps"]),
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                        },
                    )
                except Exception as e:
                    logger.warning(f"WebSocket通知失败: {str(e)}")
            else:
                self.execution_repo.update(
                    execution.id,
                    status=ExecutionStatus.FAILED,
                    error_message=result.get("error", "未知错误"),
                    steps=result["steps"],
                    completed_at=datetime.utcnow(),
                )

                # 通过WebSocket通知任务失败
                try:
                    await connection_manager.send_personal_message(
                        user_id,
                        {
                            "type": "agent_task_failed",
                            "data": {
                                "execution_id": execution.id,
                                "error": result.get("error", "未知错误"),
                                "status": ExecutionStatus.FAILED.value,
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                        },
                    )
                except Exception as e:
                    logger.warning(f"WebSocket通知失败: {str(e)}")

            # 获取更新后的执行记录
            updated_execution = self.execution_repo.get_by_id(execution.id)

            logger.info(
                f"Agent任务执行完成: execution_id={execution.id}, status={result['status']}"
            )

            return {
                "execution_id": updated_execution.id,
                "task": updated_execution.task,
                "result": updated_execution.result,
                "steps": updated_execution.steps or [],
                "status": updated_execution.status.value,
                "error_message": updated_execution.error_message,
                "created_at": updated_execution.created_at.isoformat(),
                "completed_at": updated_execution.completed_at.isoformat()
                if updated_execution.completed_at
                else None,
            }

        except Exception as e:
            logger.error(f"Agent任务执行失败: {str(e)}", exc_info=True)

            # 如果执行记录已创建，更新为失败状态
            if "execution" in locals():
                self.execution_repo.set_failed(execution.id, error_message=str(e))

            raise

    async def stream_execute(
        self,
        user_id: int,
        task: str,
        tool_ids: Optional[List[int]] = None,
        max_iterations: int = 10,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式执行Agent任务

        Args:
            user_id: 用户ID
            task: 任务描述
            tool_ids: 要使用的工具ID列表
            max_iterations: 最大迭代次数

        Yields:
            执行过程中的事件字典
        """
        try:
            logger.info(f"用户 {user_id} 开始流式执行Agent任务: {task}")

            # 创建执行记录
            execution = self.execution_repo.create(
                user_id=user_id, task=task, status=ExecutionStatus.PENDING
            )

            # 发送执行记录创建事件
            yield {
                "type": "created",
                "data": {
                    "execution_id": execution.id,
                    "task": task,
                    "status": ExecutionStatus.PENDING.value,
                },
            }

            # 设置状态为执行中
            self.execution_repo.set_running(execution.id)

            yield {
                "type": "status",
                "data": {
                    "execution_id": execution.id,
                    "status": ExecutionStatus.RUNNING.value,
                },
            }

            # 流式执行任务
            async for event in self.agent_manager.stream_execute_task(
                task=task, tool_ids=tool_ids, max_iterations=max_iterations
            ):
                # 如果是步骤事件，更新数据库
                if event["type"] == "step":
                    self.execution_repo.add_step(execution.id, event["data"])

                    # 通过WebSocket通知步骤更新
                    try:
                        await connection_manager.send_personal_message(
                            user_id,
                            {
                                "type": "agent_step",
                                "data": {
                                    "execution_id": execution.id,
                                    "step": event["data"],
                                    "timestamp": datetime.utcnow().isoformat(),
                                },
                            },
                        )
                    except Exception as e:
                        logger.warning(f"WebSocket步骤通知失败: {str(e)}")
                elif event["type"] == "error":
                    event = {
                        "type": "error",
                        "data": {
                            "execution_id": execution.id,
                            "message": "任务执行失败",
                        },
                    }

                # 转发事件给客户端
                yield event

            # 获取最终执行记录
            final_execution = self.execution_repo.get_by_id(execution.id)

            logger.info(f"Agent流式任务执行完成: execution_id={execution.id}")

        except Exception as e:
            logger.error(f"Agent流式任务执行失败: {str(e)}", exc_info=True)

            # 如果执行记录已创建，更新为失败状态
            if "execution" in locals():
                self.execution_repo.set_failed(execution.id, error_message=str(e))

            yield {
                "type": "error",
                "data": {
                    "execution_id": execution.id if "execution" in locals() else None,
                    "message": "任务执行失败",
                },
            }


__all__ = [
    "TaskExecutionService",
]
