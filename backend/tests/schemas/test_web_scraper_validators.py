"""Web Scraper JSON Schema验证器测试

测试selector_config和scraper_config的JSON验证功能。
"""
import pytest
from pydantic import ValidationError

from app.schemas.web_scraper_validators import (
    SelectorConfig,
    ScraperConfig,
    ExecutionDetails,
    validate_selector_config,
    validate_scraper_config,
    validate_execution_details,
)


class TestSelectorConfig:
    """选择器配置验证测试类"""

    def test_valid_selector_config(self):
        """测试有效的选择器配置"""
        config = {
            "title": "h1.article-title",
            "content": "div.article-content",
            "author": "span.author-name",
            "publish_date": "time.publish-date",
            "exclude": [".advertisement", ".sidebar"]
        }
        result = SelectorConfig(**config)
        assert result.title == "h1.article-title"
        assert result.content == "div.article-content"
        assert result.author == "span.author-name"
        assert result.publish_date == "time.publish-date"
        assert result.exclude == [".advertisement", ".sidebar"]

    def test_minimal_selector_config(self):
        """测试最小选择器配置"""
        config = {
            "title": "h1",
            "content": "article"
        }
        result = SelectorConfig(**config)
        assert result.title == "h1"
        assert result.content == "article"
        assert result.author is None
        assert result.publish_date is None
        assert result.exclude is None

    def test_missing_required_fields(self):
        """测试缺少必需字段"""
        config = {
            "title": "h1"
            # 缺少content
        }
        with pytest.raises(ValidationError):
            SelectorConfig(**config)

    def test_empty_selector(self):
        """测试空选择器"""
        config = {
            "title": "",
            "content": "article"
        }
        with pytest.raises(ValidationError, match="at least 1 character"):
            SelectorConfig(**config)

    def test_selector_too_long(self):
        """测试选择器过长"""
        config = {
            "title": "h1" * 300,  # 超过500字符
            "content": "article"
        }
        with pytest.raises(ValidationError, match="at most 500 characters"):
            SelectorConfig(**config)

    def test_dangerous_selector_script(self):
        """测试包含危险内容的选择器"""
        config = {
            "title": "h1<script>alert('xss')</script>",
            "content": "article"
        }
        with pytest.raises(ValidationError, match="选择器包含危险内容"):
            SelectorConfig(**config)

    def test_dangerous_selector_javascript(self):
        """测试包含JavaScript的选择器"""
        config = {
            "title": "h1",
            "content": "div[onclick='javascript:alert()']"
        }
        with pytest.raises(ValidationError, match="选择器包含危险内容"):
            SelectorConfig(**config)

    def test_exclude_list_too_long(self):
        """测试排除列表过长"""
        config = {
            "title": "h1",
            "content": "article",
            "exclude": [f".class{i}" for i in range(25)]  # 超过20个
        }
        with pytest.raises(ValidationError, match="排除选择器数量不能超过20个"):
            SelectorConfig(**config)

    def test_exclude_item_too_long(self):
        """测试排除项过长"""
        config = {
            "title": "h1",
            "content": "article",
            "exclude": [".class" * 200]  # 超过500字符
        }
        with pytest.raises(ValidationError, match="排除选择器长度必须在1-500字符之间"):
            SelectorConfig(**config)


