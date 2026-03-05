"""
OpenClaw 工具管理 API 端点测试
"""

import pytest
from fastapi import status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.openclaw_tool import OpenClawTool, ToolStatus


@pytest.fixture
def admin_user(db: Session) -> User:
    """创建管理员用户"""
    from app.core.security import hash_password

    user = User(
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("adminpassword123"),
        is_active=True,
        is_admin=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user: User) -> dict:
    """创建管理员认证头"""
    from app.core.security import create_access_token

    token = create_access_token(subject=admin_user.id, username=admin_user.username)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_tool(db: Session, admin_user: User) -> OpenClawTool:
    """创建示例工具"""
    tool = OpenClawTool(
        name="test_tool",
        display_name="测试工具",
        description="这是一个测试工具",
        endpoint_url="http://localhost:8000/api/v1/test",
        method="POST",
        auth_type="api_token",
        auth_config={"header_name": "X-API-Token"},
        parameters_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            }
        },
        response_schema={
            "type": "object",
            "properties": {
                "result": {"type": "string"}
            }
        },
        status=ToolStatus.ACTIVE,
        is_builtin=False,
        created_by=admin_user.id
    )
    db.add(tool)
    db.commit()
    db.refresh(tool)
    return tool


class TestRegisterTool:
    """测试工具注册"""

    def test_register_tool_success(self, client, admin_headers, db):
        """测试成功注册工具"""
        tool_data = {
            "name": "new_tool",
            "display_name": "新工具",
            "description": "这是一个新工具",
            "endpoint_url": "http://localhost:8000/api/v1/new-tool",
            "method": "POST",
            "auth_type": "api_token",
            "auth_config": {"header_name": "X-API-Token"},
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "input": {"type": "string"}
                }
            },
            "response_schema": {
                "type": "object",
                "properties": {
                    "output": {"type": "string"}
                }
            }
        }

        response = client.post(
            "/api/v1/openclaw/tools/register",
            json=tool_data,
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "new_tool"
        assert data["display_name"] == "新工具"
        assert data["status"] == "active"
        assert data["is_builtin"] is False

    def test_register_tool_duplicate_name(self, client, admin_headers, sample_tool):
        """测试注册重复名称的工具"""
        tool_data = {
            "name": "test_tool",  # 与sample_tool重复
            "display_name": "重复工具",
            "description": "这是一个重复的工具",
            "endpoint_url": "http://localhost:8000/api/v1/duplicate",
            "method": "POST",
            "auth_type": "api_token"
        }

        response = client.post(
            "/api/v1/openclaw/tools/register",
            json=tool_data,
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "已存在" in response.json()["message"]

    def test_register_tool_without_auth(self, client):
        """测试未认证注册工具"""
        tool_data = {
            "name": "unauthorized_tool",
            "display_name": "未授权工具",
            "description": "测试未授权",
            "endpoint_url": "http://localhost:8000/api/v1/test",
            "method": "POST",
            "auth_type": "api_token"
        }

        response = client.post(
            "/api/v1/openclaw/tools/register",
            json=tool_data
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_register_tool_non_admin(self, client, auth_headers):
        """测试非管理员注册工具"""
        tool_data = {
            "name": "non_admin_tool",
            "display_name": "非管理员工具",
            "description": "测试非管理员",
            "endpoint_url": "http://localhost:8000/api/v1/test",
            "method": "POST",
            "auth_type": "api_token"
        }

        response = client.post(
            "/api/v1/openclaw/tools/register",
            json=tool_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestListTools:
    """测试获取工具列表"""

    def test_list_tools_success(self, client, auth_headers, sample_tool):
        """测试成功获取工具列表"""
        response = client.get(
            "/api/v1/openclaw/tools",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

        # 验证工具数据
        tool = data["items"][0]
        assert "id" in tool
        assert "name" in tool
        assert "display_name" in tool

    def test_list_tools_with_filters(self, client, auth_headers, sample_tool, db):
        """测试带过滤条件的工具列表"""
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

        # 测试过滤内置工具
        response = client.get(
            "/api/v1/openclaw/tools?is_builtin=true",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(tool["is_builtin"] for tool in data["items"])

    def test_list_tools_pagination(self, client, auth_headers, sample_tool):
        """测试分页"""
        response = client.get(
            "/api/v1/openclaw/tools?skip=0&limit=10",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) <= 10

    def test_list_tools_without_auth(self, client):
        """测试未认证获取工具列表"""
        response = client.get("/api/v1/openclaw/tools")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetTool:
    """测试获取工具详情"""

    def test_get_tool_success(self, client, auth_headers, sample_tool):
        """测试成功获取工具详情"""
        response = client.get(
            f"/api/v1/openclaw/tools/{sample_tool.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_tool.id
        assert data["name"] == sample_tool.name
        assert data["display_name"] == sample_tool.display_name
        assert data["endpoint_url"] == sample_tool.endpoint_url

    def test_get_tool_not_found(self, client, auth_headers):
        """测试获取不存在的工具"""
        response = client.get(
            "/api/v1/openclaw/tools/99999",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_tool_without_auth(self, client, sample_tool):
        """测试未认证获取工具详情"""
        response = client.get(f"/api/v1/openclaw/tools/{sample_tool.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
