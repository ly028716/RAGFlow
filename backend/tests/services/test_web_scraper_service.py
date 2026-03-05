"""
Web Scraper 服务层测试
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.models.web_scraper_task import WebScraperTask, TaskStatus, ScheduleType
from app.models.web_scraper_log import WebScraperLog, LogStatus
from app.services.web_scraper_service import (
    WebScraperService,
    TaskNotFoundError,
    InvalidTaskConfigError,
    KnowledgeBaseAccessError,
)


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
def scraper_service(db: Session) -> WebScraperService:
    """创建Web Scraper服务实例"""
    return WebScraperService(db)


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
    """测试创建任务"""

    def test_create_task_success(self, scraper_service, test_user, test_kb):
        """测试成功创建任务"""
        task = scraper_service.create_task(
            name="新任务",
            url="https://example.com/page",
            knowledge_base_id=test_kb.id,
            user_id=test_user.id,
            description="测试描述",
            schedule_type=ScheduleType.ONCE,
            selector_config={
                "title": "h1",
                "content": "article"
            }
        )

        assert task.id is not None
        assert task.name == "新任务"
        assert task.url == "https://example.com/page"
        assert task.knowledge_base_id == test_kb.id
        assert task.created_by == test_user.id
        assert task.status == TaskStatus.PAUSED

    def test_create_task_with_cron(self, scraper_service, test_user, test_kb):
        """测试创建定时任务"""
        with patch('app.services.web_scraper_service.get_scheduler') as mock_scheduler:
            mock_scheduler.return_value.add_job.return_value = True

            task = scraper_service.create_task(
                name="定时任务",
                url="https://example.com/page",
                knowledge_base_id=test_kb.id,
                user_id=test_user.id,
                schedule_type=ScheduleType.CRON,
                cron_expression="0 0 * * *",
                selector_config={
                    "title": "h1",
                    "content": "article"
                }
            )

            assert task.schedule_type == ScheduleType.CRON
            assert task.cron_expression == "0 0 * * *"
            assert task.status == TaskStatus.ACTIVE

    def test_create_task_invalid_url(self, scraper_service, test_user, test_kb):
        """测试创建任务时URL无效"""
        with pytest.raises(InvalidTaskConfigError, match="URL验证失败"):
            scraper_service.create_task(
                name="无效URL任务",
                url="javascript:alert('xss')",
                knowledge_base_id=test_kb.id,
                user_id=test_user.id,
                selector_config={
                    "title": "h1",
                    "content": "article"
                }
            )

    def test_create_task_nonexistent_kb(self, scraper_service, test_user):
        """测试创建任务时知识库不存在"""
        with pytest.raises(KnowledgeBaseAccessError, match="知识库不存在"):
            scraper_service.create_task(
                name="任务",
                url="https://example.com/page",
                knowledge_base_id=99999,
                user_id=test_user.id,
                selector_config={
                    "title": "h1",
                    "content": "article"
                }
            )

    def test_create_task_missing_cron_expression(self, scraper_service, test_user, test_kb):
        """测试创建定时任务时缺少Cron表达式"""
        with pytest.raises(InvalidTaskConfigError, match="必须提供Cron表达式"):
            scraper_service.create_task(
                name="定时任务",
                url="https://example.com/page",
                knowledge_base_id=test_kb.id,
                user_id=test_user.id,
                schedule_type=ScheduleType.CRON,
                selector_config={
                    "title": "h1",
                    "content": "article"
                }
            )

    def test_create_task_missing_selector_fields(self, scraper_service, test_user, test_kb):
        """测试创建任务时选择器配置缺少必需字段"""
        with pytest.raises(InvalidTaskConfigError, match="缺少必需字段"):
            scraper_service.create_task(
                name="任务",
                url="https://example.com/page",
                knowledge_base_id=test_kb.id,
                user_id=test_user.id,
                selector_config={
                    "title": "h1"
                    # 缺少 content 字段
                }
            )


class TestUpdateTask:
    """测试更新任务"""

    def test_update_task_success(self, scraper_service, sample_task, test_user):
        """测试成功更新任务"""
        updated_task = scraper_service.update_task(
            task_id=sample_task.id,
            user_id=test_user.id,
            name="更新后的名称",
            description="更新后的描述"
        )

        assert updated_task.name == "更新后的名称"
        assert updated_task.description == "更新后的描述"

    def test_update_task_not_found(self, scraper_service, test_user):
        """测试更新不存在的任务"""
        with pytest.raises(TaskNotFoundError):
            scraper_service.update_task(
                task_id=99999,
                user_id=test_user.id,
                name="新名称"
            )

    def test_update_task_no_permission(self, scraper_service, sample_task, other_user):
        """测试更新其他用户的任务"""
        with pytest.raises(KnowledgeBaseAccessError, match="无权限"):
            scraper_service.update_task(
                task_id=sample_task.id,
                user_id=other_user.id,
                name="新名称"
            )

    def test_update_task_invalid_url(self, scraper_service, sample_task, test_user):
        """测试更新任务时URL无效"""
        with pytest.raises(InvalidTaskConfigError, match="URL验证失败"):
            scraper_service.update_task(
                task_id=sample_task.id,
                user_id=test_user.id,
                url="ftp://invalid.com"
            )


class TestDeleteTask:
    """测试删除任务"""

    def test_delete_task_success(self, scraper_service, sample_task, test_user):
        """测试成功删除任务"""
        result = scraper_service.delete_task(sample_task.id, test_user.id)

        assert result is True

    def test_delete_task_not_found(self, scraper_service, test_user):
        """测试删除不存在的任务"""
        with pytest.raises(TaskNotFoundError):
            scraper_service.delete_task(99999, test_user.id)

    def test_delete_task_no_permission(self, scraper_service, sample_task, other_user):
        """测试删除其他用户的任务"""
        with pytest.raises(KnowledgeBaseAccessError, match="无权限"):
            scraper_service.delete_task(sample_task.id, other_user.id)


class TestGetTask:
    """测试获取任务"""

    def test_get_task_success(self, scraper_service, sample_task, test_user):
        """测试成功获取任务"""
        task = scraper_service.get_task(sample_task.id, test_user.id)

        assert task.id == sample_task.id
        assert task.name == sample_task.name

    def test_get_task_not_found(self, scraper_service, test_user):
        """测试获取不存在的任务"""
        with pytest.raises(TaskNotFoundError):
            scraper_service.get_task(99999, test_user.id)

    def test_get_task_no_permission(self, scraper_service, sample_task, other_user):
        """测试获取其他用户的任务"""
        with pytest.raises(KnowledgeBaseAccessError, match="无权限"):
            scraper_service.get_task(sample_task.id, other_user.id)


class TestListTasks:
    """测试获取任务列表"""

    def test_list_tasks_success(self, scraper_service, sample_task, test_user):
        """测试成功获取任务列表"""
        tasks = scraper_service.list_tasks(user_id=test_user.id)

        assert len(tasks) >= 1
        assert any(t.id == sample_task.id for t in tasks)

    def test_list_tasks_with_filters(self, scraper_service, sample_task, test_user, test_kb):
        """测试使用过滤条件获取任务列表"""
        tasks = scraper_service.list_tasks(
            user_id=test_user.id,
            status=TaskStatus.PAUSED,
            knowledge_base_id=test_kb.id
        )

        assert all(t.status == TaskStatus.PAUSED for t in tasks)
        assert all(t.knowledge_base_id == test_kb.id for t in tasks)


class TestTaskLifecycle:
    """测试任务生命周期管理"""

    def test_start_task(self, scraper_service, sample_task, test_user):
        """测试启动任务"""
        with patch('app.services.web_scraper_service.get_scheduler') as mock_scheduler:
            mock_scheduler.return_value.add_job.return_value = True

            task = scraper_service.start_task(sample_task.id, test_user.id)

            assert task.status == TaskStatus.ACTIVE

    def test_stop_task(self, scraper_service, sample_task, test_user):
        """测试停止任务"""
        with patch('app.services.web_scraper_service.get_scheduler') as mock_scheduler:
            mock_scheduler.return_value.remove_job.return_value = True

            task = scraper_service.stop_task(sample_task.id, test_user.id)

            assert task.status == TaskStatus.STOPPED

    def test_pause_task(self, scraper_service, sample_task, test_user):
        """测试暂停任务"""
        with patch('app.services.web_scraper_service.get_scheduler') as mock_scheduler:
            mock_scheduler.return_value.remove_job.return_value = True

            task = scraper_service.pause_task(sample_task.id, test_user.id)

            assert task.status == TaskStatus.PAUSED

    def test_resume_task(self, scraper_service, sample_task, test_user):
        """测试恢复任务"""
        with patch('app.services.web_scraper_service.get_scheduler') as mock_scheduler:
            mock_scheduler.return_value.add_job.return_value = True

            task = scraper_service.resume_task(sample_task.id, test_user.id)

            assert task.status == TaskStatus.ACTIVE
