"""
OpenClaw 工具服务层测试
"""

import pytest
from datetime import datetime
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


class TestRegisterTool:
    """测试工具注册"""

    def test_register_tool_success(self, tool_service, test_user):
        """测试成功注册工具"""
        tool = tool_service.register_tool(
            name="new_tool",
            display_name="新工具",
            description="这是一个新工具",
            endpoint_url="http://localhost:8000/api/v1/new-tool",
            method="POST",
            auth_type="api_token",
            created_by=test_user.id
        )

        assert tool.id is not None
        assert tool.name == "new_tool"
        assert tool.display_name == "新工具"
        assert tool.status == ToolStatus.ACTIVE
        assert tool.is_builtin is False
        assert tool.created_by == test_user.id

    def test_register_tool_duplicate_name(self, tool_service, sample_tool, test_user):
        """测试注册重复名称的工具"""
        with pytest.raises(ValueError, match="已存在"):
            tool_service.register_tool(
                name="test_tool",  # 与sample_tool重复
                display_name="重复工具",
                description="测试重复",
                endpoint_url="http://localhost:8000/api/v1/duplicate",
                method="POST",
                auth_type="api_token",
                created_by=test_user.id
            )

    def test_register_builtin_tool(self, tool_service):
        """测试注册内置工具"""
        tool = tool_service.register_tool(
            name="builtin_tool",
            display_name="内置工具",
            description="这是一个内置工具",
            endpoint_url="http://localhost:8000/api/v1/builtin",
            method="GET",
            auth_type="none",
            is_builtin=True
        )

        assert tool.is_builtin is True
        assert tool.created_by is None

    def test_register_tool_with_schemas(self, tool_service, test_user):
        """测试注册带Schema的工具"""
        parameters_schema = {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"}
            }
        }

        response_schema = {
            "type": "object",
            "properties": {
                "results": {"type": "array"}
            }
        }

        tool = tool_service.register_tool(
            name="schema_tool",
            display_name="Schema工具",
            description="带Schema的工具",
            endpoint_url="http://localhost:8000/api/v1/schema",
            method="POST",
            auth_type="api_token",
            parameters_schema=parameters_schema,
            response_schema=response_schema,
            created_by=test_user.id
        )

        assert tool.parameters_schema == parameters_schema
        assert tool.response_schema == response_schema


class TestGetTool:
    """测试获取工具"""

    def test_get_tool_by_id(self, tool_service, sample_tool):
        """测试根据ID获取工具"""
        tool = tool_service.get_tool(sample_tool.id)

        assert tool is not None
        assert tool.id == sample_tool.id
        assert tool.name == sample_tool.name

    def test_get_tool_not_found(self, tool_service):
        """测试获取不存在的工具"""
        tool = tool_service.get_tool(99999)
        assert tool is None

    def test_get_tool_by_name(self, tool_service, sample_tool):
        """测试根据名称获取工具"""
        tool = tool_service.get_tool_by_name("test_tool")

        assert tool is not None
        assert tool.id == sample_tool.id
        assert tool.name == "test_tool"

    def test_get_tool_by_name_not_found(self, tool_service):
        """测试根据名称获取不存在的工具"""
        tool = tool_service.get_tool_by_name("nonexistent_tool")
        assert tool is None


