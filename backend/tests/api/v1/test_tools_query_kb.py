"""
知识库查询工具 API 端点测试
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.openclaw_tool import OpenClawTool, ToolStatus


@pytest.fixture
def query_kb_tool(db: Session) -> OpenClawTool:
    """创建知识库查询工具"""
    tool = OpenClawTool(
        name="query_knowledge_base",
        display_name="知识库查询",
        description="查询指定知识库中的相关文档",
        endpoint_url="http://localhost:8000/api/v1/tools/query-kb",
        method="POST",
        auth_type="api_token",
        auth_config={"header_name": "X-API-Token"},
        parameters_schema={
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "knowledge_base_ids": {"type": "array"},
                "top_k": {"type": "integer"},
                "similarity_threshold": {"type": "number"}
            }
        },
        status=ToolStatus.ACTIVE,
        is_builtin=True
    )
    db.add(tool)
    db.commit()
    db.refresh(tool)
    return tool


class TestQueryKnowledgeBase:
    """测试知识库查询工具"""

    @patch("app.api.v1.tools.RAGService")
    def test_query_kb_success(self, mock_rag_service, client, query_kb_tool):
        """测试成功查询知识库"""
        # 模拟RAG服务返回结果
        mock_service_instance = mock_rag_service.return_value
        mock_service_instance.retrieve_documents = AsyncMock(return_value=[
            {
                "content": "Python是一种高级编程语言",
                "similarity_score": 0.95,
                "document_id": 1,
                "document_name": "Python教程.pdf",
                "knowledge_base_id": 1,
                "knowledge_base_name": "技术文档"
            },
            {
                "content": "Python具有简洁的语法",
                "similarity_score": 0.88,
                "document_id": 2,
                "document_name": "Python入门.pdf",
                "knowledge_base_id": 1,
                "knowledge_base_name": "技术文档"
            }
        ])

        request_data = {
            "query": "什么是Python",
            "knowledge_base_ids": [1],
            "top_k": 5,
            "similarity_threshold": 0.7
        }

        response = client.post(
            "/api/v1/tools/query-kb",
            json=request_data,
            headers={"X-API-Token": "test-token"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["query"] == "什么是Python"
        assert len(data["results"]) == 2
        assert data["total_results"] == 2

        # 验证结果内容
        result = data["results"][0]
        assert result["content"] == "Python是一种高级编程语言"
        assert result["similarity_score"] == 0.95
        assert result["document_name"] == "Python教程.pdf"

    def test_query_kb_without_token(self, client, query_kb_tool):
        """测试未提供API Token"""
        request_data = {
            "query": "测试查询",
            "top_k": 5
        }

        response = client.post(
            "/api/v1/tools/query-kb",
            json=request_data
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "API Token" in response.json()["message"]

    @patch("app.config.settings")
    def test_query_kb_invalid_token(self, mock_settings, client, query_kb_tool):
        """测试无效的API Token"""
        # 模拟配置中的有效token
        mock_openclaw = type('obj', (object,), {'api_tokens': 'valid-token-1,valid-token-2'})()
        mock_settings.openclaw = mock_openclaw

        request_data = {
            "query": "测试查询",
            "top_k": 5
        }

        response = client.post(
            "/api/v1/tools/query-kb",
            json=request_data,
            headers={"X-API-Token": "invalid-token"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_query_kb_empty_query(self, client, query_kb_tool):
        """测试空查询"""
        request_data = {
            "query": "",
            "top_k": 5
        }

        response = client.post(
            "/api/v1/tools/query-kb",
            json=request_data,
            headers={"X-API-Token": "test-token"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_kb_invalid_top_k(self, client, query_kb_tool):
        """测试无效的top_k参数"""
        request_data = {
            "query": "测试查询",
            "top_k": 0  # 无效值
        }

        response = client.post(
            "/api/v1/tools/query-kb",
            json=request_data,
            headers={"X-API-Token": "test-token"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_kb_invalid_similarity_threshold(self, client, query_kb_tool):
        """测试无效的相似度阈值"""
        request_data = {
            "query": "测试查询",
            "similarity_threshold": 1.5  # 超出范围
        }

        response = client.post(
            "/api/v1/tools/query-kb",
            json=request_data,
            headers={"X-API-Token": "test-token"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("app.api.v1.tools.RAGService")
    def test_query_kb_no_results(self, mock_rag_service, client, query_kb_tool):
        """测试查询无结果"""
        # 模拟RAG服务返回空结果
        mock_service_instance = mock_rag_service.return_value
        mock_service_instance.retrieve_documents = AsyncMock(return_value=[])

        request_data = {
            "query": "不存在的内容",
            "top_k": 5
        }

        response = client.post(
            "/api/v1/tools/query-kb",
            json=request_data,
            headers={"X-API-Token": "test-token"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) == 0
        assert data["total_results"] == 0

    @patch("app.api.v1.tools.RAGService")
    def test_query_kb_with_specific_kb_ids(self, mock_rag_service, client, query_kb_tool):
        """测试指定知识库ID查询"""
        mock_service_instance = mock_rag_service.return_value
        mock_service_instance.retrieve_documents = AsyncMock(return_value=[
            {
                "content": "测试内容",
                "similarity_score": 0.9,
                "document_id": 1,
                "document_name": "test.pdf",
                "knowledge_base_id": 2,
                "knowledge_base_name": "测试库"
            }
        ])

        request_data = {
            "query": "测试查询",
            "knowledge_base_ids": [2, 3],
            "top_k": 5
        }

        response = client.post(
            "/api/v1/tools/query-kb",
            json=request_data,
            headers={"X-API-Token": "test-token"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

        # 验证调用参数
        mock_service_instance.retrieve_documents.assert_called_once()
        call_kwargs = mock_service_instance.retrieve_documents.call_args.kwargs
        assert call_kwargs["knowledge_base_ids"] == [2, 3]

    @patch("app.api.v1.tools.RAGService")
    def test_query_kb_service_error(self, mock_rag_service, client, query_kb_tool):
        """测试RAG服务错误"""
        # 模拟RAG服务抛出异常
        mock_service_instance = mock_rag_service.return_value
        mock_service_instance.retrieve_documents = AsyncMock(
            side_effect=Exception("数据库连接失败")
        )

        request_data = {
            "query": "测试查询",
            "top_k": 5
        }

        response = client.post(
            "/api/v1/tools/query-kb",
            json=request_data,
            headers={"X-API-Token": "test-token"}
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "查询失败" in response.json()["message"]

    @patch("app.api.v1.tools.RAGService")
    @patch("app.api.v1.tools.OpenClawToolService")
    def test_query_kb_records_call(self, mock_tool_service, mock_rag_service, client, query_kb_tool):
        """测试工具调用记录"""
        # 模拟RAG服务
        mock_rag_instance = mock_rag_service.return_value
        mock_rag_instance.retrieve_documents = AsyncMock(return_value=[])

        # 模拟工具服务
        mock_tool_instance = mock_tool_service.return_value
        mock_tool_instance.get_tool_by_name = lambda name: query_kb_tool
        mock_tool_instance.record_tool_call = lambda **kwargs: None

        request_data = {
            "query": "测试查询",
            "top_k": 5
        }

        response = client.post(
            "/api/v1/tools/query-kb",
            json=request_data,
            headers={"X-API-Token": "test-token"}
        )

        assert response.status_code == status.HTTP_200_OK
