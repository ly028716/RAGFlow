"""
Web Scraper Pydantic Schemas

定义网页采集任务和日志的请求/响应模型
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.models.web_scraper_task import ScheduleType, TaskStatus
from app.models.web_scraper_log import LogStatus


# ==================== 选择器配置 ====================

class SelectorConfigSchema(BaseModel):
    """选择器配置"""

    title: str = Field(..., description="标题选择器（CSS选择器）", min_length=1, max_length=200)
    content: str = Field(..., description="内容选择器（CSS选择器）", min_length=1, max_length=200)
    author: Optional[str] = Field(None, description="作者选择器（CSS选择器）", max_length=200)
    publish_date: Optional[str] = Field(None, description="发布日期选择器（CSS选择器）", max_length=200)
    exclude: Optional[List[str]] = Field(default_factory=list, description="排除元素选择器列表")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "h1.article-title",
                "content": "div.article-content",
                "author": "span.author-name",
                "publish_date": "time.publish-date",
                "exclude": ["script", "style", "nav", "footer"]
            }
        }


class ScraperConfigSchema(BaseModel):
    """采集器配置"""

    wait_for_selector: str = Field(
        default="body",
        description="等待加载的选择器",
        min_length=1,
        max_length=200
    )
    wait_timeout: int = Field(
        default=30000,
        description="等待超时时间（毫秒）",
        ge=1000,
        le=120000
    )
    screenshot: bool = Field(default=False, description="是否截图")
    user_agent: Optional[str] = Field(None, description="自定义User-Agent", max_length=500)
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="自定义HTTP头")
    retry_times: int = Field(default=3, description="重试次数", ge=1, le=10)
    retry_delay: int = Field(default=5, description="重试延迟（秒）", ge=1, le=60)

    class Config:
        json_schema_extra = {
            "example": {
                "wait_for_selector": "article",
                "wait_timeout": 30000,
                "screenshot": False,
                "retry_times": 3,
                "retry_delay": 5
            }
        }


# ==================== 任务请求模型 ====================

class TaskCreateRequest(BaseModel):
    """创建任务请求"""

    name: str = Field(..., description="任务名称", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="任务描述", max_length=1000)
    url: str = Field(..., description="目标URL")
    url_pattern: Optional[str] = Field(None, description="URL匹配模式（支持通配符）", max_length=500)
    knowledge_base_id: int = Field(..., description="目标知识库ID", gt=0)
    schedule_type: ScheduleType = Field(
        default=ScheduleType.ONCE,
        description="调度类型：once-一次性，cron-定时"
    )
    cron_expression: Optional[str] = Field(
        None,
        description="Cron表达式（定时任务必需）",
        max_length=100
    )
    selector_config: SelectorConfigSchema = Field(..., description="选择器配置")
    scraper_config: Optional[ScraperConfigSchema] = Field(
        default_factory=ScraperConfigSchema,
        description="采集器配置"
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """验证URL格式"""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL必须以http://或https://开头")
        return v

    @field_validator("cron_expression")
    @classmethod
    def validate_cron_expression(cls, v: Optional[str], info) -> Optional[str]:
        """验证Cron表达式"""
        if info.data.get("schedule_type") == ScheduleType.CRON and not v:
            raise ValueError("定时任务必须提供Cron表达式")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "技术博客采集",
                "description": "定期采集技术博客文章",
                "url": "https://example.com/blog",
                "knowledge_base_id": 1,
                "schedule_type": "cron",
                "cron_expression": "0 0 * * *",
                "selector_config": {
                    "title": "h1.title",
                    "content": "div.content",
                    "author": "span.author",
                    "exclude": ["script", "style"]
                },
                "scraper_config": {
                    "wait_for_selector": "article",
                    "wait_timeout": 30000,
                    "retry_times": 3
                }
            }
        }


class TaskUpdateRequest(BaseModel):
    """更新任务请求"""

    name: Optional[str] = Field(None, description="任务名称", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="任务描述", max_length=1000)
    url: Optional[str] = Field(None, description="目标URL")
    url_pattern: Optional[str] = Field(None, description="URL匹配模式", max_length=500)
    schedule_type: Optional[ScheduleType] = Field(None, description="调度类型")
    cron_expression: Optional[str] = Field(None, description="Cron表达式", max_length=100)
    selector_config: Optional[SelectorConfigSchema] = Field(None, description="选择器配置")
    scraper_config: Optional[ScraperConfigSchema] = Field(None, description="采集器配置")
    status: Optional[TaskStatus] = Field(None, description="任务状态")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """验证URL格式"""
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("URL必须以http://或https://开头")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "更新后的任务名称",
                "description": "更新后的描述",
                "status": "paused"
            }
        }


# ==================== 任务响应模型 ====================

class TaskResponse(BaseModel):
    """任务响应"""

    id: int = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    url: str = Field(..., description="目标URL")
    url_pattern: Optional[str] = Field(None, description="URL匹配模式")
    knowledge_base_id: int = Field(..., description="知识库ID")
    schedule_type: ScheduleType = Field(..., description="调度类型")
    cron_expression: Optional[str] = Field(None, description="Cron表达式")
    selector_config: Dict[str, Any] = Field(..., description="选择器配置")
    scraper_config: Dict[str, Any] = Field(..., description="采集器配置")
    status: TaskStatus = Field(..., description="任务状态")
    last_run_at: Optional[datetime] = Field(None, description="最后执行时间")
    next_run_at: Optional[datetime] = Field(None, description="下次执行时间")
    created_by: int = Field(..., description="创建者用户ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "技术博客采集",
                "description": "定期采集技术博客文章",
                "url": "https://example.com/blog",
                "knowledge_base_id": 1,
                "schedule_type": "cron",
                "cron_expression": "0 0 * * *",
                "selector_config": {
                    "title": "h1.title",
                    "content": "div.content"
                },
                "scraper_config": {
                    "wait_for_selector": "article",
                    "wait_timeout": 30000
                },
                "status": "active",
                "last_run_at": "2024-01-01T00:00:00",
                "next_run_at": "2024-01-02T00:00:00",
                "created_by": 1,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }


class TaskListResponse(BaseModel):
    """任务列表响应"""

    total: int = Field(..., description="总数")
    items: List[TaskResponse] = Field(..., description="任务列表")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 10,
                "items": []
            }
        }


# ==================== 日志响应模型 ====================

class LogResponse(BaseModel):
    """执行日志响应"""

    id: int = Field(..., description="日志ID")
    task_id: int = Field(..., description="任务ID")
    status: LogStatus = Field(..., description="执行状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    pages_scraped: int = Field(..., description="抓取页面数")
    documents_created: int = Field(..., description="创建文档数")
    error_message: Optional[str] = Field(None, description="错误信息")
    execution_details: Optional[Dict[str, Any]] = Field(None, description="执行详情")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "task_id": 1,
                "status": "success",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-01T00:01:00",
                "pages_scraped": 1,
                "documents_created": 1,
                "error_message": None,
                "execution_details": {
                    "url": "https://example.com/article",
                    "title": "文章标题",
                    "document_id": 123
                },
                "created_at": "2024-01-01T00:00:00"
            }
        }


class LogListResponse(BaseModel):
    """日志列表响应"""

    total: int = Field(..., description="总数")
    items: List[LogResponse] = Field(..., description="日志列表")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 50,
                "items": []
            }
        }


class LogStatisticsResponse(BaseModel):
    """日志统计响应"""

    total: int = Field(..., description="总执行次数")
    success: int = Field(..., description="成功次数")
    failed: int = Field(..., description="失败次数")
    running: int = Field(..., description="运行中次数")
    success_rate: float = Field(..., description="成功率（百分比）")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 100,
                "success": 95,
                "failed": 5,
                "running": 0,
                "success_rate": 95.0
            }
        }


# ==================== 操作响应模型 ====================

class TaskExecuteResponse(BaseModel):
    """任务执行响应"""

    task_id: int = Field(..., description="任务ID")
    log_id: int = Field(..., description="日志ID")
    status: str = Field(..., description="执行状态")
    message: str = Field(..., description="响应消息")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": 1,
                "log_id": 123,
                "status": "running",
                "message": "任务已开始执行"
            }
        }
