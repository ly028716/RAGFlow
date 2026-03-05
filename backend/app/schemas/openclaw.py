"""
OpenClaw API Schemas

定义 OpenClaw 相关的请求和响应模型
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OpenClawStatus(str, Enum):
    """OpenClaw 状态枚举"""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class OpenClawHealthResponse(BaseModel):
    """OpenClaw 健康检查响应"""

    status: OpenClawStatus = Field(..., description="健康状态")
    version: Optional[str] = Field(None, description="OpenClaw 版本")
    uptime: Optional[int] = Field(None, description="运行时间（秒）")
    gateway_url: str = Field(..., description="Gateway URL")
    error: Optional[str] = Field(None, description="错误信息（如果不健康）")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "2026.2.6-3",
                "uptime": 3600,
                "gateway_url": "http://localhost:19001",
                "error": None,
            }
        }


class OpenClawMessageRequest(BaseModel):
    """OpenClaw 消息发送请求"""

    message: str = Field(
        ..., min_length=1, max_length=10000, description="消息内容"
    )
    agent_id: Optional[str] = Field("default", description="Agent ID")
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="上下文信息"
    )
    stream: bool = Field(False, description="是否使用流式响应")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "查询产品文档",
                "agent_id": "default",
                "context": {"user_id": 1},
                "stream": False,
            }
        }


class AgentStep(BaseModel):
    """Agent 执行步骤"""

    type: str = Field(..., description="步骤类型: thought, action, observation")
    content: str = Field(..., description="步骤内容")
    timestamp: Optional[str] = Field(None, description="时间戳")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "thought",
                "content": "我需要查询知识库",
                "timestamp": "2026-03-03T12:00:00Z",
            }
        }


class OpenClawMessageResponse(BaseModel):
    """OpenClaw 消息响应"""

    response: str = Field(..., description="Agent 响应内容")
    agent_id: str = Field(..., description="Agent ID")
    execution_time: float = Field(..., description="执行时间（秒）")
    steps: Optional[List[AgentStep]] = Field(None, description="执行步骤（如果有）")

    class Config:
        json_schema_extra = {
            "example": {
                "response": "根据知识库查询结果...",
                "agent_id": "default",
                "execution_time": 1.5,
                "steps": [
                    {
                        "type": "thought",
                        "content": "我需要查询知识库",
                        "timestamp": "2026-03-03T12:00:00Z",
                    }
                ],
            }
        }


# ============================================================================
# 工具注册相关 Schemas
# ============================================================================


class ToolRegisterRequest(BaseModel):
    """工具注册请求"""

    name: str = Field(..., min_length=1, max_length=100, description="工具名称（唯一标识）")
    display_name: str = Field(..., min_length=1, max_length=200, description="工具显示名称")
    description: str = Field(..., min_length=1, description="工具描述")
    endpoint_url: str = Field(..., description="工具端点URL")
    method: str = Field("POST", description="HTTP方法（GET/POST）")
    auth_type: str = Field("api_token", description="认证类型")
    auth_config: Optional[Dict[str, Any]] = Field(None, description="认证配置")
    parameters_schema: Optional[Dict[str, Any]] = Field(None, description="参数Schema")
    response_schema: Optional[Dict[str, Any]] = Field(None, description="响应Schema")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "query_knowledge_base",
                "display_name": "知识库查询",
                "description": "查询指定知识库中的相关文档",
                "endpoint_url": "http://localhost:8000/api/v1/tools/query-kb",
                "method": "POST",
                "auth_type": "api_token",
                "auth_config": {"header_name": "X-API-Token"},
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "kb_id": {"type": "integer"},
                    },
                },
            }
        }


class ToolResponse(BaseModel):
    """工具响应"""

    id: int = Field(..., description="工具ID")
    name: str = Field(..., description="工具名称")
    display_name: str = Field(..., description="工具显示名称")
    description: str = Field(..., description="工具描述")
    endpoint_url: str = Field(..., description="工具端点URL")
    method: str = Field(..., description="HTTP方法")
    auth_type: str = Field(..., description="认证类型")
    status: str = Field(..., description="工具状态")
    is_builtin: bool = Field(..., description="是否为内置工具")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class ToolListResponse(BaseModel):
    """工具列表响应"""

    total: int = Field(..., description="总数")
    items: List[ToolResponse] = Field(..., description="工具列表")


class ToolCallRequest(BaseModel):
    """工具调用请求（知识库查询）"""

    query: str = Field(..., min_length=1, max_length=1000, description="查询内容")
    kb_id: Optional[int] = Field(None, description="知识库ID")
    top_k: int = Field(5, ge=1, le=20, description="返回结果数量")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "如何使用OpenClaw",
                "kb_id": 1,
                "top_k": 5,
            }
        }


class ToolCallResponse(BaseModel):
    """工具调用响应"""

    success: bool = Field(..., description="是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time: float = Field(..., description="执行时间（秒）")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "results": [
                        {
                            "content": "OpenClaw是一个...",
                            "score": 0.95,
                            "metadata": {"source": "doc1.pdf"},
                        }
                    ]
                },
                "error": None,
                "execution_time": 0.5,
            }
        }
