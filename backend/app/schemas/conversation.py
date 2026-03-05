"""
对话相关的Pydantic模型

定义对话和消息的API请求和响应数据模型。
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class MessageRoleEnum(str, Enum):
    """消息角色枚举"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatModeEnum(str, Enum):
    """对话模式枚举"""

    NORMAL = "normal"
    PROFESSIONAL = "professional"
    CREATIVE = "creative"
    ENHANCED = "enhanced"  # 增强模式：结合OpenClaw Agent和知识库RAG


class ExportFormatEnum(str, Enum):
    """导出格式枚举"""

    MARKDOWN = "markdown"
    JSON = "json"


# ============ 请求模型 ============


class ConversationCreate(BaseModel):
    """创建对话请求模型"""

    title: str = Field(default="新对话", max_length=200, description="对话标题")


class ConversationUpdate(BaseModel):
    """更新对话请求模型"""

    title: str = Field(..., max_length=200, description="对话标题")


class ChatConfig(BaseModel):
    """
    对话配置模型

    用于配置对话的模型参数。
    """

    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数，控制输出随机性")
    max_tokens: int = Field(default=2000, ge=1, le=4000, description="最大输出token数")
    mode: ChatModeEnum = Field(default=ChatModeEnum.NORMAL, description="对话模式")


class ChatRequest(BaseModel):
    """
    聊天请求模型

    用于发送消息到对话。
    如果conversation_id为null，将自动创建新对话。
    """

    conversation_id: Optional[int] = Field(
        default=None, description="对话ID，为null时自动创建新对话", examples=[1, 42, None]
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="消息内容",
        examples=["你好，请介绍一下Python", "什么是机器学习？"],
    )
    knowledge_base_ids: Optional[List[int]] = Field(
        default=None, description="使用的知识库ID列表"
    )
    config: Optional[ChatConfig] = Field(default=None, description="对话配置")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "conversation_id": 1,
                    "content": "你好，请介绍一下Python",
                    "config": {
                        "temperature": 0.7,
                        "max_tokens": 2000,
                        "mode": "normal",
                    },
                },
                {
                    "conversation_id": None,
                    "content": "帮我写一个快速排序算法",
                    "config": {
                        "temperature": 0.3,
                        "max_tokens": 1500,
                        "mode": "professional",
                    },
                },
            ]
        }
    }


class MessageCreate(BaseModel):
    """创建消息请求模型"""

    content: str = Field(..., min_length=1, max_length=10000, description="消息内容")
    config: Optional[ChatConfig] = Field(default=None, description="对话配置")


# ============ 响应模型 ============


class MessageResponse(BaseModel):
    """消息响应模型"""

    id: int = Field(..., description="消息ID")
    conversation_id: int = Field(..., description="对话ID")
    role: MessageRoleEnum = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    tokens: int = Field(default=0, description="消耗的token数量")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    """对话响应模型"""

    id: int = Field(..., description="对话ID")
    title: str = Field(..., description="对话标题")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = {"from_attributes": True}


class ConversationListItem(BaseModel):
    """对话列表项模型"""

    id: int = Field(..., description="对话ID")
    title: str = Field(..., description="对话标题")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    message_count: int = Field(default=0, description="消息数量")


class ConversationListResponse(BaseModel):
    """对话列表响应模型"""

    total: int = Field(..., description="总数")
    items: List[ConversationListItem] = Field(..., description="对话列表")


class ConversationDetailResponse(BaseModel):
    """对话详情响应模型"""

    id: int = Field(..., description="对话ID")
    title: str = Field(..., description="对话标题")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    messages: List[MessageResponse] = Field(default=[], description="消息列表")

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    """聊天响应模型（非流式）"""

    message_id: int = Field(..., description="AI回复消息ID")
    content: str = Field(..., description="AI回复内容")
    tokens_used: int = Field(default=0, description="消耗的token数量")


class StreamTokenEvent(BaseModel):
    """流式token事件模型"""

    type: str = Field(default="token", description="事件类型")
    content: str = Field(..., description="文本片段")


class DocumentChunk(BaseModel):
    """文档片段模型"""
    
    content: str = Field(..., description="文档内容片段")
    document_name: str = Field(..., description="文档名称")
    similarity_score: float = Field(..., description="相似度分数")
    document_id: Optional[int] = Field(default=None, description="文档ID")
    chunk_index: Optional[int] = Field(default=None, description="分块索引")


class StreamSourcesEvent(BaseModel):
    """流式引用源事件模型"""

    type: str = Field(default="sources", description="事件类型")
    sources: List[DocumentChunk] = Field(..., description="引用源列表")


class StreamDoneEvent(BaseModel):
    """流式完成事件模型"""

    type: str = Field(default="done", description="事件类型")
    message_id: int = Field(..., description="AI回复消息ID")
    tokens_used: int = Field(default=0, description="消耗的token数量")


class StreamErrorEvent(BaseModel):
    """流式错误事件模型"""

    type: str = Field(default="error", description="事件类型")
    error: str = Field(..., description="错误信息")


class DeleteResponse(BaseModel):
    """删除响应模型"""

    message: str = Field(..., description="响应消息")


class ExportResponse(BaseModel):
    """导出响应模型"""

    content: str = Field(..., description="导出的内容")
    format: str = Field(..., description="导出格式")
    filename: str = Field(..., description="建议的文件名")


class TitleGenerateRequest(BaseModel):
    """标题生成请求模型"""

    message: str = Field(..., min_length=1, max_length=10000, description="用于生成标题的消息内容")


class TitleGenerateResponse(BaseModel):
    """标题生成响应模型"""

    title: str = Field(..., description="生成的标题")


# 导出
__all__ = [
    # 枚举
    "MessageRoleEnum",
    "ChatModeEnum",
    "ExportFormatEnum",
    # 请求模型
    "ConversationCreate",
    "ConversationUpdate",
    "ChatConfig",
    "ChatRequest",
    "MessageCreate",
    "TitleGenerateRequest",
    # 响应模型
    "MessageResponse",
    "ConversationResponse",
    "ConversationListItem",
    "ConversationListResponse",
    "ConversationDetailResponse",
    "ChatResponse",
    "StreamTokenEvent",
    "StreamSourcesEvent",
    "StreamDoneEvent",
    "StreamErrorEvent",
    "DeleteResponse",
    "ExportResponse",
    "TitleGenerateResponse",
]
