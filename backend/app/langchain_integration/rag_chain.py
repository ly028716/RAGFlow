"""
RAG查询链模块

实现检索增强生成（RAG）查询功能，提供：
- 向量检索
- 上下文构建
- LLM生成答案
- 多知识库联合检索

需求引用:
    - 需求4.1: 用户提交RAG查询请求且指定知识库ID，将查询文本向量化并在向量数据库中检索相似度最高的前5个文档片段
    - 需求4.2: 向量检索完成，将检索到的文档片段作为上下文传递给通义千问模型生成答案
    - 需求4.3: 在响应中返回生成的答案、相关文档片段、来源文档名称和相似度评分
    - 需求4.4: 用户指定多个知识库ID，在所有指定知识库中进行联合检索
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document

from app.config import settings
from app.core.llm import TongyiLLM, get_llm, get_streaming_llm, invoke_llm
from app.core.vector_store import VectorStoreManager, get_vector_store_manager
from app.services.rag.retrieval_service import RetrievalService, distance_to_similarity

logger = logging.getLogger(__name__)

def _distance_to_similarity(distance: Any) -> float:
    # Kept as a compatibility helper for callers importing this private name.
    return distance_to_similarity(distance)


# RAG提示模板
RAG_PROMPT_TEMPLATE = """你是一个智能问答助手。请根据以下提供的参考资料回答用户的问题。

参考资料:
{context}

用户问题: {question}

请根据参考资料回答问题。如果参考资料中没有相关信息，请明确告知用户。回答时请：
1. 准确引用参考资料中的信息
2. 保持回答简洁明了
3. 如果需要，可以综合多个参考资料的内容

回答:"""


RAG_CONVERSATION_TEMPLATE = """你是一个智能问答助手。请根据以下提供的参考资料和对话历史回答用户的问题。

参考资料:
{context}

对话历史:
{chat_history}

用户问题: {question}

请根据参考资料和对话历史回答问题。如果参考资料中没有相关信息，请明确告知用户。

