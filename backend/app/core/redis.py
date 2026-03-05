"""
Redis连接管理模块

配置Redis连接池、超时设置和依赖注入函数。
用于缓存、会话存储、登录尝试记录、配额管理等功能。
"""

from typing import Generator, Optional

import redis
from redis import ConnectionPool, Redis
from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

from app.config import settings

# 创建Redis连接池
# max_connections: 连接池最大连接数
# socket_timeout: socket超时时间（秒）
# socket_connect_timeout: 连接超时时间（秒）
# socket_keepalive: 启用TCP keepalive
# decode_responses: 自动解码响应为字符串
redis_pool = ConnectionPool(
    host=settings.redis.redis_host,
    port=settings.redis.redis_port,
    password=settings.redis.redis_password,
    db=settings.redis.redis_db,
    max_connections=50,
    socket_timeout=5,
    socket_connect_timeout=5,
    socket_keepalive=True,
    decode_responses=True,
    encoding="utf-8",
)


# 创建Redis客户端实例
redis_client: Optional[Redis] = None

# 创建异步Redis客户端实例
async_redis_client: Optional[AsyncRedis] = None


def get_redis_client() -> Redis:
    """
    获取Redis客户端实例

    使用单例模式，确保整个应用使用同一个Redis客户端。

    Returns:
        Redis: Redis客户端实例
    """
    global redis_client
    if redis_client is None:
        redis_client = Redis(connection_pool=redis_pool)
    return redis_client


def get_redis() -> Generator[Redis, None, None]:
    """
    Redis依赖函数

    用于FastAPI的依赖注入，提供Redis客户端实例。
    自动处理连接的获取和释放。

    使用方式:
        @app.get("/cache")
        def get_cache(redis: Redis = Depends(get_redis)):
            value = redis.get("key")
            return {"value": value}

    Yields:
        Redis: Redis客户端实例
    """
    client = get_redis_client()
    try:
        yield client
    except RedisError as e:
        # 记录Redis错误但不中断请求
        print(f"Redis错误: {e}")
        raise
    finally:
        # Redis连接池会自动管理连接，无需手动关闭
        pass


def ping_redis() -> bool:
    """
    测试Redis连接

    用于健康检查，验证Redis服务是否可用。

    Returns:
        bool: Redis连接是否正常
    """
    try:
        client = get_redis_client()
        return client.ping()
    except (RedisError, RedisConnectionError) as e:
        print(f"Redis连接测试失败: {e}")
        return False


def get_async_redis_client() -> AsyncRedis:
    """
    获取异步Redis客户端实例

    使用单例模式，确保整个应用使用同一个异步Redis客户端。
    用于需要异步操作的场景，如任务调度器。

    Returns:
        AsyncRedis: 异步Redis客户端实例
    """
    global async_redis_client
    if async_redis_client is None:
        async_redis_client = AsyncRedis(
            host=settings.redis.redis_host,
            port=settings.redis.redis_port,
            password=settings.redis.redis_password,
            db=settings.redis.redis_db,
            decode_responses=True,
            encoding="utf-8",
        )
    return async_redis_client


def close_redis() -> None:
    """
    关闭Redis连接

    在应用关闭时调用，清理Redis连接池。
    """
    global redis_client
    if redis_client is not None:
        redis_client.close()
        redis_client = None

    if redis_pool is not None:
        redis_pool.disconnect()


async def close_async_redis() -> None:
    """
    关闭异步Redis连接

    在应用关闭时调用，清理异步Redis连接。
    """
    global async_redis_client
    if async_redis_client is not None:
        await async_redis_client.close()
        async_redis_client = None


# Redis键命名空间常量
class RedisKeys:
    """
    Redis键命名规范

    统一管理Redis键的命名，避免键冲突。
    """

    # 用户相关
    USER_INFO = "user:{user_id}:info"
    USER_TOKEN_BLACKLIST = "user:token:blacklist:{token}"

    # 登录尝试
    LOGIN_ATTEMPTS = "login:attempts:{username}"
    ACCOUNT_LOCKED = "login:locked:{username}"

    # 配额管理
    USER_QUOTA = "quota:{user_id}:monthly"
    USER_QUOTA_USED = "quota:{user_id}:used"

    # 缓存
    CONVERSATION_LIST = "cache:conversations:{user_id}"
    KNOWLEDGE_BASE_LIST = "cache:knowledge_bases:{user_id}"
    SYSTEM_CONFIG = "cache:system:config"

    # 文档处理进度
    DOCUMENT_PROGRESS = "document:{document_id}:progress"

    # Agent执行状态
    AGENT_EXECUTION = "agent:execution:{execution_id}"

    # WebSocket连接
    WS_CONNECTION = "ws:connection:{user_id}"

    @staticmethod
    def format_key(template: str, **kwargs) -> str:
        """
        格式化Redis键

        Args:
            template: 键模板
            **kwargs: 模板参数

        Returns:
            str: 格式化后的键
        """
        return template.format(**kwargs)


# 导出
__all__ = [
    "redis_pool",
    "redis_client",
    "async_redis_client",
    "get_redis_client",
    "get_async_redis_client",
    "get_redis",
    "ping_redis",
    "close_redis",
    "close_async_redis",
    "RedisKeys",
]
