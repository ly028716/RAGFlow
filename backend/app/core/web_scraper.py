"""
Web Scraper 核心模块

基于Playwright的浏览器自动化采集器，支持网页内容提取、清洗和格式化。
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
import html2text

from app.config import settings
from app.core.url_validator import validate_scraper_url, URLValidationError


logger = logging.getLogger(__name__)


class WebScraperError(Exception):
    """Web Scraper基础异常"""
    pass


class BrowserInitError(WebScraperError):
    """浏览器初始化失败"""
    pass


class PageLoadError(WebScraperError):
    """页面加载失败"""
    pass


class ContentExtractionError(WebScraperError):
    """内容提取失败"""
    pass


class SelectorNotFoundError(WebScraperError):
    """选择器未找到"""
    pass


class ScraperConfig:
    """采集器配置"""

    def __init__(
        self,
        wait_for_selector: str,
        wait_timeout: int = 30000,
        screenshot: bool = False,
        user_agent: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_times: int = 3,
        retry_delay: int = 5,
    ):
        self.wait_for_selector = wait_for_selector
        self.wait_timeout = wait_timeout
        self.screenshot = screenshot
        self.user_agent = user_agent or settings.scraper.user_agent
        self.headers = headers or {}
        self.retry_times = retry_times
        self.retry_delay = retry_delay


class SelectorConfig:
    """选择器配置"""

    def __init__(
        self,
        title: str,
        content: str,
        author: Optional[str] = None,
        publish_date: Optional[str] = None,
        exclude: Optional[List[str]] = None,
    ):
        self.title = title
        self.content = content
        self.author = author
        self.publish_date = publish_date
        self.exclude = exclude or []


class ScrapedContent:
    """采集的内容"""

    def __init__(
        self,
        url: str,
        title: str,
        content: str,
        author: Optional[str] = None,
        publish_date: Optional[str] = None,
        raw_html: Optional[str] = None,
        screenshot_path: Optional[str] = None,
    ):
        self.url = url
        self.title = title
        self.content = content
        self.author = author
        self.publish_date = publish_date
        self.raw_html = raw_html
        self.screenshot_path = screenshot_path

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "publish_date": self.publish_date,
            "has_screenshot": self.screenshot_path is not None,
        }


class WebScraper:
    """
    浏览器自动化采集器

    使用Playwright进行网页内容采集，支持：
    - 浏览器自动化
    - 内容提取（基于CSS选择器）
    - HTML清洗和格式化
    - 错误处理和重试
    """

    def __init__(self, scraper_config: ScraperConfig, selector_config: SelectorConfig):
        self.scraper_config = scraper_config
        self.selector_config = selector_config
        self.browser: Optional[Browser] = None
        self.playwright = None
        self._initialized = False

    async def initialize(self):
        """初始化浏览器"""
        if self._initialized:
            return

        try:
            logger.info("初始化Playwright浏览器")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                ]
            )
            self._initialized = True
            logger.info("Playwright浏览器初始化成功")
        except Exception as e:
            logger.error(f"浏览器初始化失败: {str(e)}")
            raise BrowserInitError(f"浏览器初始化失败: {str(e)}")

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        self._initialized = False
        logger.info("浏览器已关闭")

    async def scrape_url(self, url: str) -> ScrapedContent:
        """
        抓取单个URL

        Args:
            url: 目标URL

        Returns:
            ScrapedContent: 采集的内容

        Raises:
            URLValidationError: URL验证失败
            PageLoadError: 页面加载失败
            ContentExtractionError: 内容提取失败
        """
        # 验证URL安全性
        try:
            validate_scraper_url(url)
        except URLValidationError as e:
            logger.error(f"URL验证失败: {url}, 错误: {str(e)}")
            raise

        # 确保浏览器已初始化
        if not self._initialized:
            await self.initialize()

        # 重试机制
        last_error = None
        for attempt in range(self.scraper_config.retry_times):
            try:
                logger.info(f"开始采集URL: {url} (尝试 {attempt + 1}/{self.scraper_config.retry_times})")
                content = await self._scrape_with_browser(url)
                logger.info(f"采集成功: {url}")
                return content
            except Exception as e:
                last_error = e
                logger.warning(f"采集失败 (尝试 {attempt + 1}/{self.scraper_config.retry_times}): {str(e)}")
                if attempt < self.scraper_config.retry_times - 1:
                    await asyncio.sleep(self.scraper_config.retry_delay)

        # 所有重试都失败
        logger.error(f"采集失败，已重试{self.scraper_config.retry_times}次: {url}")
        raise PageLoadError(f"采集失败: {str(last_error)}")

    async def _scrape_with_browser(self, url: str) -> ScrapedContent:
        """使用浏览器采集内容"""
        page: Optional[Page] = None
        try:
            # 创建新页面
            page = await self.browser.new_page(
                user_agent=self.scraper_config.user_agent,
                extra_http_headers=self.scraper_config.headers
            )

            # 访问页面
            logger.debug(f"访问页面: {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=self.scraper_config.wait_timeout)

            # 等待选择器
            logger.debug(f"等待选择器: {self.scraper_config.wait_for_selector}")
            await page.wait_for_selector(
                self.scraper_config.wait_for_selector,
                timeout=self.scraper_config.wait_timeout
            )

            # 获取页面HTML
            html_content = await page.content()

            # 截图（如果需要）
            screenshot_path = None
            if self.scraper_config.screenshot:
                screenshot_path = f"./data/screenshots/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(url)}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                logger.debug(f"截图已保存: {screenshot_path}")

            # 提取内容
            scraped_content = await self._extract_content(url, html_content)
            scraped_content.screenshot_path = screenshot_path

            return scraped_content

        except PlaywrightTimeout as e:
            raise PageLoadError(f"页面加载超时: {str(e)}")
        except Exception as e:
            raise PageLoadError(f"页面加载失败: {str(e)}")
        finally:
            if page:
                await page.close()

    async def _extract_content(self, url: str, html_content: str) -> ScrapedContent:
        """
        从HTML中提取内容（优化版：减少重复解析）

        Args:
            url: 页面URL
            html_content: HTML内容

        Returns:
            ScrapedContent: 提取的内容

        Raises:
            ContentExtractionError: 内容提取失败
        """
        try:
            # 一次性解析HTML
            soup = BeautifulSoup(html_content, 'lxml')

            # 移除排除的元素
            for exclude_selector in self.selector_config.exclude:
                for element in soup.select(exclude_selector):
                    element.decompose()

            # 提取标题
            title = self._extract_text(soup, self.selector_config.title, "标题")

            # 提取内容元素
            content_elements = soup.select(self.selector_config.content)
            if not content_elements:
                raise SelectorNotFoundError(f"内容选择器未找到元素: {self.selector_config.content}")

            content_element = content_elements[0]

            # 直接在BeautifulSoup对象上清洗（避免重新解析）
            self._clean_html_inplace(content_element)

            # 转换为Markdown
            content_markdown = self._html_to_markdown(str(content_element))

            # 提取作者（可选）
            author = None
            if self.selector_config.author:
                try:
                    author = self._extract_text(soup, self.selector_config.author, "作者", required=False)
                except SelectorNotFoundError:
                    pass

            # 提取发布日期（可选）
            publish_date = None
            if self.selector_config.publish_date:
                try:
                    publish_date = self._extract_text(soup, self.selector_config.publish_date, "发布日期", required=False)
                except SelectorNotFoundError:
                    pass

            return ScrapedContent(
                url=url,
                title=title,
                content=content_markdown,
                author=author,
                publish_date=publish_date,
                raw_html=str(content_element)
            )

        except SelectorNotFoundError:
            raise
        except Exception as e:
            logger.error(f"内容提取失败: {str(e)}")
            raise ContentExtractionError(f"内容提取失败: {str(e)}")

    def _extract_text(self, soup: BeautifulSoup, selector: str, field_name: str, required: bool = True) -> str:
        """提取文本内容"""
        elements = soup.select(selector)
        if not elements:
            if required:
                raise SelectorNotFoundError(f"{field_name}选择器未找到元素: {selector}")
            return ""

        text = elements[0].get_text(strip=True)
        if not text and required:
            raise ContentExtractionError(f"{field_name}内容为空")

        return text

    def _clean_html_inplace(self, element) -> None:
        """
        就地清洗HTML内容（优化版：直接操作BeautifulSoup对象，避免重新解析）

        Args:
            element: BeautifulSoup元素对象

        移除脚本、样式、注释等不需要的内容
        """
        # 移除脚本和样式
        for tag in element.find_all(['script', 'style', 'noscript']):
            tag.decompose()

        # 移除注释
        from bs4 import Comment
        for comment in element.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # 移除空白元素（优化：使用列表推导式一次性收集，避免在迭代中修改）
        empty_elements = [
            el for el in element.find_all()
            if not el.get_text(strip=True) and not el.find('img')
        ]
        for el in empty_elements:
            el.decompose()

    def _html_to_markdown(self, html: str) -> str:
        """
        将HTML转换为Markdown

        Args:
            html: HTML内容

        Returns:
            str: Markdown内容
        """
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.ignore_emphasis = False
        h.body_width = 0  # 不换行
        h.unicode_snob = True
        h.skip_internal_links = True

        markdown = h.handle(html)

        # 清理多余的空行
        lines = markdown.split('\n')
        cleaned_lines = []
        prev_empty = False

        for line in lines:
            is_empty = not line.strip()
            if is_empty and prev_empty:
                continue
            cleaned_lines.append(line)
            prev_empty = is_empty

        return '\n'.join(cleaned_lines).strip()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()


# 便捷函数
async def scrape_url(
    url: str,
    selector_config: Dict[str, Any],
    scraper_config: Optional[Dict[str, Any]] = None
) -> ScrapedContent:
    """
    采集单个URL的便捷函数

    Args:
        url: 目标URL
        selector_config: 选择器配置字典
        scraper_config: 采集器配置字典（可选）

    Returns:
        ScrapedContent: 采集的内容

    Example:
        content = await scrape_url(
            "https://example.com/article",
            selector_config={
                "title": "h1.title",
                "content": "div.content"
            }
        )
    """
    selector = SelectorConfig(**selector_config)
    scraper_cfg = ScraperConfig(**(scraper_config or {}))

    async with WebScraper(scraper_cfg, selector) as scraper:
        return await scraper.scrape_url(url)
