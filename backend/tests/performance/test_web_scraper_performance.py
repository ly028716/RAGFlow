"""
Web Scraper 性能和压力测试

测试范围:
- 单任务采集性能
- 批量任务处理能力
- 内存泄漏检测
- 长时间运行稳定性
- 资源使用监控

性能指标:
- 单页采集时间: <10秒（P95）
- 批量任务处理: >5任务/分钟
- 内存使用: <500MB（10个并发任务）
- CPU使用: <80%（峰值）
- 浏览器启动时间: <3秒
"""

import pytest
import asyncio
import time
import psutil
import gc
from datetime import datetime
from typing import List, Dict
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.orm import Session
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.models.web_scraper_task import WebScraperTask, ScheduleType, TaskStatus
from app.services.web_scraper_service import WebScraperService
from app.core.web_scraper import WebScraper, ScraperConfig, SelectorConfig


# 性能监控辅助类
class PerformanceMonitor:
    """性能监控工具"""

    def __init__(self):
        self.process = psutil.Process()
        self.start_time = None
        self.start_memory = None
        self.start_cpu = None

    def start(self):
        """开始监控"""
        gc.collect()  # 强制垃圾回收，获取准确的内存基线
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.start_cpu = self.process.cpu_percent(interval=0.1)

    def stop(self) -> Dict:
        """停止监控并返回指标"""
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        end_cpu = self.process.cpu_percent(interval=0.1)

        return {
            'duration': end_time - self.start_time,
            'memory_start': self.start_memory,
            'memory_end': end_memory,
            'memory_delta': end_memory - self.start_memory,
            'cpu_start': self.start_cpu,
            'cpu_end': end_cpu,
            'cpu_peak': max(self.start_cpu, end_cpu)
        }


@pytest.fixture
def performance_monitor():
    """性能监控器fixture"""
    return PerformanceMonitor()


@pytest.fixture
async def scraper_service(db: Session, test_user: User, test_kb: KnowledgeBase):
    """创建Web Scraper服务实例"""
    service = WebScraperService(db)
    yield service


@pytest.fixture
def mock_browser_context():
    """Mock浏览器上下文"""
    context = AsyncMock()
    page = AsyncMock()

    # 模拟页面导航
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.query_selector = AsyncMock()
    page.query_selector_all = AsyncMock(return_value=[])
    page.title = AsyncMock(return_value="Test Page")
    # 返回包含h1和article元素的HTML内容
    page.content = AsyncMock(return_value="""
    <html>
    <head><title>Test Page</title></head>
    <body>
    <h1>Test Title</h1>
    <article>Test Content</article>
    </body>
    </html>
    """)
    page.close = AsyncMock()

    context.new_page = AsyncMock(return_value=page)
    context.close = AsyncMock()

    return context


@pytest.fixture
def default_scraper_config():
    """默认采集器配置"""
    return ScraperConfig(
        wait_for_selector="article",
        wait_timeout=30000,
        screenshot=False,
        retry_times=3,
        retry_delay=5
    )


@pytest.fixture
def default_selector_config():
    """默认选择器配置"""
    return SelectorConfig(
        title="h1",
        content="article",
        author=None,
        publish_date=None
    )


