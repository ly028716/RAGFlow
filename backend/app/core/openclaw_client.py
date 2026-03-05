"""
OpenClaw Gateway API 客户端

提供与 OpenClaw Gateway 通信的统一接口，包括：
- 健康检查
- 消息发送
- 连接管理
- 错误处理和重试
- 熔断器模式
- 健康检查缓存
"""

import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# 熔断器状态
# ============================================================================


class CircuitState(str, Enum):
    """熔断器状态"""

    CLOSED = "closed"  # 正常状态，允许请求通过
    OPEN = "open"  # 熔断状态，拒绝请求
    HALF_OPEN = "half_open"  # 半开状态，允许部分请求通过以测试恢复


class CircuitBreaker:
    """
    熔断器实现

    当连续失败次数达到阈值时，熔断器打开，拒绝所有请求。
    经过一段时间后，熔断器进入半开状态，允许部分请求通过。
    如果请求成功，熔断器关闭；如果失败，熔断器重新打开。
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        """
        初始化熔断器

        Args:
            failure_threshold: 失败阈值，连续失败次数达到此值时打开熔断器
            recovery_timeout: 恢复超时时间（秒），熔断器打开后等待此时间进入半开状态
            expected_exception: 预期的异常类型
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED

    def call(self, func, *args, **kwargs):
        """
        通过熔断器调用函数

        Args:
            func: 要调用的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            函数返回值

        Raises:
            OpenClawCircuitBreakerError: 熔断器打开时抛出
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("熔断器进入半开状态，尝试恢复")
            else:
                raise OpenClawCircuitBreakerError("熔断器已打开，拒绝请求")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    async def call_async(self, func, *args, **kwargs):
        """
        通过熔断器调用异步函数

        Args:
            func: 要调用的异步函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            函数返回值

        Raises:
            OpenClawCircuitBreakerError: 熔断器打开时抛出
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("熔断器进入半开状态，尝试恢复")
            else:
                raise OpenClawCircuitBreakerError("熔断器已打开，拒绝请求")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """判断是否应该尝试重置熔断器"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout

    def _on_success(self):
        """请求成功时的处理"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("熔断器已关闭，服务恢复正常")

    def _on_failure(self):
        """请求失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"熔断器已打开，连续失败 {self.failure_count} 次，"
                f"将在 {self.recovery_timeout} 秒后尝试恢复"
            )

    def reset(self):
        """重置熔断器"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        logger.info("熔断器已手动重置")


class HealthCheckCache:
    """
    健康检查缓存

    缓存健康检查结果，避免频繁请求
    """

    def __init__(self, ttl: int = 30):
        """
        初始化缓存

        Args:
            ttl: 缓存过期时间（秒）
        """
        self.ttl = ttl
        self.cached_result: Optional[Dict[str, Any]] = None
        self.cached_at: Optional[datetime] = None

    def get(self) -> Optional[Dict[str, Any]]:
        """获取缓存的健康检查结果"""
        if self.cached_result is None or self.cached_at is None:
            return None

        if datetime.now() - self.cached_at > timedelta(seconds=self.ttl):
            # 缓存已过期
            return None

        return self.cached_result

    def set(self, result: Dict[str, Any]):
        """设置缓存"""
        self.cached_result = result
        self.cached_at = datetime.now()

    def clear(self):
        """清除缓存"""
        self.cached_result = None
        self.cached_at = None


# ============================================================================
# 自定义异常类
# ============================================================================


class OpenClawError(Exception):
    """OpenClaw 基础异常类"""

    pass


class OpenClawConnectionError(OpenClawError):
    """OpenClaw 连接错误"""

    pass


class OpenClawAPIError(OpenClawError):
    """OpenClaw API 调用错误"""

    def __init__(self, message: str, status_code: int = 500):
        self.status_code = status_code
        super().__init__(message)


class OpenClawTimeoutError(OpenClawError):
    """OpenClaw 请求超时"""

    pass


class OpenClawCircuitBreakerError(OpenClawError):
    """熔断器打开错误"""

    pass


# ============================================================================
# OpenClawClient 类
# ============================================================================


