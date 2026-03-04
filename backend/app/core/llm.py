"""
通义千问LLM配置模块

配置和管理通义千问大语言模型实例，提供LLM调用的重试机制。
支持流式和非流式输出模式。
"""

import logging
import re
from typing import Any, AsyncGenerator, Dict, Iterator, List, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_community.llms import Tongyi as OriginalTongyi

class PatchedTongyi(OriginalTongyi):
    """
    Patch Tongyi to avoid 'Additional kwargs key output_tokens already exists' error in streaming mode.
    """
    @property
    def _default_params(self) -> Dict[str, Any]:
        params = super()._default_params.copy()
        if self.streaming:
             if "max_tokens" in params:
                del params["max_tokens"]
             if "output_tokens" in params:
                del params["output_tokens"]
        return params
        
    def _invocation_params(self, stop: Optional[List[str]], **kwargs: Any) -> Dict[str, Any]:
        params = super()._invocation_params(stop=stop, **kwargs)
        if self.streaming:
             if "max_tokens" in params:
                del params["max_tokens"]
             if "output_tokens" in params:
                del params["output_tokens"]
        return params

    def _stream(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[Any]:
        if self.streaming:
            if "max_tokens" in kwargs:
                del kwargs["max_tokens"]
            if "output_tokens" in kwargs:
                del kwargs["output_tokens"]
                
        # 手动实现流式调用
        params = self._invocation_params(stop=stop, **kwargs)
        
        # 再次确保 params 中没有冲突的 key
        if self.streaming:
             if "max_tokens" in params:
                del params["max_tokens"]
             if "output_tokens" in params:
                del params["output_tokens"]
        
        # 直接调用 DashScope SDK
        import dashscope
        from langchain_core.outputs import GenerationChunk
        
        # 确保 api_key
        if not dashscope.api_key:
            if not self.dashscope_api_key:
                raise ValueError("DASHSCOPE_API_KEY 未配置，请在环境变量中设置")
            dashscope.api_key = self.dashscope_api_key
            
        # 彻底清理 params
        clean_params = params.copy()

        # 保留必要的参数，而不是全部删除
        minimal_params = {
            "result_format": "message",  # 强制使用 message 格式
            "incremental_output": True,  # 流式输出必需
        }

        # 从 clean_params 中提取安全的参数
        safe_params = ["temperature", "top_p", "seed"]
        for param in safe_params:
            if param in clean_params:
                minimal_params[param] = clean_params[param]

        logger.debug(f"[_stream] 调用 DashScope, params={minimal_params}, model={self.model_name}")
        
        responses = dashscope.Generation.call(
            model=self.model_name,
            prompt=prompt,
            api_key=self.dashscope_api_key,
            stream=True,
            **minimal_params, # 使用最小参数集
        )
        
        last_text = ""
        chunk_count = 0
        for response in responses:
            logger.debug(f"[_stream] 收到响应: status_code={response.status_code}")
            if response.status_code == 200:
                # 添加完整响应结构日志
                logger.debug(f"[_stream] 完整响应结构: {response}")
                logger.debug(f"[_stream] output类型={type(response.output)}, output={response.output}")

                # 尝试多种方式提取文本
                text_content = None

                # 方式1: output.text (旧格式) - 检查值不为None
                if hasattr(response.output, 'text') and response.output.text is not None:
                    text_content = response.output.text
                    logger.debug(f"[_stream] 从output.text获取: {text_content}")

                # 方式2: output.choices[0].message.content (message格式)
                if text_content is None and hasattr(response.output, 'choices') and len(response.output.choices) > 0:
                    choice = response.output.choices[0]
                    if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                        text_content = choice.message.content
                        logger.debug(f"[_stream] 从choices[0].message.content获取: {text_content}")

                # 方式3: 直接从 output 字典获取 (某些版本的格式)
                if text_content is None and isinstance(response.output, dict):
                    if 'text' in response.output and response.output['text'] is not None:
                        text_content = response.output['text']
                        logger.debug(f"[_stream] 从output['text']获取: {text_content}")
                    elif 'choices' in response.output and len(response.output['choices']) > 0:
                        text_content = response.output['choices'][0].get('message', {}).get('content')
                        logger.debug(f"[_stream] 从output['choices']获取: {text_content}")

                # 方式4: 尝试直接转换为字符串
                if text_content is None and response.output:
                    text_content = str(response.output)
                    logger.debug(f"[_stream] 从str(output)获取: {text_content}")

                if text_content is not None and text_content:
                    # DashScope API在流式模式下返回的是增量内容，不是累积内容
                    # 所以直接使用text_content作为delta
                    delta = str(text_content)  # 确保delta是字符串类型
                    last_text += delta  # 累积完整文本用于调试
                    chunk_count += 1
                    logger.debug(f"[_stream] 生成chunk #{chunk_count}, delta长度={len(delta)}")
                    yield GenerationChunk(text=delta)
                else:
                    logger.warning(f"[_stream] 无法从响应中提取文本内容, response.output结构: {dir(response.output)}")
            else:
                logger.error(f"[_stream] DashScope错误: status={response.status_code}, message={response.message}")

        logger.info(f"[_stream] 同步流式调用完成, 共生成 {chunk_count} 个chunks")

    async def _astream(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[Any, None]:
        """
        Async stream implementation that delegates to the synchronous _stream
        running in a thread pool to avoid blocking the event loop.
        """
        import asyncio

        logger.info(f"[_astream] 开始异步流式调用, prompt长度={len(prompt)}")

        # 创建一个包装函数来安全地获取下一个元素
        def safe_next(iterator, sentinel=object()):
            """安全地获取迭代器的下一个元素，避免StopIteration"""
            try:
                return next(iterator)
            except StopIteration:
                return sentinel

        # 在线程中创建迭代器
        logger.info("[_astream] 在线程中创建迭代器")
        iterator = await asyncio.to_thread(
            self._stream, prompt, stop, run_manager, **kwargs
        )

        # 使用哨兵值来检测迭代结束
        sentinel = object()
        chunk_count = 0

        while True:
            # 在线程中安全地获取下一个 chunk
            chunk = await asyncio.to_thread(safe_next, iterator, sentinel)

            if chunk is sentinel:
                # 迭代结束
                logger.info(f"[_astream] 流式调用完成, 共生成 {chunk_count} 个chunks")
                break

            chunk_count += 1
            logger.debug(f"[_astream] 生成chunk #{chunk_count}: {chunk}")
            yield chunk


from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM
from tenacity import (before_sleep_log, retry, retry_if_exception_type,
                      stop_after_attempt, wait_exponential)

from app.config import DEFAULT_DASHSCOPE_API_KEY, settings

logger = logging.getLogger(__name__)


# 定义可重试的异常类型
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    Exception,  # 捕获dashscope API的通用异常
)


class TongyiLLM:
    """
    通义千问LLM封装类

    提供统一的LLM调用接口，支持：
    - 流式和非流式输出
    - 自动重试机制（3次，指数退避）
    - 自定义模型参数

    使用方式:
        from app.core.llm import get_llm, get_streaming_llm

        # 获取非流式LLM实例
        llm = get_llm()
        response = await llm.ainvoke("你好")

        # 获取流式LLM实例
        streaming_llm = get_streaming_llm()
        async for chunk in streaming_llm.astream("你好"):
            print(chunk)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        streaming: bool = False,
    ):
        """
        初始化通义千问LLM实例

        Args:
            api_key: DashScope API密钥，默认从配置读取
            model_name: 模型名称，默认从配置读取
            temperature: 温度参数，控制输出随机性
            max_tokens: 最大输出token数
            streaming: 是否启用流式输出
        """
        self.api_key = api_key or settings.tongyi.dashscope_api_key
        self.model_name = model_name or settings.tongyi.tongyi_model_name
        self.temperature = (
            temperature
            if temperature is not None
            else settings.tongyi.tongyi_temperature
        )
        self.max_tokens = max_tokens or settings.tongyi.tongyi_max_tokens
        self.streaming = streaming

        self._llm: Optional[Any] = None

    @property
    def llm(self) -> Any:
        """
        获取或创建LLM实例（懒加载）

        Returns:
            Tongyi: 通义千问LLM实例
        """
        if self._llm is None:
            self._llm = self._create_llm()
        return self._llm

    def _create_llm(self) -> Any:
        """
        创建通义千问LLM实例

        Returns:
            Tongyi: 配置好的LLM实例
        """
        logger.info(
            f"创建通义千问LLM实例: model={self.model_name}, "
            f"temperature={self.temperature}, max_tokens={self.max_tokens}, "
            f"streaming={self.streaming}"
        )

        if _is_placeholder_dashscope_api_key(self.api_key) and (
            settings.debug or settings.environment.lower() == "development"
        ):
            # logger.warning(
            #     "检测到占位 DashScope API Key，已启用开发模式 Mock LLM（仅用于本地调试）。"
            # )
            # 暂时屏蔽 MockLLM，因为它的 astream 返回字符串而不是 Chunk 对象，会导致下游处理出错
            # 且我们现在的测试环境似乎能连上真实的 API（看前面的日志 "Answer: 根据参考资料..."）
            # 或者我们应该让 MockLLM 的行为更像真实 LLM
            # return DevMockTongyi(...)
            pass

        # 使用 PatchedTongyi 替代 Tongyi
        params = {
            "dashscope_api_key": self.api_key,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "streaming": self.streaming,
        }
        
        if self.max_tokens:
            params["max_tokens"] = self.max_tokens
            
        return PatchedTongyi(**params)

    def update_params(
        self,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        """
        更新LLM参数

        Args:
            temperature: 新的温度参数
            max_tokens: 新的最大token数
        """
        if temperature is not None:
            self.temperature = temperature
        if max_tokens is not None:
            self.max_tokens = max_tokens

        # 重新创建LLM实例以应用新参数
        self._llm = None
        logger.info(
            f"LLM参数已更新: temperature={self.temperature}, max_tokens={self.max_tokens}"
        )


# 创建重试装饰器
def create_retry_decorator(
    max_attempts: int = 3, min_wait: int = 2, max_wait: int = 10
):
    """
    创建LLM调用重试装饰器

    Args:
        max_attempts: 最大重试次数
        min_wait: 最小等待时间（秒）
        max_wait: 最大等待时间（秒）

    Returns:
        重试装饰器
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


# 默认重试装饰器（3次，指数退避：2秒、4秒、8秒）
llm_retry = create_retry_decorator(max_attempts=3, min_wait=2, max_wait=10)


@llm_retry
async def invoke_llm(
    prompt: str,
    llm: Optional[TongyiLLM] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    调用LLM生成响应（带重试机制）

    Args:
        prompt: 输入提示词
        llm: TongyiLLM实例，默认使用全局实例
        temperature: 温度参数（可选，覆盖默认值）
        max_tokens: 最大token数（可选，覆盖默认值）

    Returns:
        str: LLM生成的响应文本

    Raises:
        Exception: 重试3次后仍然失败时抛出异常
    """
    if llm is None:
        llm = get_llm(temperature=temperature, max_tokens=max_tokens)

    logger.debug(f"调用LLM: prompt长度={len(prompt)}")

    try:
        response = await llm.llm.ainvoke(prompt)
        logger.debug(f"LLM响应成功: 响应长度={len(response)}")
        return response
    except Exception as e:
        logger.error(f"LLM调用失败: {str(e)}")
        raise


@llm_retry
def invoke_llm_sync(
    prompt: str,
    llm: Optional[TongyiLLM] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    同步调用LLM生成响应（带重试机制）

    Args:
        prompt: 输入提示词
        llm: TongyiLLM实例，默认使用全局实例
        temperature: 温度参数（可选，覆盖默认值）
        max_tokens: 最大token数（可选，覆盖默认值）

    Returns:
        str: LLM生成的响应文本

    Raises:
        Exception: 重试3次后仍然失败时抛出异常
    """
    if llm is None:
        llm = get_llm(temperature=temperature, max_tokens=max_tokens)

    logger.debug(f"同步调用LLM: prompt长度={len(prompt)}")

    try:
        response = llm.llm.invoke(prompt)
        logger.debug(f"LLM响应成功: 响应长度={len(response)}")
        return response
    except Exception as e:
        logger.error(f"LLM调用失败: {str(e)}")
        raise


async def stream_llm(
    prompt: str,
    llm: Optional[TongyiLLM] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> AsyncGenerator[str, None]:
    """
    流式调用LLM生成响应

    Args:
        prompt: 输入提示词
        llm: TongyiLLM实例，默认使用流式LLM实例
        temperature: 温度参数（可选，覆盖默认值）
        max_tokens: 最大token数（可选，覆盖默认值）

    Yields:
        str: LLM生成的响应文本片段

    Raises:
        Exception: 调用失败时抛出异常
    """
    if llm is None:
        llm = get_streaming_llm(temperature=temperature, max_tokens=max_tokens)

    logger.debug(f"流式调用LLM: prompt长度={len(prompt)}")

    try:
        async for chunk in llm.llm.astream(prompt):
            yield chunk
        logger.debug("流式LLM响应完成")
    except Exception as e:
        logger.error(f"流式LLM调用失败: {str(e)}")
        raise


# 全局LLM实例缓存
_llm_instances: Dict[str, TongyiLLM] = {}


def get_llm(
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    model_name: Optional[str] = None,
) -> TongyiLLM:
    """
    获取非流式LLM实例

    Args:
        temperature: 温度参数
        max_tokens: 最大token数
        model_name: 模型名称

    Returns:
        TongyiLLM: 配置好的LLM实例
    """
    # 使用参数生成缓存键
    cache_key = f"llm_{model_name or 'default'}_{temperature}_{max_tokens}_False"

    if cache_key not in _llm_instances:
        _llm_instances[cache_key] = TongyiLLM(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=False,
        )

    return _llm_instances[cache_key]


def get_streaming_llm(
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    model_name: Optional[str] = None,
) -> TongyiLLM:
    """
    获取流式LLM实例

    Args:
        temperature: 温度参数
        max_tokens: 最大token数
        model_name: 模型名称

    Returns:
        TongyiLLM: 配置好的流式LLM实例
    """
    # 使用参数生成缓存键
    cache_key = f"llm_{model_name or 'default'}_{temperature}_{max_tokens}_True"

    if cache_key not in _llm_instances:
        _llm_instances[cache_key] = TongyiLLM(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=True,
        )

    return _llm_instances[cache_key]


def clear_llm_cache() -> None:
    """
    清除LLM实例缓存

    用于在配置更新后重新创建LLM实例
    """
    global _llm_instances
    _llm_instances.clear()
    logger.info("LLM实例缓存已清除")


def get_llm_config() -> Dict[str, Any]:
    """
    获取当前LLM配置信息

    Returns:
        dict: LLM配置字典
    """
    return {
        "model_name": settings.tongyi.tongyi_model_name,
        "temperature": settings.tongyi.tongyi_temperature,
        "max_tokens": settings.tongyi.tongyi_max_tokens,
        "embedding_model": settings.tongyi.embedding_model,
    }


# 导出
__all__ = [
    "TongyiLLM",
    "get_llm",
    "get_streaming_llm",
    "invoke_llm",
    "invoke_llm_sync",
    "stream_llm",
    "clear_llm_cache",
    "get_llm_config",
    "llm_retry",
    "create_retry_decorator",
]


def _is_placeholder_dashscope_api_key(api_key: Optional[str]) -> bool:
    if not api_key:
        return True
    key = api_key.strip()
    if not key:
        return True
    if key == DEFAULT_DASHSCOPE_API_KEY:
        return True
    if key == "DUMMY_DASHSCOPE_API_KEY":
        return True
    if key == "sk-INSERT_YOUR_KEY_HERE":
        return True
    if "YOUR_DASHSCOPE_API_KEY" in key or "INSERT_YOUR_KEY" in key:
        return True
    if re.fullmatch(r"your-.*api-key-.*", key, flags=re.IGNORECASE):
        return True
    return False


class DevMockTongyi:
    def __init__(
        self,
        model_name: str,
        temperature: float,
        max_tokens: int,
        streaming: bool,
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.streaming = streaming

    def _extract_user_question(self, prompt: str) -> str:
        if not prompt:
            return ""

        m = re.findall(r"用户问题:\s*(.+)", prompt)
        if m:
            return m[-1].strip()

        m = re.findall(r"用户:\s*(.+)", prompt)
        if m:
            return m[-1].strip()

        return prompt[-200:].strip()

    def _generate_text(self, prompt: str) -> str:
        question = self._extract_user_question(prompt)
        prefix = "（开发模式模拟回复：未配置 DashScope API Key）"
        if question:
            return f"{prefix}\n你刚才说：{question}"
        return f"{prefix}\n已收到你的消息。"

    async def ainvoke(self, prompt: str, **kwargs: Any) -> str:
        return self._generate_text(prompt)

    def invoke(self, prompt: str, **kwargs: Any) -> str:
        return self._generate_text(prompt)

    async def astream(self, prompt: str, **kwargs: Any) -> AsyncGenerator[Any, None]:
        text = self._generate_text(prompt)
        step = 12
        for i in range(0, len(text), step):
            # 模拟 LangChain Chunk 对象
            class MockChunk:
                def __init__(self, content):
                    self.content = content
                def __str__(self):
                    return self.content
            
            yield MockChunk(text[i : i + step])
