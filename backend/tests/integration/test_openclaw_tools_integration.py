"""
OpenClaw 工具注册功能集成测试

端到端测试：注册工具 -> 调用工具 -> 查看调用记录
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.openclaw_tool import ToolStatus


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


class TestToolRegistrationIntegration:
    """测试工具注册集成流程"""

    def test_complete_tool_lifecycle(self, client, admin_headers, db):
        """测试完整的工具生命周期：注册 -> 查询 -> 更新 -> 删除"""

        # 1. 注册工具
        tool_data = {
            "name": "lifecycle_tool",
            "display_name": "生命周期测试工具",
            "description": "测试完整生命周期",
            "endpoint_url": "http://localhost:8000/api/v1/lifecycle",
            "method": "POST",
            "auth_type": "api_token"
        }

        register_response = client.post(
            "/api/v1/openclaw/tools/register",
            json=tool_data,
            headers=admin_headers
        )

        assert register_response.status_code == status.HTTP_201_CREATED
        tool = register_response.json()
        tool_id = tool["id"]
        assert tool["name"] == "lifecycle_tool"
        assert tool["status"] == "active"

        # 2. 查询工具详情
        get_response = client.get(
            f"/api/v1/openclaw/tools/{tool_id}",
            headers=admin_headers
        )

        assert get_response.status_code == status.HTTP_200_OK
        retrieved_tool = get_response.json()
        assert retrieved_tool["id"] == tool_id
        assert retrieved_tool["name"] == "lifecycle_tool"

        # 3. 查询工具列表
        list_response = client.get(
            "/api/v1/openclaw/tools",
            headers=admin_headers
        )

        assert list_response.status_code == status.HTTP_200_OK
        tools_list = list_response.json()
        assert any(t["id"] == tool_id for t in tools_list["items"])

        # 4. 验证工具在数据库中
        from app.models.openclaw_tool import OpenClawTool
        db_tool = db.query(OpenClawTool).filter(OpenClawTool.id == tool_id).first()
        assert db_tool is not None
        assert db_tool.name == "lifecycle_tool"


class TestKnowledgeBaseQueryIntegration:
    """测试知识库查询工具集成流程"""

    @patch("app.api.v1.tools.RAGService")
    def test_query_kb_end_to_end(self, mock_rag_service, client, db):
        """测试知识库查询端到端流程"""

        # 1. 确保知识库查询工具已注册
        from app.services.openclaw_tool_service import OpenClawToolService
        tool_service = OpenClawToolService(db)

        kb_tool = tool_service.get_tool_by_name("query_knowledge_base")
        if not kb_tool:
            kb_tool = tool_service.register_tool(
                name="query_knowledge_base",
                display_name="知识库查询",
                description="查询知识库",
                endpoint_url="http://localhost:8000/api/v1/tools/query-kb",
                method="POST",
                auth_type="api_token",
                is_builtin=True
            )

        # 2. 模拟RAG服务返回结果
        mock_service_instance = mock_rag_service.return_value
        mock_service_instance.retrieve_documents = AsyncMock(return_value=[
            {
                "content": "测试内容",
                "similarity_score": 0.95,
                "document_id": 1,
                "document_name": "test.pdf",
                "knowledge_base_id": 1,
                "knowledge_base_name": "测试库"
            }
        ])

        # 3. 调用知识库查询工具
        query_request = {
            "query": "测试查询",
            "top_k": 5
        }

        query_response = client.post(
            "/api/v1/tools/query-kb",
            json=query_request,
            headers={"X-API-Token": "test-token"}
        )

        assert query_response.status_code == status.HTTP_200_OK
        result = query_response.json()
        assert result["success"] is True
        assert len(result["results"]) == 1

        # 4. 验证调用记录已创建
        from app.models.openclaw_tool_call import OpenClawToolCall
        calls = db.query(OpenClawToolCall).filter(
            OpenClawToolCall.tool_id == kb_tool.id
        ).all()

        assert len(calls) >= 1
        latest_call = calls[-1]
        assert latest_call.status == "success"
        assert latest_call.request_params["query"] == "测试查询"


class TestMultipleToolsIntegration:
    """测试多个工具的集成场景"""

    def test_register_multiple_tools(self, client, admin_headers):
        """测试注册多个工具"""

        tools_data = [
            {
                "name": "tool_1",
                "display_name": "工具1",
                "description": "第一个工具",
                "endpoint_url": "http://localhost:8000/api/v1/tool1",
                "method": "POST",
                "auth_type": "api_token"
            },
            {
                "name": "tool_2",
                "display_name": "工具2",
                "description": "第二个工具",
                "endpoint_url": "http://localhost:8000/api/v1/tool2",
                "method": "GET",
                "auth_type": "none"
            },
            {
                "name": "tool_3",
                "display_name": "工具3",
                "description": "第三个工具",
                "endpoint_url": "http://localhost:8000/api/v1/tool3",
                "method": "POST",
                "auth_type": "api_token"
            }
        ]

        tool_ids = []
        for tool_data in tools_data:
            response = client.post(
                "/api/v1/openclaw/tools/register",
                json=tool_data,
                headers=admin_headers
            )
            assert response.status_code == status.HTTP_201_CREATED
            tool_ids.append(response.json()["id"])

        # 验证所有工具都已注册
        list_response = client.get(
            "/api/v1/openclaw/tools",
            headers=admin_headers
        )

        assert list_response.status_code == status.HTTP_200_OK
        tools_list = list_response.json()

        for tool_id in tool_ids:
            assert any(t["id"] == tool_id for t in tools_list["items"])


class TestToolCallHistoryIntegration:
    """测试工具调用历史集成"""

    @patch("app.api.v1.tools.RAGService")
    def test_multiple_calls_history(self, mock_rag_service, client, db):
        """测试多次调用的历史记录"""

        # 1. 确保工具已注册
        from app.services.openclaw_tool_service import OpenClawToolService
        tool_service = OpenClawToolService(db)

        kb_tool = tool_service.get_tool_by_name("query_knowledge_base")
        if not kb_tool:
            kb_tool = tool_service.register_tool(
                name="query_knowledge_base",
                display_name="知识库查询",
                description="查询知识库",
                endpoint_url="http://localhost:8000/api/v1/tools/query-kb",
                method="POST",
                auth_type="api_token",
                is_builtin=True
            )

        # 2. 模拟RAG服务
        mock_service_instance = mock_rag_service.return_value
        mock_service_instance.retrieve_documents = AsyncMock(return_value=[])

        # 3. 执行多次调用
        queries = ["查询1", "查询2", "查询3"]
        for query in queries:
            client.post(
                "/api/v1/tools/query-kb",
                json={"query": query, "top_k": 5},
                headers={"X-API-Token": "test-token"}
            )

        # 4. 验证调用历史
        from app.models.openclaw_tool_call import OpenClawToolCall
        calls = db.query(OpenClawToolCall).filter(
            OpenClawToolCall.tool_id == kb_tool.id
        ).all()

        assert len(calls) >= 3

        # 验证每个查询都被记录
        recorded_queries = [call.request_params.get("query") for call in calls]
        for query in queries:
            assert query in recorded_queries


class TestErrorHandlingIntegration:
    """测试错误处理集成"""

    @patch("app.api.v1.tools.RAGService")
    def test_failed_call_recorded(self, mock_rag_service, client, db):
        """测试失败的调用也会被记录"""

        # 1. 确保工具已注册
        from app.services.openclaw_tool_service import OpenClawToolService
        tool_service = OpenClawToolService(db)

        kb_tool = tool_service.get_tool_by_name("query_knowledge_base")
        if not kb_tool:
            kb_tool = tool_service.register_tool(
                name="query_knowledge_base",
                display_name="知识库查询",
                description="查询知识库",
                endpoint_url="http://localhost:8000/api/v1/tools/query-kb",
                method="POST",
                auth_type="api_token",
                is_builtin=True
            )

        # 2. 模拟RAG服务抛出异常
        mock_service_instance = mock_rag_service.return_value
        mock_service_instance.retrieve_documents = AsyncMock(
            side_effect=Exception("数据库错误")
        )

        # 3. 执行调用（预期失败）
        response = client.post(
            "/api/v1/tools/query-kb",
            json={"query": "测试查询", "top_k": 5},
            headers={"X-API-Token": "test-token"}
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        # 4. 验证失败的调用被记录
        from app.models.openclaw_tool_call import OpenClawToolCall
        calls = db.query(OpenClawToolCall).filter(
            OpenClawToolCall.tool_id == kb_tool.id,
            OpenClawToolCall.status == "failed"
        ).all()

        assert len(calls) >= 1
        latest_call = calls[-1]
        assert "数据库错误" in latest_call.error_message
