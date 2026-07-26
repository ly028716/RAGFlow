"""Backward-compatible facade for the local knowledge-base RAG service.

The former implementation depended on an external agent gateway.  Keeping
this small facade avoids breaking integrations that still import the legacy
factory while ensuring every call uses the local RAG pipeline only.
"""

from typing import Any, AsyncGenerator, Dict, List, Optional

from app.langchain_integration.rag_chain import get_rag_manager


class EnhancedConversationService:
    """Compatibility wrapper delegating to :class:`RAGManager`."""

    def __init__(self) -> None:
        self.rag_manager = get_rag_manager()

    async def chat(
        self,
        question: str,
        knowledge_base_ids: Optional[List[int]] = None,
        conversation_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        if not knowledge_base_ids:
            return {
                "answer": "请先选择一个知识库，以便基于本地资料回答问题。",
                "sources": [],
                "tokens_used": 0,
                "mode": "rag",
            }
        response = await self.rag_manager.query(
            knowledge_base_ids=knowledge_base_ids,
            question=question,
            conversation_id=conversation_id,
            chat_history=chat_history,
        )
        return {**response.to_dict(), "mode": "rag"}

    async def stream_chat(
        self,
        question: str,
        knowledge_base_ids: Optional[List[int]] = None,
        conversation_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not knowledge_base_ids:
            message = "请先选择一个知识库，以便基于本地资料回答问题。"
            yield {"type": "token", "content": message}
            yield {"type": "done", "content": message, "tokens_used": 0, "mode": "rag"}
            return
        async for event in self.rag_manager.stream_query(
            knowledge_base_ids=knowledge_base_ids,
            question=question,
            conversation_id=conversation_id,
            chat_history=chat_history,
        ):
            yield event


_rag_conversation_service: Optional[EnhancedConversationService] = None


def get_enhanced_conversation_service() -> EnhancedConversationService:
    """Return the legacy facade; new code should call ``get_rag_manager``."""
    global _rag_conversation_service
    if _rag_conversation_service is None:
        _rag_conversation_service = EnhancedConversationService()
    return _rag_conversation_service


__all__ = ["EnhancedConversationService", "get_enhanced_conversation_service"]
