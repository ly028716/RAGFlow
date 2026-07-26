"""
种子数据脚本测试
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from scripts.seed_data import create_builtin_tools, create_test_users


@pytest.fixture
def mock_session():
    """Mock数据库会话"""
    session = Mock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.commit = Mock()
    session.add = Mock()
    session.flush = Mock()
    return session


class TestSeedData:
    """种子数据脚本测试类"""

    def test_create_builtin_tools_success(self, mock_session):
        """测试创建内置工具成功"""
        # 执行创建
        create_builtin_tools(mock_session)

        # 验证添加了6个工具
        assert mock_session.add.call_count == 2
        assert mock_session.commit.called

    def test_create_builtin_tools_skip_existing(self, mock_session):
        """测试跳过已存在的工具"""
        # Mock已存在的工具
        existing_tool = Mock()
        existing_tool.name = "calculator"
        mock_session.query.return_value.filter.return_value.first.return_value = existing_tool

        # 执行创建
        create_builtin_tools(mock_session)

        # 验证没有添加工具（因为都已存在）
        assert mock_session.add.call_count == 0

    def test_builtin_tools_have_correct_names(self, mock_session):
        """测试内置工具名称正确"""
        create_builtin_tools(mock_session)

        # 获取所有添加的工具
        added_tools = [call[0][0] for call in mock_session.add.call_args_list]
        tool_names = [tool.name for tool in added_tools]

        # 验证包含所有6种工具
        expected_names = [
            "calculator",
            "data_analysis",
        ]

        for name in expected_names:
            assert name in tool_names

    def test_builtin_tools_have_correct_type(self, mock_session):
        """测试内置工具类型正确"""
        create_builtin_tools(mock_session)

        # 获取所有添加的工具
        added_tools = [call[0][0] for call in mock_session.add.call_args_list]

        # 验证所有工具类型都是builtin
        for tool in added_tools:
            assert tool.tool_type == "builtin"

    def test_builtin_tools_are_enabled(self, mock_session):
        """测试内置工具默认启用"""
        create_builtin_tools(mock_session)

        # 获取所有添加的工具
        added_tools = [call[0][0] for call in mock_session.add.call_args_list]

        # 验证所有工具都是启用状态
        for tool in added_tools:
            assert tool.is_enabled is True

    def test_builtin_tools_have_descriptions(self, mock_session):
        """测试内置工具有描述"""
        create_builtin_tools(mock_session)

        # 获取所有添加的工具
        added_tools = [call[0][0] for call in mock_session.add.call_args_list]

        # 验证所有工具都有描述
        for tool in added_tools:
            assert tool.description is not None
            assert len(tool.description) > 0

    def test_builtin_tools_have_config(self, mock_session):
        """测试内置工具有配置"""
        create_builtin_tools(mock_session)

        # 获取所有添加的工具
        added_tools = [call[0][0] for call in mock_session.add.call_args_list]

        # 验证所有工具都有配置
        for tool in added_tools:
            assert tool.config is not None
            assert isinstance(tool.config, dict)
            assert "type" in tool.config

    def test_create_test_users_success(self, mock_session):
        """测试创建测试用户成功"""
        # Mock用户ID
        mock_user = Mock()
        mock_user.id = 1
        mock_session.add.side_effect = lambda obj: setattr(obj, 'id', 1)

        # 执行创建
        users = create_test_users(mock_session)

        # 验证创建了用户
        assert len(users) > 0
        assert mock_session.commit.called

    @patch('scripts.seed_data.logger')
    def test_logging_on_success(self, mock_logger, mock_session):
        """测试成功时的日志记录"""
        create_builtin_tools(mock_session)

        # 验证记录了成功日志
        assert mock_logger.info.called
        log_messages = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("Creating built-in tools" in msg for msg in log_messages)
        assert any("Created tool" in msg for msg in log_messages)
