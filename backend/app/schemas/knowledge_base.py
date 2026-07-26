"""
知识库和文档相关的Pydantic模型

定义知识库、文档和RAG查询的请求和响应模型。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# ==================== 知识库相关 ====================


class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求"""

    name: str = Field(..., min_length=1, max_length=100, description="知识库名称")
    description: Optional[str] = Field(None, max_length=500, description="知识库描述")
    category: Optional[str] = Field(None, max_length=50, description="知识库分类")


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求"""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="知识库名称")
    description: Optional[str] = Field(None, max_length=500, description="知识库描述")
    category: Optional[str] = Field(None, max_length=50, description="知识库分类")


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""

    id: int = Field(..., description="知识库ID")
    name: str = Field(..., description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")
    category: Optional[str] = Field(None, description="知识库分类")
    document_count: int = Field(0, description="文档数量")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应"""

    total: int = Field(..., description="总数")
    items: List[KnowledgeBaseResponse] = Field(..., description="知识库列表")


# ==================== 文档相关 ====================


class DocumentResponse(BaseModel):
    """文档响应"""

    id: int = Field(..., description="文档ID")
    knowledge_base_id: int = Field(..., description="知识库ID")
    filename: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    file_type: str = Field(..., description="文件类型")
    status: str = Field(..., description="处理状态")
    chunk_count: int = Field(0, description="分块数量")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应"""

    total: int = Field(..., description="总数")
    items: List[DocumentResponse] = Field(..., description="文档列表")


class DocumentStatusResponse(BaseModel):
    """文档状态响应"""

    document_id: int = Field(..., description="文档ID")
    status: str = Field(..., description="处理状态")
    progress: int = Field(..., ge=0, le=100, description="处理进度（0-100）")
    chunk_count: int = Field(0, description="分块数量")
    error_message: Optional[str] = Field(None, description="错误信息")


class DocumentPreviewResponse(BaseModel):
    """文档预览响应"""

    document_id: int = Field(..., description="文档ID")
    filename: str = Field(..., description="文件名")
    content: str = Field(..., description="预览内容")
    total_length: int = Field(..., description="文档总长度")


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""

    id: int = Field(..., description="文档ID")
    filename: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    status: str = Field(..., description="处理状态")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class BatchUploadResponse(BaseModel):
    """批量上传响应"""

    documents: List[DocumentUploadResponse] = Field(..., description="上传成功的文档列表")
    errors: List[dict] = Field(default_factory=list, description="上传失败的文件列表")


# ==================== RAG查询相关 ====================


class RAGQueryRequest(BaseModel):
    """RAG查询请求"""

    knowledge_base_ids: List[int] = Field(..., min_length=1, description="知识库ID列表")
    question: str = Field(..., min_length=1, max_length=2000, description="查询问题")
    top_k: int = Field(5, ge=1, le=20, description="检索文档数量")
    conversation_id: Optional[str] = Field(None, description="对话ID（用于维护上下文）")


class DocumentChunkResponse(BaseModel):
    """文档片段响应"""

    content: str = Field(..., description="片段内容")
    document_name: str = Field(..., description="来源文档名称")
    similarity_score: float = Field(..., ge=0, le=1, description="相似度评分")
    document_id: Optional[int] = Field(None, description="文档ID")
    chunk_index: Optional[int] = Field(None, description="分块索引")


class RAGQueryResponse(BaseModel):
    """RAG查询响应"""

    answer: str = Field(..., description="生成的答案")
    sources: List[DocumentChunkResponse] = Field(..., description="参考文档片段")
    tokens_used: int = Field(..., description="消耗的token数量")
    retrieval_time_ms: float = Field(..., description="检索耗时（毫秒）")
    generation_time_ms: float = Field(..., description="生成耗时（毫秒）")


class RAGStreamSourcesEvent(BaseModel):
    """RAG流式响应 - 文档片段事件"""

    type: str = Field("sources", description="事件类型")
    sources: List[DocumentChunkResponse] = Field(..., description="参考文档片段")
    retrieval_time_ms: float = Field(..., description="检索耗时（毫秒）")


class RAGStreamTokenEvent(BaseModel):
    """RAG流式响应 - 文本片段事件"""

    type: str = Field("token", description="事件类型")
    content: str = Field(..., description="文本片段")


class RAGStreamDoneEvent(BaseModel):
    """RAG流式响应 - 完成事件"""

    type: str = Field("done", description="事件类型")
    content: str = Field(..., description="完整答案")
    tokens_used: int = Field(..., description="消耗的token数量")
    retrieval_time_ms: float = Field(..., description="检索耗时（毫秒）")
    generation_time_ms: float = Field(..., description="生成耗时（毫秒）")


class RAGStreamErrorEvent(BaseModel):
    """RAG流式响应 - 错误事件"""

    type: str = Field("error", description="事件类型")
    error: str = Field(..., description="错误信息")


# ==================== 通用响应 ====================


class MessageResponse(BaseModel):
    """通用消息响应"""

    message: str = Field(..., description="消息内容")


class ErrorResponse(BaseModel):
    """错误响应"""

    detail: str = Field(..., description="错误详情")


# 导出
__all__ = [
    # 知识库
    "KnowledgeBaseCreate",
    "KnowledgeBaseUpdate",
    "KnowledgeBaseResponse",
    "KnowledgeBaseListResponse",
    # 文档
    "DocumentResponse",
    "DocumentListResponse",
    "DocumentStatusResponse",
    "DocumentPreviewResponse",
    "DocumentUploadResponse",
    "BatchUploadResponse",
    # RAG
    "RAGQueryRequest",
    "DocumentChunkResponse",
    "RAGQueryResponse",
    "RAGStreamSourcesEvent",
    "RAGStreamTokenEvent",
    "RAGStreamDoneEvent",
    "RAGStreamErrorEvent",
    # 通用
    "MessageResponse",
    "ErrorResponse",
]
