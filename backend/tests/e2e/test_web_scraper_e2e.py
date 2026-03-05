"""
Web Scraper E2E测试

测试Web Scraper功能的端到端场景：
1. 任务CRUD操作
2. 任务调度和执行
3. 日志查询和分析
4. 错误处理和恢复
5. 并发任务执行
6. 定时任务调度
"""
import pytest
import requests
import time
from typing import Dict, Any
from datetime import datetime, timedelta


class TestWebScraperE2E:
    """Web Scraper端到端测试类"""

    BASE_URL = "http://localhost:8000/api/v1"

    @pytest.fixture(scope="class")
    def api_client(self):
        """API客户端fixture"""
        client = {
            "base_url": self.BASE_URL,
            "headers": {},
            "user_id": None,
            "token": None,
            "kb_id": None,
            "task_ids": []
        }

        # 用户注册和登录
        self._setup_user(client)

        # 创建知识库
        self._setup_knowledge_base(client)

        yield client

        # 清理测试数据
        self._cleanup(client)

    def _setup_user(self, client: Dict[str, Any]):
        """设置测试用户"""
        # 注册
        response = requests.post(
            f"{client['base_url']}/auth/register",
            json={
                "username": f"e2e_scraper_user_{int(time.time())}",
                "email": f"e2e_scraper_{int(time.time())}@test.com",
                "password": "Test123456"
            }
        )

        if response.status_code == 201:
            data = response.json()
            client["user_id"] = data["id"]

        # 登录
        response = requests.post(
            f"{client['base_url']}/auth/login",
            json={
                "username": response.json().get("username", f"e2e_scraper_user_{int(time.time())}"),
                "password": "Test123456"
            }
        )

        if response.status_code == 200:
            data = response.json()
            client["token"] = data["access_token"]
            client["headers"]["Authorization"] = f"Bearer {data['access_token']}"

    def _setup_knowledge_base(self, client: Dict[str, Any]):
        """设置测试知识库"""
        response = requests.post(
            f"{client['base_url']}/knowledge-bases",
            headers=client["headers"],
            json={
                "name": f"E2E Scraper KB {int(time.time())}",
                "description": "用于Web Scraper E2E测试的知识库"
            }
        )

        if response.status_code == 201:
            data = response.json()
            client["kb_id"] = data["id"]

    def _cleanup(self, client: Dict[str, Any]):
        """清理测试数据"""
        # 删除所有创建的任务
        for task_id in client.get("task_ids", []):
            try:
                requests.delete(
                    f"{client['base_url']}/web-scraper/tasks/{task_id}",
                    headers=client["headers"]
                )
            except:
                pass

        # 删除知识库
        if client.get("kb_id"):
            try:
                requests.delete(
                    f"{client['base_url']}/knowledge-bases/{client['kb_id']}",
                    headers=client["headers"]
                )
            except:
                pass

    def test_01_create_once_task(self, api_client: Dict[str, Any]):
        """测试创建一次性任务"""
        response = requests.post(
            f"{api_client['base_url']}/web-scraper/tasks",
            headers=api_client["headers"],
            json={
                "name": "E2E一次性任务",
                "url": "https://example.com/test",
                "knowledge_base_id": api_client["kb_id"],
                "schedule_type": "once",
                "selector_config": {
                    "title": "h1",
                    "content": "article"
                },
                "scraper_config": {
                    "wait_for_selector": "body",
                    "wait_timeout": 30000
                }
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "E2E一次性任务"
        assert data["schedule_type"] == "once"
        assert data["status"] == "paused"

        api_client["task_ids"].append(data["id"])

    def test_02_create_cron_task(self, api_client: Dict[str, Any]):
        """测试创建定时任务"""
        response = requests.post(
            f"{api_client['base_url']}/web-scraper/tasks",
            headers=api_client["headers"],
            json={
                "name": "E2E定时任务",
                "url": "https://example.com/cron",
                "knowledge_base_id": api_client["kb_id"],
                "schedule_type": "cron",
                "cron_expression": "0 0 * * *",  # 每天午夜执行
                "selector_config": {
                    "title": "h1",
                    "content": ".content"
                }
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["schedule_type"] == "cron"
        assert data["cron_expression"] == "0 0 * * *"

        api_client["task_ids"].append(data["id"])

    def test_03_list_tasks(self, api_client: Dict[str, Any]):
        """测试获取任务列表"""
        response = requests.get(
            f"{api_client['base_url']}/web-scraper/tasks",
            headers=api_client["headers"]
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 2  # 至少有前面创建的2个任务

    def test_04_get_task_detail(self, api_client: Dict[str, Any]):
        """测试获取任务详情"""
        task_id = api_client["task_ids"][0]
        response = requests.get(
            f"{api_client['base_url']}/web-scraper/tasks/{task_id}",
            headers=api_client["headers"]
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert "selector_config" in data
        assert "scraper_config" in data

    def test_05_update_task(self, api_client: Dict[str, Any]):
        """测试更新任务"""
        task_id = api_client["task_ids"][0]
        response = requests.put(
            f"{api_client['base_url']}/web-scraper/tasks/{task_id}",
            headers=api_client["headers"],
            json={
                "name": "E2E一次性任务(已更新)",
                "url": "https://example.com/updated",
                "selector_config": {
                    "title": "h2",
                    "content": ".article-content"
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "E2E一次性任务(已更新)"
        assert data["url"] == "https://example.com/updated"
        assert data["selector_config"]["title"] == "h2"

    def test_06_start_task(self, api_client: Dict[str, Any]):
        """测试启动任务"""
        task_id = api_client["task_ids"][0]
        response = requests.post(
            f"{api_client['base_url']}/web-scraper/tasks/{task_id}/start",
            headers=api_client["headers"]
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

    def test_07_check_task_logs(self, api_client: Dict[str, Any]):
        """测试查看任务日志"""
        task_id = api_client["task_ids"][0]

        # 等待任务执行
        time.sleep(3)

        response = requests.get(
            f"{api_client['base_url']}/web-scraper/tasks/{task_id}/logs",
            headers=api_client["headers"],
            params={"skip": 0, "limit": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_08_filter_logs_by_status(self, api_client: Dict[str, Any]):
        """测试按状态筛选日志"""
        task_id = api_client["task_ids"][0]

        response = requests.get(
            f"{api_client['base_url']}/web-scraper/tasks/{task_id}/logs",
            headers=api_client["headers"],
            params={"status": "success", "skip": 0, "limit": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        # 所有返回的日志状态应该是success
        for log in data["items"]:
            assert log["status"] == "success"

    def test_09_stop_task(self, api_client: Dict[str, Any]):
        """测试停止任务"""
        task_id = api_client["task_ids"][0]
        response = requests.post(
            f"{api_client['base_url']}/web-scraper/tasks/{task_id}/stop",
            headers=api_client["headers"]
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["stopped", "paused"]

    def test_10_create_multiple_tasks(self, api_client: Dict[str, Any]):
        """测试创建多个任务"""
        task_names = ["批量任务1", "批量任务2", "批量任务3"]
        created_ids = []

        for name in task_names:
            response = requests.post(
                f"{api_client['base_url']}/web-scraper/tasks",
                headers=api_client["headers"],
                json={
                    "name": name,
                    "url": f"https://example.com/{name}",
                    "knowledge_base_id": api_client["kb_id"],
                    "schedule_type": "once",
                    "selector_config": {
                        "title": "h1",
                        "content": "article"
                    }
                }
            )

            assert response.status_code == 201
            data = response.json()
            created_ids.append(data["id"])
            api_client["task_ids"].append(data["id"])

        assert len(created_ids) == 3

    def test_11_filter_tasks_by_status(self, api_client: Dict[str, Any]):
        """测试按状态筛选任务"""
        response = requests.get(
            f"{api_client['base_url']}/web-scraper/tasks",
            headers=api_client["headers"],
            params={"status": "paused"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        # 所有返回的任务状态应该是paused
        for task in data["items"]:
            assert task["status"] == "paused"

    def test_12_filter_tasks_by_schedule_type(self, api_client: Dict[str, Any]):
        """测试按调度类型筛选任务"""
        response = requests.get(
            f"{api_client['base_url']}/web-scraper/tasks",
            headers=api_client["headers"],
            params={"schedule_type": "cron"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        # 所有返回的任务调度类型应该是cron
        for task in data["items"]:
            assert task["schedule_type"] == "cron"

    def test_13_pagination(self, api_client: Dict[str, Any]):
        """测试分页功能"""
        # 第一页
        response1 = requests.get(
            f"{api_client['base_url']}/web-scraper/tasks",
            headers=api_client["headers"],
            params={"skip": 0, "limit": 2}
        )

        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1["items"]) <= 2

        # 第二页
        response2 = requests.get(
            f"{api_client['base_url']}/web-scraper/tasks",
            headers=api_client["headers"],
            params={"skip": 2, "limit": 2}
        )

        assert response2.status_code == 200
        data2 = response2.json()

        # 确保两页的任务不重复
        if len(data1["items"]) > 0 and len(data2["items"]) > 0:
            ids1 = {task["id"] for task in data1["items"]}
            ids2 = {task["id"] for task in data2["items"]}
            assert ids1.isdisjoint(ids2)

    def test_14_delete_task(self, api_client: Dict[str, Any]):
        """测试删除任务"""
        # 创建一个临时任务用于删除
        response = requests.post(
            f"{api_client['base_url']}/web-scraper/tasks",
            headers=api_client["headers"],
            json={
                "name": "待删除任务",
                "url": "https://example.com/delete",
                "knowledge_base_id": api_client["kb_id"],
                "schedule_type": "once",
                "selector_config": {
                    "title": "h1",
                    "content": "article"
                }
            }
        )

        assert response.status_code == 201
        task_id = response.json()["id"]

        # 删除任务
        delete_response = requests.delete(
            f"{api_client['base_url']}/web-scraper/tasks/{task_id}",
            headers=api_client["headers"]
        )

        assert delete_response.status_code == 204

        # 验证任务已被删除
        get_response = requests.get(
            f"{api_client['base_url']}/web-scraper/tasks/{task_id}",
            headers=api_client["headers"]
        )

        assert get_response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
