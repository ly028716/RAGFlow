"""
Conversation 导出服务模块

实现对话导出功能。
"""

import json
import logging
from typing import List

from app.models.conversation import Conversation
from app.models.message import Message, MessageRole

logger = logging.getLogger(__name__)


class ExportService:
    """
    对话导出服务类

    提供对话导出为Markdown或JSON格式功能。

    使用方式:
        service = ExportService()
        markdown = service.to_markdown(conversation, messages)
        json_str = service.to_json(conversation, messages)
    """

    def export(
        self,
        conversation: Conversation,
        messages: List[Message],
        format: str = "markdown"
    ) -> str:
        """
        导出对话内容

        Args:
            conversation: 对话对象
            messages: 消息列表
            format: 导出格式，支持 "markdown" 或 "json"

        Returns:
            str: 导出的内容字符串

        Raises:
            ValueError: 不支持的导出格式
        """
        format = format.lower()
        if format not in ("markdown", "json", "md"):
            raise ValueError(f"不支持的导出格式: {format}，支持的格式: markdown, json")

        if format in ("markdown", "md"):
            return self.to_markdown(conversation, messages)
        else:
            return self.to_json(conversation, messages)

    def to_markdown(
        self, conversation: Conversation, messages: List[Message]
    ) -> str:
        """
        将对话导出为Markdown格式

        Args:
            conversation: 对话对象
            messages: 消息列表

        Returns:
            str: Markdown格式的对话内容
        """
        lines = []

        # 标题
        lines.append(f"# {conversation.title}")
        lines.append("")

        # 元信息
        lines.append(
            f"**创建时间:** {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        lines.append(
            f"**更新时间:** {conversation.updated_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        lines.append(f"**消息数量:** {len(messages)}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 消息内容
        for msg in messages:
            role_display = {
                MessageRole.USER: "👤 用户",
                MessageRole.ASSISTANT: "🤖 AI助手",
                MessageRole.SYSTEM: "⚙️ 系统",
            }.get(msg.role, str(msg.role.value))

            lines.append(f"### {role_display}")
            lines.append(f"*{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}*")
            lines.append("")
            lines.append(msg.content)
            lines.append("")

            if msg.tokens > 0:
                lines.append(f"*Token消耗: {msg.tokens}*")
                lines.append("")

        return "\n".join(lines)

    def to_json(
        self, conversation: Conversation, messages: List[Message]
    ) -> str:
        """
        将对话导出为JSON格式

        Args:
            conversation: 对话对象
            messages: 消息列表

        Returns:
            str: JSON格式的对话内容
        """
        from datetime import datetime

        data = {
            "conversation": {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
            },
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role.value,
                    "content": msg.content,
                    "tokens": msg.tokens,
                    "created_at": msg.created_at.isoformat(),
                }
                for msg in messages
            ],
            "statistics": {
                "message_count": len(messages),
                "total_tokens": sum(msg.tokens for msg in messages),
                "user_messages": sum(
                    1 for msg in messages if msg.role == MessageRole.USER
                ),
                "assistant_messages": sum(
                    1 for msg in messages if msg.role == MessageRole.ASSISTANT
                ),
            },
            "exported_at": datetime.utcnow().isoformat(),
        }

        return json.dumps(data, ensure_ascii=False, indent=2)


__all__ = [
    "ExportService",
]
