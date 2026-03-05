"""
增强型对话服务

结合 OpenClaw Agent 和本地知识库RAG，提供混合推理能力。
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.openclaw_client import (
    OpenClawAPIError,
    OpenClawCircuitBreakerError,
    OpenClawTimeoutError,
    get_openclaw_client,
)
from app.langchain_integration.rag_chain import get_rag_manager

logger = logging.getLogger(__name__)


class EnhancedConversationService:
    """
    增强型对话服务

    提供混合推理能力，结合：
    1. OpenClaw Agent 的推理和工具调用能力
    2. 本地知识库的RAG检索能力
    3. 智能降级机制（OpenClaw不可用时自动降级到RAG模式）
    """

    def __init__(self):
        self.openclaw_client = get_openclaw_client()
        self.rag_manager = get_rag_manager()

    async def chat(
        self,
        question: str,
        knowledge_base_ids: Optional[List[int]] = None,
        conversation_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        增强型对话（非流式）

        Args:
            question: 用户问题
            knowledge_base_ids: 知识库ID列表
            conversation_id: 对话ID
            chat_history: 对话历史

        Returns:
            Dict包含answer和tokens_used
        """
        # 1. 检查 OpenClaw 是否可用
        openclaw_available = await self._check_openclaw_availability()

        if not openclaw_available:
            logger.info("OpenClaw 不可用，降级到 RAG 模式")
            return await self._fallback_to_rag(
                question=question,
                knowledge_base_ids=knowledge_base_ids,
                conversation_id=conversation_id,
                chat_history=chat_history,
            )

        # 2. 如果指定了知识库，先进行 RAG 检索
        rag_context = None
        if knowledge_base_ids:
            try:
                rag_response = await self.rag_manager.query(
                    knowledge_base_ids=knowledge_base_ids,
                    question=question,
                    conversation_id=conversation_id,
                    chat_history=chat_history,
                )
                rag_context = {
                    "answer": rag_response.answer,
                    "sources": rag_response.sources,
                    "tokens_used": rag_response.tokens_used,
                }
                logger.info(f"RAG 检索完成，找到 {len(rag_response.sources)} 个相关文档")
            except Exception as e:
                logger.error(f"RAG 检索失败: {str(e)}")
                # RAG失败不影响继续使用OpenClaw

        # 3. 构建 OpenClaw 请求上下文
        context = self._build_openclaw_context(
            question=question,
            rag_context=rag_context,
            chat_history=chat_history,
        )

        # 4. 调用 OpenClaw Agent
        try:
            openclaw_response = await self.openclaw_client.send_message(
                message=question,
                context=context,
                stream=False,
            )

            # 5. 整合响应
            return {
                "answer": openclaw_response.get("message", ""),
                "tokens_used": openclaw_response.get("tokens_used", 0),
                "sources": rag_context.get("sources", []) if rag_context else [],
                "mode": "enhanced",
                "openclaw_used": True,
            }

        except (OpenClawAPIError, OpenClawTimeoutError, OpenClawCircuitBreakerError) as e:
            logger.warning(f"OpenClaw 调用失败，降级到 RAG 模式: {str(e)}")
            return await self._fallback_to_rag(
                question=question,
                knowledge_base_ids=knowledge_base_ids,
                conversation_id=conversation_id,
                chat_history=chat_history,
            )

    async def stream_chat(
        self,
        question: str,
        knowledge_base_ids: Optional[List[int]] = None,
        conversation_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        增强型对话（流式）

        Args:
            question: 用户问题
            knowledge_base_ids: 知识库ID列表
            conversation_id: 对话ID
            chat_history: 对话历史

        Yields:
            事件字典，包含type和相关数据
        """
        # 1. 检查 OpenClaw 是否可用
        openclaw_available = await self._check_openclaw_availability()

        if not openclaw_available:
            logger.info("OpenClaw 不可用，降级到 RAG 流式模式")
            async for event in self._fallback_to_rag_stream(
                question=question,
                knowledge_base_ids=knowledge_base_ids,
                conversation_id=conversation_id,
                chat_history=chat_history,
            ):
                yield event
            return

        # 2. 如果指定了知识库，先进行 RAG 检索
        rag_context = None
        if knowledge_base_ids:
            try:
                rag_response = await self.rag_manager.query(
                    knowledge_base_ids=knowledge_base_ids,
                    question=question,
                    conversation_id=conversation_id,
                    chat_history=chat_history,
                )
                rag_context = {
                    "answer": rag_response.answer,
                    "sources": rag_response.sources,
                    "tokens_used": rag_response.tokens_used,
                }

                # 发送引用源事件
                if rag_response.sources:
                    yield {
                        "type": "sources",
                        "sources": rag_response.sources,
                    }

                logger.info(f"RAG 检索完成，找到 {len(rag_response.sources)} 个相关文档")
            except Exception as e:
                logger.error(f"RAG 检索失败: {str(e)}")

        # 3. 构建 OpenClaw 请求上下文
        context = self._build_openclaw_context(
            question=question,
            rag_context=rag_context,
            chat_history=chat_history,
        )

        # 4. 调用 OpenClaw Agent（流式）
        try:
            openclaw_response = await self.openclaw_client.send_message(
                message=question,
                context=context,
                stream=True,
            )

            # 5. 流式返回 OpenClaw 响应
            # 注意：这里假设 OpenClaw 返回的是完整响应，不是流式的
            # 如果 OpenClaw 支持流式，需要相应调整
            content = openclaw_response.get("message", "")
            tokens_used = openclaw_response.get("tokens_used", 0)

            # 模拟流式输出（按字符分块）
            chunk_size = 10
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                yield {
                    "type": "token",
                    "content": chunk,
                }

            # 发送完成事件
            yield {
                "type": "done",
                "tokens_used": tokens_used,
                "mode": "enhanced",
                "openclaw_used": True,
            }

        except (OpenClawAPIError, OpenClawTimeoutError, OpenClawCircuitBreakerError) as e:
            logger.warning(f"OpenClaw 调用失败，降级到 RAG 流式模式: {str(e)}")
            async for event in self._fallback_to_rag_stream(
                question=question,
                knowledge_base_ids=knowledge_base_ids,
                conversation_id=conversation_id,
                chat_history=chat_history,
            ):
                yield event

    async def _check_openclaw_availability(self) -> bool:
        """
        检查 OpenClaw 是否可用

        Returns:
            bool: True 表示可用，False 表示不可用
        """
        try:
            health_info = await self.openclaw_client.health_check()
            return health_info.get("status") == "healthy"
        except Exception as e:
            logger.debug(f"OpenClaw 健康检查失败: {str(e)}")
            return False

    def _build_openclaw_context(
        self,
        question: str,
        rag_context: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        构建 OpenClaw 请求上下文

        Args:
            question: 用户问题
            rag_context: RAG检索结果
            chat_history: 对话历史

        Returns:
            上下文字典
        """
        context = {
            "question": question,
            "mode": "enhanced",
        }

        # 添加 RAG 上下文
        if rag_context:
            context["rag_context"] = {
                "answer": rag_context.get("answer"),
                "sources": [
                    {
                        "content": source.get("content"),
                        "document_name": source.get("document_name"),
                        "similarity_score": source.get("similarity_score"),
                    }
                    for source in rag_context.get("sources", [])
                ],
            }

        # 添加对话历史
        if chat_history:
            context["chat_history"] = chat_history[-5:]  # 只保留最近5轮对话

        return context

    async def _fallback_to_rag(
        self,
        question: str,
        knowledge_base_ids: Optional[List[int]] = None,
        conversation_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        降级到 RAG 模式（非流式）

        Args:
            question: 用户问题
            knowledge_base_ids: 知识库ID列表
            conversation_id: 对话ID
            chat_history: 对话历史

        Returns:
            Dict包含answer和tokens_used
        """
        if not knowledge_base_ids:
            # 如果没有指定知识库，返回提示信息
            return {
                "answer": "抱歉，OpenClaw 服务暂时不可用，且未指定知识库。请指定知识库以使用 RAG 模式，或稍后重试。",
                "tokens_used": 0,
                "sources": [],
                "mode": "degraded",
                "openclaw_used": False,
            }

        rag_response = await self.rag_manager.query(
            knowledge_base_ids=knowledge_base_ids,
            question=question,
            conversation_id=conversation_id,
            chat_history=chat_history,
        )

        return {
            "answer": rag_response.answer,
            "tokens_used": rag_response.tokens_used,
            "sources": rag_response.sources,
            "mode": "degraded",
            "openclaw_used": False,
        }

    async def _fallback_to_rag_stream(
        self,
        question: str,
        knowledge_base_ids: Optional[List[int]] = None,
        conversation_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        降级到 RAG 流式模式

        Args:
            question: 用户问题
            knowledge_base_ids: 知识库ID列表
            conversation_id: 对话ID
            chat_history: 对话历史

        Yields:
            事件字典
        """
        if not knowledge_base_ids:
            # 如果没有指定知识库，返回提示信息
            error_message = "抱歉，OpenClaw 服务暂时不可用，且未指定知识库。请指定知识库以使用 RAG 模式，或稍后重试。"
            yield {
                "type": "token",
                "content": error_message,
            }
            yield {
                "type": "done",
                "tokens_used": 0,
                "mode": "degraded",
                "openclaw_used": False,
            }
            return

        # 使用 RAG 流式查询
        async for event in self.rag_manager.stream_query(
            knowledge_base_ids=knowledge_base_ids,
            question=question,
            conversation_id=conversation_id,
            chat_history=chat_history,
        ):
            # 添加降级标记
            if event.get("type") == "done":
                event["mode"] = "degraded"
                event["openclaw_used"] = False
            yield event


# 单例模式
_enhanced_conversation_service: Optional[EnhancedConversationService] = None


def get_enhanced_conversation_service() -> EnhancedConversationService:
    """
    获取增强型对话服务单例

    Returns:
        EnhancedConversationService: 增强型对话服务实例
    """
    global _enhanced_conversation_service
    if _enhanced_conversation_service is None:
        _enhanced_conversation_service = EnhancedConversationService()
    return _enhanced_conversation_service
