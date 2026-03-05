"""
Redis缓存工具模块

提供缓存装饰器和缓存管理功能，用于优化数据库查询性能。
"""

import json
import logging
import functools
from typing import Any, Callable, Optional, Union
from datetime import timedelta

from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)


class CacheKeyBuilder:
    """缓存键构建器"""

    @staticmethod
    def build_key(prefix: str, *args, **kwargs) -> str:
        """
        构建缓存键

        Args:
            prefix: 键前缀
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            str: 缓存键
        """
        parts = [prefix]

        # 添加位置参数
        for arg in args:
            if arg is not None:
                parts.append(str(arg))

        # 添加关键字参数（排序以保证一致性）
        for key in sorted(kwargs.keys()):
            value = kwargs[key]
            if value is not None:
                parts.append(f"{key}:{value}")

        return ":".join(parts)


def cache_result(
    key_prefix: str,
    ttl: int = 300,
    key_builder: Optional[Callable] = None
):
    """
    缓存函数结果的装饰器

    Args:
        key_prefix: 缓存键前缀
        ttl: 过期时间（秒），默认300秒
        key_builder: 自定义键构建函数

    Example:
        @cache_result("task_list", ttl=60)
        def list_tasks(self, user_id: int, status: str = None):
            return self.task_repo.get_all(user_id=user_id, status=status)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 获取Redis客户端
            redis_client = get_redis_client()
            if not redis_client:
                logger.warning("Redis客户端不可用，跳过缓存")
                return func(*args, **kwargs)

            # 构建缓存键
            if key_builder:
                cache_key = key_builder(key_prefix, *args, **kwargs)
            else:
                # 跳过self参数（如果是方法）
                cache_args = args[1:] if args and hasattr(args[0], '__dict__') else args
                cache_key = CacheKeyBuilder.build_key(key_prefix, *cache_args, **kwargs)

            try:
                # 尝试从缓存获取
                cached_value = redis_client.get(cache_key)
                if cached_value:
                    logger.debug(f"缓存命中: {cache_key}")
                    return json.loads(cached_value)

                # 缓存未命中，执行函数
                logger.debug(f"缓存未命中: {cache_key}")
                result = func(*args, **kwargs)

                # 存入缓存
                if result is not None:
                    redis_client.setex(
                        cache_key,
                        ttl,
                        json.dumps(result, default=str)
                    )
                    logger.debug(f"已缓存结果: {cache_key}, TTL: {ttl}秒")

                return result

            except Exception as e:
                logger.error(f"缓存操作失败: {str(e)}", exc_info=True)
                # 缓存失败时直接执行函数
                return func(*args, **kwargs)

        return wrapper
    return decorator


async def cache_result_async(
    key_prefix: str,
    ttl: int = 300,
    key_builder: Optional[Callable] = None
):
    """
    缓存异步函数结果的装饰器

    Args:
        key_prefix: 缓存键前缀
        ttl: 过期时间（秒），默认300秒
        key_builder: 自定义键构建函数

    Example:
        @cache_result_async("task_detail", ttl=120)
        async def get_task(self, task_id: int):
            return await self.task_repo.get_by_id(task_id)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # 获取Redis客户端
            redis_client = get_redis_client()
            if not redis_client:
                logger.warning("Redis客户端不可用，跳过缓存")
                return await func(*args, **kwargs)

            # 构建缓存键
            if key_builder:
                cache_key = key_builder(key_prefix, *args, **kwargs)
            else:
                cache_args = args[1:] if args and hasattr(args[0], '__dict__') else args
                cache_key = CacheKeyBuilder.build_key(key_prefix, *cache_args, **kwargs)

            try:
                # 尝试从缓存获取
                cached_value = redis_client.get(cache_key)
                if cached_value:
                    logger.debug(f"缓存命中: {cache_key}")
                    return json.loads(cached_value)

                # 缓存未命中，执行函数
                logger.debug(f"缓存未命中: {cache_key}")
                result = await func(*args, **kwargs)

                # 存入缓存
                if result is not None:
                    redis_client.setex(
                        cache_key,
                        ttl,
                        json.dumps(result, default=str)
                    )
                    logger.debug(f"已缓存结果: {cache_key}, TTL: {ttl}秒")

                return result

            except Exception as e:
                logger.error(f"缓存操作失败: {str(e)}", exc_info=True)
                return await func(*args, **kwargs)

        return wrapper
    return decorator


class CacheManager:
    """缓存管理器"""

    @staticmethod
    def invalidate_pattern(pattern: str) -> int:
        """
        删除匹配模式的所有缓存键

        Args:
            pattern: 键模式（支持通配符*）

        Returns:
            int: 删除的键数量
        """
        redis_client = get_redis_client()
        if not redis_client:
            logger.warning("Redis客户端不可用")
            return 0

        try:
            # 查找匹配的键
            keys = redis_client.keys(pattern)
            if not keys:
                return 0

            # 删除键
            deleted = redis_client.delete(*keys)
            logger.info(f"已删除 {deleted} 个缓存键，模式: {pattern}")
            return deleted

        except Exception as e:
            logger.error(f"删除缓存失败: {str(e)}", exc_info=True)
            return 0

    @staticmethod
    def invalidate_key(key: str) -> bool:
        """
        删除指定的缓存键

        Args:
            key: 缓存键

        Returns:
            bool: 是否成功删除
        """
        redis_client = get_redis_client()
        if not redis_client:
            logger.warning("Redis客户端不可用")
            return False

        try:
            deleted = redis_client.delete(key)
            if deleted:
                logger.debug(f"已删除缓存键: {key}")
            return deleted > 0

        except Exception as e:
            logger.error(f"删除缓存键失败: {str(e)}", exc_info=True)
            return False

    @staticmethod
    def clear_all() -> bool:
        """
        清空所有缓存（谨慎使用）

        Returns:
            bool: 是否成功
        """
        redis_client = get_redis_client()
        if not redis_client:
            logger.warning("Redis客户端不可用")
            return False

        try:
            redis_client.flushdb()
            logger.warning("已清空所有缓存")
            return True

        except Exception as e:
            logger.error(f"清空缓存失败: {str(e)}", exc_info=True)
            return False


# 缓存键前缀常量
class CacheKeys:
    """缓存键前缀常量"""

    # Web Scraper相关
    TASK_LIST = "scraper:task:list"
    TASK_DETAIL = "scraper:task:detail"
    TASK_STATS = "scraper:task:stats"
    LOG_LIST = "scraper:log:list"
    LOG_STATS = "scraper:log:stats"

    # 知识库相关
    KB_LIST = "kb:list"
    KB_DETAIL = "kb:detail"

    # 用户相关
    USER_DETAIL = "user:detail"
