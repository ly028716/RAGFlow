"""
端到端测试脚本

测试完整的用户场景：
1. 用户注册和登录
2. 创建知识库
3. 上传文档
4. 查询知识库
5. 对话交互
"""
import pytest
import requests
from typing import Dict, Any


class TestEndToEnd:
    """端到端测试类"""

    BASE_URL = "http://localhost:8000/api/v1"

    @pytest.fixture(scope="class")
    def api_client(self):
        """API客户端fixture"""
        return {
            "base_url": self.BASE_URL,
            "headers": {},
            "user_id": None,
            "token": None
        }

    def test_01_user_registration(self, api_client: Dict[str, Any]):
        """测试用户注册"""
        response = requests.post(
            f"{api_client['base_url']}/auth/register",
            json={
                "username": "e2e_test_user",
                "email": "e2e@test.com",
                "password": "Test123456"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["username"] == "e2e_test_user"

        api_client["user_id"] = data["id"]

    def test_02_user_login(self, api_client: Dict[str, Any]):
        """测试用户登录"""
        response = requests.post(
            f"{api_client['base_url']}/auth/login",
            json={
                "username": "e2e_test_user",
                "password": "Test123456"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

        api_client["token"] = data["access_token"]
        api_client["headers"]["Authorization"] = f"Bearer {data['access_token']}"

    def test_03_create_knowledge_base(self, api_client: Dict[str, Any]):
        """测试创建知识库"""
        response = requests.post(
            f"{api_client['base_url']}/knowledge-bases",
            headers=api_client["headers"],
            json={
                "name": "E2E测试知识库",
                "description": "用于端到端测试的知识库"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "E2E测试知识库"

        api_client["kb_id"] = data["id"]

    def test_04_query_knowledge_base(self, api_client: Dict[str, Any]):
        """测试查询知识库"""
        response = requests.post(
            f"{api_client['base_url']}/knowledge-bases/{api_client['kb_id']}/query",
            headers=api_client["headers"],
            json={
                "query": "测试查询",
                "top_k": 5
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_05_chat_with_knowledge(self, api_client: Dict[str, Any]):
        """测试基于知识库的对话"""
        response = requests.post(
            f"{api_client['base_url']}/chat",
            headers=api_client["headers"],
            json={
                "content": "请介绍一下知识库中的内容",
                "knowledge_base_id": api_client["kb_id"],
                "stream": False
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"]["role"] == "assistant"

    def test_06_cleanup(self, api_client: Dict[str, Any]):
        """清理测试数据"""
        # 删除知识库
        requests.delete(
            f"{api_client['base_url']}/knowledge-bases/{api_client['kb_id']}",
            headers=api_client["headers"]
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
