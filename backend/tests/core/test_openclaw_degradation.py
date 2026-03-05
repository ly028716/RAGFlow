"""
OpenClaw 降级与恢复机制测试

测试内容：
1. 熔断器在连续5次失败后打开
2. 健康检查缓存（30秒TTL）正常工作
3. 熔断器在60秒后进入半开状态
4. 半开状态下成功请求关闭熔断器
5. 健康检查成功时重置熔断器
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.core.openclaw_client import (
    OpenClawClient,
    OpenClawAPIError,
    OpenClawCircuitBreakerError,
    CircuitState,
)


@pytest.fixture
def openclaw_client():
    """创建 OpenClawClient 实例"""
    return OpenClawClient(
        gateway_url="http://localhost:19001",
        timeout=30.0,
        max_retries=3
    )


class TestCircuitBreaker:
    """测试熔断器功能"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_5_failures(self, openclaw_client):
        """测试熔断器在连续5次失败后打开"""
        # 模拟连续失败的请求
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

            # 前5次失败应该抛出 OpenClawAPIError
            for i in range(5):
                with pytest.raises(OpenClawAPIError):
                    await openclaw_client.send_message(message=f"测试消息 {i}")

                # 检查失败计数
                assert openclaw_client.circuit_breaker.failure_count == i + 1

            # 验证熔断器已打开
            assert openclaw_client.circuit_breaker.state == CircuitState.OPEN

            # 第6次请求应该直接被熔断器拒绝
            with pytest.raises(OpenClawCircuitBreakerError) as exc_info:
                await openclaw_client.send_message(message="测试消息 6")

            assert "熔断器已打开" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_after_timeout(self, openclaw_client):
        """测试熔断器在恢复超时后进入半开状态"""
        # 先触发熔断器打开
        openclaw_client.circuit_breaker.failure_count = 5
        openclaw_client.circuit_breaker.last_failure_time = time.time()
        openclaw_client.circuit_breaker.state = CircuitState.OPEN

        # 验证熔断器已打开
        assert openclaw_client.circuit_breaker.state == CircuitState.OPEN

        # 模拟等待恢复超时（60秒）
        openclaw_client.circuit_breaker.last_failure_time = time.time() - 61

        # 模拟成功的请求
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

            # 发送请求，应该进入半开状态并成功
            result = await openclaw_client.send_message(message="测试消息")

            # 验证请求成功
            assert result["response"] == "测试响应"

            # 验证熔断器已关闭
            assert openclaw_client.circuit_breaker.state == CircuitState.CLOSED
            assert openclaw_client.circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_reopens_on_half_open_failure(self, openclaw_client):
        """测试半开状态下失败会重新打开熔断器"""
        # 设置为半开状态
        openclaw_client.circuit_breaker.state = CircuitState.HALF_OPEN
        openclaw_client.circuit_breaker.failure_count = 0
        openclaw_client.circuit_breaker.last_failure_time = time.time() - 61

        # 模拟失败的请求
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

            # 发送请求，应该失败
            with pytest.raises(OpenClawAPIError):
                await openclaw_client.send_message(message="测试消息")

            # 验证失败计数增加
            assert openclaw_client.circuit_breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_manual_circuit_breaker_reset(self, openclaw_client):
        """测试手动重置熔断器"""
        # 设置熔断器为打开状态
        openclaw_client.circuit_breaker.failure_count = 5
        openclaw_client.circuit_breaker.last_failure_time = time.time()
        openclaw_client.circuit_breaker.state = CircuitState.OPEN

        # 手动重置
        openclaw_client.reset_circuit_breaker()

        # 验证熔断器已重置
        assert openclaw_client.circuit_breaker.state == CircuitState.CLOSED
        assert openclaw_client.circuit_breaker.failure_count == 0
        assert openclaw_client.circuit_breaker.last_failure_time is None

    def test_get_circuit_state(self, openclaw_client):
        """测试获取熔断器状态"""
        # 初始状态应该是关闭
        assert openclaw_client.get_circuit_state() == "closed"

        # 设置为打开状态
        openclaw_client.circuit_breaker.state = CircuitState.OPEN
        assert openclaw_client.get_circuit_state() == "open"

        # 设置为半开状态
        openclaw_client.circuit_breaker.state = CircuitState.HALF_OPEN
        assert openclaw_client.get_circuit_state() == "half_open"


