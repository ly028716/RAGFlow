"""
Agent 服务模块 (Facade)

此模块现在作为 Facade，内部委托给子服务。
所有实际功能已迁移到 app.services.agent 包中的子服务。

推荐使用方式:
    from app.services.agent import ToolService, TaskExecutionService, ExecutionQueryService

向后兼容用法:
    from app.services.agent import AgentService
    service = AgentService(db)  # 内部委托给子服务
"""

from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.agent_execution import ExecutionStatus
from app.models.agent_tool import ToolType

from app.services.agent.execution_query_service import ExecutionQueryService
from app.services.agent.execution_service import TaskExecutionService
from app.services.agent.tool_service import ToolService


class AgentService:
    """
    Agent服务类 (Facade)

    提供Agent工具管理和任务执行的业务逻辑。
    此服务现在作为 Facade，内部委托给子服务。

    向后兼容用法:
        service = AgentService(db)
        tools = service.get_tools(user_id=1)

    推荐新用法:
        from app.services.agent import ToolService, TaskExecutionService
        tool_service = ToolService(db)
        execution_service = TaskExecutionService(db)
    """

    def __init__(self, db: Session):
        """
        初始化Agent服务

        Args:
            db: 数据库会话
        """
        self.db = db
        # 初始化子服务
        self._tool_service = ToolService(db)
        self._execution_service = TaskExecutionService(db)
        self._query_service = ExecutionQueryService(db)

    # ==================== 工具管理 (委托给 ToolService) ====================

    def get_tools(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        tool_type: Optional[ToolType] = None,
        is_enabled: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        return self._tool_service.get_list(
            user_id=user_id, skip=skip, limit=limit,
            tool_type=tool_type, is_enabled=is_enabled
        )

    def get_tools_with_total(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        tool_type: Optional[ToolType] = None,
        is_enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """获取工具列表和总数"""
        return self._tool_service.get_list_with_total(
            user_id=user_id, skip=skip, limit=limit,
            tool_type=tool_type, is_enabled=is_enabled
        )

    def get_tool(self, tool_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """获取单个工具信息"""
        return self._tool_service.get_by_id(tool_id, user_id)

    def create_tool(
        self,
        user_id: int,
        name: str,
        description: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """创建自定义工具"""
        return self._tool_service.create(
            user_id=user_id, name=name, description=description, config=config
        )

    def update_tool(
        self,
        tool_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        is_enabled: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        """更新工具配置"""
        return self._tool_service.update(
            tool_id=tool_id,
            user_id=user_id,
            name=name,
            description=description,
            config=config,
            is_enabled=is_enabled,
        )

    def delete_tool(self, tool_id: int, user_id: int) -> bool:
        """删除工具"""
        return self._tool_service.delete(tool_id, user_id)

    # ==================== 任务执行 (委托给 TaskExecutionService) ====================

    async def execute_task(
        self,
        user_id: int,
        task: str,
        tool_ids: Optional[List[int]] = None,
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
        """执行Agent任务"""
        return await self._execution_service.execute(
            user_id=user_id, task=task, tool_ids=tool_ids, max_iterations=max_iterations
        )

    async def stream_execute_task(
        self,
        user_id: int,
        task: str,
        tool_ids: Optional[List[int]] = None,
        max_iterations: int = 10,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式执行Agent任务"""
        async for event in self._execution_service.stream_execute(
            user_id=user_id, task=task, tool_ids=tool_ids, max_iterations=max_iterations
        ):
            yield event

    # ==================== 执行查询 (委托给 ExecutionQueryService) ====================

    def get_execution(
        self, execution_id: int, user_id: int
    ) -> Optional[Dict[str, Any]]:
        """获取执行记录"""
        return self._query_service.get_by_id(execution_id, user_id)

    def get_user_executions(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        status: Optional[ExecutionStatus] = None,
    ) -> Dict[str, Any]:
        """获取用户的执行历史"""
        return self._query_service.get_user_executions(
            user_id=user_id, skip=skip, limit=limit, status=status
        )


__all__ = [
    "AgentService",
]
