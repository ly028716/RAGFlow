"""
Web Scraper 调度器测试
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.core.scheduler import (
    DistributedLock,
    ScraperScheduler,
    initialize_scheduler,
    shutdown_scheduler,
    get_scheduler,
)


@pytest.fixture
async def mock_redis():
    """创建Mock Redis客户端"""
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.eval = AsyncMock(return_value=1)
    redis.close = AsyncMock()
    return redis


@pytest.fixture
async def scheduler(mock_redis):
    """创建调度器实例"""
    scheduler = ScraperScheduler(mock_redis, max_concurrent_tasks=3)
    await scheduler.initialize()
    yield scheduler
    await scheduler.shutdown()


class TestDistributedLock:
    """测试分布式锁"""

    @pytest.mark.asyncio
    async def test_acquire_lock_success(self, mock_redis):
        """测试成功获取锁"""
        mock_redis.set.return_value = True

        lock = DistributedLock(mock_redis, "test_lock", timeout=60)
        result = await lock.acquire()

        assert result is True
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "scraper:lock:test_lock"
        assert call_args[1]["nx"] is True
        assert call_args[1]["ex"] == 60

    @pytest.mark.asyncio
    async def test_acquire_lock_failure(self, mock_redis):
        """测试获取锁失败（锁已被占用）"""
        mock_redis.set.return_value = False

        lock = DistributedLock(mock_redis, "test_lock")
        result = await lock.acquire()

        assert result is False

    @pytest.mark.asyncio
    async def test_release_lock_success(self, mock_redis):
        """测试成功释放锁"""
        mock_redis.set.return_value = True
        mock_redis.eval.return_value = 1

        lock = DistributedLock(mock_redis, "test_lock")
        await lock.acquire()
        result = await lock.release()

        assert result is True
        mock_redis.eval.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_lock_not_owner(self, mock_redis):
        """测试释放不属于自己的锁"""
        mock_redis.set.return_value = True
        mock_redis.eval.return_value = 0  # 锁不属于当前持有者

        lock = DistributedLock(mock_redis, "test_lock")
        await lock.acquire()
        result = await lock.release()

        assert result is False

    @pytest.mark.asyncio
    async def test_extend_lock_success(self, mock_redis):
        """测试成功延长锁"""
        mock_redis.set.return_value = True
        mock_redis.eval.return_value = 1

        lock = DistributedLock(mock_redis, "test_lock")
        await lock.acquire()
        result = await lock.extend(additional_time=30)

        assert result is True

    @pytest.mark.asyncio
    async def test_lock_context_manager(self, mock_redis):
        """测试锁的上下文管理器"""
        mock_redis.set.return_value = True
        mock_redis.eval.return_value = 1

        lock = DistributedLock(mock_redis, "test_lock")

        async with lock() as acquired:
            assert acquired is True
            mock_redis.set.assert_called_once()

        # 验证锁已释放
        mock_redis.eval.assert_called_once()


class TestScraperScheduler:
    """测试调度器"""

    @pytest.mark.asyncio
    async def test_scheduler_initialization(self, mock_redis):
        """测试调度器初始化"""
        scheduler = ScraperScheduler(mock_redis, max_concurrent_tasks=5)
        await scheduler.initialize()

        assert scheduler.is_running is True
        assert scheduler.max_concurrent_tasks == 5
        assert scheduler.running_task_count == 0

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_add_job_success(self, scheduler):
        """测试成功添加任务"""
        callback = AsyncMock()

        result = scheduler.add_job(
            job_id="test_job_1",
            cron_expression="0 0 * * *",
            callback=callback,
            param1="value1"
        )

        assert result is True
        assert "test_job_1" in scheduler._task_callbacks

    @pytest.mark.asyncio
    async def test_add_job_invalid_cron(self, scheduler):
        """测试添加无效Cron表达式的任务"""
        callback = AsyncMock()

        result = scheduler.add_job(
            job_id="test_job_2",
            cron_expression="invalid cron",
            callback=callback
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_remove_job_success(self, scheduler):
        """测试成功删除任务"""
        callback = AsyncMock()

        scheduler.add_job(
            job_id="test_job_3",
            cron_expression="0 0 * * *",
            callback=callback
        )

        result = scheduler.remove_job("test_job_3")

        assert result is True
        assert "test_job_3" not in scheduler._task_callbacks

    @pytest.mark.asyncio
    async def test_remove_nonexistent_job(self, scheduler):
        """测试删除不存在的任务"""
        result = scheduler.remove_job("nonexistent_job")

        assert result is False

    @pytest.mark.asyncio
    async def test_pause_job_success(self, scheduler):
        """测试成功暂停任务"""
        callback = AsyncMock()

        scheduler.add_job(
            job_id="test_job_4",
            cron_expression="0 0 * * *",
            callback=callback
        )

        result = scheduler.pause_job("test_job_4")

        assert result is True

    @pytest.mark.asyncio
    async def test_resume_job_success(self, scheduler):
        """测试成功恢复任务"""
        callback = AsyncMock()

        scheduler.add_job(
            job_id="test_job_5",
            cron_expression="0 0 * * *",
            callback=callback
        )
        scheduler.pause_job("test_job_5")

        result = scheduler.resume_job("test_job_5")

        assert result is True

    @pytest.mark.asyncio
    async def test_get_job_info(self, scheduler):
        """测试获取任务信息"""
        callback = AsyncMock()

        scheduler.add_job(
            job_id="test_job_6",
            cron_expression="0 0 * * *",
            callback=callback
        )

        job_info = scheduler.get_job("test_job_6")

        assert job_info is not None
        assert job_info["id"] == "test_job_6"
        assert "next_run_time" in job_info
        assert "trigger" in job_info

    @pytest.mark.asyncio
    async def test_get_all_jobs(self, scheduler):
        """测试获取所有任务"""
        callback = AsyncMock()

        scheduler.add_job("job1", "0 0 * * *", callback)
        scheduler.add_job("job2", "0 1 * * *", callback)

        jobs = scheduler.get_all_jobs()

        assert len(jobs) >= 2
        job_ids = [job["id"] for job in jobs]
        assert "job1" in job_ids
        assert "job2" in job_ids

    @pytest.mark.asyncio
    async def test_concurrent_task_limit(self, scheduler, mock_redis):
        """测试并发任务限制"""
        # 设置最大并发为3
        scheduler.max_concurrent_tasks = 3

        # 模拟3个正在运行的任务
        scheduler._running_tasks = {
            "task1": asyncio.create_task(asyncio.sleep(10)),
            "task2": asyncio.create_task(asyncio.sleep(10)),
            "task3": asyncio.create_task(asyncio.sleep(10)),
        }

        # 尝试执行第4个任务应该被跳过
        mock_redis.set.return_value = True
        callback = AsyncMock()
        scheduler._task_callbacks["test_job"] = callback

        await scheduler._execute_job("test_job", {})

        # 由于达到并发限制，回调不应该被执行
        callback.assert_not_called()

        # 清理
        for task in scheduler._running_tasks.values():
            task.cancel()

    @pytest.mark.asyncio
    async def test_job_execution_with_async_callback(self, scheduler, mock_redis):
        """测试异步回调函数执行"""
        mock_redis.set.return_value = True
        mock_redis.eval.return_value = 1

        # 创建异步回调
        callback = AsyncMock()
        callback.return_value = "success"

        scheduler._task_callbacks["test_job"] = callback

        # 执行任务
        await scheduler._execute_job("test_job", {"param1": "value1"})

        # 验证回调被调用
        callback.assert_called_once_with(param1="value1")

    @pytest.mark.asyncio
    async def test_job_execution_with_sync_callback(self, scheduler, mock_redis):
        """测试同步回调函数执行"""
        mock_redis.set.return_value = True
        mock_redis.eval.return_value = 1

        # 创建同步回调
        callback = MagicMock()
        callback.return_value = "success"

        scheduler._task_callbacks["test_job"] = callback

        # 执行任务
        await scheduler._execute_job("test_job", {"param1": "value1"})

        # 验证回调被调用
        callback.assert_called_once_with(param1="value1")

    @pytest.mark.asyncio
    async def test_job_execution_failure_handling(self, scheduler, mock_redis):
        """测试任务执行失败处理"""
        mock_redis.set.return_value = True
        mock_redis.eval.return_value = 1

        # 创建会抛出异常的回调
        callback = AsyncMock()
        callback.side_effect = Exception("Task execution failed")

        scheduler._task_callbacks["test_job"] = callback

        # 执行任务应该捕获异常
        with pytest.raises(Exception, match="Task execution failed"):
            await scheduler._execute_job("test_job", {})

    @pytest.mark.asyncio
    async def test_job_execution_without_lock(self, scheduler, mock_redis):
        """测试无法获取锁时跳过任务执行"""
        mock_redis.set.return_value = False  # 无法获取锁

        callback = AsyncMock()
        scheduler._task_callbacks["test_job"] = callback

        # 执行任务
        await scheduler._execute_job("test_job", {})

        # 验证回调未被调用
        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_job_callback_not_found(self, scheduler, mock_redis):
        """测试回调函数不存在"""
        mock_redis.set.return_value = True
        mock_redis.eval.return_value = 1

        # 不设置回调函数
        # 执行任务
        await scheduler._execute_job("nonexistent_job", {})

        # 应该记录错误但不抛出异常

    @pytest.mark.asyncio
    async def test_duplicate_job_id(self, scheduler):
        """测试添加重复的任务ID"""
        callback = AsyncMock()

        # 添加第一个任务
        result1 = scheduler.add_job(
            job_id="duplicate_job",
            cron_expression="0 0 * * *",
            callback=callback
        )
        assert result1 is True

        # 添加相同ID的任务（应该替换）
        result2 = scheduler.add_job(
            job_id="duplicate_job",
            cron_expression="0 1 * * *",
            callback=callback
        )
        assert result2 is True

        # 验证只有一个任务
        job_info = scheduler.get_job("duplicate_job")
        assert job_info is not None

    @pytest.mark.asyncio
    async def test_cron_expression_variations(self, scheduler):
        """测试各种Cron表达式"""
        callback = AsyncMock()

        # 测试每天午夜
        assert scheduler.add_job("job1", "0 0 * * *", callback) is True

        # 测试每小时
        assert scheduler.add_job("job2", "0 * * * *", callback) is True

        # 测试每周一
        assert scheduler.add_job("job3", "0 0 * * 1", callback) is True

        # 测试每月1号
        assert scheduler.add_job("job4", "0 0 1 * *", callback) is True

        # 测试每5分钟
        assert scheduler.add_job("job5", "*/5 * * * *", callback) is True

        # 验证所有任务都已添加
        jobs = scheduler.get_all_jobs()
        assert len(jobs) >= 5

    @pytest.mark.asyncio
    async def test_scheduler_running_state(self, scheduler):
        """测试调度器运行状态"""
        assert scheduler.is_running is True
        assert scheduler.running_task_count == 0

        # 模拟添加运行中的任务
        scheduler._running_tasks["task1"] = asyncio.create_task(asyncio.sleep(0.1))
        assert scheduler.running_task_count == 1

        # 等待任务完成
        await asyncio.sleep(0.2)
        scheduler._running_tasks.clear()
        assert scheduler.running_task_count == 0

    @pytest.mark.asyncio
    async def test_scheduler_shutdown_with_running_tasks(self, mock_redis):
        """测试关闭调度器时等待运行中的任务"""
        scheduler = ScraperScheduler(mock_redis, max_concurrent_tasks=3)
        await scheduler.initialize()

        # 添加运行中的任务
        async def long_task():
            await asyncio.sleep(0.1)

        scheduler._running_tasks["task1"] = asyncio.create_task(long_task())
        scheduler._running_tasks["task2"] = asyncio.create_task(long_task())

        # 关闭调度器应该等待任务完成
        await scheduler.shutdown()

        assert scheduler.is_running is False
        assert len(scheduler._running_tasks) == 0

    @pytest.mark.asyncio
    async def test_job_next_run_time(self, scheduler):
        """测试任务下次运行时间"""
        callback = AsyncMock()

        scheduler.add_job(
            job_id="test_job",
            cron_expression="0 0 * * *",  # 每天午夜
            callback=callback
        )

        job_info = scheduler.get_job("test_job")
        assert job_info is not None
        assert job_info["next_run_time"] is not None
        assert isinstance(job_info["next_run_time"], datetime)


class TestGlobalScheduler:
    """测试全局调度器实例"""

    @pytest.mark.asyncio
    async def test_initialize_global_scheduler(self, mock_redis):
        """测试初始化全局调度器"""
        await initialize_scheduler(mock_redis, max_concurrent_tasks=5)

        scheduler = get_scheduler()
        assert scheduler is not None
        assert scheduler.is_running is True

        await shutdown_scheduler()

    @pytest.mark.asyncio
    async def test_get_scheduler_before_init(self):
        """测试在初始化前获取调度器"""
        # 确保全局调度器未初始化
        from app.core import scheduler as scheduler_module
        scheduler_module._scheduler_instance = None

        with pytest.raises(RuntimeError, match="调度器未初始化"):
            get_scheduler()

    @pytest.mark.asyncio
    async def test_shutdown_global_scheduler(self, mock_redis):
        """测试关闭全局调度器"""
        await initialize_scheduler(mock_redis)

        await shutdown_scheduler()

        # 验证调度器已关闭
        from app.core import scheduler as scheduler_module
        assert scheduler_module._scheduler_instance is None