class TestScraperConfig:
    """采集器配置验证测试类"""

    def test_valid_scraper_config(self):
        """测试有效的采集器配置"""
        config = {
            "wait_for_selector": "div.content",
            "wait_timeout": 30000,
            "screenshot": False,
            "user_agent": "Mozilla/5.0...",
            "headers": {"Accept-Language": "zh-CN"},
            "retry_times": 3,
            "retry_delay": 5
        }
        result = ScraperConfig(**config)
        assert result.wait_for_selector == "div.content"
        assert result.wait_timeout == 30000
        assert result.screenshot is False
        assert result.user_agent == "Mozilla/5.0..."
        assert result.headers == {"Accept-Language": "zh-CN"}
        assert result.retry_times == 3
        assert result.retry_delay == 5

    def test_minimal_scraper_config(self):
        """测试最小采集器配置"""
        config = {
            "wait_for_selector": "body"
        }
        result = ScraperConfig(**config)
        assert result.wait_for_selector == "body"
        assert result.wait_timeout == 30000  # 默认值
        assert result.screenshot is False  # 默认值
        assert result.retry_times == 3  # 默认值
        assert result.retry_delay == 5  # 默认值

    def test_wait_timeout_too_small(self):
        """测试等待超时过小"""
        config = {
            "wait_for_selector": "body",
            "wait_timeout": 500  # 小于1000
        }
        with pytest.raises(ValidationError, match="greater than or equal to 1000"):
            ScraperConfig(**config)

    def test_wait_timeout_too_large(self):
        """测试等待超时过大"""
        config = {
            "wait_for_selector": "body",
            "wait_timeout": 400000  # 大于300000
        }
        with pytest.raises(ValidationError, match="less than or equal to 300000"):
            ScraperConfig(**config)

    def test_retry_times_negative(self):
        """测试重试次数为负"""
        config = {
            "wait_for_selector": "body",
            "retry_times": -1
        }
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            ScraperConfig(**config)

    def test_retry_times_too_large(self):
        """测试重试次数过大"""
        config = {
            "wait_for_selector": "body",
            "retry_times": 15  # 大于10
        }
        with pytest.raises(ValidationError, match="less than or equal to 10"):
            ScraperConfig(**config)

    def test_retry_delay_too_small(self):
        """测试重试延迟过小"""
        config = {
            "wait_for_selector": "body",
            "retry_delay": 0
        }
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            ScraperConfig(**config)

    def test_retry_delay_too_large(self):
        """测试重试延迟过大"""
        config = {
            "wait_for_selector": "body",
            "retry_delay": 100  # 大于60
        }
        with pytest.raises(ValidationError, match="less than or equal to 60"):
            ScraperConfig(**config)

    def test_headers_too_many(self):
        """测试请求头过多"""
        config = {
            "wait_for_selector": "body",
            "headers": {f"Header{i}": f"Value{i}" for i in range(25)}  # 超过20个
        }
        with pytest.raises(ValidationError, match="自定义请求头数量不能超过20个"):
            ScraperConfig(**config)

    def test_headers_dangerous_host(self):
        """测试危险的请求头（Host）"""
        config = {
            "wait_for_selector": "body",
            "headers": {"Host": "evil.com"}
        }
        with pytest.raises(ValidationError, match="不允许设置请求头: Host"):
            ScraperConfig(**config)

    def test_headers_dangerous_connection(self):
        """测试危险的请求头（Connection）"""
        config = {
            "wait_for_selector": "body",
            "headers": {"Connection": "close"}
        }
        with pytest.raises(ValidationError, match="不允许设置请求头: Connection"):
            ScraperConfig(**config)

    def test_headers_key_too_long(self):
        """测试请求头键过长"""
        config = {
            "wait_for_selector": "body",
            "headers": {"X-" + "A" * 100: "value"}  # 键超过100字符
        }
        with pytest.raises(ValidationError, match="请求头键或值过长"):
            ScraperConfig(**config)

    def test_headers_value_too_long(self):
        """测试请求头值过长"""
        config = {
            "wait_for_selector": "body",
            "headers": {"X-Custom": "A" * 1500}  # 值超过1000字符
        }
        with pytest.raises(ValidationError, match="请求头键或值过长"):
            ScraperConfig(**config)

    def test_user_agent_with_newline(self):
        """测试包含换行符的User-Agent"""
        config = {
            "wait_for_selector": "body",
            "user_agent": "Mozilla/5.0\nInjected-Header: value"
        }
        with pytest.raises(ValidationError, match="User-Agent不能包含换行符"):
            ScraperConfig(**config)


