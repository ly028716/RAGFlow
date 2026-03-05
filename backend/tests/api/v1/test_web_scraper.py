"""
Web Scraper API 端点测试
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, AsyncMock

from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.models.web_scraper_task import WebScraperTask, TaskStatus, ScheduleType


@pytest.fixture
def test_kb(db: Session, test_user: User) -> KnowledgeBase:
    """创建测试知识库"""
    kb = KnowledgeBase(
        name="测试知识库",
        description="用于测试的知识库",
        user_id=test_user.id,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


@pytest.fixture
def sample_task(db: Session, test_user: User, test_kb: KnowledgeBase) -> WebScraperTask:
    """创建示例任务"""
    task = WebScraperTask(
        name="测试任务",
        description="这是一个测试任务",
        url="https://example.com/article",
        knowledge_base_id=test_kb.id,
        schedule_type=ScheduleType.ONCE,
        selector_config={
            "title": "h1.title",
            "content": "div.content"
        },
        scraper_config={
            "wait_for_selector": "article",
            "wait_timeout": 30000
        },
        status=TaskStatus.PAUSED,
        created_by=test_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


class TestCreateTask:
    """测试创建任务端点"""

    def test_create_task_success(self, client: TestClient, auth_headers: dict, test_kb: KnowledgeBase):
        """测试成功创建任务"""
        response = client.post(
            "/api/v1/web-scraper/tasks",
            json={
                "name": "新任务",
                "url": "https://example.com/page",
                "knowledge_base_id": test_kb.id,
                "schedule_type": "once",
                "selector_config": {
                    "title": "h1",
                    "content": "article"
                }
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "新任务"
        assert data["url"] == "https://example.com/page"
        assert data["knowledge_base_id"] == test_kb.id

    def test_create_task_unauthorized(self, client: TestClient, test_kb: KnowledgeBase):
        """测试未认证创建任务"""
        response = client.post(
            "/api/v1/web-scraper/tasks",
            json={
                "name": "新任务",
                "url": "https://example.com/page",
                "knowledge_base_id": test_kb.id,
                "selector_config": {
                    "title": "h1",
                    "content": "article"
                }
            }
        )

        assert response.status_code == 401

    def test_create_task_invalid_url(self, client: TestClient, auth_headers: dict, test_kb: KnowledgeBase):
        """测试创建任务时URL无效"""
        response = client.post(
            "/api/v1/web-scraper/tasks",
            json={
                "name": "无效URL任务",
                "url": "javascript:alert('xss')",
                "knowledge_base_id": test_kb.id,
                "selector_config": {
                    "title": "h1",
                    "content": "article"
                }
            },
            headers=auth_headers
        )

        assert response.status_code == 422  # Pydantic validation error

    def test_create_task_missing_fields(self, client: TestClient, auth_headers: dict, test_kb: KnowledgeBase):
        """测试创建任务时缺少必需字段"""
        response = client.post(
            "/api/v1/web-scraper/tasks",
            json={
                "name": "任务",
                "url": "https://example.com/page",
                "knowledge_base_id": test_kb.id,
                "selector_config": {
                    "title": "h1"
                    # 缺少 content 字段
                }
            },
            headers=auth_headers
        )

        assert response.status_code == 422


class TestListTasks:
    """测试获取任务列表端点"""

    def test_list_tasks_success(self, client: TestClient, auth_headers: dict, sample_task: WebScraperTask):
        """测试成功获取任务列表"""
        response = client.get(
            "/api/v1/web-scraper/tasks",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] >= 1

    def test_list_tasks_with_filters(self, client: TestClient, auth_headers: dict, sample_task: WebScraperTask):
        """测试使用过滤条件获取任务列表"""
        response = client.get(
            "/api/v1/web-scraper/tasks?status=paused",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert all(item["status"] == "paused" for item in data["items"])

    def test_list_tasks_unauthorized(self, client: TestClient):
        """测试未认证获取任务列表"""
        response = client.get("/api/v1/web-scraper/tasks")

        assert response.status_code == 401


class TestGetTask:
    """测试获取任务详情端点"""

    def test_get_task_success(self, client: TestClient, auth_headers: dict, sample_task: WebScraperTask):
        """测试成功获取任务详情"""
        response = client.get(
            f"/api/v1/web-scraper/tasks/{sample_task.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_task.id
        assert data["name"] == sample_task.name

    def test_get_task_not_found(self, client: TestClient, auth_headers: dict):
        """测试获取不存在的任务"""
        response = client.get(
            "/api/v1/web-scraper/tasks/99999",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_get_task_no_permission(self, client: TestClient, other_auth_headers: dict, sample_task: WebScraperTask):
        """测试获取其他用户的任务"""
        response = client.get(
            f"/api/v1/web-scraper/tasks/{sample_task.id}",
            headers=other_auth_headers
        )

        assert response.status_code == 403


class TestUpdateTask:
    """测试更新任务端点"""

    def test_update_task_success(self, client: TestClient, auth_headers: dict, sample_task: WebScraperTask):
        """测试成功更新任务"""
        response = client.put(
            f"/api/v1/web-scraper/tasks/{sample_task.id}",
            json={
                "name": "更新后的名称",
                "description": "更新后的描述"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新后的名称"
        assert data["description"] == "更新后的描述"

    def test_update_task_not_found(self, client: TestClient, auth_headers: dict):
        """测试更新不存在的任务"""
        response = client.put(
            "/api/v1/web-scraper/tasks/99999",
            json={"name": "新名称"},
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_update_task_no_permission(self, client: TestClient, other_auth_headers: dict, sample_task: WebScraperTask):
        """测试更新其他用户的任务"""
        response = client.put(
            f"/api/v1/web-scraper/tasks/{sample_task.id}",
            json={"name": "新名称"},
            headers=other_auth_headers
        )

        assert response.status_code == 403


class TestDeleteTask:
    """测试删除任务端点"""

    def test_delete_task_success(self, client: TestClient, auth_headers: dict, sample_task: WebScraperTask):
        """测试成功删除任务"""
        response = client.delete(
            f"/api/v1/web-scraper/tasks/{sample_task.id}",
            headers=auth_headers
        )

        assert response.status_code == 204

    def test_delete_task_not_found(self, client: TestClient, auth_headers: dict):
        """测试删除不存在的任务"""
        response = client.delete(
            "/api/v1/web-scraper/tasks/99999",
            headers=auth_headers
        )

        assert response.status_code == 404


class TestTaskControl:
    """测试任务控制端点"""

    @patch('app.services.web_scraper_service.get_scheduler')
    def test_start_task(self, mock_scheduler, client: TestClient, auth_headers: dict, sample_task: WebScraperTask):
        """测试启动任务"""
        mock_scheduler.return_value.add_job.return_value = True

        response = client.post(
            f"/api/v1/web-scraper/tasks/{sample_task.id}/start",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

    @patch('app.services.web_scraper_service.get_scheduler')
    def test_stop_task(self, mock_scheduler, client: TestClient, auth_headers: dict, sample_task: WebScraperTask):
        """测试停止任务"""
        mock_scheduler.return_value.remove_job.return_value = True

        response = client.post(
            f"/api/v1/web-scraper/tasks/{sample_task.id}/stop",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"

    @patch('app.services.web_scraper_service.get_scheduler')
    def test_pause_task(self, mock_scheduler, client: TestClient, auth_headers: dict, sample_task: WebScraperTask):
        """测试暂停任务"""
        mock_scheduler.return_value.remove_job.return_value = True

        response = client.post(
            f"/api/v1/web-scraper/tasks/{sample_task.id}/pause",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"

    @patch('app.services.web_scraper_service.get_scheduler')
    def test_resume_task(self, mock_scheduler, client: TestClient, auth_headers: dict, sample_task: WebScraperTask):
        """测试恢复任务"""
        mock_scheduler.return_value.add_job.return_value = True

        response = client.post(
            f"/api/v1/web-scraper/tasks/{sample_task.id}/resume",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
