"""
Agent相关的Pydantic模型

定义Agent工具和执行记录的请求/响应模型。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

# ==================== 工具相关模型 ====================


class ToolBase(BaseModel):
    """工具基础模型"""

    name: str = Field(..., min_length=1, max_length=100, description="工具名称")
    description: str = Field(..., min_length=1, max_length=500, description="工具描述")


class ToolCreate(ToolBase):
    """创建工具请求模型"""

    config: Optional[Dict[str, Any]] = Field(default=None, description="工具配置参数")


class ToolUpdate(BaseModel):
    """更新工具请求模型"""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="工具名称")
    description: Optional[str] = Field(
        None, min_length=1, max_length=500, description="工具描述"
    )
    config: Optional[Dict[str, Any]] = Field(None, description="工具配置参数")
    is_enabled: Optional[bool] = Field(None, description="是否启用")


class ToolResponse(ToolBase):
    """工具响应模型"""

    id: int = Field(..., description="工具ID")
    tool_type: str = Field(..., description="工具类型（builtin/custom）")
    config: Optional[Dict[str, Any]] = Field(None, description="工具配置参数")
    is_enabled: bool = Field(..., description="是否启用")
    created_at: str = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class ToolListResponse(BaseModel):
    """工具列表响应模型"""

    total: int = Field(..., description="工具总数")
    items: List[ToolResponse] = Field(..., description="工具列表")


# ==================== 执行相关模型 ====================


class AgentStep(BaseModel):
    """Agent执行步骤模型"""

    step_number: int = Field(..., description="步骤编号")
    thought: str = Field(..., description="思考过程")
    action: str = Field(..., description="执行的动作/工具")
    action_input: Union[Dict[str, Any], str] = Field(..., description="动作输入参数")
    observation: str = Field(..., description="观察结果")
    citations: List[Dict[str, Any]] = Field(default_factory=list, description="检索引用片段")
    citation_count: int = Field(default=0, ge=0, description="引用片段数量")
    phase: Optional[str] = Field(None, description="受限 RAG 工作流阶段")
    data: Dict[str, Any] = Field(default_factory=dict, description="结构化步骤数据和指标")
    timestamp: Optional[str] = Field(None, description="时间戳")


class TaskExecuteRequest(BaseModel):
    """执行任务请求模型"""

    task: str = Field(..., min_length=1, max_length=2000, description="任务描述")
    knowledge_base_ids: Optional[List[int]] = Field(
        default=None, min_length=1, description="Agent 可检索的知识库 ID 范围"
    )
    max_iterations: int = Field(default=10, ge=1, le=50, description="最大迭代次数")


class ExecutionResponse(BaseModel):
    """执行记录响应模型"""

    execution_id: int = Field(..., description="执行记录ID")
    task: str = Field(..., description="任务描述")
    result: Optional[str] = Field(None, description="执行结果")
    steps: List[AgentStep] = Field(default_factory=list, description="执行步骤列表")
    status: str = Field(..., description="执行状态（pending/running/completed/failed）")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: str = Field(..., description="创建时间")
    completed_at: Optional[str] = Field(None, description="完成时间")


class ExecutionListItem(BaseModel):
    """执行记录列表项模型"""

    execution_id: int = Field(..., description="执行记录ID")
    task: str = Field(..., description="任务描述")
    result: Optional[str] = Field(None, description="执行结果")
    status: str = Field(..., description="执行状态")
    error_message: Optional[str] = Field(None, description="错误信息")
    step_count: int = Field(..., description="步骤数量")
    created_at: str = Field(..., description="创建时间")
    completed_at: Optional[str] = Field(None, description="完成时间")


class ExecutionListResponse(BaseModel):
    """执行记录列表响应模型"""

    total: int = Field(..., description="执行记录总数")
    items: List[ExecutionListItem] = Field(..., description="执行记录列表")


class DeleteResponse(BaseModel):
    """删除响应模型"""

    message: str = Field(..., description="删除成功消息")


# 导出
__all__ = [
    "ToolBase",
    "ToolCreate",
    "ToolUpdate",
    "ToolResponse",
    "ToolListResponse",
    "AgentStep",
    "TaskExecuteRequest",
    "ExecutionResponse",
    "ExecutionListItem",
    "ExecutionListResponse",
    "DeleteResponse",
]
