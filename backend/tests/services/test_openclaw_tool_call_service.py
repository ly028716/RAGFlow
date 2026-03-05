"""
OpenClaw 工具调用记录测试
"""

import pytest
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.openclaw_tool import OpenClawTool, ToolStatus
from app.models.openclaw_tool_call import OpenClawToolCall, CallStatus
from app.services.openclaw_tool_service import OpenClawToolService


@pytest.fixture
def tool_service(db: Session) -> OpenClawToolService:
    """创建工具服务实例"""
    return OpenClawToolService(db)


@pytest.fixture
def test_user(db: Session) -> User:
    """创建测试用户"""
    from app.core.security import hash_password

    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("testpassword123"),
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_tool(db: Session, test_user: User) -> OpenClawTool:
    """创建示例工具"""
    tool = OpenClawTool(
        name="test_tool",
        display_name="测试工具",
        description="这是一个测试工具",
        endpoint_url="http://localhost:8000/api/v1/test",
        method="POST",
        auth_type="api_token",
        status=ToolStatus.ACTIVE,
        is_builtin=False,
        created_by=test_user.id
    )
    db.add(tool)
    db.commit()
    db.refresh(tool)
    return tool


class TestRecordToolCall:
    """测试工具调用记录"""

    def test_record_tool_call_success(self, tool_service, sample_tool):
        """测试成功记录工具调用"""
        call = tool_service.record_tool_call(
            tool_id=sample_tool.id,
            agent_id="test_agent",
            user_id=None,
            request_params={"query": "测试查询"},
            response_data={"results": []},
            status=CallStatus.SUCCESS,
            execution_time=1.5
        )

        assert call.id is not None
        assert call.tool_id == sample_tool.id
        assert call.agent_id == "test_agent"
        assert call.status == CallStatus.SUCCESS
        assert call.execution_time == 1.5

    def test_record_tool_call_with_user(self, tool_service, sample_tool, test_user):
        """测试记录带用户ID的工具调用"""
        call = tool_service.record_tool_call(
            tool_id=sample_tool.id,
            user_id=test_user.id,
            request_params={"query": "测试"},
            status=CallStatus.SUCCESS
        )

        assert call.user_id == test_user.id

    def test_record_tool_call_failed(self, tool_service, sample_tool):
        """测试记录失败的工具调用"""
        call = tool_service.record_tool_call(
            tool_id=sample_tool.id,
            status=CallStatus.FAILED,
            error_message="连接超时",
            execution_time=30.0
        )

        assert call.status == CallStatus.FAILED
        assert call.error_message == "连接超时"

    def test_record_tool_call_filters_sensitive_params(self, tool_service, sample_tool):
        """测试过滤敏感参数"""
        call = tool_service.record_tool_call(
            tool_id=sample_tool.id,
            request_params={
                "query": "测试",
                "password": "secret123",
                "api_key": "key123",
                "token": "token123"
            },
            status=CallStatus.SUCCESS
        )

        # 验证敏感参数被过滤
        assert "query" in call.request_params
        assert "password" not in call.request_params
        assert "api_key" not in call.request_params
        assert "token" not in call.request_params


class TestGetToolCalls:
    """测试获取工具调用记录"""

    @pytest.fixture
    def tool_calls(self, db, sample_tool, test_user):
        """创建多个工具调用记录"""
        calls = []
        for i in range(5):
            call = OpenClawToolCall(
                tool_id=sample_tool.id,
                agent_id=f"agent_{i}",
                user_id=test_user.id if i % 2 == 0 else None,
                request_params={"query": f"query_{i}"},
                status=CallStatus.SUCCESS if i % 2 == 0 else CallStatus.FAILED,
                execution_time=float(i)
            )
            db.add(call)
            calls.append(call)
        db.commit()
        return calls

    def test_get_tool_calls_by_tool_id(self, tool_service, sample_tool, tool_calls):
        """测试根据工具ID获取调用记录"""
        calls = tool_service.get_tool_calls(tool_id=sample_tool.id)

        assert len(calls) == 5
        assert all(c.tool_id == sample_tool.id for c in calls)

    def test_get_tool_calls_by_user_id(self, tool_service, test_user, tool_calls):
        """测试根据用户ID获取调用记录"""
        calls = tool_service.get_tool_calls(user_id=test_user.id)

        assert len(calls) >= 3  # 偶数索引的调用
        assert all(c.user_id == test_user.id for c in calls)

    def test_get_tool_calls_by_agent_id(self, tool_service, tool_calls):
        """测试根据Agent ID获取调用记录"""
        calls = tool_service.get_tool_calls(agent_id="agent_0")

        assert len(calls) >= 1
        assert all(c.agent_id == "agent_0" for c in calls)

    def test_get_tool_calls_with_status_filter(self, tool_service, sample_tool, tool_calls):
        """测试按状态过滤调用记录"""
        success_calls = tool_service.get_tool_calls(
            tool_id=sample_tool.id,
            status=CallStatus.SUCCESS
        )

        assert all(c.status == CallStatus.SUCCESS for c in success_calls)

    def test_get_tool_calls_pagination(self, tool_service, sample_tool, tool_calls):
        """测试分页"""
        page1 = tool_service.get_tool_calls(tool_id=sample_tool.id, skip=0, limit=2)
        page2 = tool_service.get_tool_calls(tool_id=sample_tool.id, skip=2, limit=2)

        assert len(page1) == 2
        assert len(page2) >= 2
        assert page1[0].id != page2[0].id


class TestGetToolStats:
    """测试获取工具统计"""

    @pytest.fixture
    def tool_with_calls(self, db, sample_tool):
        """创建带调用记录的工具"""
        # 创建成功的调用
        for i in range(3):
            call = OpenClawToolCall(
                tool_id=sample_tool.id,
                status=CallStatus.SUCCESS,
                execution_time=float(i + 1)
            )
            db.add(call)

        # 创建失败的调用
        for i in range(2):
            call = OpenClawToolCall(
                tool_id=sample_tool.id,
                status=CallStatus.FAILED,
                execution_time=float(i + 1)
            )
            db.add(call)

        db.commit()
        return sample_tool

    def test_get_tool_stats(self, tool_service, tool_with_calls):
        """测试获取工具统计"""
        stats = tool_service.get_tool_stats(tool_with_calls.id)

        assert "total" in stats
        assert "success" in stats
        assert "failed" in stats
        assert stats["total"] == 5
        assert stats["success"] == 3
        assert stats["failed"] == 2