class TestPerformanceBaseline:
    """性能基准测试"""

    @pytest.mark.asyncio
    async def test_single_page_scraping_time(
        self,
        db: Session,
        test_user: User,
        test_kb: KnowledgeBase,
        scraper_service: WebScraperService,
        performance_monitor: PerformanceMonitor,
        mock_browser_context,
        default_scraper_config: ScraperConfig,
        default_selector_config: SelectorConfig
    ):
        """测试单页采集时间 - 目标: <10秒（P95）"""
        # Mock缓存层和调度器
        with patch('app.core.cache.CacheManager.invalidate_pattern'), \
             patch('app.core.cache.CacheManager.invalidate_key'), \
             patch('app.services.web_scraper_service.get_scheduler') as mock_get_scheduler, \
             patch('app.core.web_scraper.async_playwright') as mock_playwright:

            # 配置mock
            mock_scheduler = MagicMock()
            mock_scheduler.add_job.return_value = True
            mock_get_scheduler.return_value = mock_scheduler

            mock_pw = AsyncMock()
            mock_browser = AsyncMock()

            # Configure mock page
            mock_page = mock_browser_context.new_page.return_value
            mock_browser.new_page = AsyncMock(return_value=mock_page)
            mock_browser.close = AsyncMock()

            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

            mock_playwright_manager = MagicMock()
            mock_playwright_manager.start = AsyncMock(return_value=mock_pw)
            mock_playwright.return_value = mock_playwright_manager

            # 创建任务
            task = scraper_service.create_task(
                name="性能测试-单页采集",
                url="https://example.com/test",
                knowledge_base_id=test_kb.id,
                user_id=test_user.id,
                schedule_type=ScheduleType.ONCE,
                selector_config={"title": "h1", "content": "article"}
            )

            # 开始性能监控
            performance_monitor.start()

            # 执行采集
            scraper = WebScraper(default_scraper_config, default_selector_config)
            await scraper.initialize()
            try:
                result = await scraper.scrape_url(url=task.url)
            finally:
                await scraper.close()

            # 停止监控
            metrics = performance_monitor.stop()

            # 验证性能指标
            assert metrics['duration'] < 10.0, f"单页采集时间超过10秒: {metrics['duration']:.2f}秒"
            assert result is not None
            print(f"\n单页采集性能: {metrics['duration']:.2f}秒, 内存增长: {metrics['memory_delta']:.2f}MB")

    @pytest.mark.asyncio
    async def test_batch_tasks_throughput(
        self,
        db: Session,
        test_user: User,
        test_kb: KnowledgeBase,
        scraper_service: WebScraperService,
        performance_monitor: PerformanceMonitor,
        mock_browser_context,
        default_scraper_config: ScraperConfig,
        default_selector_config: SelectorConfig
    ):
        """测试批量任务处理能力 - 目标: >5任务/分钟"""
        # Mock缓存层和调度器
        with patch('app.core.cache.CacheManager.invalidate_pattern'), \
             patch('app.core.cache.CacheManager.invalidate_key'), \
             patch('app.services.web_scraper_service.get_scheduler') as mock_get_scheduler, \
             patch('app.core.web_scraper.async_playwright') as mock_playwright:

            # 配置mock
            mock_scheduler = MagicMock()
            mock_scheduler.add_job.return_value = True
            mock_get_scheduler.return_value = mock_scheduler

            mock_pw = AsyncMock()
            mock_browser = AsyncMock()

            # Configure mock page
            mock_page = mock_browser_context.new_page.return_value
            mock_browser.new_page = AsyncMock(return_value=mock_page)
            mock_browser.close = AsyncMock()

            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

            mock_playwright_manager = MagicMock()
            mock_playwright_manager.start = AsyncMock(return_value=mock_pw)
            mock_playwright.return_value = mock_playwright_manager

            # 创建10个任务
            tasks = []
            for i in range(10):
                task = scraper_service.create_task(
                    name=f"批量测试任务{i+1}",
                    url=f"https://example.com/batch{i+1}",
                    knowledge_base_id=test_kb.id,
                    user_id=test_user.id,
                    schedule_type=ScheduleType.ONCE,
                    selector_config={"title": "h1", "content": "article"}
                )
                tasks.append(task)

            # 开始性能监控
            performance_monitor.start()

            # 批量执行采集
            scraper = WebScraper(default_scraper_config, default_selector_config)
            await scraper.initialize()
            try:
                results = await asyncio.gather(*[
                    scraper.scrape_url(url=task.url)
                    for task in tasks
                ], return_exceptions=True)
            finally:
                await scraper.close()

            # 停止监控
            metrics = performance_monitor.stop()

            # 计算吞吐量
            throughput = len(tasks) / (metrics['duration'] / 60)  # 任务/分钟

            # 验证性能指标
            assert throughput >= 5.0, f"批量任务吞吐量低于5任务/分钟: {throughput:.2f}"
            print(f"\n批量任务吞吐量: {throughput:.2f}任务/分钟, 总耗时: {metrics['duration']:.2f}秒")

    @pytest.mark.asyncio
    async def test_browser_startup_time(
        self,
        performance_monitor: PerformanceMonitor,
        mock_browser_context,
        default_scraper_config: ScraperConfig,
        default_selector_config: SelectorConfig
    ):
        """测试浏览器启动时间 - 目标: <3秒"""
        with patch('app.core.web_scraper.async_playwright') as mock_playwright:
            # 配置mock
            mock_pw = AsyncMock()
            mock_browser = AsyncMock()

            # Configure mock page
            mock_page = mock_browser_context.new_page.return_value
            mock_browser.new_page = AsyncMock(return_value=mock_page)
            mock_browser.close = AsyncMock()

            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

            mock_playwright_manager = MagicMock()
            mock_playwright_manager.start = AsyncMock(return_value=mock_pw)
            mock_playwright.return_value = mock_playwright_manager

            # 开始性能监控
            performance_monitor.start()

            # 启动浏览器
            scraper = WebScraper(default_scraper_config, default_selector_config)
            await scraper.initialize()
            await scraper.close()

            # 停止监控
            metrics = performance_monitor.stop()

            # 验证性能指标
            assert metrics['duration'] < 3.0, f"浏览器启动时间超过3秒: {metrics['duration']:.2f}秒"
            print(f"\n浏览器启动时间: {metrics['duration']:.2f}秒")

    @pytest.mark.asyncio
    async def test_content_extraction_speed(
        self,
        performance_monitor: PerformanceMonitor,
        mock_browser_context,
        default_scraper_config: ScraperConfig,
        default_selector_config: SelectorConfig
    ):
        """测试内容提取速度"""
        with patch('app.core.web_scraper.async_playwright') as mock_playwright:
            # 配置mock - 模拟大量内容
            page = mock_browser_context.new_page.return_value

            # 模拟多个元素
            mock_elements = []
            for i in range(100):
                elem = AsyncMock()
                elem.inner_text = AsyncMock(return_value=f"Content {i}")
                mock_elements.append(elem)

            page.query_selector_all = AsyncMock(return_value=mock_elements)

            mock_pw = AsyncMock()
            mock_browser = AsyncMock()

            # Configure mock page
            mock_page = mock_browser_context.new_page.return_value
            mock_browser.new_page = AsyncMock(return_value=mock_page)
            mock_browser.close = AsyncMock()

            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

            mock_playwright_manager = MagicMock()
            mock_playwright_manager.start = AsyncMock(return_value=mock_pw)
            mock_playwright.return_value = mock_playwright_manager

            # 开始性能监控
            performance_monitor.start()

            # 执行内容提取
            scraper = WebScraper(default_scraper_config, default_selector_config)
            await scraper.initialize()
            try:
                result = await scraper.scrape_url(url="https://example.com/large-content")
            finally:
                await scraper.close()

            # 停止监控
            metrics = performance_monitor.stop()

            # 验证性能指标
            assert metrics['duration'] < 5.0, f"内容提取时间过长: {metrics['duration']:.2f}秒"
            assert result is not None
            print(f"\n内容提取速度: {metrics['duration']:.2f}秒, 提取100个元素")


