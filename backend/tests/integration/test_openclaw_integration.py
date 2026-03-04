"""
OpenClaw 集成测试

测试与真实 OpenClaw Gateway 的集成，验证端到端流程。

运行前提：
1. OpenClaw Gateway 必须在 localhost:19001 运行
2. 设置环境变量 OPENCLAW_GATEWAY_URL
3. 运行命令: pytest tests/integration/test_openclaw_integration.py -v

注意：这些测试需要真实的 OpenClaw Gateway，不使用 mock。
"""

import os
import pytest
import httpx
from app.core.openclaw_client import OpenClawClient, get_openclaw_client


# 标记为集成测试，默认不运行
pytestmark = pytest.mark.integration


@pytest.fixture
def openclaw_gateway_url():
    """获取 OpenClaw Gateway URL"""
    url = os.getenv("OPENCLAW_GATEWAY_URL", "http://localhost:19001")
    return url


@pytest.fixture
async def openclaw_client(openclaw_gateway_url):
    """创建 OpenClaw 客户端"""
    client = OpenClawClient(gateway_url=openclaw_gateway_url)
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_openclaw_gateway_reachable(openclaw_gateway_url):
    """测试 OpenClaw Gateway 是否可达"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{openclaw_gateway_url}/health", timeout=5.0)
            assert response.status_code == 200, f"Gateway 返回状态码 {response.status_code}"
            print(f"✓ OpenClaw Gateway 可达: {openclaw_gateway_url}")
        except httpx.ConnectError:
            pytest.skip(f"OpenClaw Gateway 不可达: {openclaw_gateway_url}")


@pytest.mark.asyncio
async def test_health_check_integration(openclaw_client):
    """测试健康检查集成"""
    result = await openclaw_client.health_check()

    assert "status" in result
    assert result["status"] in ["healthy", "unhealthy"]
    assert "gateway_url" in result

    if result["status"] == "healthy":
        assert "version" in result
        print(f"✓ 健康检查成功: version={result.get('version')}")
    else:
        print(f"✗ 健康检查失败: {result.get('error')}")


@pytest.mark.asyncio
async def test_send_message_integration(openclaw_client):
    """测试发送消息集成"""
    # 先检查健康状态
    health = await openclaw_client.health_check()
    if health["status"] != "healthy":
        pytest.skip("OpenClaw Gateway 不健康，跳过消息发送测试")

    # 发送测试消息
    message = "这是一条集成测试消息，请简单回复确认收到。"
    result = await openclaw_client.send_message(
        message=message,
        agent_id="default",
        context={"test": True}
    )

    assert "response" in result
    assert "agent_id" in result
    assert "execution_time" in result
    assert result["agent_id"] == "default"
    assert isinstance(result["execution_time"], (int, float))

    print(f"✓ 消息发送成功: execution_time={result['execution_time']}s")
    print(f"  响应: {result['response'][:100]}...")


@pytest.mark.asyncio
async def test_send_message_with_context(openclaw_client):
    """测试带上下文的消息发送"""
    health = await openclaw_client.health_check()
    if health["status"] != "healthy":
        pytest.skip("OpenClaw Gateway 不健康")

    context = {
        "user_id": 999,
        "session_id": "integration-test-session",
        "test_mode": True
    }

    result = await openclaw_client.send_message(
        message="测试带上下文的消息",
        agent_id="default",
        context=context
    )

    assert "response" in result
    print(f"✓ 带上下文的消息发送成功")


@pytest.mark.asyncio
async def test_global_client_singleton():
    """测试全局客户端单例模式"""
    client1 = get_openclaw_client()
    client2 = get_openclaw_client()

    assert client1 is client2
    print(f"✓ 全局客户端单例模式正常")


@pytest.mark.asyncio
async def test_end_to_end_flow(openclaw_client):
    """测试端到端流程"""
    # 1. 健康检查
    health = await openclaw_client.health_check()
    assert health["status"] in ["healthy", "unhealthy"]
    print(f"1. 健康检查: {health['status']}")

    if health["status"] != "healthy":
        pytest.skip("OpenClaw Gateway 不健康，跳过端到端测试")

    # 2. 发送简单消息
    result1 = await openclaw_client.send_message(
        message="你好",
        agent_id="default"
    )
    assert "response" in result1
    print(f"2. 简单消息: ✓")

    # 3. 发送带上下文的消息
    result2 = await openclaw_client.send_message(
        message="继续对话",
        agent_id="default",
        context={"previous_message": "你好"}
    )
    assert "response" in result2
    print(f"3. 带上下文消息: ✓")

    # 4. 再次健康检查
    health2 = await openclaw_client.health_check()
    assert health2["status"] == "healthy"
    print(f"4. 最终健康检查: {health2['status']}")

    print(f"\n✓ 端到端流程测试通过")


if __name__ == "__main__":
    """
    直接运行此文件进行快速集成测试

    使用方法:
        python -m pytest tests/integration/test_openclaw_integration.py -v -s
    """
    import asyncio

    async def quick_test():
        """快速测试"""
        print("=" * 60)
        print("OpenClaw 集成测试 - 快速验证")
        print("=" * 60)

        gateway_url = os.getenv("OPENCLAW_GATEWAY_URL", "http://localhost:19001")
        print(f"\nGateway URL: {gateway_url}\n")

        async with OpenClawClient(gateway_url=gateway_url) as client:
            # 测试1: 健康检查
            print("测试 1: 健康检查...")
            health = await client.health_check()
            print(f"  状态: {health['status']}")
            if health["status"] == "healthy":
                print(f"  版本: {health.get('version', 'N/A')}")
                print(f"  运行时间: {health.get('uptime', 0)} 秒")
            else:
                print(f"  错误: {health.get('error', 'N/A')}")
                return

            # 测试2: 发送消息
            print("\n测试 2: 发送消息...")
            result = await client.send_message(
                message="这是一条测试消息",
                agent_id="default"
            )
            print(f"  执行时间: {result['execution_time']} 秒")
            print(f"  响应: {result['response'][:100]}...")

            print("\n" + "=" * 60)
            print("✓ 所有测试通过")
            print("=" * 60)

    asyncio.run(quick_test())
