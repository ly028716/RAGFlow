---
name: langchain-tool
description: 创建新的 LangChain Agent 工具。当需要为 AI Agent 添加新能力、创建自定义工具、扩展 Agent 功能时使用。
---

# LangChain 工具开发 Skill

为 RAGAgentLangChain 项目创建符合规范的 LangChain Agent 工具。

## 项目结构

```
backend/app/langchain_integration/
├── tools/
│   ├── __init__.py           # 工具导出
│   ├── calculator_tool.py    # 计算器工具
│   ├── search_tool.py        # 搜索工具
│   └── weather_tool.py       # 天气工具
├── chains.py                 # 对话链
├── rag_chain.py              # RAG检索链
└── agent_executor.py         # Agent执行器
```

## 创建新工具的步骤

### 1. 创建工具文件

文件位置：`backend/app/langchain_integration/tools/{tool_name}_tool.py`

```python
"""{工具名称}工具 - {简短描述}"""
from typing import Optional, Type
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun
from pydantic import BaseModel, Field


class {ToolName}Input(BaseModel):
    """{工具名称}工具的输入模型"""
    query: str = Field(description="输入参数描述")
    # 添加更多参数...


class {ToolName}Tool(BaseTool):
    """
    {工具名称}工具 - {详细描述}

    功能说明:
    - 功能1
    - 功能2
    - 功能3
    """

    name: str = "{tool_name}"
    description: str = (
        "{工具的详细描述，告诉 Agent 何时使用这个工具}。"
        "输入应该是{输入格式说明}。"
        "返回{返回内容说明}。"
    )
    args_schema: Type[BaseModel] = {ToolName}Input

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """
        执行工具

        Args:
            query: 输入查询
            run_manager: 回调管理器

        Returns:
            工具执行结果的字符串表示
        """
        try:
            # 实现工具逻辑
            result = self._execute(query)
            return result
        except Exception as e:
            return f"错误: {str(e)}"

    async def _arun(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """异步执行工具"""
        return self._run(query, run_manager)

    def _execute(self, query: str) -> str:
        """
        实际执行逻辑

        Args:
            query: 输入查询

        Returns:
            执行结果
        """
        # 实现具体逻辑
        pass
```

### 2. 注册工具

在 `backend/app/langchain_integration/tools/__init__.py` 中注册：

```python
from .{tool_name}_tool import {ToolName}Tool

__all__ = [
    # ... 现有工具
    '{ToolName}Tool',
]
```

## 完整示例：天气查询工具

```python
"""天气查询工具 - 获取指定城市的天气信息"""
from typing import Optional, Type
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun
from pydantic import BaseModel, Field
import httpx


class WeatherInput(BaseModel):
    """天气查询工具的输入模型"""
    city: str = Field(description="要查询天气的城市名称，例如: '北京', '上海', 'Beijing'")


class WeatherTool(BaseTool):
    """
    天气查询工具 - 获取指定城市的实时天气信息

    功能说明:
    - 查询指定城市的当前天气
    - 返回温度、湿度、天气状况等信息
    - 支持中英文城市名
    """

    name: str = "weather"
    description: str = (
        "用于查询指定城市天气信息的工具。"
        "输入应该是一个城市名称，例如: '北京', '上海', 'New York'。"
        "返回该城市的当前天气状况，包括温度、湿度、天气描述等。"
    )
    args_schema: Type[BaseModel] = WeatherInput

    # 配置参数
    api_key: str = ""
    api_url: str = "https://api.weather.example.com/v1/current"
    timeout: int = 10

    def _run(
        self,
        city: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """
        执行天气查询

        Args:
            city: 城市名称
            run_manager: 回调管理器

        Returns:
            天气信息的字符串表示
        """
        try:
            city = city.strip()
            if not city:
                return "错误: 城市名称不能为空"

            weather_data = self._fetch_weather(city)
            return self._format_weather(weather_data)

        except httpx.TimeoutException:
            return f"错误: 查询超时，请稍后重试"
        except httpx.HTTPError as e:
            return f"错误: 网络请求失败 - {str(e)}"
        except Exception as e:
            return f"查询失败: {str(e)}"

    async def _arun(
        self,
        city: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """异步执行天气查询"""
        try:
            city = city.strip()
            if not city:
                return "错误: 城市名称不能为空"

            weather_data = await self._fetch_weather_async(city)
            return self._format_weather(weather_data)

        except Exception as e:
            return f"查询失败: {str(e)}"

    def _fetch_weather(self, city: str) -> dict:
        """
        同步获取天气数据

        Args:
            city: 城市名称

        Returns:
            天气数据字典
        """
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                self.api_url,
                params={"city": city, "key": self.api_key}
            )
            response.raise_for_status()
            return response.json()

    async def _fetch_weather_async(self, city: str) -> dict:
        """
        异步获取天气数据

        Args:
            city: 城市名称

        Returns:
            天气数据字典
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                self.api_url,
                params={"city": city, "key": self.api_key}
            )
            response.raise_for_status()
            return response.json()

    def _format_weather(self, data: dict) -> str:
        """
        格式化天气数据

        Args:
            data: 天气API返回的数据

        Returns:
            格式化的天气信息字符串
        """
        return (
            f"城市: {data.get('city', '未知')}\n"
            f"天气: {data.get('weather', '未知')}\n"
            f"温度: {data.get('temperature', '未知')}°C\n"
            f"湿度: {data.get('humidity', '未知')}%\n"
            f"风速: {data.get('wind_speed', '未知')} km/h"
        )
```