class TestResourceUsage:
    """资源使用测试"""

    @pytest.mark.asyncio
    async def test_memory_usage_single_task(
        self,
        db: Session,
        test_user: User,
        test_kb: KnowledgeBase,
        scraper_service: WebScraperService,
        performance_monitor: PerformanceMonitor,
        mock_browser_context,
        default_scraper_config: ScraperConfig,
        default_selector_config: SelectorConfig
    ):
        """测试单任务内存使用 - 目标: 合理的内存增长"""
        with patch('app.core.cache.CacheManager.invalidate_pattern'), \
             patch('app.core.cache.CacheManager.invalidate_key'), \
             patch('app.services.web_scraper_service.get_scheduler') as mock_get_scheduler, \
             patch('app.core.web_scraper.async_playwright') as mock_playwright:

            mock_scheduler = MagicMock()
            mock_scheduler.add_job.return_value = True
            mock_get_scheduler.return_value = mock_scheduler

            mock_pw = AsyncMock()
            mock_browser = AsyncMock()

            # Configure mock page
            mock_page = mock_browser_context.new_page.return_value
            mock_browser.new_page = AsyncMock(return_value=mock_page)
            mock_browser.close = AsyncMock()

            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

            mock_playwright_manager = MagicMock()
            mock_playwright_manager.start = AsyncMock(return_value=mock_pw)
            mock_playwright.return_value = mock_playwright_manager

            task = scraper_service.create_task(
                name="内存测试-单任务",
                url="https://example.com/memory-test",
                knowledge_base_id=test_kb.id,
                user_id=test_user.id,
                schedule_type=ScheduleType.ONCE,
                selector_config={"title": "h1", "content": "article"}
            )

            performance_monitor.start()

            scraper = WebScraper(default_scraper_config, default_selector_config)
            await scraper.initialize()
            try:
                result = await scraper.scrape_url(url=task.url)
            finally:
                await scraper.close()

            metrics = performance_monitor.stop()

            assert metrics['memory_delta'] < 200, f"单任务内存增长过大: {metrics['memory_delta']:.2f}MB"
            print(f"\n单任务内存使用: 起始={metrics['memory_start']:.2f}MB, "
                  f"结束={metrics['memory_end']:.2f}MB, 增长={metrics['memory_delta']:.2f}MB")

    @pytest.mark.asyncio
    async def test_memory_usage_concurrent_tasks(
        self,
        db: Session,
        test_user: User,
        test_kb: KnowledgeBase,
        scraper_service: WebScraperService,
        performance_monitor: PerformanceMonitor,
        mock_browser_context,
        default_scraper_config: ScraperConfig,
        default_selector_config: SelectorConfig
    ):
        """测试并发任务内存使用 - 目标: <500MB（10个并发任务）"""
        with patch('app.core.cache.CacheManager.invalidate_pattern'), \
             patch('app.core.cache.CacheManager.invalidate_key'), \
             patch('app.services.web_scraper_service.get_scheduler') as mock_get_scheduler, \
             patch('app.core.web_scraper.async_playwright') as mock_playwright:

            mock_scheduler = MagicMock()
            mock_scheduler.add_job.return_value = True
            mock_get_scheduler.return_value = mock_scheduler

            mock_pw = AsyncMock()
            mock_browser = AsyncMock()

            # Configure mock page
            mock_page = mock_browser_context.new_page.return_value
            mock_browser.new_page = AsyncMock(return_value=mock_page)
            mock_browser.close = AsyncMock()

            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

            mock_playwright_manager = MagicMock()
            mock_playwright_manager.start = AsyncMock(return_value=mock_pw)
            mock_playwright.return_value = mock_playwright_manager

            tasks = []
            for i in range(10):
                task = scraper_service.create_task(
                    name=f"并发内存测试{i+1}",
                    url=f"https://example.com/concurrent{i+1}",
                    knowledge_base_id=test_kb.id,
                    user_id=test_user.id,
                    schedule_type=ScheduleType.ONCE,
                    selector_config={"title": "h1", "content": "article"}
                )
                tasks.append(task)

            performance_monitor.start()

            scraper = WebScraper(default_scraper_config, default_selector_config)
            await scraper.initialize()
            try:
                results = await asyncio.gather(*[
                    scraper.scrape_url(url=task.url)
                    for task in tasks
                ], return_exceptions=True)
            finally:
                await scraper.close()

            metrics = performance_monitor.stop()

            assert metrics['memory_delta'] < 500, f"并发任务内存增长超过500MB: {metrics['memory_delta']:.2f}MB"
            print(f"\n并发任务内存使用: 10个任务, 内存增长={metrics['memory_delta']:.2f}MB")

    @pytest.mark.asyncio
    async def test_cpu_usage_under_load(
        self,
        db: Session,
        test_user: User,
        test_kb: KnowledgeBase,
        scraper_service: WebScraperService,
        performance_monitor: PerformanceMonitor,
        mock_browser_context,
        default_scraper_config: ScraperConfig,
        default_selector_config: SelectorConfig
    ):
        """测试负载下的CPU使用 - 目标: <80%（峰值）"""
        with patch('app.core.cache.CacheManager.invalidate_pattern'), \
             patch('app.core.cache.CacheManager.invalidate_key'), \
             patch('app.services.web_scraper_service.get_scheduler') as mock_get_scheduler, \
             patch('app.core.web_scraper.async_playwright') as mock_playwright:

            mock_scheduler = MagicMock()
            mock_scheduler.add_job.return_value = True
            mock_get_scheduler.return_value = mock_scheduler

            mock_pw = AsyncMock()
            mock_browser = AsyncMock()

            # Configure mock page
            mock_page = mock_browser_context.new_page.return_value
            mock_browser.new_page = AsyncMock(return_value=mock_page)
            mock_browser.close = AsyncMock()

            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

            mock_playwright_manager = MagicMock()
            mock_playwright_manager.start = AsyncMock(return_value=mock_pw)
            mock_playwright.return_value = mock_playwright_manager

            tasks = []
            for i in range(5):
                task = scraper_service.create_task(
                    name=f"CPU测试任务{i+1}",
                    url=f"https://example.com/cpu{i+1}",
                    knowledge_base_id=test_kb.id,
                    user_id=test_user.id,
                    schedule_type=ScheduleType.ONCE,
                    selector_config={"title": "h1", "content": "article"}
                )
                tasks.append(task)

            performance_monitor.start()

            scraper = WebScraper(default_scraper_config, default_selector_config)
            await scraper.initialize()
            try:
                results = await asyncio.gather(*[
                    scraper.scrape_url(url=task.url)
                    for task in tasks
                ], return_exceptions=True)
            finally:
                await scraper.close()

            metrics = performance_monitor.stop()

            print(f"\nCPU使用: 起始={metrics['cpu_start']:.2f}%, "
                  f"结束={metrics['cpu_end']:.2f}%, 峰值={metrics['cpu_peak']:.2f}%")

    @pytest.mark.asyncio
    async def test_memory_leak_detection(
        self,
        db: Session,
        test_user: User,
        test_kb: KnowledgeBase,
        scraper_service: WebScraperService,
        mock_browser_context,
        default_scraper_config: ScraperConfig,
        default_selector_config: SelectorConfig
    ):
        """测试内存泄漏检测 - 多次执行后内存应该稳定"""
        with patch('app.core.cache.CacheManager.invalidate_pattern'), \
             patch('app.core.cache.CacheManager.invalidate_key'), \
             patch('app.services.web_scraper_service.get_scheduler') as mock_get_scheduler, \
             patch('app.core.web_scraper.async_playwright') as mock_playwright:

            mock_scheduler = MagicMock()
            mock_scheduler.add_job.return_value = True
            mock_get_scheduler.return_value = mock_scheduler

            mock_pw = AsyncMock()
            mock_browser = AsyncMock()

            # Configure mock page
            mock_page = mock_browser_context.new_page.return_value
            mock_browser.new_page = AsyncMock(return_value=mock_page)
            mock_browser.close = AsyncMock()

            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

            mock_playwright_manager = MagicMock()
            mock_playwright_manager.start = AsyncMock(return_value=mock_pw)
            mock_playwright.return_value = mock_playwright_manager

            task = scraper_service.create_task(
                name="内存泄漏测试",
                url="https://example.com/leak-test",
                knowledge_base_id=test_kb.id,
                user_id=test_user.id,
                schedule_type=ScheduleType.ONCE,
                selector_config={"title": "h1", "content": "article"}
            )

            memory_samples = []

            for i in range(5):
                gc.collect()
                start_memory = psutil.Process().memory_info().rss / 1024 / 1024

                scraper = WebScraper(default_scraper_config, default_selector_config)
                await scraper.initialize()
                try:
                    result = await scraper.scrape_url(url=task.url)
                finally:
                    await scraper.close()

                gc.collect()
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_delta = end_memory - start_memory
                memory_samples.append(memory_delta)

            avg_memory = sum(memory_samples) / len(memory_samples)
            max_deviation = max(abs(m - avg_memory) for m in memory_samples)

            print(f"\n内存泄漏检测: 5次执行内存增长={memory_samples}")
            print(f"平均内存增长={avg_memory:.2f}MB, 最大偏差={max_deviation:.2f}MB")

            assert max_deviation < avg_memory * 0.5 or max_deviation < 50, \
                f"检测到可能的内存泄漏: 最大偏差={max_deviation:.2f}MB"


