"""
OpenClaw API 端点单元测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status

from app.core.openclaw_client import OpenClawAPIError, OpenClawTimeoutError


@pytest.mark.asyncio
async def test_health_check_success(client):
    """测试健康检查成功"""
    mock_health_data = {
        "status": "healthy",
        "version": "2026.2.6-3",
        "uptime": 3600,
        "gateway_url": "http://localhost:19001",
    }

    with patch("app.api.v1.openclaw.get_openclaw_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.health_check = AsyncMock(return_value=mock_health_data)
        mock_get_client.return_value = mock_client

        response = client.get("/api/v1/openclaw/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2026.2.6-3"
        assert data["uptime"] == 3600


@pytest.mark.asyncio
async def test_health_check_unhealthy(client):
    """测试健康检查不健康状态"""
    mock_health_data = {
        "status": "unhealthy",
        "gateway_url": "http://localhost:19001",
        "error": "连接失败",
    }

    with patch("app.api.v1.openclaw.get_openclaw_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.health_check = AsyncMock(return_value=mock_health_data)
        mock_get_client.return_value = mock_client

        response = client.get("/api/v1/openclaw/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "error" in data


@pytest.mark.asyncio
async def test_send_message_success(client, auth_headers):
    """测试发送消息成功"""
    mock_response_data = {
        "response": "测试响应内容",
        "agent_id": "default",
        "execution_time": 1.5,
    }

    with patch("app.api.v1.openclaw.get_openclaw_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.send_message = AsyncMock(return_value=mock_response_data)
        mock_get_client.return_value = mock_client

        payload = {
            "message": "测试消息",
            "agent_id": "default",
            "context": {"user_id": 1},
            "stream": False,
        }

        response = client.post(
            "/api/v1/openclaw/message", json=payload, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["response"] == "测试响应内容"
        assert data["agent_id"] == "default"
        assert data["execution_time"] == 1.5


@pytest.mark.asyncio
async def test_send_message_unauthorized(client):
    """测试发送消息未认证"""
    payload = {"message": "测试消息"}

    response = client.post("/api/v1/openclaw/message", json=payload)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_send_message_timeout(client, auth_headers):
    """测试发送消息超时"""
    with patch("app.api.v1.openclaw.get_openclaw_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.send_message = AsyncMock(
            side_effect=OpenClawTimeoutError("请求超时")
        )
        mock_get_client.return_value = mock_client

        payload = {"message": "测试消息"}

        response = client.post(
            "/api/v1/openclaw/message", json=payload, headers=auth_headers
        )

        assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT


@pytest.mark.asyncio
async def test_send_message_api_error(client, auth_headers):
    """测试发送消息 API 错误"""
    with patch("app.api.v1.openclaw.get_openclaw_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.send_message = AsyncMock(
            side_effect=OpenClawAPIError("API 错误", status_code=503)
        )
        mock_get_client.return_value = mock_client

        payload = {"message": "测试消息"}

        response = client.post(
            "/api/v1/openclaw/message", json=payload, headers=auth_headers
        )

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.asyncio
async def test_send_message_validation_error(client, auth_headers):
    """测试发送消息验证错误"""
    # 消息为空
    payload = {"message": ""}

    response = client.post(
        "/api/v1/openclaw/message", json=payload, headers=auth_headers
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_send_message_with_context(client, auth_headers):
    """测试发送消息带上下文"""
    mock_response_data = {
        "response": "测试响应",
        "agent_id": "default",
        "execution_time": 1.5,
    }

    with patch("app.api.v1.openclaw.get_openclaw_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.send_message = AsyncMock(return_value=mock_response_data)
        mock_get_client.return_value = mock_client

        payload = {
            "message": "测试消息",
            "context": {"user_id": 1, "session_id": "test-session"},
        }

        response = client.post(
            "/api/v1/openclaw/message", json=payload, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        # 验证 send_message 被调用时传递了正确的参数
        mock_client.send_message.assert_called_once()
        call_kwargs = mock_client.send_message.call_args[1]
        assert call_kwargs["context"] == payload["context"]


@pytest.mark.asyncio
async def test_send_message_stream_mode(client, auth_headers):
    """测试流式响应模式"""
    mock_response_data = {
        "response": "测试响应",
        "agent_id": "default",
        "execution_time": 1.5,
    }

    with patch("app.api.v1.openclaw.get_openclaw_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.send_message = AsyncMock(return_value=mock_response_data)
        mock_get_client.return_value = mock_client

        payload = {"message": "测试消息", "stream": True}

        response = client.post(
            "/api/v1/openclaw/message", json=payload, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        # 验证 stream 参数被传递
        call_kwargs = mock_client.send_message.call_args[1]
        assert call_kwargs["stream"] is True
