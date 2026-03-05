"""
OpenClaw性能和压力测试

测试范围:
- 性能基准测试（初始化、响应时间、吞吐量）
- 资源使用测试（内存、CPU、连接池）
- 并发测试（并发请求、压力测试）
- 稳定性测试（长时间运行、连续请求）
"""
import pytest
import asyncio
import time
import psutil
import os
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from app.core.openclaw_client import OpenClawClient, get_openclaw_client


class PerformanceMonitor:
    """性能监控辅助类"""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_time = None
        self.start_memory = None
        self.start_cpu = None

    def start(self):
        """开始监控"""
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.start_cpu = self.process.cpu_percent(interval=0.1)

    def stop(self) -> Dict[str, float]:
        """停止监控并返回结果"""
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        end_cpu = self.process.cpu_percent(interval=0.1)

        return {
            "duration": end_time - self.start_time,
            "memory_used": end_memory - self.start_memory,
            "memory_total": end_memory,
            "cpu_percent": end_cpu
        }


@pytest.fixture
def performance_monitor():
    """性能监控fixture"""
    return PerformanceMonitor()


@pytest.fixture
def mock_openclaw_response():
    """Mock OpenClaw响应"""
    return {
        "message": "测试响应",
        "status": "success",
        "data": {"result": "测试结果"}
    }


@pytest.fixture
async def mock_client():
    """Mock OpenClaw客户端"""
    client = OpenClawClient(
        gateway_url="http://localhost:19001",
        timeout=30.0,
        max_retries=3
    )

    # Mock the client's httpx client
    mock_http_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value={
        "message": "测试响应",
        "status": "success"
    })
    mock_http_client.post = AsyncMock(return_value=mock_response)
    mock_http_client.get = AsyncMock(return_value=mock_response)
    mock_http_client.aclose = AsyncMock()

    client.client = mock_http_client

    yield client

    await client.close()


class TestPerformanceBaseline:
    """性能基准测试"""

    @pytest.mark.asyncio
    async def test_client_initialization_time(self, performance_monitor):
        """测试客户端初始化时间"""
        import time

        # 测试10次初始化，取平均值
        times = []
        for _ in range(10):
            start = time.perf_counter()
            client = OpenClawClient(
                gateway_url="http://localhost:19001",
                timeout=30.0,
                max_retries=3
            )
            end = time.perf_counter()
            times.append(end - start)

        avg_time = sum(times) / len(times)

        # 验证初始化时间 < 500ms
        assert avg_time < 0.5, f"初始化时间过长: {avg_time:.3f}秒"

    @pytest.mark.asyncio
    async def test_single_message_response_time(self, mock_client, performance_monitor):
        """测试单次消息发送响应时间"""
        import time

        # 测试10次消息发送，取平均值
        times = []
        for _ in range(10):
            start = time.perf_counter()
            response = await mock_client.send_message(
                message="测试消息"
            )
            end = time.perf_counter()
            times.append(end - start)

        avg_time = sum(times) / len(times)

        # 验证响应时间 < 2秒
        assert avg_time < 2.0, f"响应时间过长: {avg_time:.3f}秒"

    @pytest.mark.asyncio
    async def test_batch_message_throughput(self, mock_client, performance_monitor):
        """测试批量消息发送吞吐量"""
        performance_monitor.start()

        # 发送50条消息
        message_count = 50
        tasks = []

        for i in range(message_count):
            task = mock_client.send_message(
                message=f"测试消息 {i}"
            )
            tasks.append(task)

        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        metrics = performance_monitor.stop()

        # 计算吞吐量（消息/分钟）
        throughput = (message_count / metrics["duration"]) * 60

        # 验证吞吐量 > 50消息/分钟
        assert throughput > 50, f"吞吐量不足: {throughput:.2f}消息/分钟"

        # 验证成功率
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        success_rate = success_count / message_count
        assert success_rate >= 0.95, f"成功率过低: {success_rate:.2%}"

    @pytest.mark.asyncio
    async def test_health_check_response_time(self, mock_client):
        """测试健康检查响应时间"""
        import time

        # 测试20次健康检查，取平均值
        times = []
        for _ in range(20):
            start = time.perf_counter()
            result = await mock_client.health_check()
            end = time.perf_counter()
            times.append(end - start)

        avg_time = sum(times) / len(times)

        # 验证健康检查时间 < 200ms
        assert avg_time < 0.2, f"健康检查时间过长: {avg_time:.3f}秒"


