"""
OpenClaw Gateway API 客户端

提供与 OpenClaw Gateway 通信的统一接口，包括：
- 健康检查
- 消息发送
- 连接管理
- 错误处理和重试
"""

import asyncio
import logging
from typing import Any, Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


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

        logger.info(
            f"OpenClawClient 初始化: gateway_url={self.gateway_url}, "
            f"timeout={timeout}s, max_retries={max_retries}"
        )

    def _get_default_gateway_url(self) -> str:
        """从配置获取默认 Gateway URL"""
        return settings.openclaw.gateway_url

    async def health_check(self) -> Dict[str, Any]:
        """
        检查 OpenClaw Gateway 健康状态

        Returns:
            健康状态信息:
            {
                "status": "healthy" | "unhealthy",
                "version": "2026.2.6-3",
                "uptime": 3600,
                "gateway_url": "http://localhost:19001",
                "error": "错误信息（如果不健康）"
            }

        Raises:
            OpenClawConnectionError: 连接失败
        """
        try:
            response = await self.client.get(f"{self.gateway_url}/health")
            response.raise_for_status()

            data = response.json()
            logger.debug(f"OpenClaw 健康检查成功: {data}")

            return {
                "status": "healthy",
                "version": data.get("version", "unknown"),
                "uptime": data.get("uptime", 0),
                "gateway_url": self.gateway_url,
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenClaw 健康检查失败: HTTP {e.response.status_code}")
            return {
                "status": "unhealthy",
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                "gateway_url": self.gateway_url,
            }

        except httpx.ConnectError as e:
            logger.error(f"OpenClaw 连接失败: {str(e)}")
            return {
                "status": "unhealthy",
                "error": f"连接失败: {str(e)}",
                "gateway_url": self.gateway_url,
            }

        except Exception as e:
            logger.error(f"OpenClaw 健康检查异常: {str(e)}")
            return {
                "status": "unhealthy",
                "error": f"未知错误: {str(e)}",
                "gateway_url": self.gateway_url,
            }

    async def send_message(
        self,
        message: str,
        agent_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        发送消息到 OpenClaw Agent

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

        try:
            response = await self.client.post(
                f"{self.gateway_url}/api/message", json=payload
            )
            response.raise_for_status()

            data = response.json()
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

    async def close(self):
        """关闭客户端连接"""
        await self.client.aclose()
        logger.info("OpenClawClient 连接已关闭")

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
