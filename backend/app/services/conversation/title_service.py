"""
Conversation 标题服务模块

实现对话标题生成功能。
"""

import logging

logger = logging.getLogger(__name__)


class TitleService:
    """
    对话标题服务类

    提供使用LLM自动生成对话标题功能。

    使用方式:
        service = TitleService()
        title = await service.generate("用户消息内容", max_length=20)
        title = service.generate_sync("用户消息内容", max_length=20)
    """

    async def generate(self, first_message: str, max_length: int = 20) -> str:
        """
        使用LLM根据第一条消息生成对话标题

        Args:
            first_message: 第一条用户消息内容
            max_length: 标题最大长度，默认20个字符

        Returns:
            str: 生成的对话标题
        """
        from app.core.llm import invoke_llm

        prompt = f"""请根据以下用户消息，生成一个简短的对话标题。

要求：
1. 标题长度不超过{max_length}个字符
2. 标题要简洁明了，概括消息的主题
3. 只返回标题文本，不要包含任何其他内容
4. 不要使用引号包裹标题

用户消息：
{first_message[:500]}

标题："""

        try:
            title = await invoke_llm(
                prompt=prompt, temperature=0.3, max_tokens=50  # 使用较低温度以获得更稳定的输出
            )

            # 清理标题
            title = title.strip()

            # 移除可能的引号
            if title.startswith('"') and title.endswith('"'):
                title = title[1:-1]
            if title.startswith("'") and title.endswith("'"):
                title = title[1:-1]
            if title.startswith("《") and title.endswith("》"):
                title = title[1:-1]

            # 截断到最大长度
            if len(title) > max_length:
                title = title[: max_length - 1] + "…"

            # 如果标题为空，返回默认值
            if not title:
                title = "新对话"

            logger.info(f"生成对话标题: {title}")
            return title

        except Exception as e:
            logger.error(f"生成对话标题失败: {str(e)}")
            # 失败时返回默认标题
            return "新对话"

    def generate_sync(self, first_message: str, max_length: int = 20) -> str:
        """
        同步版本：使用LLM根据第一条消息生成对话标题

        Args:
            first_message: 第一条用户消息内容
            max_length: 标题最大长度，默认20个字符

        Returns:
            str: 生成的对话标题
        """
        from app.core.llm import invoke_llm_sync

        prompt = f"""请根据以下用户消息，生成一个简短的对话标题。

要求：
1. 标题长度不超过{max_length}个字符
2. 标题要简洁明了，概括消息的主题
3. 只返回标题文本，不要包含任何其他内容
4. 不要使用引号包裹标题

用户消息：
{first_message[:500]}

标题："""

        try:
            title = invoke_llm_sync(
                prompt=prompt, temperature=0.3, max_tokens=50  # 使用较低温度以获得更稳定的输出
            )

            # 清理标题
            title = title.strip()

            # 移除可能的引号
            if title.startswith('"') and title.endswith('"'):
                title = title[1:-1]
            if title.startswith("'") and title.endswith("'"):
                title = title[1:-1]
            if title.startswith("《") and title.endswith("》"):
                title = title[1:-1]

            # 截断到最大长度
            if len(title) > max_length:
                title = title[: max_length - 1] + "…"

            # 如果标题为空，返回默认值
            if not title:
                title = "新对话"

            logger.info(f"生成对话标题: {title}")
            return title

        except Exception as e:
            logger.error(f"生成对话标题失败: {str(e)}")
            # 失败时返回默认标题
            return "新对话"


__all__ = [
    "TitleService",
]
