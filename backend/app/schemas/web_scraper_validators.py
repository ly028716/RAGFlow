"""Web Scraper JSON Schema验证器

验证selector_config和scraper_config的JSON结构。
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class SelectorConfig(BaseModel):
    """选择器配置Schema"""

    title: str = Field(..., min_length=1, max_length=500, description="标题选择器")
    content: str = Field(..., min_length=1, max_length=500, description="内容选择器")
    author: Optional[str] = Field(None, max_length=500, description="作者选择器")
    publish_date: Optional[str] = Field(None, max_length=500, description="发布日期选择器")
    exclude: Optional[List[str]] = Field(default=None, description="排除选择器列表")

    @field_validator('exclude')
    @classmethod
    def validate_exclude(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """验证排除选择器列表"""
        if v is not None:
            if len(v) > 20:
                raise ValueError("排除选择器数量不能超过20个")
            for selector in v:
                if not selector or len(selector) > 500:
                    raise ValueError("排除选择器长度必须在1-500字符之间")
        return v

    @field_validator('title', 'content', 'author', 'publish_date')
    @classmethod
    def validate_selector(cls, v: Optional[str]) -> Optional[str]:
        """验证选择器格式"""
        if v is not None:
            # 检查是否包含危险字符
            dangerous_chars = ['<script', 'javascript:', 'onerror=']
            v_lower = v.lower()
            for char in dangerous_chars:
                if char in v_lower:
                    raise ValueError(f"选择器包含危险内容: {char}")
        return v


class ScraperConfig(BaseModel):
    """采集器配置Schema"""

    wait_for_selector: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="等待的选择器"
    )
    wait_timeout: int = Field(
        default=30000,
        ge=1000,
        le=300000,
        description="等待超时时间（毫秒），1秒-5分钟"
    )
    screenshot: bool = Field(default=False, description="是否截图")
    user_agent: Optional[str] = Field(
        None,
        max_length=500,
        description="User-Agent"
    )
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="自定义请求头"
    )
    retry_times: int = Field(
        default=3,
        ge=0,
        le=10,
        description="重试次数，0-10次"
    )
    retry_delay: int = Field(
        default=5,
        ge=1,
        le=60,
        description="重试延迟（秒），1-60秒"
    )

    @field_validator('headers')
    @classmethod
    def validate_headers(cls, v: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """验证自定义请求头"""
        if v is not None:
            if len(v) > 20:
                raise ValueError("自定义请求头数量不能超过20个")

            # 检查危险的请求头
            dangerous_headers = ['host', 'connection', 'content-length']
            for key in v.keys():
                if key.lower() in dangerous_headers:
                    raise ValueError(f"不允许设置请求头: {key}")

                # 检查键和值的长度
                if len(key) > 100 or len(v[key]) > 1000:
                    raise ValueError("请求头键或值过长")

        return v

    @field_validator('user_agent')
    @classmethod
    def validate_user_agent(cls, v: Optional[str]) -> Optional[str]:
        """验证User-Agent"""
        if v is not None:
            # 检查是否包含危险字符
            if '\n' in v or '\r' in v:
                raise ValueError("User-Agent不能包含换行符")
        return v


class ExecutionDetails(BaseModel):
    """执行详情Schema（用于日志）"""

    urls_processed: List[str] = Field(default_factory=list, description="处理的URL列表")
    processing_time: Dict[str, float] = Field(
        default_factory=dict,
        description="处理时间统计"
    )
    documents: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="创建的文档列表"
    )
    errors: List[str] = Field(default_factory=list, description="错误列表")

    @field_validator('urls_processed')
    @classmethod
    def validate_urls(cls, v: List[str]) -> List[str]:
        """验证URL列表"""
        if len(v) > 1000:
            raise ValueError("处理的URL数量不能超过1000个")
        return v

    @field_validator('processing_time')
    @classmethod
    def validate_processing_time(cls, v: Dict[str, float]) -> Dict[str, float]:
        """验证处理时间"""
        allowed_keys = {'scraping', 'processing', 'storing', 'total'}
        for key in v.keys():
            if key not in allowed_keys:
                raise ValueError(f"无效的处理时间键: {key}")
            if v[key] < 0:
                raise ValueError(f"处理时间不能为负数: {key}={v[key]}")
        return v

    @field_validator('documents')
    @classmethod
    def validate_documents(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """验证文档列表"""
        if len(v) > 1000:
            raise ValueError("创建的文档数量不能超过1000个")

        for doc in v:
            required_keys = {'title', 'url', 'document_id'}
            if not all(key in doc for key in required_keys):
                raise ValueError(f"文档缺少必需字段: {required_keys}")

        return v


# 验证函数
def validate_selector_config(config: Dict[str, Any]) -> SelectorConfig:
    """验证选择器配置

    Args:
        config: 选择器配置字典

    Returns:
        SelectorConfig: 验证后的配置对象

    Raises:
        ValueError: 配置验证失败
    """
    return SelectorConfig(**config)


def validate_scraper_config(config: Dict[str, Any]) -> ScraperConfig:
    """验证采集器配置

    Args:
        config: 采集器配置字典

    Returns:
        ScraperConfig: 验证后的配置对象

    Raises:
        ValueError: 配置验证失败
    """
    return ScraperConfig(**config)


def validate_execution_details(details: Dict[str, Any]) -> ExecutionDetails:
    """验证执行详情

    Args:
        details: 执行详情字典

    Returns:
        ExecutionDetails: 验证后的详情对象

    Raises:
        ValueError: 详情验证失败
    """
    return ExecutionDetails(**details)