class TestExecutionDetails:
    """执行详情验证测试类"""

    def test_valid_execution_details(self):
        """测试有效的执行详情"""
        details = {
            "urls_processed": ["https://example.com/page1"],
            "processing_time": {
                "scraping": 10.5,
                "processing": 5.2,
                "storing": 2.3
            },
            "documents": [
                {
                    "title": "文档标题",
                    "url": "https://example.com/page1",
                    "document_id": 123
                }
            ],
            "errors": []
        }
        result = ExecutionDetails(**details)
        assert len(result.urls_processed) == 1
        assert result.processing_time["scraping"] == 10.5
        assert len(result.documents) == 1
        assert len(result.errors) == 0

    def test_empty_execution_details(self):
        """测试空执行详情"""
        details = {}
        result = ExecutionDetails(**details)
        assert result.urls_processed == []
        assert result.processing_time == {}
        assert result.documents == []
        assert result.errors == []

    def test_urls_too_many(self):
        """测试URL过多"""
        details = {
            "urls_processed": [f"https://example.com/page{i}" for i in range(1500)]
        }
        with pytest.raises(ValidationError, match="处理的URL数量不能超过1000个"):
            ExecutionDetails(**details)

    def test_processing_time_invalid_key(self):
        """测试无效的处理时间键"""
        details = {
            "processing_time": {
                "invalid_key": 10.5
            }
        }
        with pytest.raises(ValidationError, match="无效的处理时间键"):
            ExecutionDetails(**details)

    def test_processing_time_negative(self):
        """测试负数处理时间"""
        details = {
            "processing_time": {
                "scraping": -5.0
            }
        }
        with pytest.raises(ValidationError, match="处理时间不能为负数"):
            ExecutionDetails(**details)

    def test_documents_too_many(self):
        """测试文档过多"""
        details = {
            "documents": [
                {
                    "title": f"文档{i}",
                    "url": f"https://example.com/page{i}",
                    "document_id": i
                }
                for i in range(1500)
            ]
        }
        with pytest.raises(ValidationError, match="创建的文档数量不能超过1000个"):
            ExecutionDetails(**details)

    def test_documents_missing_fields(self):
        """测试文档缺少必需字段"""
        details = {
            "documents": [
                {
                    "title": "文档标题",
                    # 缺少url和document_id
                }
            ]
        }
        with pytest.raises(ValidationError, match="文档缺少必需字段"):
            ExecutionDetails(**details)


class TestValidationFunctions:
    """验证函数测试类"""

    def test_validate_selector_config_success(self):
        """测试validate_selector_config成功"""
        config = {
            "title": "h1",
            "content": "article"
        }
        result = validate_selector_config(config)
        assert isinstance(result, SelectorConfig)
        assert result.title == "h1"

    def test_validate_selector_config_failure(self):
        """测试validate_selector_config失败"""
        config = {
            "title": "h1"
            # 缺少content
        }
        with pytest.raises(ValidationError):
            validate_selector_config(config)

    def test_validate_scraper_config_success(self):
        """测试validate_scraper_config成功"""
        config = {
            "wait_for_selector": "body"
        }
        result = validate_scraper_config(config)
        assert isinstance(result, ScraperConfig)
        assert result.wait_for_selector == "body"

    def test_validate_scraper_config_failure(self):
        """测试validate_scraper_config失败"""
        config = {
            "wait_timeout": 500  # 过小
        }
        with pytest.raises(ValidationError):
            validate_scraper_config(config)

    def test_validate_execution_details_success(self):
        """测试validate_execution_details成功"""
        details = {
            "urls_processed": ["https://example.com"]
        }
        result = validate_execution_details(details)
        assert isinstance(result, ExecutionDetails)
        assert len(result.urls_processed) == 1

    def test_validate_execution_details_failure(self):
        """测试validate_execution_details失败"""
        details = {
            "processing_time": {
                "invalid": 10.0
            }
        }
        with pytest.raises(ValidationError):
            validate_execution_details(details)