class TestListTools:
    """测试获取工具列表"""

    def test_list_all_tools(self, tool_service, sample_tool):
        """测试获取所有工具"""
        tools = tool_service.list_tools()

        assert len(tools) >= 1
        assert any(t.id == sample_tool.id for t in tools)

    def test_list_tools_with_status_filter(self, tool_service, sample_tool, db):
        """测试按状态过滤工具"""
        # 创建一个停用的工具
        inactive_tool = OpenClawTool(
            name="inactive_tool",
            display_name="停用工具",
            description="停用的工具",
            endpoint_url="http://localhost:8000/api/v1/inactive",
            method="POST",
            auth_type="api_token",
            status=ToolStatus.INACTIVE,
            is_builtin=False
        )
        db.add(inactive_tool)
        db.commit()

        # 获取激活的工具
        active_tools = tool_service.list_tools(status=ToolStatus.ACTIVE)
        assert all(t.status == ToolStatus.ACTIVE for t in active_tools)

        # 获取停用的工具
        inactive_tools = tool_service.list_tools(status=ToolStatus.INACTIVE)
        assert all(t.status == ToolStatus.INACTIVE for t in inactive_tools)

    def test_list_tools_with_builtin_filter(self, tool_service, sample_tool, db):
        """测试按内置标志过滤工具"""
        # 创建一个内置工具
        builtin_tool = OpenClawTool(
            name="builtin_tool",
            display_name="内置工具",
            description="内置工具",
            endpoint_url="http://localhost:8000/api/v1/builtin",
            method="POST",
            auth_type="api_token",
            status=ToolStatus.ACTIVE,
            is_builtin=True
        )
        db.add(builtin_tool)
        db.commit()

        # 获取内置工具
        builtin_tools = tool_service.list_tools(is_builtin=True)
        assert all(t.is_builtin for t in builtin_tools)

        # 获取非内置工具
        custom_tools = tool_service.list_tools(is_builtin=False)
        assert all(not t.is_builtin for t in custom_tools)

    def test_list_tools_pagination(self, tool_service, sample_tool):
        """测试分页"""
        # 获取第一页
        page1 = tool_service.list_tools(skip=0, limit=1)
        assert len(page1) <= 1

        # 获取第二页
        page2 = tool_service.list_tools(skip=1, limit=1)
        if len(page2) > 0:
            assert page1[0].id != page2[0].id

    def test_get_active_tools(self, tool_service, sample_tool):
        """测试获取所有激活的工具"""
        active_tools = tool_service.get_active_tools()

        assert len(active_tools) >= 1
        assert all(t.status == ToolStatus.ACTIVE for t in active_tools)


class TestUpdateTool:
    """测试更新工具"""

    def test_update_tool_success(self, tool_service, sample_tool):
        """测试成功更新工具"""
        update_data = {
            "display_name": "更新后的工具",
            "description": "更新后的描述"
        }

        updated_tool = tool_service.update_tool(sample_tool.id, update_data)

        assert updated_tool is not None
        assert updated_tool.display_name == "更新后的工具"
        assert updated_tool.description == "更新后的描述"
        assert updated_tool.name == sample_tool.name  # 名称不变

    def test_update_tool_not_found(self, tool_service):
        """测试更新不存在的工具"""
        update_data = {"display_name": "不存在"}
        updated_tool = tool_service.update_tool(99999, update_data)

        assert updated_tool is None

    def test_activate_tool(self, tool_service, sample_tool, db):
        """测试激活工具"""
        # 先停用工具
        sample_tool.status = ToolStatus.INACTIVE
        db.commit()

        # 激活工具
        activated_tool = tool_service.activate_tool(sample_tool.id)

        assert activated_tool is not None
        assert activated_tool.status == ToolStatus.ACTIVE

    def test_deactivate_tool(self, tool_service, sample_tool):
        """测试停用工具"""
        deactivated_tool = tool_service.deactivate_tool(sample_tool.id)

        assert deactivated_tool is not None
        assert deactivated_tool.status == ToolStatus.INACTIVE


class TestDeleteTool:
    """测试删除工具"""

    def test_delete_tool_success(self, tool_service, sample_tool):
        """测试成功删除工具"""
        success = tool_service.delete_tool(sample_tool.id)

        assert success is True

        # 验证工具已被软删除（状态变为DELETED）
        deleted_tool = tool_service.get_tool(sample_tool.id)
        assert deleted_tool is not None
        assert deleted_tool.status == ToolStatus.DELETED

    def test_delete_tool_not_found(self, tool_service):
        """测试删除不存在的工具"""
        success = tool_service.delete_tool(99999)
        assert success is False
