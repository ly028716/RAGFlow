"""
OpenClawClient 单元测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.core.openclaw_client import (
    OpenClawClient,
    OpenClawError,
    OpenClawConnectionError,
    OpenClawAPIError,
    OpenClawTimeoutError,
    get_openclaw_client,
    close_openclaw_client,
)


@pytest.fixture
def openclaw_client():
    """创建 OpenClawClient 实例"""
    return OpenClawClient(
        gateway_url="http://localhost:19001", timeout=30.0, max_retries=3
    )


@pytest.mark.asyncio
async def test_health_check_success(openclaw_client):
    """测试健康检查成功"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"version": "2026.2.6-3", "uptime": 3600}

    with patch.object(openclaw_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        result = await openclaw_client.health_check()

        assert result["status"] == "healthy"
        assert result["version"] == "2026.2.6-3"
        assert result["uptime"] == 3600
        assert result["gateway_url"] == "http://localhost:19001"
        mock_get.assert_called_once_with("http://localhost:19001/health")


@pytest.mark.asyncio
async def test_health_check_http_error(openclaw_client):
    """测试健康检查 HTTP 错误"""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch.object(openclaw_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )

        result = await openclaw_client.health_check()

        assert result["status"] == "unhealthy"
        assert "HTTP 500" in result["error"]


@pytest.mark.asyncio
async def test_health_check_connection_error(openclaw_client):
    """测试健康检查连接错误"""
    with patch.object(openclaw_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection refused")

        result = await openclaw_client.health_check()

        assert result["status"] == "unhealthy"
        assert "连接失败" in result["error"]


@pytest.mark.asyncio
async def test_send_message_success(openclaw_client):
    """测试发送消息成功"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": "测试响应",
        "agent_id": "default",
        "execution_time": 1.5,
    }

    with patch.object(
        openclaw_client.client, "post", new_callable=AsyncMock
    ) as mock_post:
        mock_post.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        result = await openclaw_client.send_message(
            message="测试消息", agent_id="default"
        )

        assert result["response"] == "测试响应"
        assert result["agent_id"] == "default"
        assert result["execution_time"] == 1.5
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_send_message_timeout(openclaw_client):
    """测试发送消息超时"""
    with patch.object(
        openclaw_client.client, "post", new_callable=AsyncMock
    ) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Request timeout")

        with pytest.raises(OpenClawTimeoutError) as exc_info:
            await openclaw_client.send_message(message="测试消息")

        assert "超时" in str(exc_info.value)


@pytest.mark.asyncio
async def test_send_message_api_error(openclaw_client):
    """测试发送消息 API 错误"""
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.text = "Service Unavailable"

    with patch.object(
        openclaw_client.client, "post", new_callable=AsyncMock
    ) as mock_post:
        mock_post.return_value = mock_response
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Service Error", request=MagicMock(), response=mock_response
        )

        with pytest.raises(OpenClawAPIError) as exc_info:
            await openclaw_client.send_message(message="测试消息")

        assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_close(openclaw_client):
    """测试关闭客户端"""
    with patch.object(
        openclaw_client.client, "aclose", new_callable=AsyncMock
    ) as mock_close:
        await openclaw_client.close()
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_context_manager():
    """测试异步上下文管理器"""
    async with OpenClawClient() as client:
        assert client is not None
        assert isinstance(client, OpenClawClient)


def test_get_openclaw_client():
    """测试获取全局客户端实例"""
    client1 = get_openclaw_client()
    client2 = get_openclaw_client()

    assert client1 is client2  # 单例模式


@pytest.mark.asyncio
async def test_close_openclaw_client():
    """测试关闭全局客户端"""
    client = get_openclaw_client()

    with patch.object(client, "close", new_callable=AsyncMock) as mock_close:
        await close_openclaw_client()
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_send_message_with_context(openclaw_client):
    """测试发送消息带上下文"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": "测试响应",
        "agent_id": "default",
        "execution_time": 1.5,
    }

    with patch.object(
        openclaw_client.client, "post", new_callable=AsyncMock
    ) as mock_post:
        mock_post.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        context = {"user_id": 1, "session_id": "test-session"}
        result = await openclaw_client.send_message(
            message="测试消息", agent_id="default", context=context
        )

        assert result["response"] == "测试响应"
        # 验证 context 被传递
        call_args = mock_post.call_args
        assert call_args[1]["json"]["context"] == context


@pytest.mark.asyncio
async def test_send_message_stream_mode(openclaw_client):
    """测试流式响应模式"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": "测试响应",
        "agent_id": "default",
        "execution_time": 1.5,
    }

    with patch.object(
        openclaw_client.client, "post", new_callable=AsyncMock
    ) as mock_post:
        mock_post.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        result = await openclaw_client.send_message(
            message="测试消息", stream=True
        )

        # 验证 stream 参数被传递
        call_args = mock_post.call_args
        assert call_args[1]["json"]["stream"] is True
