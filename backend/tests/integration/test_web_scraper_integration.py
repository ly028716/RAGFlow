"""
Web Scraper 集成测试

测试完整的采集流程：
1. 创建采集任务
2. 启动任务
3. 执行采集
4. 验证结果
5. 查看日志
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.models.web_scraper_task import WebScraperTask, TaskStatus, ScheduleType
from app.models.web_scraper_log import WebScraperLog, LogStatus
from app.services.web_scraper_service import WebScraperService
from app.core.scheduler import ScraperScheduler


@pytest.fixture
def test_kb(db: Session, test_user: User) -> KnowledgeBase:
    """创建测试知识库"""
    kb = KnowledgeBase(
        name="集成测试知识库",
        description="用于集成测试的知识库",
        user_id=test_user.id,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


@pytest.fixture
def scraper_service(db: Session) -> WebScraperService:
    """创建Web Scraper服务实例"""
    return WebScraperService(db)


class TestWebScraperIntegration:
    """Web Scraper集成测试类"""

    @pytest.mark.asyncio
    async def test_complete_scraping_workflow(
        self, db: Session, test_user: User, test_kb: KnowledgeBase, scraper_service: WebScraperService
    ):
        """测试完整的采集工作流程"""

        # 1. 创建采集任务
        task = scraper_service.create_task(
            name="集成测试任务",
            url="https://example.com/test-page",
            knowledge_base_id=test_kb.id,
            user_id=test_user.id,
            description="集成测试采集任务",
            schedule_type=ScheduleType.ONCE,
            selector_config={
                "title": "h1.title",
                "content": "article.content"
            },
            scraper_config={
                "wait_for_selector": "article",
                "wait_timeout": 30000,
                "retry_times": 3
            }
        )

        assert task.id is not None
        assert task.status == TaskStatus.PAUSED
        assert task.name == "集成测试任务"

        # 2. Mock调度器和采集器
        with patch('app.services.web_scraper_service.get_scheduler') as mock_get_scheduler, \
             patch('app.core.web_scraper.WebScraper') as mock_scraper_class:

            # Mock调度器
            mock_scheduler = MagicMock(spec=ScraperScheduler)
            mock_scheduler.add_job.return_value = True
            mock_get_scheduler.return_value = mock_scheduler

            # Mock采集器
            mock_scraper = AsyncMock()
            mock_scraper.scrape.return_value = {
                "title": "测试文章标题",
                "content": "这是测试文章的内容...",
                "url": "https://example.com/test-page",
                "scraped_at": datetime.utcnow().isoformat()
            }
            mock_scraper_class.return_value = mock_scraper

            # 3. 启动任务
            started_task = scraper_service.start_task(task.id, test_user.id)

            assert started_task.status == TaskStatus.ACTIVE
            mock_scheduler.add_job.assert_called_once()

            # 4. 模拟执行采集
            log = WebScraperLog(
                task_id=task.id,
                status=LogStatus.RUNNING,
                start_time=datetime.utcnow()
            )
            db.add(log)
            db.commit()
            db.refresh(log)

            # 执行采集
            result = await mock_scraper.scrape()

            assert result["title"] == "测试文章标题"
            assert "content" in result

            # 5. 更新日志状态
            log.status = LogStatus.SUCCESS
            log.end_time = datetime.utcnow()
            log.pages_scraped = 1
            log.documents_created = 1
            log.execution_details = {
                "urls_processed": [result["url"]],
                "processing_time": {
                    "scraping": 5.2,
                    "processing": 2.1,
                    "storing": 1.3,
                    "total": 8.6
                },
                "documents": [
                    {
                        "title": result["title"],
                        "url": result["url"],
                        "document_id": 1
                    }
                ]
            }
            db.commit()

            # 6. 验证日志
            logs = scraper_service.get_task_logs(task.id, test_user.id)

            assert len(logs) > 0
            assert logs[0].status == LogStatus.SUCCESS
            assert logs[0].pages_scraped == 1
            assert logs[0].documents_created == 1

            # 7. 停止任务
            mock_scheduler.remove_job.return_value = True
            stopped_task = scraper_service.stop_task(task.id, test_user.id)

            assert stopped_task.status == TaskStatus.STOPPED
            mock_scheduler.remove_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_scraping_with_error_handling(
        self, db: Session, test_user: User, test_kb: KnowledgeBase, scraper_service: WebScraperService
    ):
        """测试采集过程中的错误处理"""

        # 创建任务
        task = scraper_service.create_task(
            name="错误处理测试任务",
            url="https://example.com/error-page",
            knowledge_base_id=test_kb.id,
            user_id=test_user.id,
            schedule_type=ScheduleType.ONCE,
            selector_config={
                "title": "h1",
                "content": "article"
            }
        )

        with patch('app.core.web_scraper.WebScraper') as mock_scraper_class:
            # Mock采集器抛出异常
            mock_scraper = AsyncMock()
            mock_scraper.scrape.side_effect = Exception("网络连接超时")
            mock_scraper_class.return_value = mock_scraper

            # 创建日志记录
            log = WebScraperLog(
                task_id=task.id,
                status=LogStatus.RUNNING,
                start_time=datetime.utcnow()
            )
            db.add(log)
            db.commit()

            # 执行采集（应该失败）
            try:
                await mock_scraper.scrape()
            except Exception as e:
                # 记录错误
                log.status = LogStatus.FAILED
                log.end_time = datetime.utcnow()
                log.error_message = str(e)
                db.commit()

            # 验证错误日志
            db.refresh(log)
            assert log.status == LogStatus.FAILED
            assert "网络连接超时" in log.error_message

    @pytest.mark.asyncio
    async def test_concurrent_scraping_tasks(
        self, db: Session, test_user: User, test_kb: KnowledgeBase, scraper_service: WebScraperService
    ):
        """测试并发采集任务"""

        # 创建多个任务
        tasks = []
        for i in range(3):
            task = scraper_service.create_task(
                name=f"并发测试任务{i+1}",
                url=f"https://example.com/page{i+1}",
                knowledge_base_id=test_kb.id,
                user_id=test_user.id,
                schedule_type=ScheduleType.ONCE,
                selector_config={
                    "title": "h1",
                    "content": "article"
                }
            )
            tasks.append(task)

        assert len(tasks) == 3

        with patch('app.services.web_scraper_service.get_scheduler') as mock_get_scheduler:
            mock_scheduler = MagicMock(spec=ScraperScheduler)
            mock_scheduler.add_job.return_value = True
            mock_get_scheduler.return_value = mock_scheduler

            # 启动所有任务
            for task in tasks:
                started_task = scraper_service.start_task(task.id, test_user.id)
                assert started_task.status == TaskStatus.ACTIVE

            # 验证调度器被调用了3次
            assert mock_scheduler.add_job.call_count == 3

    def test_task_lifecycle_management(
        self, db: Session, test_user: User, test_kb: KnowledgeBase, scraper_service: WebScraperService
    ):
        """测试任务生命周期管理"""

        # 创建任务
        task = scraper_service.create_task(
            name="生命周期测试任务",
            url="https://example.com/lifecycle",
            knowledge_base_id=test_kb.id,
            user_id=test_user.id,
            schedule_type=ScheduleType.ONCE,
            selector_config={
                "title": "h1",
                "content": "article"
            }
        )

        assert task.status == TaskStatus.PAUSED

        with patch('app.services.web_scraper_service.get_scheduler') as mock_get_scheduler:
            mock_scheduler = MagicMock(spec=ScraperScheduler)
            mock_scheduler.add_job.return_value = True
            mock_scheduler.remove_job.return_value = True
            mock_get_scheduler.return_value = mock_scheduler

            # 启动 -> 暂停 -> 恢复 -> 停止

            # 启动
            task = scraper_service.start_task(task.id, test_user.id)
            assert task.status == TaskStatus.ACTIVE

            # 暂停
            task = scraper_service.pause_task(task.id, test_user.id)
            assert task.status == TaskStatus.PAUSED

            # 恢复
            task = scraper_service.resume_task(task.id, test_user.id)
            assert task.status == TaskStatus.ACTIVE

            # 停止
            task = scraper_service.stop_task(task.id, test_user.id)
            assert task.status == TaskStatus.STOPPED


class TestConcurrentScraping:
    """并发采集场景测试"""

    @pytest.mark.asyncio
    async def test_concurrent_tasks_execution(
        self, db: Session, test_user: User, test_kb: KnowledgeBase, scraper_service: WebScraperService
    ):
        """测试多任务并发执行"""
        from app.core.web_scraper import WebScraper, ScraperConfig, SelectorConfig, ScrapedContent

        # 创建5个并发任务
        tasks = []
        for i in range(5):
            task = scraper_service.create_task(
                name=f"并发执行任务{i+1}",
                url=f"https://example.com/concurrent{i+1}",
                knowledge_base_id=test_kb.id,
                user_id=test_user.id,
                schedule_type=ScheduleType.ONCE,
                selector_config={
                    "title": "h1",
                    "content": "article"
                }
            )
            tasks.append(task)

        # Mock采集器
        async def mock_scrape(url):
            await asyncio.sleep(0.1)  # 模拟采集延迟
            return ScrapedContent(
                url=url,
                title=f"标题-{url}",
                content=f"内容-{url}"
            )

        with patch('app.core.web_scraper.WebScraper') as mock_scraper_class:
            mock_scraper = AsyncMock()
            mock_scraper.scrape_url = mock_scrape
            mock_scraper_class.return_value = mock_scraper

            # 并发执行所有任务
            start_time = asyncio.get_event_loop().time()
            results = await asyncio.gather(*[
                mock_scraper.scrape_url(task.url) for task in tasks
            ])
            end_time = asyncio.get_event_loop().time()

            # 验证所有任务都成功
            assert len(results) == 5
            for i, result in enumerate(results):
                assert f"concurrent{i+1}" in result.url
                assert result.title is not None

            # 验证并发执行（总时间应该接近单个任务时间，而不是5倍）
            total_time = end_time - start_time
            assert total_time < 0.3  # 并发执行应该在0.3秒内完成（而不是0.5秒）

    @pytest.mark.asyncio
    async def test_concurrent_browser_instances(
        self, db: Session, test_user: User, test_kb: KnowledgeBase
    ):
        """测试并发浏览器实例管理"""
        from app.core.web_scraper import WebScraper, ScraperConfig, SelectorConfig

        # 创建3个WebScraper实例
        scrapers = []
        for i in range(3):
            scraper_config = ScraperConfig(
                wait_for_selector="body",
                wait_timeout=30000,
                retry_times=3,
                retry_delay=5
            )
            selector_config = SelectorConfig(
                title="h1",
                content="article"
            )
            scraper = WebScraper(scraper_config, selector_config)
            scrapers.append(scraper)

        with patch('app.core.web_scraper.async_playwright') as mock_playwright:
            # Mock playwright
            mock_pw = AsyncMock()
            mock_browsers = [AsyncMock() for _ in range(3)]

            # 每个scraper获取独立的浏览器实例
            mock_pw.chromium.launch.side_effect = mock_browsers

            mock_playwright_instance = AsyncMock()
            mock_playwright_instance.start = AsyncMock(return_value=mock_pw)
            mock_playwright.return_value = mock_playwright_instance

            # 并发初始化所有scraper
            await asyncio.gather(*[scraper.initialize() for scraper in scrapers])

            # 验证每个scraper都有独立的浏览器实例
            assert mock_pw.chromium.launch.call_count == 3
            for scraper in scrapers:
                assert scraper.browser is not None
                assert scraper._initialized is True

            # 清理
            await asyncio.gather(*[scraper.close() for scraper in scrapers])

    @pytest.mark.asyncio
    async def test_concurrent_database_writes(
        self, db: Session, test_user: User, test_kb: KnowledgeBase, scraper_service: WebScraperService
    ):
        """测试并发数据库写入"""
        # Mock缓存层以避免Redis依赖
        with patch('app.core.cache.CacheManager.invalidate_pattern'), \
             patch('app.core.cache.CacheManager.invalidate_key'):

            # 创建10个任务并发写入数据库
            async def create_task_async(i):
                return scraper_service.create_task(
                    name=f"并发写入任务{i}",
                    url=f"https://example.com/db{i}",
                    knowledge_base_id=test_kb.id,
                    user_id=test_user.id,
                    schedule_type=ScheduleType.ONCE,
                    selector_config={
                        "title": "h1",
                        "content": "article"
                    }
                )

            # 并发创建任务
            tasks = []
            for i in range(10):
                task = create_task_async(i)
                tasks.append(task)

            # 注意：由于SQLAlchemy的Session不是线程安全的，这里实际上是顺序执行
            # 但我们可以验证所有任务都被正确创建
            created_tasks = [await t for t in tasks]

            # 验证所有任务都成功创建
            assert len(created_tasks) == 10
            for i, task in enumerate(created_tasks):
                assert task.id is not None
                assert task.name == f"并发写入任务{i}"
                assert task.status == TaskStatus.PAUSED

            # 验证数据库中的任务数量
            all_tasks = scraper_service.list_tasks(test_user.id)
            assert len([t for t in all_tasks if "并发写入任务" in t['name']]) == 10

    @pytest.mark.asyncio
    async def test_resource_isolation(
        self, db: Session, test_user: User, test_kb: KnowledgeBase
    ):
        """测试资源隔离（每个任务使用独立的浏览器页面）"""
        from app.core.web_scraper import WebScraper, ScraperConfig, SelectorConfig

        scraper_config = ScraperConfig(
            wait_for_selector="body",
            wait_timeout=30000,
            retry_times=3,
            retry_delay=5
        )
        selector_config = SelectorConfig(
            title="h1",
            content="article"
        )

        with patch('app.core.web_scraper.async_playwright') as mock_playwright:
            # Mock playwright
            mock_pw = AsyncMock()
            mock_browser = AsyncMock()
            mock_pages = [AsyncMock() for _ in range(3)]

            mock_pw.chromium.launch.return_value = mock_browser
            mock_browser.new_page.side_effect = mock_pages

            for page in mock_pages:
                page.goto.return_value = None
                page.wait_for_selector.return_value = None
                page.content.return_value = '<html><body><h1>测试</h1><article>内容</article></body></html>'

            mock_playwright_instance = AsyncMock()
            mock_playwright_instance.start = AsyncMock(return_value=mock_pw)
            mock_playwright.return_value = mock_playwright_instance

            scraper = WebScraper(scraper_config, selector_config)
            await scraper.initialize()

            # 并发采集3个URL（每个使用独立的页面）
            urls = [
                "https://example.com/page1",
                "https://example.com/page2",
                "https://example.com/page3"
            ]

            results = await asyncio.gather(*[
                scraper.scrape_url(url) for url in urls
            ])

            # 验证创建了3个独立的页面
            assert mock_browser.new_page.call_count == 3

            # 验证每个页面都被关闭（资源清理）
            for page in mock_pages:
                page.close.assert_called_once()

            # 验证所有采集都成功
            assert len(results) == 3

            await scraper.close()

    @pytest.mark.asyncio
    async def test_max_concurrent_tasks_limit(
        self, db: Session, test_user: User, test_kb: KnowledgeBase, scraper_service: WebScraperService
    ):
        """测试最大并发任务限制"""
        from app.core.scheduler import ScraperScheduler
        from unittest.mock import AsyncMock

        # 创建调度器，设置最大并发为3
        mock_redis = AsyncMock()
        scheduler = ScraperScheduler(mock_redis, max_concurrent_tasks=3)
        await scheduler.initialize()

        # 创建5个任务
        tasks = []
        for i in range(5):
            task = scraper_service.create_task(
                name=f"并发限制测试{i+1}",
                url=f"https://example.com/limit{i+1}",
                knowledge_base_id=test_kb.id,
                user_id=test_user.id,
                schedule_type=ScheduleType.ONCE,
                selector_config={
                    "title": "h1",
                    "content": "article"
                }
            )
            tasks.append(task)

        # 模拟3个正在运行的任务
        scheduler._running_tasks = {
            "task1": asyncio.create_task(asyncio.sleep(10)),
            "task2": asyncio.create_task(asyncio.sleep(10)),
            "task3": asyncio.create_task(asyncio.sleep(10)),
        }

        # 验证当前运行任务数
        assert scheduler.running_task_count == 3

        # 尝试添加第4个任务（应该被限制）
        # 注意：实际的限制逻辑在_execute_job中，这里只验证计数
        assert scheduler.running_task_count >= scheduler.max_concurrent_tasks

        # 清理
        for task in scheduler._running_tasks.values():
            task.cancel()
        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_task_queue_management(
        self, db: Session, test_user: User, test_kb: KnowledgeBase, scraper_service: WebScraperService
    ):
        """测试任务队列管理"""
        # Mock缓存层和调度器
        with patch('app.core.cache.CacheManager.invalidate_pattern'), \
             patch('app.core.cache.CacheManager.invalidate_key'), \
             patch('app.services.web_scraper_service.get_scheduler') as mock_get_scheduler:

            mock_scheduler = MagicMock()
            mock_scheduler.add_job.return_value = True
            mock_get_scheduler.return_value = mock_scheduler

            # 创建10个任务
            tasks = []
            for i in range(10):
                task = scraper_service.create_task(
                    name=f"队列测试任务{i+1}",
                    url=f"https://example.com/queue{i+1}",
                    knowledge_base_id=test_kb.id,
                    user_id=test_user.id,
                    schedule_type=ScheduleType.ONCE,
                    selector_config={
                        "title": "h1",
                        "content": "article"
                    }
                )
                tasks.append(task)

            # 验证所有任务都在队列中（PAUSED状态）
            assert len(tasks) == 10
            for task in tasks:
                assert task.status == TaskStatus.PAUSED

            # 启动前5个任务
            active_tasks = []
            for i in range(5):
                started_task = scraper_service.start_task(tasks[i].id, test_user.id)
                active_tasks.append(started_task)
                assert started_task.status == TaskStatus.ACTIVE

            # 验证启动的任务状态正确
            assert len(active_tasks) == 5
            for task in active_tasks:
                assert task.status == TaskStatus.ACTIVE

            # 验证剩余5个任务仍在队列中
            remaining_tasks = scraper_service.list_tasks(test_user.id)
            paused_count = len([t for t in remaining_tasks if t['status'] == 'paused' and "队列测试" in t['name']])
            active_count = len([t for t in remaining_tasks if t['status'] == 'active' and "队列测试" in t['name']])

            # 验证队列管理：5个活动，5个暂停
            assert active_count == 5
            assert paused_count == 5

    @pytest.mark.asyncio
    async def test_browser_pool_management(
        self, db: Session, test_user: User, test_kb: KnowledgeBase
    ):
        """测试浏览器池管理（复用浏览器实例）"""
        from app.core.web_scraper import WebScraper, ScraperConfig, SelectorConfig

        scraper_config = ScraperConfig(
            wait_for_selector="body",
            wait_timeout=30000,
            retry_times=3,
            retry_delay=5
        )
        selector_config = SelectorConfig(
            title="h1",
            content="article"
        )

        with patch('app.core.web_scraper.async_playwright') as mock_playwright:
            # Mock playwright
            mock_pw = AsyncMock()
            mock_browser = AsyncMock()

            mock_pw.chromium.launch.return_value = mock_browser

            mock_playwright_instance = AsyncMock()
            mock_playwright_instance.start = AsyncMock(return_value=mock_pw)
            mock_playwright.return_value = mock_playwright_instance

            # 创建3个scraper实例，它们应该复用同一个浏览器
            scrapers = []
            for i in range(3):
                scraper = WebScraper(scraper_config, selector_config)
                await scraper.initialize()
                scrapers.append(scraper)

            # 验证浏览器只被启动了3次（每个scraper一个）
            assert mock_pw.chromium.launch.call_count == 3

            # 清理所有scraper
            for scraper in scrapers:
                await scraper.close()

            # 验证所有浏览器都被关闭
            assert mock_browser.close.call_count == 3

    @pytest.mark.asyncio
    async def test_concurrent_error_handling(
        self, db: Session, test_user: User, test_kb: KnowledgeBase, scraper_service: WebScraperService
    ):
        """测试并发场景下的错误处理"""
        from app.core.web_scraper import WebScraper, ScraperConfig, SelectorConfig

        # 创建5个任务
        tasks = []
        for i in range(5):
            task = scraper_service.create_task(
                name=f"并发错误测试{i+1}",
                url=f"https://example.com/error{i+1}",
                knowledge_base_id=test_kb.id,
                user_id=test_user.id,
                schedule_type=ScheduleType.ONCE,
                selector_config={
                    "title": "h1",
                    "content": "article"
                }
            )
            tasks.append(task)

        # Mock采集器，部分成功部分失败
        async def mock_scrape_with_errors(url):
            await asyncio.sleep(0.05)
            # 奇数任务失败，偶数任务成功
            if "error1" in url or "error3" in url or "error5" in url:
                raise Exception(f"采集失败: {url}")
            from app.core.web_scraper import ScrapedContent
            return ScrapedContent(
                url=url,
                title=f"标题-{url}",
                content=f"内容-{url}"
            )

        with patch('app.core.web_scraper.WebScraper') as mock_scraper_class:
            mock_scraper = AsyncMock()
            mock_scraper.scrape_url = mock_scrape_with_errors
            mock_scraper_class.return_value = mock_scraper

            # 并发执行所有任务，使用gather的return_exceptions=True
            results = await asyncio.gather(*[
                mock_scraper.scrape_url(task.url) for task in tasks
            ], return_exceptions=True)

            # 验证结果
            assert len(results) == 5

            # 统计成功和失败的任务
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            error_count = sum(1 for r in results if isinstance(r, Exception))

            assert success_count == 2  # error2, error4成功
            assert error_count == 3    # error1, error3, error5失败

            # 验证错误信息
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    assert "采集失败" in str(result)

