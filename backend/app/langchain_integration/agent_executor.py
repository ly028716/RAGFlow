"""
Agent执行器模块

实现基于LangChain的Agent执行器，使用ReAct模式进行任务推理和执行。
支持工具调用、步骤记录和异步执行。
"""

import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from langchain.agents import AgentExecutor, create_react_agent
from langchain.callbacks.base import BaseCallbackHandler
from langchain.prompts import PromptTemplate
from langchain.schema import AgentAction, AgentFinish
from langchain.tools import BaseTool
from langchain_community.llms import Tongyi

from app.config import settings
from app.langchain_integration.tools import (
    CalculatorTool,
    DataAnalysisTool,
    KnowledgeBaseSearchTool,
)

logger = logging.getLogger(__name__)


class StepRecordingCallback(BaseCallbackHandler):
    """
    步骤记录回调处理器

    记录Agent执行过程中的每个步骤，包括思考、行动和观察结果。
    """

    def __init__(self):
        self.steps: List[Dict[str, Any]] = []
        self.current_step: Dict[str, Any] = {}

    def on_agent_action(self, action: AgentAction, **kwargs) -> None:
        """当Agent执行动作时调用"""
        self.current_step = {
            "step_number": len(self.steps) + 1,
            "thought": action.log.split("Action:")[0].replace("Thought:", "").strip()
            if "Thought:" in action.log
            else "",
            "action": action.tool,
            "action_input": action.tool_input,
            "observation": "",
            "timestamp": datetime.utcnow().isoformat(),
        }

    def on_tool_end(self, output: str, **kwargs) -> None:
        """当工具执行完成时调用"""
        if self.current_step:
            self.current_step["observation"] = output
            if self.current_step.get("action") == "knowledge_base_search":
                try:
                    payload = json.loads(output)
                    self.current_step["citations"] = payload.get("results", [])
                    self.current_step["citation_count"] = payload.get("count", 0)
                except (TypeError, json.JSONDecodeError):
                    self.current_step["citations"] = []
            self.steps.append(self.current_step.copy())
            self.current_step = {}

    def on_agent_finish(self, finish: AgentFinish, **kwargs) -> None:
        """当Agent完成任务时调用"""
        # 记录最终思考
        if finish.log:
            final_step = {
                "step_number": len(self.steps) + 1,
                "thought": finish.log,
                "action": "finish",
                "action_input": {},
                "observation": finish.return_values.get("output", ""),
                "timestamp": datetime.utcnow().isoformat(),
            }
            self.steps.append(final_step)

    def get_steps(self) -> List[Dict[str, Any]]:
        """获取所有记录的步骤"""
        return self.steps


