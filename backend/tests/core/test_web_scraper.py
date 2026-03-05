"""
WebScraper类单元测试

测试范围：
- 浏览器初始化和关闭
- 页面访问和等待
- 内容提取（基于选择器）
- 内容清洗和格式化
- 错误处理和重试机制
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from playwright.async_api import Page, Browser, BrowserContext, Error as PlaywrightError

from app.core.web_scraper import WebScraper
from app.schemas.web_scraper import SelectorConfigSchema, ScraperConfigSchema


@pytest.fixture
def selector_config():
    """选择器配置fixture"""
    return SelectorConfigSchema(
        title="h1.article-title",
        content="div.article-content",
        author="span.author-name",
        exclude=["script", "style", ".advertisement"]
    )


@pytest.fixture
def scraper_config():
    """采集器配置fixture"""
    return ScraperConfigSchema(
        wait_for_selector="body",
        wait_timeout=30000,
        screenshot=False,
        retry_times=3,
        retry_delay=5
    )


@pytest.fixture
async def mock_browser():
    """Mock浏览器fixture"""
    browser = AsyncMock(spec=Browser)
    context = AsyncMock(spec=BrowserContext)
    page = AsyncMock(spec=Page)

    browser.new_context.return_value = context
    context.new_page.return_value = page

    return browser, context, page


class TestWebScraperInit:
    """WebScraper初始化测试"""

    @pytest.mark.asyncio
    async def test_init_with_default_config(self, selector_config):
        """测试使用默认配置初始化"""
        scraper = WebScraper(
            url="https://example.com",
            selector_config=selector_config
        )

        assert scraper.url == "https://example.com"
        assert scraper.selector_config == selector_config
        assert scraper.scraper_config.wait_timeout == 30000
        assert scraper.scraper_config.retry_times == 3

    @pytest.mark.asyncio
    async def test_init_with_custom_config(self, selector_config, scraper_config):
        """测试使用自定义配置初始化"""
        scraper = WebScraper(
            url="https://example.com",
            selector_config=selector_config,
            scraper_config=scraper_config
        )

        assert scraper.scraper_config.wait_timeout == 30000
        assert scraper.scraper_config.retry_times == 3
        assert scraper.scraper_config.screenshot is False


class TestWebScraperBrowser:
    """浏览器管理测试"""

    @pytest.mark.asyncio
    @patch('app.core.web_scraper.async_playwright')
    async def test_browser_initialization(self, mock_playwright, selector_config):
        """测试浏览器初始化"""
        # Mock playwright
        mock_pw = AsyncMock()
        mock_browser = AsyncMock(spec=Browser)
        mock_pw.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__aenter__.return_value = mock_pw

        scraper = WebScraper(
            url="https://example.com",
            selector_config=selector_config
        )

        await scraper._init_browser()

        assert scraper.browser is not None
        mock_pw.chromium.launch.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.core.web_scraper.async_playwright')
    async def test_browser_close(self, mock_playwright, selector_config):
        """测试浏览器关闭"""
        # Mock playwright
        mock_pw = AsyncMock()
        mock_browser = AsyncMock(spec=Browser)
        mock_pw.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__aenter__.return_value = mock_pw

        scraper = WebScraper(
            url="https://example.com",
            selector_config=selector_config
        )

        await scraper._init_browser()
        await scraper._close_browser()

        mock_browser.close.assert_called_once()
        assert scraper.browser is None


class TestWebScraperPageAccess:
    """页面访问测试"""

    @pytest.mark.asyncio
    @patch('app.core.web_scraper.async_playwright')
    async def test_page_access_success(self, mock_playwright, selector_config):
        """测试成功访问页面"""
        # Mock playwright
        mock_pw = AsyncMock()
        mock_browser = AsyncMock(spec=Browser)
        mock_context = AsyncMock(spec=BrowserContext)
        mock_page = AsyncMock(spec=Page)

        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.goto.return_value = None
        mock_page.wait_for_selector.return_value = None

        mock_playwright.return_value.__aenter__.return_value = mock_pw

        scraper = WebScraper(
            url="https://example.com",
            selector_config=selector_config
        )

        await scraper._init_browser()
        page = await scraper._get_page()

        mock_page.goto.assert_called_once_with(
            "https://example.com",
            wait_until="networkidle",
            timeout=30000
        )
        mock_page.wait_for_selector.assert_called_once_with(
            "body",
            timeout=30000
        )

    @pytest.mark.asyncio
    @patch('app.core.web_scraper.async_playwright')
    async def test_page_access_timeout(self, mock_playwright, selector_config):
        """测试页面访问超时"""
        # Mock playwright
        mock_pw = AsyncMock()
        mock_browser = AsyncMock(spec=Browser)
        mock_context = AsyncMock(spec=BrowserContext)
        mock_page = AsyncMock(spec=Page)

        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.goto.side_effect = PlaywrightError("Timeout")

        mock_playwright.return_value.__aenter__.return_value = mock_pw

        scraper = WebScraper(
            url="https://example.com",
            selector_config=selector_config
        )

        await scraper._init_browser()

        with pytest.raises(Exception) as exc_info:
            await scraper._get_page()

        assert "访问页面失败" in str(exc_info.value) or "Timeout" in str(exc_info.value)


class TestWebScraperContentExtraction:
    """内容提取测试"""

    @pytest.mark.asyncio
    @patch('app.core.web_scraper.async_playwright')
    async def test_extract_title(self, mock_playwright, selector_config):
        """测试提取标题"""
        # Mock playwright
        mock_pw = AsyncMock()
        mock_browser = AsyncMock(spec=Browser)
        mock_context = AsyncMock(spec=BrowserContext)
        mock_page = AsyncMock(spec=Page)
        mock_element = AsyncMock()

        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.goto.return_value = None
        mock_page.wait_for_selector.return_value = None
        mock_page.query_selector.return_value = mock_element
        mock_element.inner_text.return_value = "测试标题"

        mock_playwright.return_value.__aenter__.return_value = mock_pw

        scraper = WebScraper(
            url="https://example.com",
            selector_config=selector_config
        )

        await scraper._init_browser()
        page = await scraper._get_page()
        title = await scraper._extract_title(page)

        assert title == "测试标题"
        mock_page.query_selector.assert_called_with("h1.article-title")

    @pytest.mark.asyncio
    @patch('app.core.web_scraper.async_playwright')
    async def test_extract_content(self, mock_playwright, selector_config):
        """测试提取内容"""
        # Mock playwright
        mock_pw = AsyncMock()
        mock_browser = AsyncMock(spec=Browser)
        mock_context = AsyncMock(spec=BrowserContext)
        mock_page = AsyncMock(spec=Page)
        mock_element = AsyncMock()

        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.goto.return_value = None
        mock_page.wait_for_selector.return_value = None
        mock_page.query_selector.return_value = mock_element
        mock_element.inner_text.return_value = "测试内容\n\n多余空行\n\n"

        mock_playwright.return_value.__aenter__.return_value = mock_pw

        scraper = WebScraper(
            url="https://example.com",
            selector_config=selector_config
        )

        await scraper._init_browser()
        page = await scraper._get_page()
        content = await scraper._extract_content(page)

        # 验证内容被清洗（去除多余空行）
        assert "测试内容" in content
        assert "\n\n\n" not in content


class TestWebScraperRetryMechanism:
    """错误恢复和重试机制测试"""

    @pytest.mark.asyncio
    @patch('app.core.web_scraper.async_playwright')
    async def test_retry_on_network_timeout(self, mock_playwright, selector_config, scraper_config):
        """测试网络超时时的重试机制"""
        from playwright.async_api import TimeoutError as PlaywrightTimeout
        from app.core.web_scraper import ScraperConfig, SelectorConfig

        # Mock playwright - 正确的模式
        mock_pw = AsyncMock()
        mock_browser = AsyncMock(spec=Browser)
        mock_page = AsyncMock(spec=Page)

        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # 前2次超时，第3次成功
        mock_page.goto.side_effect = [
            PlaywrightTimeout("Timeout 30000ms exceeded"),
            PlaywrightTimeout("Timeout 30000ms exceeded"),
            None  # 第3次成功
        ]
        mock_page.wait_for_selector.return_value = None
        mock_page.content.return_value = '<html><body><h1 class="article-title">测试标题</h1><div class="article-content">测试内容</div></body></html>'

        # 正确设置mock: async_playwright().start()
        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.start = AsyncMock(return_value=mock_pw)
        mock_playwright.return_value = mock_playwright_instance

        # 转换为正确的类型
        scraper_cfg = ScraperConfig(
            wait_for_selector=scraper_config.wait_for_selector,
            wait_timeout=scraper_config.wait_timeout,
            retry_times=scraper_config.retry_times,
            retry_delay=scraper_config.retry_delay
        )
        selector_cfg = SelectorConfig(
            title=selector_config.title,
            content=selector_config.content,
            author=selector_config.author,
            exclude=selector_config.exclude
        )

        scraper = WebScraper(
            scraper_config=scraper_cfg,
            selector_config=selector_cfg
        )

        # 执行采集，应该在第3次重试时成功
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await scraper.scrape_url("https://example.com")

        # 验证重试了2次（第3次成功）
        assert mock_page.goto.call_count == 3
        # 验证重试延迟被调用了2次（前2次失败后的延迟）
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(scraper_config.retry_delay)

        # 验证最终成功
        assert result.title == "测试标题"
        assert "测试内容" in result.content

    @pytest.mark.asyncio
    @patch('app.core.web_scraper.async_playwright')
    async def test_retry_on_page_load_failure(self, mock_playwright, selector_config, scraper_config):
        """测试页面加载失败时的重试机制"""
        from app.core.web_scraper import ScraperConfig, SelectorConfig

        # Mock playwright
        mock_pw = AsyncMock()
        mock_browser = AsyncMock(spec=Browser)
        mock_page = AsyncMock(spec=Page)

        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # 前2次失败，第3次成功
        mock_page.goto.side_effect = [
            Exception("net::ERR_CONNECTION_REFUSED"),
            Exception("net::ERR_NAME_NOT_RESOLVED"),
            None  # 第3次成功
        ]
        mock_page.wait_for_selector.return_value = None
        mock_page.content.return_value = '<html><body><h1 class="article-title">测试标题</h1><div class="article-content">测试内容</div></body></html>'

        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.start = AsyncMock(return_value=mock_pw)
        mock_playwright.return_value = mock_playwright_instance

        scraper_cfg = ScraperConfig(
            wait_for_selector=scraper_config.wait_for_selector,
            wait_timeout=scraper_config.wait_timeout,
            retry_times=scraper_config.retry_times,
            retry_delay=scraper_config.retry_delay
        )
        selector_cfg = SelectorConfig(
            title=selector_config.title,
            content=selector_config.content,
            author=selector_config.author,
            exclude=selector_config.exclude
        )

        scraper = WebScraper(
            scraper_config=scraper_cfg,
            selector_config=selector_cfg
        )

        # 执行采集
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await scraper.scrape_url("https://example.com")

        # 验证重试了2次
        assert mock_page.goto.call_count == 3
        assert mock_sleep.call_count == 2
        assert result.title == "测试标题"

    @pytest.mark.asyncio
    @patch('app.core.web_scraper.async_playwright')
    async def test_max_retry_limit_exceeded(self, mock_playwright, selector_config, scraper_config):
        """测试超过最大重试次数后抛出异常"""
        from app.core.web_scraper import PageLoadError, ScraperConfig, SelectorConfig

        # Mock playwright
        mock_pw = AsyncMock()
        mock_browser = AsyncMock(spec=Browser)
        mock_page = AsyncMock(spec=Page)

        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # 所有尝试都失败
        mock_page.goto.side_effect = Exception("Connection failed")

        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.start = AsyncMock(return_value=mock_pw)
        mock_playwright.return_value = mock_playwright_instance

        scraper_cfg = ScraperConfig(
            wait_for_selector=scraper_config.wait_for_selector,
            wait_timeout=scraper_config.wait_timeout,
            retry_times=scraper_config.retry_times,
            retry_delay=scraper_config.retry_delay
        )
        selector_cfg = SelectorConfig(
            title=selector_config.title,
            content=selector_config.content,
            author=selector_config.author,
            exclude=selector_config.exclude
        )

        scraper = WebScraper(
            scraper_config=scraper_cfg,
            selector_config=selector_cfg
        )

        # 执行采集，应该抛出异常
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(PageLoadError) as exc_info:
                await scraper.scrape_url("https://example.com")

        # 验证重试了配置的次数
        assert mock_page.goto.call_count == scraper_config.retry_times
        # 验证延迟调用次数（retry_times - 1）
        assert mock_sleep.call_count == scraper_config.retry_times - 1
        assert "采集失败" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('app.core.web_scraper.async_playwright')
    async def test_retry_on_selector_not_found(self, mock_playwright, selector_config, scraper_config):
        """测试选择器未找到时的重试机制"""
        from playwright.async_api import TimeoutError as PlaywrightTimeout
        from app.core.web_scraper import ScraperConfig, SelectorConfig

        # Mock playwright
        mock_pw = AsyncMock()
        mock_browser = AsyncMock(spec=Browser)
        mock_page = AsyncMock(spec=Page)

        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        mock_page.goto.return_value = None

        # 前2次选择器超时，第3次成功
        mock_page.wait_for_selector.side_effect = [
            PlaywrightTimeout("Timeout waiting for selector"),
            PlaywrightTimeout("Timeout waiting for selector"),
            None  # 第3次成功
        ]
        mock_page.content.return_value = '<html><body><h1 class="article-title">测试标题</h1><div class="article-content">测试内容</div></body></html>'

        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.start = AsyncMock(return_value=mock_pw)
        mock_playwright.return_value = mock_playwright_instance

        scraper_cfg = ScraperConfig(
            wait_for_selector=scraper_config.wait_for_selector,
            wait_timeout=scraper_config.wait_timeout,
            retry_times=scraper_config.retry_times,
            retry_delay=scraper_config.retry_delay
        )
        selector_cfg = SelectorConfig(
            title=selector_config.title,
            content=selector_config.content,
            author=selector_config.author,
            exclude=selector_config.exclude
        )

        scraper = WebScraper(
            scraper_config=scraper_cfg,
            selector_config=selector_cfg
        )

        # 执行采集
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await scraper.scrape_url("https://example.com")

        # 验证重试了2次
        assert mock_page.wait_for_selector.call_count == 3
        assert mock_sleep.call_count == 2
        assert result.title == "测试标题"

    @pytest.mark.asyncio
    @patch('app.core.web_scraper.async_playwright')
    async def test_retry_delay_configuration(self, mock_playwright, selector_config):
        """测试重试延迟配置"""
        from app.core.web_scraper import ScraperConfig, SelectorConfig

        # 自定义重试配置
        custom_config = ScraperConfig(
            wait_for_selector="body",
            wait_timeout=30000,
            retry_times=2,
            retry_delay=10  # 10秒延迟
        )

        # Mock playwright
        mock_pw = AsyncMock()
        mock_browser = AsyncMock(spec=Browser)
        mock_page = AsyncMock(spec=Page)

        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # 第1次失败，第2次成功
        mock_page.goto.side_effect = [
            Exception("Connection failed"),
            None  # 第2次成功
        ]
        mock_page.wait_for_selector.return_value = None
        mock_page.content.return_value = '<html><body><h1 class="article-title">测试标题</h1><div class="article-content">测试内容</div></body></html>'

        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.start = AsyncMock(return_value=mock_pw)
        mock_playwright.return_value = mock_playwright_instance

        selector_cfg = SelectorConfig(
            title=selector_config.title,
            content=selector_config.content,
            author=selector_config.author,
            exclude=selector_config.exclude
        )

        scraper = WebScraper(
            scraper_config=custom_config,
            selector_config=selector_cfg
        )

        # 执行采集
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await scraper.scrape_url("https://example.com")

        # 验证使用了自定义的延迟时间
        mock_sleep.assert_called_once_with(10)
        assert result.title == "测试标题"

    @pytest.mark.asyncio
    @patch('app.core.web_scraper.async_playwright')
    async def test_browser_crash_recovery(self, mock_playwright, selector_config, scraper_config):
        """测试浏览器崩溃后的恢复"""
        from app.core.web_scraper import ScraperConfig, SelectorConfig

        # Mock playwright
        mock_pw = AsyncMock()
        mock_browser = AsyncMock(spec=Browser)
        mock_page = AsyncMock(spec=Page)

        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        # 第1次浏览器崩溃，第2次成功
        mock_page.goto.side_effect = [
            Exception("Browser has been closed"),
            None  # 第2次成功
        ]
        mock_page.wait_for_selector.return_value = None
        mock_page.content.return_value = '<html><body><h1 class="article-title">测试标题</h1><div class="article-content">测试内容</div></body></html>'

        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.start = AsyncMock(return_value=mock_pw)
        mock_playwright.return_value = mock_playwright_instance

        scraper_cfg = ScraperConfig(
            wait_for_selector=scraper_config.wait_for_selector,
            wait_timeout=scraper_config.wait_timeout,
            retry_times=scraper_config.retry_times,
            retry_delay=scraper_config.retry_delay
        )
        selector_cfg = SelectorConfig(
            title=selector_config.title,
            content=selector_config.content,
            author=selector_config.author,
            exclude=selector_config.exclude
        )

        scraper = WebScraper(
            scraper_config=scraper_cfg,
            selector_config=selector_cfg
        )

        # 执行采集
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await scraper.scrape_url("https://example.com")

        # 验证重试后成功
        assert mock_page.goto.call_count == 2
        assert result.title == "测试标题"

    @pytest.mark.asyncio
    @patch('app.core.web_scraper.async_playwright')
    async def test_page_recreation_on_retry(self, mock_playwright, selector_config, scraper_config):
        """测试重试时页面重新创建"""
        from app.core.web_scraper import ScraperConfig, SelectorConfig

        # Mock playwright
        mock_pw = AsyncMock()
        mock_browser = AsyncMock(spec=Browser)
        mock_page1 = AsyncMock(spec=Page)
        mock_page2 = AsyncMock(spec=Page)

        mock_pw.chromium.launch.return_value = mock_browser
        # 每次重试创建新页面
        mock_browser.new_page.side_effect = [mock_page1, mock_page2]

        # 第1个页面失败，第2个页面成功
        mock_page1.goto.side_effect = Exception("Page crashed")
        mock_page2.goto.return_value = None
        mock_page2.wait_for_selector.return_value = None
        mock_page2.content.return_value = '<html><body><h1 class="article-title">测试标题</h1><div class="article-content">测试内容</div></body></html>'

        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.start = AsyncMock(return_value=mock_pw)
        mock_playwright.return_value = mock_playwright_instance

        scraper_cfg = ScraperConfig(
            wait_for_selector=scraper_config.wait_for_selector,
            wait_timeout=scraper_config.wait_timeout,
            retry_times=scraper_config.retry_times,
            retry_delay=scraper_config.retry_delay
        )
        selector_cfg = SelectorConfig(
            title=selector_config.title,
            content=selector_config.content,
            author=selector_config.author,
            exclude=selector_config.exclude
        )

        scraper = WebScraper(
            scraper_config=scraper_cfg,
            selector_config=selector_cfg
        )

        # 执行采集
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await scraper.scrape_url("https://example.com")

        # 验证创建了2个页面（重试时重新创建）
        assert mock_browser.new_page.call_count == 2
        # 验证第1个页面被关闭
        mock_page1.close.assert_called_once()
        # 验证第2个页面成功
        assert result.title == "测试标题"

    @pytest.mark.asyncio
    @patch('app.core.web_scraper.async_playwright')
    async def test_partial_failure_recovery(self, mock_playwright, selector_config, scraper_config):
        """测试部分失败后的恢复（例如：页面加载成功但选择器失败）"""
        from playwright.async_api import TimeoutError as PlaywrightTimeout
        from app.core.web_scraper import ScraperConfig, SelectorConfig

        # Mock playwright
        mock_pw = AsyncMock()
        mock_browser = AsyncMock(spec=Browser)
        mock_page = AsyncMock(spec=Page)

        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        mock_page.goto.return_value = None

        # 第1次选择器超时，第2次成功
        mock_page.wait_for_selector.side_effect = [
            PlaywrightTimeout("Selector timeout"),
            None  # 第2次成功
        ]
        mock_page.content.return_value = '<html><body><h1 class="article-title">测试标题</h1><div class="article-content">测试内容</div></body></html>'

        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.start = AsyncMock(return_value=mock_pw)
        mock_playwright.return_value = mock_playwright_instance

        scraper_cfg = ScraperConfig(
            wait_for_selector=scraper_config.wait_for_selector,
            wait_timeout=scraper_config.wait_timeout,
            retry_times=scraper_config.retry_times,
            retry_delay=scraper_config.retry_delay
        )
        selector_cfg = SelectorConfig(
            title=selector_config.title,
            content=selector_config.content,
            author=selector_config.author,
            exclude=selector_config.exclude
        )

        scraper = WebScraper(
            scraper_config=scraper_cfg,
            selector_config=selector_cfg
        )

        # 执行采集
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await scraper.scrape_url("https://example.com")

        # 验证页面访问成功但选择器失败后重试
        assert mock_page.goto.call_count == 2  # 重试了一次
        assert mock_page.wait_for_selector.call_count == 2
        assert mock_sleep.call_count == 1
        assert result.title == "测试标题"

    @pytest.mark.asyncio
    @patch('app.core.web_scraper.async_playwright')
    async def test_successful_first_attempt(self, mock_playwright, selector_config, scraper_config):
        """测试第一次尝试就成功（无需重试）"""
        from app.core.web_scraper import ScraperConfig, SelectorConfig

        # Mock playwright
        mock_pw = AsyncMock()
        mock_browser = AsyncMock(spec=Browser)
        mock_page = AsyncMock(spec=Page)

        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        mock_page.goto.return_value = None
        mock_page.wait_for_selector.return_value = None
        mock_page.content.return_value = '<html><body><h1 class="article-title">测试标题</h1><div class="article-content">测试内容</div></body></html>'

        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.start = AsyncMock(return_value=mock_pw)
        mock_playwright.return_value = mock_playwright_instance

        scraper_cfg = ScraperConfig(
            wait_for_selector=scraper_config.wait_for_selector,
            wait_timeout=scraper_config.wait_timeout,
            retry_times=scraper_config.retry_times,
            retry_delay=scraper_config.retry_delay
        )
        selector_cfg = SelectorConfig(
            title=selector_config.title,
            content=selector_config.content,
            author=selector_config.author,
            exclude=selector_config.exclude
        )

        scraper = WebScraper(
            scraper_config=scraper_cfg,
            selector_config=selector_cfg
        )

        # 执行采集
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await scraper.scrape_url("https://example.com")

        # 验证只尝试了1次，没有重试
        assert mock_page.goto.call_count == 1
        assert mock_sleep.call_count == 0  # 没有延迟
        assert result.title == "测试标题"

    @pytest.mark.asyncio
    @patch('app.core.web_scraper.async_playwright')
    async def test_content_extraction_failure_retry(self, mock_playwright, selector_config, scraper_config):
        """测试内容提取失败时的重试机制"""
        from app.core.web_scraper import ScraperConfig, SelectorConfig

        # Mock playwright
        mock_pw = AsyncMock()
        mock_browser = AsyncMock(spec=Browser)
        mock_page = AsyncMock(spec=Page)

        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        mock_page.goto.return_value = None
        mock_page.wait_for_selector.return_value = None

        # 第1次内容为空（选择器找不到），第2次成功
        mock_page.content.side_effect = [
            '<html><body></body></html>',  # 第1次：没有内容
            '<html><body><h1 class="article-title">测试标题</h1><div class="article-content">测试内容</div></body></html>'  # 第2次：有内容
        ]

        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.start = AsyncMock(return_value=mock_pw)
        mock_playwright.return_value = mock_playwright_instance

        scraper_cfg = ScraperConfig(
            wait_for_selector=scraper_config.wait_for_selector,
            wait_timeout=scraper_config.wait_timeout,
            retry_times=scraper_config.retry_times,
            retry_delay=scraper_config.retry_delay
        )
        selector_cfg = SelectorConfig(
            title=selector_config.title,
            content=selector_config.content,
            author=selector_config.author,
            exclude=selector_config.exclude
        )

        scraper = WebScraper(
            scraper_config=scraper_cfg,
            selector_config=selector_cfg
        )

        # 执行采集
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await scraper.scrape_url("https://example.com")

        # 验证重试了1次
        assert mock_page.content.call_count == 2
        assert mock_sleep.call_count == 1
        assert result.title == "测试标题"


