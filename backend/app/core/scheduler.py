"""
任务调度系统

基于APScheduler的网页采集任务调度器，支持：
- Cron表达式定时任务
- 分布式锁防止重复执行
- 任务生命周期管理
- 并发控制
"""

import asyncio
import logging
from datetime import datetime
from typing import Callable, Dict, Optional, List
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, JobExecutionEvent
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)


class DistributedLock:
    """Redis分布式锁"""

    def __init__(self, redis_client: Redis, lock_name: str, timeout: int = 300):
        """
        初始化分布式锁

        Args:
            redis_client: Redis客户端
            lock_name: 锁名称
            timeout: 锁超时时间（秒），默认5分钟
        """
        self.redis = redis_client
        self.lock_name = f"scraper:lock:{lock_name}"
        self.timeout = timeout
        self.lock_value = None

    async def acquire(self) -> bool:
        """
        获取锁

        Returns:
            bool: 是否成功获取锁
        """
        try:
            # 使用当前时间戳作为锁值，用于验证锁的所有权
            self.lock_value = str(datetime.utcnow().timestamp())
            result = await self.redis.set(
                self.lock_name,
                self.lock_value,
                nx=True,  # 只在键不存在时设置
                ex=self.timeout  # 设置过期时间
            )
            if result:
                logger.debug(f"成功获取锁: {self.lock_name}")
            return bool(result)
        except RedisError as e:
            logger.error(f"获取锁失败: {self.lock_name}, 错误: {str(e)}")
            return False

    async def release(self) -> bool:
        """
        释放锁

        Returns:
            bool: 是否成功释放锁
        """
        try:
            # 使用Lua脚本确保只释放自己持有的锁
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            result = await self.redis.eval(lua_script, 1, self.lock_name, self.lock_value)
            if result:
                logger.debug(f"成功释放锁: {self.lock_name}")
            return bool(result)
        except RedisError as e:
            logger.error(f"释放锁失败: {self.lock_name}, 错误: {str(e)}")
            return False

    async def extend(self, additional_time: int = 60) -> bool:
        """
        延长锁的过期时间

        Args:
            additional_time: 延长的时间（秒）

        Returns:
            bool: 是否成功延长
        """
        try:
            # 使用Lua脚本确保只延长自己持有的锁
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("expire", KEYS[1], ARGV[2])
            else
                return 0
            end
            """
            result = await self.redis.eval(
                lua_script, 1, self.lock_name, self.lock_value, str(additional_time)
            )
            return bool(result)
        except RedisError as e:
            logger.error(f"延长锁失败: {self.lock_name}, 错误: {str(e)}")
            return False

    @asynccontextmanager
    async def __call__(self):
        """上下文管理器支持"""
        acquired = await self.acquire()
        try:
            yield acquired
        finally:
            if acquired:
                await self.release()


class ScraperScheduler:
    """
    网页采集任务调度器

    使用APScheduler管理定时任务，支持：
    - Cron表达式定时执行
    - 分布式锁防止重复执行
    - 任务生命周期管理
    - 并发控制
    """

    def __init__(self, redis_client: Redis, max_concurrent_tasks: int = 5):
        """
        初始化调度器

        Args:
            redis_client: Redis客户端
            max_concurrent_tasks: 最大并发任务数
        """
        self.redis = redis_client
        self.max_concurrent_tasks = max_concurrent_tasks
        self.scheduler = AsyncIOScheduler(
            timezone="Asia/Shanghai",
            job_defaults={
                'coalesce': True,  # 合并错过的执行
                'max_instances': 1,  # 每个任务最多1个实例
                'misfire_grace_time': 300  # 错过执行的宽限时间（5分钟）
            }
        )
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._task_callbacks: Dict[str, Callable] = {}
        self._initialized = False

        # 注册事件监听器
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )

    async def initialize(self):
        """初始化调度器"""
        if self._initialized:
            return

        try:
            logger.info("初始化任务调度器")
            self.scheduler.start()
            self._initialized = True
            logger.info("任务调度器初始化成功")
        except Exception as e:
            logger.error(f"调度器初始化失败: {str(e)}")
            raise

    async def shutdown(self):
        """关闭调度器"""
        if not self._initialized:
            return

        try:
            logger.info("关闭任务调度器")

            # 等待所有运行中的任务完成
            if self._running_tasks:
                logger.info(f"等待 {len(self._running_tasks)} 个任务完成")
                await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
                # 清理已完成的任务
                self._running_tasks.clear()

            # 关闭调度器
            self.scheduler.shutdown(wait=True)
            self._initialized = False
            logger.info("任务调度器已关闭")
        except Exception as e:
            logger.error(f"关闭调度器失败: {str(e)}")

    def add_job(
        self,
        job_id: str,
        cron_expression: str,
        callback: Callable,
        **kwargs
    ) -> bool:
        """
        添加定时任务

        Args:
            job_id: 任务ID（唯一标识）
            cron_expression: Cron表达式
            callback: 任务执行回调函数
            **kwargs: 传递给回调函数的参数

        Returns:
            bool: 是否成功添加
        """
        try:
            # 解析Cron表达式
            trigger = CronTrigger.from_crontab(cron_expression, timezone="Asia/Shanghai")

            # 保存回调函数
            self._task_callbacks[job_id] = callback

            # 添加任务到调度器
            self.scheduler.add_job(
                func=self._execute_job,
                trigger=trigger,
                id=job_id,
                kwargs={'job_id': job_id, 'callback_kwargs': kwargs},
                replace_existing=True
            )

            logger.info(f"成功添加定时任务: {job_id}, Cron: {cron_expression}")
            return True
        except Exception as e:
            logger.error(f"添加定时任务失败: {job_id}, 错误: {str(e)}")
            return False

    def remove_job(self, job_id: str) -> bool:
        """
        删除定时任务

        Args:
            job_id: 任务ID

        Returns:
            bool: 是否成功删除
        """
        try:
            self.scheduler.remove_job(job_id)
            self._task_callbacks.pop(job_id, None)
            logger.info(f"成功删除定时任务: {job_id}")
            return True
        except Exception as e:
            logger.error(f"删除定时任务失败: {job_id}, 错误: {str(e)}")
            return False

    def pause_job(self, job_id: str) -> bool:
        """
        暂停定时任务

        Args:
            job_id: 任务ID

        Returns:
            bool: 是否成功暂停
        """
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"成功暂停定时任务: {job_id}")
            return True
        except Exception as e:
            logger.error(f"暂停定时任务失败: {job_id}, 错误: {str(e)}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """
        恢复定时任务

        Args:
            job_id: 任务ID

        Returns:
            bool: 是否成功恢复
        """
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"成功恢复定时任务: {job_id}")
            return True
        except Exception as e:
            logger.error(f"恢复定时任务失败: {job_id}, 错误: {str(e)}")
            return False

    def get_job(self, job_id: str) -> Optional[Dict]:
        """
        获取任务信息

        Args:
            job_id: 任务ID

        Returns:
            Optional[Dict]: 任务信息
        """
        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                return None

            return {
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time,
                'trigger': str(job.trigger),
            }
        except Exception as e:
            logger.error(f"获取任务信息失败: {job_id}, 错误: {str(e)}")
            return None

    def get_all_jobs(self) -> List[Dict]:
        """
        获取所有任务信息

        Returns:
            List[Dict]: 任务信息列表
        """
        try:
            jobs = self.scheduler.get_jobs()
            return [
                {
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time,
                    'trigger': str(job.trigger),
                }
                for job in jobs
            ]
        except Exception as e:
            logger.error(f"获取任务列表失败: {str(e)}")
            return []

    async def _execute_job(self, job_id: str, callback_kwargs: Dict):
        """
        执行任务（内部方法）

        Args:
            job_id: 任务ID
            callback_kwargs: 回调函数参数
        """
        # 检查并发限制
        if len(self._running_tasks) >= self.max_concurrent_tasks:
            logger.warning(f"达到最大并发限制 ({self.max_concurrent_tasks})，跳过任务: {job_id}")
            return

        # 获取分布式锁
        lock = DistributedLock(self.redis, job_id, timeout=3600)  # 1小时超时

        async with lock() as acquired:
            if not acquired:
                logger.warning(f"无法获取锁，任务可能正在其他实例执行: {job_id}")
                return

            # 获取回调函数
            callback = self._task_callbacks.get(job_id)
            if not callback:
                logger.error(f"任务回调函数不存在: {job_id}")
                return

            # 创建任务
            task = asyncio.create_task(self._run_callback(job_id, callback, callback_kwargs))
            self._running_tasks[job_id] = task

            try:
                await task
            finally:
                self._running_tasks.pop(job_id, None)

    async def _run_callback(self, job_id: str, callback: Callable, kwargs: Dict):
        """
        运行回调函数

        Args:
            job_id: 任务ID
            callback: 回调函数
            kwargs: 参数
        """
        try:
            logger.info(f"开始执行任务: {job_id}")
            start_time = datetime.utcnow()

            # 执行回调
            if asyncio.iscoroutinefunction(callback):
                await callback(**kwargs)
            else:
                await asyncio.to_thread(callback, **kwargs)

            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"任务执行成功: {job_id}, 耗时: {duration:.2f}秒")
        except Exception as e:
            logger.error(f"任务执行失败: {job_id}, 错误: {str(e)}", exc_info=True)
            raise

    def _job_executed_listener(self, event: JobExecutionEvent):
        """
        任务执行事件监听器

        Args:
            event: 任务执行事件
        """
        if event.exception:
            logger.error(
                f"任务执行异常: {event.job_id}, "
                f"异常: {str(event.exception)}"
            )
        else:
            logger.debug(f"任务执行完成: {event.job_id}")

    @property
    def is_running(self) -> bool:
        """调度器是否运行中"""
        return self._initialized and self.scheduler.running

    @property
    def running_task_count(self) -> int:
        """当前运行中的任务数"""
        return len(self._running_tasks)


# 全局调度器实例（由应用启动时初始化）
_scheduler_instance: Optional[ScraperScheduler] = None


def get_scheduler() -> ScraperScheduler:
    """
    获取全局调度器实例

    Returns:
        ScraperScheduler: 调度器实例

    Raises:
        RuntimeError: 调度器未初始化
    """
    if _scheduler_instance is None:
        raise RuntimeError("调度器未初始化，请先调用 initialize_scheduler()")
    return _scheduler_instance


async def initialize_scheduler(redis_client: Redis, max_concurrent_tasks: int = 5):
    """
    初始化全局调度器

    Args:
        redis_client: Redis客户端
        max_concurrent_tasks: 最大并发任务数
    """
    global _scheduler_instance
    if _scheduler_instance is not None:
        logger.warning("调度器已初始化，跳过重复初始化")
        return

    _scheduler_instance = ScraperScheduler(redis_client, max_concurrent_tasks)
    await _scheduler_instance.initialize()


async def shutdown_scheduler():
    """关闭全局调度器"""
    global _scheduler_instance
    if _scheduler_instance is not None:
        await _scheduler_instance.shutdown()
        _scheduler_instance = None