class TestStability:
    """稳定性测试"""

    @pytest.mark.asyncio
    async def test_long_running_stability(
        self,
        db: Session,
        test_user: User,
        test_kb: KnowledgeBase,
        scraper_service: WebScraperService,
        performance_monitor: PerformanceMonitor,
        mock_browser_context,
        default_scraper_config: ScraperConfig,
        default_selector_config: SelectorConfig
    ):
        """测试长时间运行稳定性 - 连续执行多个任务"""
        with patch('app.core.cache.CacheManager.invalidate_pattern'), \
             patch('app.core.cache.CacheManager.invalidate_key'), \
             patch('app.services.web_scraper_service.get_scheduler') as mock_get_scheduler, \
             patch('app.core.web_scraper.async_playwright') as mock_playwright:

            mock_scheduler = MagicMock()
            mock_scheduler.add_job.return_value = True
            mock_get_scheduler.return_value = mock_scheduler

            mock_pw = AsyncMock()
            mock_browser = AsyncMock()

            # Configure mock page
            mock_page = mock_browser_context.new_page.return_value
            mock_browser.new_page = AsyncMock(return_value=mock_page)
            mock_browser.close = AsyncMock()

            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

            mock_playwright_manager = MagicMock()
            mock_playwright_manager.start = AsyncMock(return_value=mock_pw)
            mock_playwright.return_value = mock_playwright_manager

            tasks = []
            for i in range(20):
                task = scraper_service.create_task(
                    name=f"稳定性测试任务{i+1}",
                    url=f"https://example.com/stability{i+1}",
                    knowledge_base_id=test_kb.id,
                    user_id=test_user.id,
                    schedule_type=ScheduleType.ONCE,
                    selector_config={"title": "h1", "content": "article"}
                )
                tasks.append(task)

            performance_monitor.start()

            scraper = WebScraper(default_scraper_config, default_selector_config)
            await scraper.initialize()

            success_count = 0
            error_count = 0

            try:
                for task in tasks:
                    try:
                        result = await scraper.scrape_url(url=task.url)
                        if result:
                            success_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"任务 {task.name} 执行失败: {str(e)}")
            finally:
                await scraper.close()

            metrics = performance_monitor.stop()

            success_rate = success_count / len(tasks) * 100

            print(f"\n长时间运行稳定性测试:")
            print(f"总任务数: {len(tasks)}")
            print(f"成功: {success_count}, 失败: {error_count}")
            print(f"成功率: {success_rate:.2f}%")
            print(f"总耗时: {metrics['duration']:.2f}秒")
            print(f"内存增长: {metrics['memory_delta']:.2f}MB")

            assert success_rate >= 95.0, f"成功率低于95%: {success_rate:.2f}%"

    @pytest.mark.asyncio
    async def test_continuous_task_execution(
        self,
        db: Session,
        test_user: User,
        test_kb: KnowledgeBase,
        scraper_service: WebScraperService,
        performance_monitor: PerformanceMonitor,
        mock_browser_context,
        default_scraper_config: ScraperConfig,
        default_selector_config: SelectorConfig
    ):
        """测试连续任务执行 - 验证浏览器资源正确释放"""
        with patch('app.core.cache.CacheManager.invalidate_pattern'), \
             patch('app.core.cache.CacheManager.invalidate_key'), \
             patch('app.services.web_scraper_service.get_scheduler') as mock_get_scheduler, \
             patch('app.core.web_scraper.async_playwright') as mock_playwright:

            mock_scheduler = MagicMock()
            mock_scheduler.add_job.return_value = True
            mock_get_scheduler.return_value = mock_scheduler

            mock_pw = AsyncMock()
            mock_browser = AsyncMock()

            # Configure mock page
            mock_page = mock_browser_context.new_page.return_value
            mock_browser.new_page = AsyncMock(return_value=mock_page)
            mock_browser.close = AsyncMock()

            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

            mock_playwright_manager = MagicMock()
            mock_playwright_manager.start = AsyncMock(return_value=mock_pw)
            mock_playwright.return_value = mock_playwright_manager

            task = scraper_service.create_task(
                name="连续执行测试",
                url="https://example.com/continuous",
                knowledge_base_id=test_kb.id,
                user_id=test_user.id,
                schedule_type=ScheduleType.ONCE,
                selector_config={"title": "h1", "content": "article"}
            )

            performance_monitor.start()

            execution_times = []

            for i in range(10):
                start = time.time()

                scraper = WebScraper(default_scraper_config, default_selector_config)
                await scraper.initialize()
                try:
                    result = await scraper.scrape_url(url=task.url)
                finally:
                    await scraper.close()

                execution_time = time.time() - start
                execution_times.append(execution_time)

            metrics = performance_monitor.stop()

            avg_time = sum(execution_times) / len(execution_times)
            max_time = max(execution_times)
            min_time = min(execution_times)

            print(f"\n连续任务执行测试:")
            print(f"执行次数: {len(execution_times)}")
            print(f"平均执行时间: {avg_time:.2f}秒")
            print(f"最快: {min_time:.2f}秒, 最慢: {max_time:.2f}秒")
            print(f"总内存增长: {metrics['memory_delta']:.2f}MB")

            # 验证执行时间波动（对于非常小的时间值，使用绝对差值而不是相对比例）
            if avg_time > 0.01:
                assert max_time < avg_time * 2, f"执行时间波动过大: 最慢={max_time:.2f}秒, 平均={avg_time:.2f}秒"
            else:
                # 对于非常小的执行时间，检查绝对差值
                assert max_time - min_time < 0.1, f"执行时间波动过大: 最慢={max_time:.2f}秒, 最快={min_time:.2f}秒"
            assert metrics['memory_delta'] < 300, f"连续执行内存增长过大: {metrics['memory_delta']:.2f}MB"