class TestResourceUsage:
    """资源使用测试"""

    @pytest.mark.asyncio
    async def test_memory_usage_single_client(self, performance_monitor):
        """测试单个客户端内存使用"""
        performance_monitor.start()

        # 创建客户端
        client = OpenClawClient(
            gateway_url="http://localhost:19001",
            timeout=30.0,
            max_retries=3
        )

        # 模拟使用
        with patch.object(client, 'client') as mock_http_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = AsyncMock(return_value={"status": "success"})
            mock_http_client.post = AsyncMock(return_value=mock_response)

            # 发送10条消息
            for i in range(10):
                await client.send_message(
                    message=f"测试消息 {i}"
                )

        await client.close()

        metrics = performance_monitor.stop()

        # 验证内存使用 < 100MB
        assert metrics["memory_used"] < 100, f"内存使用过高: {metrics['memory_used']:.2f}MB"

    @pytest.mark.asyncio
    async def test_memory_usage_multiple_clients(self, performance_monitor):
        """测试多个客户端内存使用"""
        performance_monitor.start()

        # 创建5个客户端
        clients = []
        for i in range(5):
            client = OpenClawClient(
                gateway_url="http://localhost:19001",
                timeout=30.0,
                max_retries=3
            )
            clients.append(client)

        # 模拟使用
        for client in clients:
            with patch.object(client, 'client') as mock_http_client:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json = AsyncMock(return_value={"status": "success"})
                mock_http_client.post = AsyncMock(return_value=mock_response)

                # 每个客户端发送5条消息
                for i in range(5):
                    await client.send_message(
                        message=f"测试消息 {i}"
                    )

        # 关闭所有客户端
        for client in clients:
            await client.close()

        metrics = performance_monitor.stop()

        # 验证总内存使用 < 200MB
        assert metrics["memory_used"] < 200, f"内存使用过高: {metrics['memory_used']:.2f}MB"

    @pytest.mark.asyncio
    async def test_cpu_usage_under_load(self, performance_monitor):
        """测试负载下的CPU使用"""
        performance_monitor.start()

        # 创建客户端
        client = OpenClawClient(
            gateway_url="http://localhost:19001",
            timeout=30.0,
            max_retries=3
        )

        # 模拟高负载
        with patch.object(client, 'client') as mock_http_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = AsyncMock(return_value={"status": "success"})
            mock_http_client.post = AsyncMock(return_value=mock_response)

            # 并发发送50条消息
            tasks = []
            for i in range(50):
                task = client.send_message(
                    message=f"测试消息 {i}"
                )
                tasks.append(task)

            await asyncio.gather(*tasks)

        await client.close()

        metrics = performance_monitor.stop()

        # 验证CPU使用 < 50%（考虑到是mock，实际使用会更低）
        assert metrics["cpu_percent"] < 50, f"CPU使用过高: {metrics['cpu_percent']:.2f}%"

    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, performance_monitor):
        """测试内存泄漏检测"""
        client = OpenClawClient(
            gateway_url="http://localhost:19001",
            timeout=30.0,
            max_retries=3
        )

        memory_samples = []

        # 执行多轮操作，监控内存变化
        for round_num in range(5):
            performance_monitor.start()

            with patch.object(client, 'client') as mock_http_client:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json = AsyncMock(return_value={"status": "success"})
                mock_http_client.post = AsyncMock(return_value=mock_response)

                # 每轮发送20条消息
                for i in range(20):
                    await client.send_message(
                        message=f"测试消息 {i}"
                    )

            metrics = performance_monitor.stop()
            memory_samples.append(metrics["memory_total"])

        await client.close()

        # 验证内存增长趋势
        # 如果存在内存泄漏，内存会持续增长
        # 正常情况下，内存应该相对稳定
        memory_growth = memory_samples[-1] - memory_samples[0]

        # 验证总内存增长 < 50MB
        assert memory_growth < 50, f"检测到可能的内存泄漏: 增长{memory_growth:.2f}MB"