class AgentManager:
    """
    Agent管理器

    负责创建和管理Agent实例，执行任务并记录执行步骤。
    使用ReAct模式进行推理和行动。
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化Agent管理器

        Args:
            api_key: DashScope API密钥，如果不提供则从配置中读取
        """
        self.api_key = api_key or settings.tongyi.dashscope_api_key

        # 初始化LLM
        self.llm = Tongyi(
            dashscope_api_key=self.api_key,
            model_name=settings.tongyi.tongyi_model_name,
            temperature=settings.tongyi.tongyi_temperature,
            max_tokens=settings.tongyi.tongyi_max_tokens,
        )

        # 加载内置工具
        self.builtin_tools = self._load_builtin_tools()

        logger.info(f"AgentManager初始化完成，加载了 {len(self.builtin_tools)} 个内置工具")

    def _load_builtin_tools(
        self, knowledge_base_ids: Optional[List[int]] = None
    ) -> List[BaseTool]:
        """
        加载内置工具

        Returns:
            内置工具列表
        """
        tools = [
            CalculatorTool(),
            DataAnalysisTool(),
            KnowledgeBaseSearchTool(
                allowed_knowledge_base_ids=knowledge_base_ids or []
            ),
        ]
        return tools

    def _create_react_prompt(self) -> PromptTemplate:
        """
        创建ReAct模式的提示词模板

        Returns:
            提示词模板
        """
        template = """你是一个智能助手，可以使用工具来完成任务。请按照以下格式进行推理和行动：

可用工具:
{tools}

工具名称: {tool_names}

使用以下格式:

Question: 你需要回答的问题或完成的任务
Thought: 你应该思考接下来要做什么
Action: 要采取的行动，必须是以下工具之一 [{tool_names}]
Action Input: 行动的输入参数
Observation: 行动的结果
... (这个 Thought/Action/Action Input/Observation 可以重复N次)
Thought: 我现在知道最终答案了
Final Answer: 对原始问题的最终答案

重要提示:
1. 每次只能使用一个工具
2. Action必须是可用工具列表中的一个
3. Action Input必须符合工具的输入要求
4. 如果遇到错误，请尝试其他方法或工具
5. 当你有足够信息回答问题时，给出Final Answer

开始!

Question: {input}
Thought: {agent_scratchpad}"""

        return PromptTemplate.from_template(template)

    def _select_tools(
        self,
        tool_ids: Optional[List[int]] = None,
        custom_tools: Optional[List[BaseTool]] = None,
        knowledge_base_ids: Optional[List[int]] = None,
    ) -> List[BaseTool]:
        """
        选择要使用的工具

        Args:
            tool_ids: 工具ID列表（用于从数据库加载的自定义工具）
            custom_tools: 自定义工具列表

        Returns:
            选择的工具列表
        """
        selected_tools = []

        # 添加内置工具
        selected_tools.extend(self.builtin_tools)

        # 添加自定义工具
        if custom_tools:
            selected_tools.extend(custom_tools)

        # TODO: 根据tool_ids从数据库加载自定义工具
        # if tool_ids:
        #     db_tools = await self._load_tools_from_db(tool_ids)
        #     selected_tools.extend(db_tools)

        return selected_tools

    @staticmethod
    def _agent_input(task: str, knowledge_base_ids: Optional[List[int]]) -> str:
        """Give the ReAct model the authorized KB scope needed by the search tool."""
        if not knowledge_base_ids:
            return task
        ids = ", ".join(str(value) for value in knowledge_base_ids)
        return (
            f"允许检索的本地知识库 ID: [{ids}]。调用 knowledge_base_search 时，"
            f"knowledge_base_ids 必须使用上述 ID。\n用户任务: {task}"
        )

    async def execute_task(
        self,
        task: str,
        tool_ids: Optional[List[int]] = None,
        custom_tools: Optional[List[BaseTool]] = None,
        knowledge_base_ids: Optional[List[int]] = None,
        max_iterations: int = 10,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """
        执行Agent任务

        Args:
            task: 要执行的任务描述
            tool_ids: 要使用的工具ID列表
            custom_tools: 自定义工具列表
            knowledge_base_ids: 知识库检索工具允许访问的知识库ID列表
            max_iterations: 最大迭代次数
            verbose: 是否输出详细日志

        Returns:
            执行结果字典，包含:
                - result: 最终结果
                - steps: 执行步骤列表
                - status: 执行状态 (completed/failed)
                - error: 错误信息（如果失败）
        """
        try:
            logger.info(f"开始执行Agent任务: {task}")

            # 选择工具
            self.builtin_tools = self._load_builtin_tools(knowledge_base_ids or [])
            tools = self._select_tools(tool_ids, custom_tools)

            if not tools:
                return {
                    "result": None,
                    "steps": [],
                    "status": "failed",
                    "error": "没有可用的工具",
                }

            logger.info(f"使用 {len(tools)} 个工具: {[t.name for t in tools]}")

            # 创建提示词模板
            prompt = self._create_react_prompt()

            # 创建Agent
            agent = create_react_agent(llm=self.llm, tools=tools, prompt=prompt)

            # 创建步骤记录回调
            callback = StepRecordingCallback()

            # 创建Agent执行器
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=verbose,
                max_iterations=max_iterations,
                handle_parsing_errors=True,
                callbacks=[callback],
            )

            # 执行任务
            result = await agent_executor.ainvoke(
                {"input": self._agent_input(task, knowledge_base_ids)}
            )

            # 获取执行步骤
            steps = callback.get_steps()

            logger.info(f"Agent任务执行完成，共 {len(steps)} 个步骤")

            return {
                "result": result.get("output", ""),
                "steps": steps,
                "status": "completed",
                "error": None,
            }

        except Exception as e:
            logger.error(f"Agent任务执行失败: {str(e)}", exc_info=True)
            return {
                "result": None,
                "steps": callback.get_steps() if "callback" in locals() else [],
                "status": "failed",
                "error": str(e),
            }

    async def stream_execute_task(
        self,
        task: str,
        tool_ids: Optional[List[int]] = None,
        custom_tools: Optional[List[BaseTool]] = None,
        knowledge_base_ids: Optional[List[int]] = None,
        max_iterations: int = 10,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式执行Agent任务

        Args:
            task: 要执行的任务描述
            tool_ids: 要使用的工具ID列表
            custom_tools: 自定义工具列表
            max_iterations: 最大迭代次数

        Yields:
            执行过程中的事件字典:
                - type: 事件类型 (step/result/error)
                - data: 事件数据
        """
        try:
            logger.info(f"开始流式执行Agent任务: {task}")

            # 选择工具
            self.builtin_tools = self._load_builtin_tools(knowledge_base_ids or [])
            tools = self._select_tools(tool_ids, custom_tools)

            if not tools:
                yield {"type": "error", "data": {"message": "没有可用的工具"}}
                return

            # 创建提示词模板
            prompt = self._create_react_prompt()

            # 创建Agent
            agent = create_react_agent(llm=self.llm, tools=tools, prompt=prompt)

            # 创建步骤记录回调
            callback = StepRecordingCallback()

            # 创建Agent执行器
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                max_iterations=max_iterations,
                handle_parsing_errors=True,
                callbacks=[callback],
            )

            last_emitted_step_index = 0
            async for _ in agent_executor.astream(
                {"input": self._agent_input(task, knowledge_base_ids)}
            ):
                while last_emitted_step_index < len(callback.steps):
                    step = callback.steps[last_emitted_step_index]
                    last_emitted_step_index += 1
                    yield {"type": "step", "data": step}

            while last_emitted_step_index < len(callback.steps):
                step = callback.steps[last_emitted_step_index]
                last_emitted_step_index += 1
                yield {"type": "step", "data": step}

            # 发送最终结果
            steps = callback.get_steps()
            final_result = ""
            if steps:
                for s in reversed(steps):
                    if s.get("action") == "finish":
                        final_result = s.get("observation", "")
                        break
                if not final_result:
                    final_result = steps[-1].get("observation", "")

            yield {
                "type": "result",
                "data": {"result": final_result, "steps": steps, "status": "completed"},
            }

        except Exception as e:
            logger.error(f"Agent流式任务执行失败: {str(e)}", exc_info=True)
            yield {
                "type": "error",
                "data": {
                    "message": str(e),
                    "steps": callback.get_steps() if "callback" in locals() else [],
                },
            }

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        获取所有可用工具的信息

        Returns:
            工具信息列表
        """
        tools_info = []
        for tool in self.builtin_tools:
            tools_info.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "type": "builtin",
                    "is_enabled": True,
                }
            )
        return tools_info
