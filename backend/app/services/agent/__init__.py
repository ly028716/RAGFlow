"""
Agent 服务包

提供 Agent 工具管理和任务执行功能。

使用方式:
    from app.services.agent import AgentService
    service = AgentService(db)
    tools = service.get_tools(user_id=1)

或者使用子服务:
    from app.services.agent import ToolService, TaskExecutionService, ExecutionQueryService
    tool_service = ToolService(db)
    execution_service = TaskExecutionService(db)
"""

# 子服务
from app.services.agent.agent_service import AgentService
from app.services.agent.execution_query_service import ExecutionQueryService
from app.services.agent.execution_service import TaskExecutionService
from app.services.agent.tool_service import ToolService

__all__ = [
    # 服务类
    "AgentService",
    "ToolService",
    "TaskExecutionService",
    "ExecutionQueryService",
]