回答:"""


@dataclass
class DocumentChunk:
    """文档片段数据类"""

    content: str
    document_name: str
    similarity_score: float
    document_id: Optional[int] = None
    chunk_index: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "document_name": self.document_name,
            "similarity_score": self.similarity_score,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
        }


@dataclass
class RAGResponse:
    """RAG响应数据类"""

    answer: str
    sources: List[DocumentChunk]
    tokens_used: int
    retrieval_time_ms: float = 0.0
    generation_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "sources": [s.to_dict() for s in self.sources],
            "tokens_used": self.tokens_used,
            "retrieval_time_ms": self.retrieval_time_ms,
            "generation_time_ms": self.generation_time_ms,
        }


class RAGManager:
    """
    RAG管理器类

    实现检索增强生成功能，支持：
    - 单知识库查询
    - 多知识库联合查询
    - 带对话历史的查询
    - 流式响应

    使用方式:
        manager = RAGManager()

        # 单知识库查询
        response = await manager.query(
            knowledge_base_ids=[1],
            question="什么是Python？",
            top_k=5
        )

        # 多知识库联合查询
        response = await manager.query(
            knowledge_base_ids=[1, 2, 3],
            question="什么是Python？",
            top_k=5
        )

        # 流式查询
        async for chunk in manager.stream_query(
            knowledge_base_ids=[1],
            question="什么是Python？"
        ):
            print(chunk)
    """

    def __init__(
        self,
        vector_store_manager: Optional[VectorStoreManager] = None,
        llm: Optional[TongyiLLM] = None,
    ):
        """
        初始化RAG管理器

        Args:
            vector_store_manager: 向量存储管理器，默认使用全局实例
            llm: LLM实例，默认使用全局实例
        """
        self.vector_store_manager = vector_store_manager or get_vector_store_manager()
        self.retrieval_service = RetrievalService(self.vector_store_manager)
        self._llm = llm

        # 对话记忆存储
        self._memories: Dict[str, ConversationBufferMemory] = {}

        # 提示模板
        self._prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template=RAG_PROMPT_TEMPLATE,
        )

        self._conversation_template = PromptTemplate(
            input_variables=["context", "chat_history", "question"],
            template=RAG_CONVERSATION_TEMPLATE,
        )

    def _get_llm(self, streaming: bool = False) -> TongyiLLM:
        """
        获取LLM实例

        Args:
            streaming: 是否流式输出

        Returns:
            TongyiLLM: LLM实例
        """
        if self._llm is not None:
            return self._llm

        if streaming:
            return get_streaming_llm()
        return get_llm()

    async def _stream_with_retry(
        self,
        llm: TongyiLLM,
        prompt: str,
        max_attempts: int = 3,
    ) -> AsyncGenerator[Any, None]:
        """Retry a transient stream failure only before the first token.

        Retrying after a token has reached the client would replay content and
        make the answer timeline inconsistent, so partial streams fail
        terminally instead.
        """
        for attempt in range(1, max_attempts + 1):
            emitted_token = False
            try:
                async for chunk in llm.llm.astream(prompt):
                    emitted_token = True
                    yield chunk
                return
            except (ConnectionError, TimeoutError) as exc:
                if emitted_token or attempt == max_attempts:
                    raise
                logger.warning(
                    "DashScope 流式生成失败，将重试: attempt=%s/%s, error=%s",
                    attempt,
                    max_attempts,
                    exc,
                )

    async def query(
        self,
        knowledge_base_ids: List[int],
        question: str,
        top_k: Optional[int] = None,
        conversation_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> RAGResponse:
        """
        执行RAG查询

        Args:
            knowledge_base_ids: 知识库ID列表
            question: 用户问题
            top_k: 检索文档数量，默认从配置读取
            conversation_id: 对话ID（用于维护对话历史）
            chat_history: 对话历史列表

        Returns:
            RAGResponse: RAG响应对象

        需求引用:
            - 需求4.1: 将查询文本向量化并在向量数据库中检索相似度最高的前5个文档片段
            - 需求4.2: 将检索到的文档片段作为上下文传递给通义千问模型生成答案
            - 需求4.3: 返回生成的答案、相关文档片段、来源文档名称和相似度评分
            - 需求4.4: 在所有指定知识库中进行联合检索
        """
        if top_k is None:
            top_k = settings.rag.rag_top_k

        logger.info(
            f"执行RAG查询: kb_ids={knowledge_base_ids}, "
            f"question长度={len(question)}, top_k={top_k}"
        )

        # 步骤1: 向量检索
        retrieval_started = time.perf_counter()
        retrieved_docs = await self._retrieve_documents(
            knowledge_base_ids=knowledge_base_ids,
            question=question,
            top_k=top_k,
        )
        retrieval_time_ms = round((time.perf_counter() - retrieval_started) * 1000, 2)

        logger.debug(f"检索到 {len(retrieved_docs)} 个文档片段")

        # 步骤2: 构建上下文
        context = self._build_context(retrieved_docs)

        # 步骤3: 构建提示
        if chat_history or conversation_id:
            history_str = self._format_chat_history(chat_history, conversation_id)
            prompt = self._conversation_template.format(
                context=context,
                chat_history=history_str,
                question=question,
            )
        else:
            prompt = self._prompt_template.format(
                context=context,
                question=question,
            )

        # Do not send an empty/low-relevance context to the model.
        generation_started = time.perf_counter()
        if not retrieved_docs:
            answer = "当前知识库中未找到足够相关的信息，无法基于知识库回答该问题。"
        else:
            llm = self._get_llm(streaming=False)
            answer = await invoke_llm(prompt, llm=llm)
        generation_time_ms = round((time.perf_counter() - generation_started) * 1000, 2)

        # 步骤5: 估算token数量
        tokens_used = self._estimate_tokens(prompt + answer)

        # 步骤6: 更新对话历史
        if conversation_id:
            self._update_memory(conversation_id, question, answer)

        logger.info(
            f"RAG查询完成: answer长度={len(answer)}, "
            f"sources={len(retrieved_docs)}, tokens≈{tokens_used}"
        )

        return RAGResponse(
            answer=answer,
            sources=retrieved_docs,
            tokens_used=tokens_used,
            retrieval_time_ms=retrieval_time_ms,
            generation_time_ms=generation_time_ms,
        )

    async def stream_query(
        self,
        knowledge_base_ids: List[int],
        question: str,
        top_k: Optional[int] = None,
        conversation_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式执行RAG查询

        Args:
            knowledge_base_ids: 知识库ID列表
            question: 用户问题
            top_k: 检索文档数量
            conversation_id: 对话ID
            chat_history: 对话历史列表

        Yields:
            Dict[str, Any]: 流式响应数据
                - type: "sources" | "token" | "done" | "error"
                - sources: 文档片段列表（type为sources时）
                - content: 文本片段（type为token时）
                - tokens_used: 总token数（type为done时）
        """
        if top_k is None:
            top_k = settings.rag.rag_top_k

        logger.info(
            f"执行流式RAG查询: kb_ids={knowledge_base_ids}, "
            f"question长度={len(question)}, top_k={top_k}"
        )

        try:
            # 步骤1: 向量检索
            retrieval_started = time.perf_counter()
            retrieved_docs = await self._retrieve_documents(
                knowledge_base_ids=knowledge_base_ids,
                question=question,
                top_k=top_k,
            )
            retrieval_time_ms = round((time.perf_counter() - retrieval_started) * 1000, 2)

            # 先返回检索到的文档片段（已去重）
            yield {
                "type": "sources",
                "sources": [doc.to_dict() for doc in retrieved_docs],
                "retrieval_time_ms": retrieval_time_ms,
            }

            if not retrieved_docs:
                refusal = "当前知识库中未找到足够相关的信息，无法基于知识库回答该问题。"
                yield {"type": "token", "content": refusal}
                yield {
                    "type": "done", "content": refusal, "tokens_used": self._estimate_tokens(refusal),
                    "retrieval_time_ms": retrieval_time_ms, "generation_time_ms": 0.0,
                }
                return

            # 步骤2: 构建上下文和提示
            context = self._build_context(retrieved_docs)

            if chat_history or conversation_id:
                history_str = self._format_chat_history(chat_history, conversation_id)
                prompt = self._conversation_template.format(
                    context=context,
                    chat_history=history_str,
                    question=question,
                )
            else:
                prompt = self._prompt_template.format(
                    context=context,
                    question=question,
                )

            # 步骤3: 流式调用LLM
            generation_started = time.perf_counter()
            llm = self._get_llm(streaming=True)
            full_answer = ""

            try:
                async for chunk in self._stream_with_retry(llm, prompt):
                    if hasattr(chunk, "content"):
                        content = chunk.content
                    else:
                        content = str(chunk)

                    full_answer += content
                    yield {
                        "type": "token",
                        "content": content,
                    }
            except Exception as stream_err:
                logger.error(f"LLM流式生成中断: {str(stream_err)}", exc_info=True)

                # 先发送错误事件给前端
                yield {
                    "type": "error",
                    "error": f"LLM生成失败: {str(stream_err)}",
                }

                # 如果已经生成了部分内容，继续后续流程
                if not full_answer:
                    return  # 直接返回，不再继续

            # 步骤4: 估算token数量
            # Note: _estimate_tokens 内部实现很简单，不会抛出 "Additional kwargs key output_tokens already exists" 错误
            # 这个错误通常来自 Pydantic 模型验证或 LangChain 内部。
            # 如果是 full_answer 拼接导致的问题，前面的循环应该会报错。
            # 这里最可疑的是 self._estimate_tokens 的调用或 yield 语句。
            # 让我们尝试捕获这个特定步骤的异常
            try:
                tokens_used = self._estimate_tokens(prompt + full_answer)
            except Exception as token_err:
                logger.warning(f"Token估算失败: {str(token_err)}")
                tokens_used = len(full_answer) # 降级策略

            # 步骤5: 更新对话历史
            if conversation_id:
                try:
                    self._update_memory(conversation_id, question, full_answer)
                except Exception as mem_err:
                    logger.warning(f"更新对话历史失败: {str(mem_err)}")

            yield {
                "type": "done",
                "content": full_answer,
                "tokens_used": tokens_used,
                "retrieval_time_ms": retrieval_time_ms,
                "generation_time_ms": round((time.perf_counter() - generation_started) * 1000, 2),
            }

            logger.info(
                f"流式RAG查询完成: answer长度={len(full_answer)}, " f"tokens≈{tokens_used}"
            )

        except Exception as e:
            logger.error(f"流式RAG查询失败: {str(e)}")
            yield {
                "type": "error",
                "error": str(e),
            }

    async def _retrieve_documents(
        self,
        knowledge_base_ids: List[int],
        question: str,
        top_k: int,
    ) -> List[DocumentChunk]:
        """
        从向量数据库检索相关文档

        Args:
            knowledge_base_ids: 知识库ID列表
            question: 查询问题
            top_k: 返回文档数量

        Returns:
            List[DocumentChunk]: 文档片段列表
        """
        results = await self.retrieval_service.retrieve(
            knowledge_base_ids=knowledge_base_ids, query=question, top_k=top_k
        )

        # 转换为DocumentChunk对象
        chunks = []
        for doc, score in results:
            similarity = score

            chunk = DocumentChunk(
                content=doc.page_content,
                document_name=doc.metadata.get("source", "Unknown"),
                similarity_score=round(similarity, 6),
                document_id=doc.metadata.get("document_id"),
                chunk_index=doc.metadata.get("chunk_index"),
            )
            chunks.append(chunk)

        return chunks

    def _build_context(self, documents: List[DocumentChunk]) -> str:
        """
        构建上下文文本

        Args:
            documents: 文档片段列表

        Returns:
            str: 格式化的上下文文本
        """
        if not documents:
            return "没有找到相关的参考资料。"

        context_parts = []
        for i, doc in enumerate(documents, 1):
            context_parts.append(
                f"[{i}] 来源: {doc.document_name}\n" f"内容: {doc.content}\n"
            )

        return "\n".join(context_parts)

    def _format_chat_history(
        self,
        chat_history: Optional[List[Dict[str, str]]],
        conversation_id: Optional[str],
    ) -> str:
        """
        格式化对话历史

        Args:
            chat_history: 对话历史列表
            conversation_id: 对话ID

        Returns:
            str: 格式化的对话历史文本
        """
        history_parts = []

        # 从传入的历史中获取
        if chat_history:
            for msg in chat_history[-10:]:  # 只保留最近10条
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "USER":
                    history_parts.append(f"用户: {content}")
                elif role == "ASSISTANT":
                    history_parts.append(f"助手: {content}")

        # 从记忆中获取
        elif conversation_id and conversation_id in self._memories:
            memory = self._memories[conversation_id]
            history = memory.load_memory_variables({})
            if "history" in history:
                for msg in history["history"][-10:]:
                    if hasattr(msg, "content"):
                        if msg.__class__.__name__ == "HumanMessage":
                            history_parts.append(f"用户: {msg.content}")
                        elif msg.__class__.__name__ == "AIMessage":
                            history_parts.append(f"助手: {msg.content}")

        return "\n".join(history_parts) if history_parts else "无"

    def _update_memory(
        self,
        conversation_id: str,
        question: str,
        answer: str,
    ) -> None:
        """
        更新对话记忆

        Args:
            conversation_id: 对话ID
            question: 用户问题
            answer: AI回答
        """
        if conversation_id not in self._memories:
            self._memories[conversation_id] = ConversationBufferMemory(
                return_messages=True,
            )

        memory = self._memories[conversation_id]
        memory.chat_memory.add_user_message(question)
        memory.chat_memory.add_ai_message(answer)

    def clear_memory(self, conversation_id: str) -> None:
        """
        清除对话记忆

        Args:
            conversation_id: 对话ID
        """
        if conversation_id in self._memories:
            self._memories[conversation_id].clear()
            del self._memories[conversation_id]

    def _estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量

        Args:
            text: 文本内容

        Returns:
            int: 估算的token数量
        """
        # 统计中文字符数
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        # 统计其他字符数
        other_chars = len(text) - chinese_chars

        # 估算token数
        estimated = (chinese_chars / 2) + (other_chars / 4)
        return int(estimated)


# 全局RAG管理器实例
_rag_manager: Optional[RAGManager] = None


def get_rag_manager() -> RAGManager:
    """
    获取全局RAG管理器实例

    Returns:
        RAGManager: RAG管理器实例
    """
    global _rag_manager

    if _rag_manager is None:
        _rag_manager = RAGManager()

    return _rag_manager


def clear_rag_manager() -> None:
    """
    清除全局RAG管理器实例

    用于测试或重置状态
    """
    global _rag_manager
    _rag_manager = None


# 导出
__all__ = [
    "RAGManager",
    "RAGResponse",
    "DocumentChunk",
    "get_rag_manager",
    "clear_rag_manager",
    "RAG_PROMPT_TEMPLATE",
    "RAG_CONVERSATION_TEMPLATE",
]