## 工具设计最佳实践

### 1. 输入模型设计

```python
class ToolInput(BaseModel):
    """使用 Pydantic 定义清晰的输入模型"""

    # 必需参数
    query: str = Field(..., description="查询内容")

    # 可选参数带默认值
    limit: int = Field(default=10, ge=1, le=100, description="返回结果数量")

    # 枚举类型
    format: str = Field(default="json", description="输出格式: json/text/xml")
```

### 2. 描述编写

```python
description: str = (
    # 1. 说明工具用途
    "用于{具体用途}的工具。"
    # 2. 说明输入格式
    "输入应该是{输入格式}，例如: {示例}。"
    # 3. 说明返回内容
    "返回{返回内容描述}。"
    # 4. 说明使用场景（可选）
    "当用户询问{场景}时使用此工具。"
)
```

### 3. 错误处理

```python
def _run(self, query: str, ...) -> str:
    try:
        # 输入验证
        if not query or not query.strip():
            return "错误: 输入不能为空"

        # 执行逻辑
        result = self._execute(query)

        # 结果验证
        if not result:
            return "未找到相关结果"

        return result

    except ValueError as e:
        return f"参数错误: {str(e)}"
    except ConnectionError as e:
        return f"网络错误: {str(e)}"
    except Exception as e:
        return f"执行失败: {str(e)}"
```

### 4. 安全考虑

```python
# 1. 输入清理
query = query.strip()
query = re.sub(r'[<>"\']', '', query)  # 移除危险字符

# 2. 长度限制
if len(query) > 1000:
    return "错误: 输入过长"

# 3. 白名单验证
ALLOWED_OPERATIONS = ['add', 'subtract', 'multiply', 'divide']
if operation not in ALLOWED_OPERATIONS:
    return f"错误: 不支持的操作 {operation}"

# 4. 避免代码执行
# 永远不要使用 eval() 或 exec()
# 使用 AST 解析代替字符串执行
```

## 在 Agent 中使用工具

```python
from langchain.agents import AgentExecutor, create_react_agent
from app.langchain_integration.tools import (
    CalculatorTool,
    SearchTool,
    WeatherTool,
    {ToolName}Tool,
)

# 创建工具列表
tools = [
    CalculatorTool(),
    SearchTool(),
    WeatherTool(api_key="your-api-key"),
    {ToolName}Tool(),
]

# 创建 Agent
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# 执行
result = agent_executor.invoke({"input": "用户问题"})
```

## 测试工具

```python
import pytest
from app.langchain_integration.tools.{tool_name}_tool import {ToolName}Tool


class Test{ToolName}Tool:
    """测试{工具名称}工具"""

    def setup_method(self):
        """测试前准备"""
        self.tool = {ToolName}Tool()

    def test_basic_query(self):
        """测试基本查询"""
        result = self.tool._run("测试输入")
        assert "预期内容" in result

    def test_empty_input(self):
        """测试空输入"""
        result = self.tool._run("")
        assert "错误" in result

    def test_invalid_input(self):
        """测试无效输入"""
        result = self.tool._run("无效输入")
        assert "错误" in result or "未找到" in result

    @pytest.mark.asyncio
    async def test_async_query(self):
        """测试异步查询"""
        result = await self.tool._arun("测试输入")
        assert "预期内容" in result
```
