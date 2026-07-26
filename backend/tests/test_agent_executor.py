"""
Agent执行器集成测试
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock

from app.langchain_integration.agent_executor import AgentManager
from app.langchain_integration.tools import (
    CalculatorTool,
    DataAnalysisTool,
)


@pytest.fixture
def agent_manager():
    """创建AgentManager实例"""
    with patch('app.langchain_integration.agent_executor.Tongyi'):
        manager = AgentManager()
        return manager


class TestAgentManager:
    """Agent管理器测试类"""

    def test_initialization(self, agent_manager):
        """测试初始化"""
        assert agent_manager is not None
        assert agent_manager.llm is not None
        assert len(agent_manager.builtin_tools) == 3

    def test_load_builtin_tools(self, agent_manager):
        """测试加载内置工具"""
        tools = agent_manager.builtin_tools

        # 验证工具数量
        assert len(tools) == 3

        # 验证工具类型
        tool_names = [tool.name for tool in tools]
        expected_names = [
            "calculator",
            "data_analysis",
            "knowledge_base_search",
        ]

        for name in expected_names:
            assert name in tool_names

    def test_get_available_tools(self, agent_manager):
        """测试获取可用工具信息"""
        tools_info = agent_manager.get_available_tools()

        assert len(tools_info) == 3
        assert all("name" in tool for tool in tools_info)
        assert all("description" in tool for tool in tools_info)
        assert all("type" in tool for tool in tools_info)
        assert all(tool["type"] == "builtin" for tool in tools_info)

    def test_select_tools_default(self, agent_manager):
        """测试默认选择所有内置工具"""
        selected = agent_manager._select_tools()

        assert len(selected) == 3

    def test_select_tools_with_custom(self, agent_manager):
        """测试选择工具包含自定义工具"""
        custom_tool = Mock()
        custom_tool.name = "custom_tool"

        selected = agent_manager._select_tools(custom_tools=[custom_tool])

        assert len(selected) == 4
        assert custom_tool in selected

    @pytest.mark.asyncio
    async def test_execute_task_no_tools(self, agent_manager):
        """测试没有工具时执行任务"""
        # Mock空工具列表
        agent_manager.builtin_tools = []

        result = await agent_manager.execute_task("test task")

        assert result["status"] == "failed"
        assert "没有可用的工具" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_task_with_mock_llm(self, agent_manager):
        """测试使用Mock LLM执行任务"""
        # Mock LLM和Agent执行器
        with patch('app.langchain_integration.agent_executor.create_react_agent'):
            with patch('app.langchain_integration.agent_executor.AgentExecutor') as mock_executor_class:
                # Mock执行结果
                mock_executor = AsyncMock()
                mock_executor.ainvoke.return_value = {"output": "任务完成"}
                mock_executor_class.return_value = mock_executor

                result = await agent_manager.execute_task("计算 2+2")

                assert result["status"] == "completed"
                assert result["result"] == "任务完成"

    @pytest.mark.asyncio
    async def test_execute_task_scopes_knowledge_base_search_to_authorized_ids(
        self, agent_manager
    ):
        """知识库范围应传给 Agent 使用的检索工具。"""
        with patch('app.langchain_integration.agent_executor.create_react_agent'):
            with patch('app.langchain_integration.agent_executor.AgentExecutor') as mock_executor_class:
                mock_executor = AsyncMock()
                mock_executor.ainvoke.return_value = {"output": "任务完成"}
                mock_executor_class.return_value = mock_executor

                result = await agent_manager.execute_task(
                    "查询知识库", knowledge_base_ids=[1]
                )

        search_tool = next(
            tool for tool in agent_manager.builtin_tools if tool.name == "knowledge_base_search"
        )
        assert result["status"] == "completed"
        assert search_tool.allowed_knowledge_base_ids == [1]

    @pytest.mark.asyncio
    async def test_execute_task_keeps_existing_positional_options_compatible(
        self, agent_manager
    ):
        """知识库范围参数不应改变原有 max_iterations 和 verbose 的位置。"""
        with patch('app.langchain_integration.agent_executor.create_react_agent'):
            with patch('app.langchain_integration.agent_executor.AgentExecutor') as mock_executor_class:
                mock_executor = AsyncMock()
                mock_executor.ainvoke.return_value = {"output": "任务完成"}
                mock_executor_class.return_value = mock_executor

                result = await agent_manager.execute_task(
                    "查询知识库", None, None, 5, False, knowledge_base_ids=[1]
                )

        search_tool = next(
            tool for tool in agent_manager.builtin_tools if tool.name == "knowledge_base_search"
        )
        assert result["status"] == "completed"
        assert search_tool.allowed_knowledge_base_ids == [1]

    @pytest.mark.asyncio
    async def test_execute_task_failure(self, agent_manager):
        """测试任务执行失败"""
        with patch('app.langchain_integration.agent_executor.create_react_agent'):
            with patch('app.langchain_integration.agent_executor.AgentExecutor') as mock_executor_class:
                # Mock执行失败
                mock_executor = AsyncMock()
                mock_executor.ainvoke.side_effect = Exception("执行错误")
                mock_executor_class.return_value = mock_executor

                result = await agent_manager.execute_task("test task")

                assert result["status"] == "failed"
                assert "执行错误" in result["error"]

    def test_create_react_prompt(self, agent_manager):
        """测试创建ReAct提示词"""
        prompt = agent_manager._create_react_prompt()

        assert prompt is not None
        assert "Thought" in prompt.template
        assert "Action" in prompt.template
        assert "Observation" in prompt.template

    @pytest.mark.asyncio
    async def test_stream_execute_task(self, agent_manager):
        """测试流式执行任务"""
        with patch('app.langchain_integration.agent_executor.create_react_agent'):
            with patch('app.langchain_integration.agent_executor.AgentExecutor') as mock_executor_class:
                # Mock流式执行
                mock_executor = Mock()

                async def mock_astream(input_dict):
                    yield {"type": "step", "data": {"step_number": 1}}
                    yield {"type": "result", "data": {"result": "完成"}}

                mock_executor.astream = mock_astream
                mock_executor_class.return_value = mock_executor

                results = []
                async for event in agent_manager.stream_execute_task("test task"):
                    results.append(event)

                assert len(results) > 0
                assert any(event["type"] == "result" for event in results)