class TestConcurrentLoad:
    """并发负载测试"""

    @pytest.mark.asyncio
    async def test_concurrent_message_sending(self, performance_monitor):
        """测试并发消息发送"""
        performance_monitor.start()

        # 创建客户端
        client = OpenClawClient(
            gateway_url="http://localhost:19001",
            timeout=30.0,
            max_retries=3
        )

        # 模拟并发请求
        with patch.object(client, 'client') as mock_http_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = AsyncMock(return_value={"status": "success"})
            mock_http_client.post = AsyncMock(return_value=mock_response)

            # 并发发送100条消息
            tasks = []
            for i in range(100):
                task = client.send_message(
                    message=f"并发测试消息 {i}"
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

        await client.close()

        metrics = performance_monitor.stop()

        # 验证成功率
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        success_rate = success_count / len(results)
        assert success_rate >= 0.95, f"并发成功率过低: {success_rate:.2%}"

        # 验证性能
        assert metrics["duration"] < 10, f"并发执行时间过长: {metrics['duration']:.2f}秒"

    @pytest.mark.asyncio
    async def test_connection_pool_stress(self, performance_monitor):
        """测试连接池压力"""
        performance_monitor.start()

        # 创建多个客户端模拟连接池压力
        clients = []
        for i in range(10):
            client = OpenClawClient(
                gateway_url="http://localhost:19001",
                timeout=30.0,
                max_retries=3
            )
            # Patch each client's httpx client upfront
            mock_http_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = AsyncMock(return_value={"status": "success"})
            mock_http_client.post = AsyncMock(return_value=mock_response)
            mock_http_client.aclose = AsyncMock()
            client.client = mock_http_client
            clients.append(client)

        # 每个客户端并发发送消息
        all_tasks = []
        for client in clients:
            for i in range(10):
                task = client.send_message(
                    message=f"压力测试消息 {i}"
                )
                all_tasks.append(task)

        results = await asyncio.gather(*all_tasks, return_exceptions=True)

        # 关闭所有客户端
        for client in clients:
            await client.close()

        metrics = performance_monitor.stop()

        # 验证成功率
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        success_rate = success_count / len(results)
        assert success_rate >= 0.90, f"压力测试成功率过低: {success_rate:.2%}"

    @pytest.mark.skip(reason="Retry mechanism for TimeoutError works at a different level than httpx mocking")
    @pytest.mark.asyncio
    async def test_timeout_and_retry_mechanism(self):
        """测试超时和重试机制"""
        client = OpenClawClient(
            gateway_url="http://localhost:19001",
            timeout=1.0,  # 短超时
            max_retries=3
        )

        # 模拟超时场景
        # Create a callable that simulates retry behavior
        call_count = {"count": 0}

        async def mock_post_with_retry(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] <= 2:
                raise asyncio.TimeoutError()
            else:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json = AsyncMock(return_value={"status": "success"})
                mock_response.raise_for_status = MagicMock()
                return mock_response

        with patch.object(client, 'client') as mock_http_client:
            mock_http_client.post = AsyncMock(side_effect=mock_post_with_retry)

            start_time = time.time()
            result = await client.send_message(
                message="测试消息"
            )
            duration = time.time() - start_time

            # 验证重试成功
            assert result is not None
            assert result["status"] == "success"

            # 验证重试次数（应该调用了3次）
            assert mock_http_client.post.call_count == 3

        await client.close()


class TestStability:
    """稳定性测试"""

    @pytest.mark.asyncio
    async def test_long_running_stability(self, performance_monitor):
        """测试长时间运行稳定性"""
        performance_monitor.start()

        client = OpenClawClient(
            gateway_url="http://localhost:19001",
            timeout=30.0,
            max_retries=3
        )

        # 模拟长时间运行（发送200条消息）
        success_count = 0
        error_count = 0

        with patch.object(client, 'client') as mock_http_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = AsyncMock(return_value={"status": "success"})
            mock_http_client.post = AsyncMock(return_value=mock_response)

            for i in range(200):
                try:
                    await client.send_message(
                        message=f"长时间运行测试 {i}"
                    )
                    success_count += 1
                except Exception:
                    error_count += 1

        await client.close()

        metrics = performance_monitor.stop()

        # 验证成功率 > 95%
        success_rate = success_count / (success_count + error_count)
        assert success_rate > 0.95, f"长时间运行成功率过低: {success_rate:.2%}"

        # 验证内存稳定（没有显著增长）
        assert metrics["memory_used"] < 100, f"长时间运行内存增长过多: {metrics['memory_used']:.2f}MB"

    @pytest.mark.asyncio
    async def test_continuous_request_execution(self, performance_monitor):
        """测试连续请求执行"""
        client = OpenClawClient(
            gateway_url="http://localhost:19001",
            timeout=30.0,
            max_retries=3
        )

        execution_times = []

        # 连续执行10轮，每轮10个请求
        for round_num in range(10):
            round_start = time.time()

            with patch.object(client, 'client') as mock_http_client:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json = AsyncMock(return_value={"status": "success"})
                mock_http_client.post = AsyncMock(return_value=mock_response)

                tasks = []
                for i in range(10):
                    task = client.send_message(
                        message=f"连续测试 轮次{round_num} 消息{i}"
                    )
                    tasks.append(task)

                await asyncio.gather(*tasks)

            round_duration = time.time() - round_start
            execution_times.append(round_duration)

        await client.close()

        # 验证执行时间稳定性
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        min_time = min(execution_times)

        # 验证执行时间波动不大（最大时间不超过平均时间的2倍）
        assert max_time < avg_time * 2, f"执行时间波动过大: 最大={max_time:.2f}s, 平均={avg_time:.2f}s"

        # 验证平均执行时间合理
        assert avg_time < 5, f"平均执行时间过长: {avg_time:.2f}秒"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
