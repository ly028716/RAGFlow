"""Deterministic, constrained local knowledge-base RAG Agent workflow."""

import json
import logging
import time
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from langchain.tools import BaseTool

from app.config import settings
from app.core.llm import get_llm, get_streaming_llm
from app.langchain_integration.tools import (
    CitationValidatorTool,
    ContextSelectorTool,
    KnowledgeBaseSearchTool,
    QueryRewriterTool,
)
from app.services.rag.citation_service import CitationService

logger = logging.getLogger(__name__)


class AgentManager:
    """Run a fixed four-stage RAG workflow with an inspectable JSON trace."""

    _CONTEXT_MAX_CHARS = 6000

    def __init__(
        self,
        api_key: Optional[str] = None,
        llm: Optional[Any] = None,
        streaming_llm: Optional[Any] = None,
    ) -> None:
        """Create the manager with the project's unified LLM factories.

        ``api_key`` remains accepted for backwards compatibility. Provider
        credentials are intentionally resolved by the centralized LLM factory,
        rather than creating a second direct Tongyi client here.
        """
        self.api_key = api_key
        self.llm = llm or get_llm()
        self.streaming_llm = streaming_llm or get_streaming_llm()
        self.builtin_tools = self._load_builtin_tools()

    def _load_builtin_tools(
        self, knowledge_base_ids: Optional[List[int]] = None
    ) -> List[BaseTool]:
        """Create the only four tools available to the RAG Agent."""
        return [
            QueryRewriterTool(),
            KnowledgeBaseSearchTool(
                allowed_knowledge_base_ids=list(knowledge_base_ids or [])
            ),
            ContextSelectorTool(),
            CitationValidatorTool(),
        ]

    def _select_tools(self) -> List[BaseTool]:
        """Return the fixed tool set; custom tools cannot enter the workflow."""
        return list(self.builtin_tools)

    @staticmethod
    def _tool_by_name(tools: List[BaseTool], name: str) -> BaseTool:
        for tool in tools:
            if tool.name == name:
                return tool
        raise ValueError(f"Required constrained RAG tool is unavailable: {name}")

    @staticmethod
    async def _invoke_json_tool(tool: BaseTool, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool and require a JSON-object observation for the trace."""
        output = await tool.ainvoke(arguments)
        if isinstance(output, dict):
            return output
        try:
            payload = json.loads(output)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Tool {tool.name} returned non-JSON output") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"Tool {tool.name} returned a non-object JSON value")
        return payload

    @staticmethod
    def _step(
        number: int,
        phase: str,
        action: str,
        action_input: Dict[str, Any],
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build a persistence-safe workflow step from a tool JSON observation."""
        citations = data.get("raw_chunks") or data.get("filtered_chunks") or []
        return {
            "step_number": number,
            "phase": phase,
            "thought": f"Constrained RAG phase: {phase}",
            "action": action,
            "action_input": action_input,
            "observation": json.dumps(data, ensure_ascii=False),
            "citations": citations,
            "citation_count": len(citations),
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def _tokens_from_response(response: Any) -> int:
        """Extract token usage from common LangChain/DashScope response shapes."""
        usage = getattr(response, "usage_metadata", None)
        if not isinstance(usage, dict):
            metadata = getattr(response, "response_metadata", None)
            usage = metadata.get("token_usage", {}) if isinstance(metadata, dict) else {}
        if not isinstance(usage, dict):
            return 0
        for key in ("total_tokens", "total_token_count", "output_tokens"):
            try:
                return int(usage.get(key, 0) or 0)
            except (TypeError, ValueError):
                continue
        return 0

    @staticmethod
    def _chunk_text(chunk: Any) -> str:
        """Normalize a LangChain streamed chunk into visible answer text."""
        if isinstance(chunk, str):
            return chunk
        content = getattr(chunk, "content", None)
        return str(content if content is not None else chunk)

    @staticmethod
    def _answer_prompt(
        original_question: str, rewritten_query: str, final_context: str
    ) -> str:
        return (
            "Answer only from the local knowledge-base context below. "
            "For every factual statement, preserve the source tag exactly as "
            "[citation:<document_id>:<chunk_index>]. If the context is insufficient, "
            "say so instead of using outside knowledge.\n\n"
            f"Original question: {original_question}\n"
            f"Retrieval query: {rewritten_query}\n\n"
            f"Local context:\n{final_context}\n\nAnswer:"
        )

    @staticmethod
    def _bounded_context(
        chunks: List[Dict[str, Any]], max_chars: int
    ) -> tuple[List[Dict[str, Any]], str]:
        """Keep only complete rendered source entries that fit the final budget."""
        selected: List[Dict[str, Any]] = []
        entries: List[str] = []
        used_chars = 0
        for chunk in chunks:
            citation_id = CitationService.citation_id(chunk)
            content = str(chunk.get("content", ""))
            if not citation_id or not content:
                continue
            entry = f"[citation:{citation_id}] {content}"
            separator_size = 2 if entries else 0
            if used_chars + separator_size + len(entry) > max_chars:
                continue
            selected.append(dict(chunk))
            entries.append(entry)
            used_chars += separator_size + len(entry)
        return selected, "\n\n".join(entries)

    def _initialize_workflow(
        self, task: str, knowledge_base_ids: Optional[List[int]]
    ) -> Dict[str, Any]:
        """Build state shared by synchronous and genuinely streaming execution."""
        scope = list(knowledge_base_ids or [])
        if not scope:
            raise ValueError("At least one authorized knowledge_base_id is required")
        self.builtin_tools = self._load_builtin_tools(scope)
        tools = self._select_tools()
        if not tools:
            raise ValueError("No constrained RAG tools are available")
        return {
            "started": time.perf_counter(),
            "task": task,
            "scope": scope,
            "tools": {
                name: self._tool_by_name(tools, name)
                for name in (
                    "query_rewriter",
                    "knowledge_base_search",
                    "context_selector",
                    "citation_validator",
                )
            },
            "steps": [],
        }

    async def _run_query_rewrite_stage(self, state: Dict[str, Any]) -> Dict[str, Any]:
        rewriter = state["tools"]["query_rewriter"]
        tool_data = await self._invoke_json_tool(rewriter, {"question": state["task"]})
        state["rewritten_query"] = str(tool_data.get("rewritten_query") or state["task"])
        step = self._step(
            1,
            "query_rewrite",
            rewriter.name,
            {"question": state["task"]},
            {
                "original_question": state["task"],
                "rewritten_query": state["rewritten_query"],
                "knowledge_base_scope": state["scope"],
            },
        )
        state["steps"].append(step)
        return step

    async def _run_retrieval_stage(self, state: Dict[str, Any]) -> Dict[str, Any]:
        search = state["tools"]["knowledge_base_search"]
        state["retrieval_parameters"] = {
            "top_k": settings.rag.rag_top_k,
            "similarity_threshold": settings.rag.rag_similarity_threshold,
        }
        tool_data = await self._invoke_json_tool(
            search,
            {
                "query": state["rewritten_query"],
                "knowledge_base_ids": state["scope"],
                "top_k": state["retrieval_parameters"]["top_k"],
            },
        )
        state["raw_chunks"] = list(tool_data.get("results") or [])
        state["retrieval_time_ms"] = float(tool_data.get("retrieval_time_ms", 0.0) or 0.0)
        step = self._step(
            2,
            "retrieval",
            search.name,
            {
                "query": state["rewritten_query"],
                "knowledge_base_ids": state["scope"],
                "top_k": state["retrieval_parameters"]["top_k"],
            },
            {
                "knowledge_base_scope": state["scope"],
                "retrieval_parameters": state["retrieval_parameters"],
                "raw_chunks": state["raw_chunks"],
                "retrieval_time_ms": state["retrieval_time_ms"],
            },
        )
        state["steps"].append(step)
        return step

    async def _run_context_selection_stage(self, state: Dict[str, Any]) -> Dict[str, Any]:
        selector = state["tools"]["context_selector"]
        tool_data = await self._invoke_json_tool(
            selector,
            {"chunks": state["raw_chunks"], "max_chars": self._CONTEXT_MAX_CHARS},
        )
        selected_chunks = list(tool_data.get("selected_chunks") or [])
        state["filtered_chunks"], state["final_context"] = self._bounded_context(
            selected_chunks, self._CONTEXT_MAX_CHARS
        )
        step = self._step(
            3,
            "context_selection",
            selector.name,
            {"chunk_count": len(state["raw_chunks"]), "max_chars": self._CONTEXT_MAX_CHARS},
            {
                "raw_chunk_count": len(state["raw_chunks"]),
                "filtered_chunks": state["filtered_chunks"],
                "final_context": state["final_context"],
                "context_char_count": len(state["final_context"]),
            },
        )
        state["steps"].append(step)
        return step

    async def _generate_answer(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a grounded, non-streaming answer with the unified LLM client."""
        if not state["final_context"]:
            return {
                "answer": "No relevant content was found in the selected local knowledge bases.",
                "tokens_used": 0,
                "generation_time_ms": 0.0,
            }
        started = time.perf_counter()
        response = await self.llm.llm.ainvoke(
            self._answer_prompt(
                state["task"], state["rewritten_query"], state["final_context"]
            )
        )
        answer = getattr(response, "content", response)
        return {
            "answer": str(answer),
            "tokens_used": self._tokens_from_response(response),
            "generation_time_ms": round((time.perf_counter() - started) * 1000, 2),
        }

    async def _stream_answer(self, state: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """Yield actual LLM deltas after retrieval/context stages have completed."""
        if not state["final_context"]:
            answer = "No relevant content was found in the selected local knowledge bases."
            state["answer_data"] = {
                "answer": answer,
                "tokens_used": 0,
                "generation_time_ms": 0.0,
            }
            yield answer
            return

        started = time.perf_counter()
        fragments: List[str] = []
        tokens_used = 0
        async for chunk in self.streaming_llm.llm.astream(
            self._answer_prompt(
                state["task"], state["rewritten_query"], state["final_context"]
            )
        ):
            delta = self._chunk_text(chunk)
            if not delta:
                continue
            fragments.append(delta)
            tokens_used = max(tokens_used, self._tokens_from_response(chunk))
            yield delta
        state["answer_data"] = {
            "answer": "".join(fragments),
            "tokens_used": tokens_used,
            "generation_time_ms": round((time.perf_counter() - started) * 1000, 2),
        }

    async def _finish_workflow(
        self, state: Dict[str, Any], answer_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate citations and form the final trace/result payload."""
        validator = state["tools"]["citation_validator"]
        answer = str(answer_data.get("answer", ""))
        citation_validation = await self._invoke_json_tool(
            validator, {"answer": answer, "chunks": state["filtered_chunks"]}
        )
        metrics = {
            "retrieval_time_ms": state["retrieval_time_ms"],
            "generation_time_ms": float(answer_data.get("generation_time_ms", 0.0) or 0.0),
            "total_time_ms": round((time.perf_counter() - state["started"]) * 1000, 2),
        }
        final_step = self._step(
            4,
            "answer_and_citation_validation",
            validator.name,
            {"answer": answer, "chunk_count": len(state["filtered_chunks"])},
            {
                "answer": answer,
                "citation_validation": citation_validation,
                "tokens_used": int(answer_data.get("tokens_used", 0) or 0),
                **metrics,
            },
        )
        state["steps"].append(final_step)
        return {
            "result": answer,
            "steps": state["steps"],
            "status": "completed",
            "error": None,
            "metrics": metrics,
        }

    async def _run_workflow(
        self, task: str, knowledge_base_ids: Optional[List[int]]
    ) -> Dict[str, Any]:
        """Execute all stages for the normal non-streaming API."""
        state = self._initialize_workflow(task, knowledge_base_ids)
        await self._run_query_rewrite_stage(state)
        await self._run_retrieval_stage(state)
        await self._run_context_selection_stage(state)
        answer_data = await self._generate_answer(state)
        return await self._finish_workflow(state, answer_data)

    @staticmethod
    def _failure(error: Exception | str) -> Dict[str, Any]:
        return {
            "result": None,
            "steps": [],
            "status": "failed",
            "error": str(error),
            "metrics": {},
        }

    async def execute_task(
        self,
        task: str,
        tool_ids: Optional[List[int]] = None,
        custom_tools: Optional[List[BaseTool]] = None,
        max_iterations: int = 10,
        verbose: bool = True,
        knowledge_base_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Execute the constrained workflow while preserving legacy call positions.

        ``tool_ids`` is deliberately ignored as a historical placeholder.
        Supplying nonempty custom tools is rejected so it cannot expand the
        local RAG capability boundary.
        """
        del tool_ids, max_iterations, verbose
        if custom_tools:
            return self._failure("Custom tools are not permitted in the constrained RAG Agent")
        try:
            self.builtin_tools = self._load_builtin_tools(knowledge_base_ids or [])
            return await self._run_workflow(task, knowledge_base_ids)
        except Exception as exc:
            logger.error("Constrained RAG Agent failed: %s", exc, exc_info=True)
            return self._failure(exc)

    async def stream_execute_task(
        self,
        task: str,
        tool_ids: Optional[List[int]] = None,
        custom_tools: Optional[List[BaseTool]] = None,
        knowledge_base_ids: Optional[List[int]] = None,
        max_iterations: int = 10,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Emit each completed stage, actual LLM deltas, then validation/result."""
        del tool_ids, max_iterations
        if custom_tools:
            yield {
                "type": "error",
                "data": {
                    "message": "Custom tools are not permitted in the constrained RAG Agent",
                    "steps": [],
                    "metrics": {},
                },
            }
            return

        state: Optional[Dict[str, Any]] = None
        try:
            state = self._initialize_workflow(task, knowledge_base_ids)
            yield {"type": "step", "data": await self._run_query_rewrite_stage(state)}
            yield {"type": "step", "data": await self._run_retrieval_stage(state)}
            yield {"type": "step", "data": await self._run_context_selection_stage(state)}
            async for delta in self._stream_answer(state):
                yield {"type": "token", "data": {"content": delta}}
            result = await self._finish_workflow(state, state["answer_data"])
            yield {"type": "step", "data": result["steps"][-1]}
            yield {
                "type": "result",
                "data": {
                    "result": result["result"],
                    "steps": result["steps"],
                    "status": result["status"],
                    "metrics": result["metrics"],
                },
            }
        except Exception as exc:
            logger.error("Constrained RAG Agent stream failed: %s", exc, exc_info=True)
            yield {
                "type": "error",
                "data": {
                    "message": str(exc),
                    "steps": state["steps"] if state else [],
                    "metrics": {},
                },
            }

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Expose only the fixed constrained RAG tool descriptors."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "type": "builtin",
                "is_enabled": True,
            }
            for tool in self.builtin_tools
        ]


__all__ = ["AgentManager"]