class OpenClawClient:
    """
    OpenClaw Gateway API 客户端

    提供与 OpenClaw Gateway 通信的统一接口，包括：
    - 健康检查
    - 消息发送
    - 连接管理
    - 错误处理和重试

    使用示例:
        # 同步使用
        client = OpenClawClient()
        health = await client.health_check()

        # 异步上下文管理器
        async with OpenClawClient() as client:
            response = await client.send_message("Hello")
    """

    def __init__(
        self,
        gateway_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        初始化 OpenClaw 客户端

        Args:
            gateway_url: OpenClaw Gateway URL，默认从配置读取
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.gateway_url = gateway_url or self._get_default_gateway_url()
        self.timeout = timeout
        self.max_retries = max_retries

        # 创建 httpx 异步客户端
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={"Content-Type": "application/json", "User-Agent": "RAGAgent/1.0"},
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )

        # 初始化熔断器
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,  # 连续失败5次后打开熔断器
            recovery_timeout=60,  # 60秒后尝试恢复
            expected_exception=OpenClawError,
        )

        # 初始化健康检查缓存
        self.health_cache = HealthCheckCache(ttl=30)  # 缓存30秒

        logger.info(
            f"OpenClawClient 初始化: gateway_url={self.gateway_url}, "
            f"timeout={timeout}s, max_retries={max_retries}, "
            f"circuit_breaker=enabled, health_cache=enabled"
        )

    def _get_default_gateway_url(self) -> str:
        """从配置获取默认 Gateway URL"""
        return settings.openclaw.gateway_url

    async def health_check(self) -> Dict[str, Any]:
        """
        检查 OpenClaw Gateway 健康状态

        使用缓存避免频繁请求

        注意：此方法不抛出异常，而是返回包含状态信息的字典。
        这是有意为之的设计，因为：
        1. 健康检查本身就是用来检测服务状态的，不应该"失败"
        2. API 端点需要获取健康状态信息，无论服务是否可用
        3. 健康检查不通过熔断器保护，避免循环依赖
        4. 健康检查成功时会重置熔断器，但失败时不触发熔断器计数

        Returns:
            健康状态信息:
            {
                "status": "healthy" | "unhealthy",
                "version": "2026.2.6-3",
                "uptime": 3600,
                "gateway_url": "http://localhost:19001",
                "error": "错误信息（如果不健康）"
            }
        """
        # 尝试从缓存获取
        cached = self.health_cache.get()
        if cached is not None:
            logger.debug("使用缓存的健康检查结果")
            return cached

        try:
            response = await self.client.get(f"{self.gateway_url}/health")
            response.raise_for_status()

            data = await response.json()
            logger.debug(f"OpenClaw 健康检查成功: {data}")

            result = {
                "status": "healthy",
                "version": data.get("version", "unknown"),
                "uptime": data.get("uptime", 0),
                "gateway_url": self.gateway_url,
            }

            # 缓存结果
            self.health_cache.set(result)

            # 健康检查成功，重置熔断器
            if self.circuit_breaker.state != CircuitState.CLOSED:
                self.circuit_breaker.reset()

            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenClaw 健康检查失败: HTTP {e.response.status_code}")
            result = {
                "status": "unhealthy",
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                "gateway_url": self.gateway_url,
            }
            self.health_cache.set(result)
            return result

        except httpx.ConnectError as e:
            logger.error(f"OpenClaw 连接失败: {str(e)}")
            result = {
                "status": "unhealthy",
                "error": f"连接失败: {str(e)}",
                "gateway_url": self.gateway_url,
            }
            self.health_cache.set(result)
            return result

        except Exception as e:
            logger.error(f"OpenClaw 健康检查异常: {str(e)}")
            result = {
                "status": "unhealthy",
                "error": f"未知错误: {str(e)}",
                "gateway_url": self.gateway_url,
            }
            self.health_cache.set(result)
            return result

    async def send_message(
        self,
        message: str,
        agent_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        发送消息到 OpenClaw Agent

        使用熔断器保护，避免在服务不可用时继续请求。

        注意：此方法通过熔断器保护，会抛出异常。
        这与 health_check 方法不同，因为：
        1. 这是实际的业务调用，失败应该触发熔断器
        2. 熔断器可以防止在服务不可用时继续发送请求
        3. 调用方需要知道请求是否成功，通过异常来传递失败信息

        Args:
            message: 消息内容
            agent_id: Agent ID，默认使用 default agent
            context: 上下文信息（可选）
            stream: 是否使用流式响应

        Returns:
            Agent 响应:
            {
                "response": "响应内容",
                "agent_id": "default",
                "execution_time": 1.5,
                "steps": [...]  # Agent 执行步骤（如果有）
            }

        Raises:
            OpenClawAPIError: API 调用失败
            OpenClawTimeoutError: 请求超时
            OpenClawCircuitBreakerError: 熔断器打开
        """
        payload = {
            "message": message,
            "agent_id": agent_id or "default",
            "context": context or {},
            "stream": stream,
        }

        logger.info(
            f"发送消息到 OpenClaw: agent_id={agent_id}, "
            f"message_length={len(message)}, stream={stream}"
        )

        async def _send_request():
            """实际发送请求的内部函数"""
            try:
                response = await self.client.post(
                    f"{self.gateway_url}/api/message", json=payload
                )
                response.raise_for_status()

                data = await response.json()
                logger.info(
                    f"OpenClaw 响应成功: execution_time={data.get('execution_time')}s"
                )

                return data

            except httpx.HTTPStatusError as e:
                error_msg = f"OpenClaw API 错误: HTTP {e.response.status_code}"
                logger.error(f"{error_msg}: {e.response.text}")
                raise OpenClawAPIError(error_msg, status_code=e.response.status_code)

            except httpx.TimeoutException as e:
                error_msg = f"OpenClaw 请求超时: {self.timeout}s"
                logger.error(error_msg)
                raise OpenClawTimeoutError(error_msg)

            except Exception as e:
                error_msg = f"OpenClaw 调用失败: {str(e)}"
                logger.error(error_msg)
                raise OpenClawAPIError(error_msg)

        # 通过熔断器调用
        try:
            return await self.circuit_breaker.call_async(_send_request)
        except OpenClawCircuitBreakerError:
            logger.warning("熔断器已打开，拒绝请求")
            raise

    async def close(self):
        """关闭客户端连接"""
        await self.client.aclose()
        logger.info("OpenClawClient 连接已关闭")

    def reset_circuit_breaker(self):
        """手动重置熔断器"""
        self.circuit_breaker.reset()
        self.health_cache.clear()
        logger.info("熔断器和健康检查缓存已手动重置")

    def get_circuit_state(self) -> str:
        """获取熔断器状态"""
        return self.circuit_breaker.state.value

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


# ============================================================================
# 全局单例模式
# ============================================================================

_openclaw_client: Optional[OpenClawClient] = None


def get_openclaw_client() -> OpenClawClient:
    """
    获取全局 OpenClaw 客户端实例（单例）

    Returns:
        OpenClawClient 实例
    """
    global _openclaw_client
    if _openclaw_client is None:
        _openclaw_client = OpenClawClient()
    return _openclaw_client


async def close_openclaw_client():
    """关闭全局 OpenClaw 客户端"""
    global _openclaw_client
    if _openclaw_client is not None:
        await _openclaw_client.close()
        _openclaw_client = None