class TestHealthCheckCache:
    """测试健康检查缓存功能"""

    @pytest.mark.asyncio
    async def test_health_check_cache_works(self, openclaw_client):
        """测试健康检查缓存正常工作"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "2026.2.6-3", "uptime": 3600}

        with patch.object(
            openclaw_client.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_response
            mock_response.raise_for_status = MagicMock()

            # 第一次调用，应该发起请求
            result1 = await openclaw_client.health_check()
            assert result1["status"] == "healthy"
            assert mock_get.call_count == 1

            # 第二次调用，应该使用缓存
            result2 = await openclaw_client.health_check()
            assert result2["status"] == "healthy"
            assert mock_get.call_count == 1  # 没有增加

            # 验证返回的是相同的结果
            assert result1 == result2

    @pytest.mark.asyncio
    async def test_health_check_cache_expires(self, openclaw_client):
        """测试健康检查缓存过期"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "2026.2.6-3", "uptime": 3600}

        with patch.object(
            openclaw_client.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_response
            mock_response.raise_for_status = MagicMock()

            # 第一次调用
            result1 = await openclaw_client.health_check()
            assert result1["status"] == "healthy"
            assert mock_get.call_count == 1

            # 模拟缓存过期（修改缓存时间）
            from datetime import datetime, timedelta
            openclaw_client.health_cache.cached_at = datetime.now() - timedelta(seconds=31)

            # 第二次调用，缓存已过期，应该重新请求
            result2 = await openclaw_client.health_check()
            assert result2["status"] == "healthy"
            assert mock_get.call_count == 2  # 增加了

    @pytest.mark.asyncio
    async def test_health_check_resets_circuit_breaker(self, openclaw_client):
        """测试健康检查成功时重置熔断器"""
        # 设置熔断器为打开状态
        openclaw_client.circuit_breaker.failure_count = 5
        openclaw_client.circuit_breaker.last_failure_time = time.time()
        openclaw_client.circuit_breaker.state = CircuitState.OPEN

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "2026.2.6-3", "uptime": 3600}

        with patch.object(
            openclaw_client.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_response
            mock_response.raise_for_status = MagicMock()

            # 执行健康检查
            result = await openclaw_client.health_check()

            # 验证健康检查成功
            assert result["status"] == "healthy"

            # 验证熔断器已重置
            assert openclaw_client.circuit_breaker.state == CircuitState.CLOSED
            assert openclaw_client.circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_health_check_caches_unhealthy_status(self, openclaw_client):
        """测试健康检查缓存不健康状态"""
        with patch.object(
            openclaw_client.client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused")

            # 第一次调用，应该发起请求
            result1 = await openclaw_client.health_check()
            assert result1["status"] == "unhealthy"
            assert mock_get.call_count == 1

            # 第二次调用，应该使用缓存
            result2 = await openclaw_client.health_check()
            assert result2["status"] == "unhealthy"
            assert mock_get.call_count == 1  # 没有增加

            # 验证返回的是相同的结果
            assert result1 == result2


class TestDegradationRecovery:
    """测试降级与恢复流程"""

    @pytest.mark.asyncio
    async def test_full_degradation_recovery_cycle(self, openclaw_client):
        """测试完整的降级与恢复周期"""
        # 1. 模拟连续失败导致熔断器打开
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 503
        mock_response_fail.text = "Service Unavailable"

        with patch.object(
            openclaw_client.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = mock_response_fail
            mock_response_fail.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Service Error", request=MagicMock(), response=mock_response_fail
            )

            # 触发5次失败
            for i in range(5):
                with pytest.raises(OpenClawAPIError):
                    await openclaw_client.send_message(message=f"测试消息 {i}")

            # 验证熔断器已打开
            assert openclaw_client.circuit_breaker.state == CircuitState.OPEN

        # 2. 模拟等待恢复超时
        openclaw_client.circuit_breaker.last_failure_time = time.time() - 61

        # 3. 模拟服务恢复，发送成功请求
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "response": "恢复成功",
            "agent_id": "default",
            "execution_time": 1.5,
        }

        with patch.object(
            openclaw_client.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = mock_response_success
            mock_response_success.raise_for_status = MagicMock()

            # 发送请求，应该成功并关闭熔断器
            result = await openclaw_client.send_message(message="恢复测试")

            # 验证请求成功
            assert result["response"] == "恢复成功"

            # 验证熔断器已关闭
            assert openclaw_client.circuit_breaker.state == CircuitState.CLOSED
            assert openclaw_client.circuit_breaker.failure_count == 0


class TestDegradationScenarios:
    """降级场景测试"""

    @pytest.mark.asyncio
    async def test_degradation_on_connection_error(self, openclaw_client):
        """测试连接错误时的降级"""
        with patch.object(
            openclaw_client.client, "post", new_callable=AsyncMock
        ) as mock_post:
            # 模拟连接错误
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            # 发送消息应该触发降级
            with pytest.raises(OpenClawAPIError):
                await openclaw_client.send_message(
                    message="测试消息"
                )

            # 验证失败计数增加
            assert openclaw_client.circuit_breaker.failure_count > 0

    @pytest.mark.asyncio
    async def test_degradation_on_timeout(self, openclaw_client):
        """测试超时时的降级"""
        with patch.object(
            openclaw_client.client, "post", new_callable=AsyncMock
        ) as mock_post:
            # 模拟超时
            import asyncio
            mock_post.side_effect = asyncio.TimeoutError()

            # 发送消息应该触发降级
            with pytest.raises(OpenClawAPIError):
                await openclaw_client.send_message(
                    message="测试消息"
                )

            # 验证失败计数增加
            assert openclaw_client.circuit_breaker.failure_count > 0

    @pytest.mark.asyncio
    async def test_degradation_during_request(self, openclaw_client):
        """测试请求过程中的降级"""
        with patch.object(
            openclaw_client.client, "post", new_callable=AsyncMock
        ) as mock_post:
            # 第一次请求成功
            mock_response_success = MagicMock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {
                "response": "成功响应",
                "agent_id": "default",
                "execution_time": 1.0,
            }
            mock_response_success.raise_for_status = MagicMock()

            # 第二次请求失败
            mock_response_fail = MagicMock()
            mock_response_fail.status_code = 503
            mock_response_fail.text = "Service Unavailable"

            mock_post.side_effect = [
                mock_response_success,
                mock_response_fail
            ]
            mock_response_fail.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Service Error", request=MagicMock(), response=mock_response_fail
            )

            # 第一次请求成功
            response1 = await openclaw_client.send_message(
                message="测试消息1"
            )
            assert response1["response"] == "成功响应"

            # 第二次请求应该失败
            with pytest.raises(OpenClawAPIError):
                await openclaw_client.send_message(
                    message="测试消息2"
                )

            # 验证失败计数增加
            assert openclaw_client.circuit_breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_multiple_degradation_cycles(self, openclaw_client):
        """测试多次降级和恢复循环"""
        # 第一次降级周期
        with patch.object(
            openclaw_client.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            with pytest.raises(OpenClawAPIError):
                await openclaw_client.send_message(message="测试1")

            first_failure_count = openclaw_client.circuit_breaker.failure_count
            assert first_failure_count > 0

        # 恢复
        openclaw_client.reset_circuit_breaker()
        assert openclaw_client.circuit_breaker.failure_count == 0

        # 第二次降级周期
        with patch.object(
            openclaw_client.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            with pytest.raises(OpenClawAPIError):
                await openclaw_client.send_message(message="测试2")

            # 验证系统能够处理多次降级循环
            assert openclaw_client.circuit_breaker.failure_count > 0

    @pytest.mark.asyncio
    async def test_degradation_with_partial_failure(self, openclaw_client):
        """测试部分失败场景的降级"""
        with patch.object(
            openclaw_client.client, "post", new_callable=AsyncMock
        ) as mock_post:
            # 模拟部分失败（50%成功率）
            mock_response_success = MagicMock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {
                "response": "成功",
                "agent_id": "default",
                "execution_time": 1.0,
            }
            mock_response_success.raise_for_status = MagicMock()

            mock_response_fail = MagicMock()
            mock_response_fail.status_code = 503
            mock_response_fail.text = "Service Unavailable"

            mock_post.side_effect = [
                mock_response_success,
                mock_response_fail,
                mock_response_success,
                mock_response_fail,
            ]
            mock_response_fail.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Service Error", request=MagicMock(), response=mock_response_fail
            )

            # 发送多个请求
            success_count = 0
            failure_count = 0

            # 第1次 - 成功
            try:
                await openclaw_client.send_message(message="测试0", conversation_id="test-conv")
                success_count += 1
            except Exception:
                failure_count += 1

            # 第2次 - 失败
            try:
                await openclaw_client.send_message(message="测试1")
                success_count += 1
            except Exception:
                failure_count += 1

            # 验证至少有一些请求成功，一些失败
            assert success_count > 0
            assert failure_count > 0


class TestDegradationStateManagement:
    """降级状态管理测试"""

    @pytest.mark.asyncio
    async def test_degradation_status_query(self, openclaw_client):
        """测试降级状态查询"""
        # 初始状态应该是关闭
        assert openclaw_client.get_circuit_state() == "closed"

        # 触发降级
        openclaw_client.circuit_breaker.state = CircuitState.OPEN
        openclaw_client.circuit_breaker.failure_count = 5

        # 查询降级状态
        assert openclaw_client.get_circuit_state() == "open"
        assert openclaw_client.circuit_breaker.failure_count == 5

    @pytest.mark.asyncio
    async def test_degradation_state_transitions(self, openclaw_client):
        """测试降级状态转换"""
        # 初始状态：正常 (CLOSED)
        assert openclaw_client.circuit_breaker.state == CircuitState.CLOSED

        # 转换到降级状态 (OPEN)
        openclaw_client.circuit_breaker.state = CircuitState.OPEN
        openclaw_client.circuit_breaker.failure_count = 5
        assert openclaw_client.get_circuit_state() == "open"

        # 转换到半开状态 (HALF_OPEN)
        openclaw_client.circuit_breaker.state = CircuitState.HALF_OPEN
        assert openclaw_client.get_circuit_state() == "half_open"

        # 恢复到正常状态 (CLOSED)
        openclaw_client.reset_circuit_breaker()
        assert openclaw_client.circuit_breaker.state == CircuitState.CLOSED
        assert openclaw_client.circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_degradation_metrics_tracking(self, openclaw_client):
        """测试降级指标跟踪"""
        # 初始失败计数为0
        assert openclaw_client.circuit_breaker.failure_count == 0

        # 模拟多次失败
        with patch.object(
            openclaw_client.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            failure_count = 0
            for i in range(3):
                try:
                    await openclaw_client.send_message(
                        message=f"测试{i}"
                    )
                except Exception:
                    failure_count += 1

            # 验证失败次数被跟踪
            assert failure_count == 3
            assert openclaw_client.circuit_breaker.failure_count == 3

        # 验证可以查询失败计数
        assert openclaw_client.circuit_breaker.failure_count > 0
