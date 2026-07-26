"""Deterministic, constrained local knowledge-base RAG Agent workflow."""

import json
import logging
import time
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from langchain.tools import BaseTool
from langchain_community.llms import Tongyi

from app.config import settings
from app.langchain_integration.tools import (
    CitationValidatorTool,
    ContextSelectorTool,
    KnowledgeBaseSearchTool,
    QueryRewriterTool,
)
from app.services.rag.citation_service import CitationService

logger = logging.getLogger(__name__)


class AgentManager:
    """Run a fixed four-stage RAG workflow with an inspectable JSON trace.

    The manager intentionally does not use ReAct tool choice: allowing an LLM
    to select arbitrary tools would weaken the local-knowledge-base boundary.
    Each tool emits JSON, which is copied into the persisted execution steps.
    """

    _CONTEXT_MAX_CHARS = 6000

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or settings.tongyi.dashscope_api_key
        self.llm = Tongyi(
            dashscope_api_key=self.api_key,
            model_name=settings.tongyi.tongyi_model_name,
            temperature=settings.tongyi.tongyi_temperature,
            max_tokens=settings.tongyi.tongyi_max_tokens,
        )
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
        """Invoke a tool and require a JSON object observation for the trace."""
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
    def _render_context(chunks: List[Dict[str, Any]]) -> str:
        """Render selected chunks in the exact citation syntax required by the LLM."""
        rendered = []
        for chunk in chunks:
            citation_id = CitationService.citation_id(chunk)
            content = str(chunk.get("content", ""))
            if citation_id and content:
                rendered.append(f"[citation:{citation_id}] {content}")
        return "\n\n".join(rendered)

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

    async def _generate_answer(
        self,
        original_question: str,
        rewritten_query: str,
        final_context: str,
    ) -> Dict[str, Any]:
        """Generate a grounded answer and record generation metrics."""
        if not final_context:
            return {
                "answer": "No relevant content was found in the selected local knowledge bases.",
                "tokens_used": 0,
                "generation_time_ms": 0.0,
            }

        prompt = (
            "Answer only from the local knowledge-base context below. "
            "For every factual statement, preserve the source tag exactly as "
            "[citation:<document_id>:<chunk_index>]. If the context is insufficient, "
            "say so instead of using outside knowledge.\n\n"
            f"Original question: {original_question}\n"
            f"Retrieval query: {rewritten_query}\n\n"
            f"Local context:\n{final_context}\n\nAnswer:"
        )
        started = time.perf_counter()
        response = await self.llm.ainvoke(prompt)
        generation_time_ms = round((time.perf_counter() - started) * 1000, 2)
        answer = getattr(response, "content", response)
        return {
            "answer": str(answer),
            "tokens_used": self._tokens_from_response(response),
            "generation_time_ms": generation_time_ms,
        }

    async def _run_workflow(
        self,
        task: str,
        knowledge_base_ids: Optional[List[int]],
    ) -> Dict[str, Any]:
        """Execute rewrite, retrieval, selection and answer/citation validation."""
        started = time.perf_counter()
        scope = list(knowledge_base_ids or [])
        if not scope:
            raise ValueError("At least one authorized knowledge_base_id is required")

        tools = self._select_tools()
        if not tools:
            return {
                "result": None,
                "steps": [],
                "status": "failed",
                "error": "No constrained RAG tools are available",
                "metrics": {},
            }

        rewriter = self._tool_by_name(tools, "query_rewriter")
        search = self._tool_by_name(tools, "knowledge_base_search")
        selector = self._tool_by_name(tools, "context_selector")
        validator = self._tool_by_name(tools, "citation_validator")

        rewrite_data = await self._invoke_json_tool(rewriter, {"question": task})
        rewritten_query = str(rewrite_data.get("rewritten_query") or task)
        steps = [
            self._step(
                1,
                "query_rewrite",
                rewriter.name,
                {"question": task},
                {
                    "original_question": task,
                    "rewritten_query": rewritten_query,
                    "knowledge_base_scope": scope,
                },
            )
        ]

        retrieval_parameters = {
            "top_k": settings.rag.rag_top_k,
            "similarity_threshold": settings.rag.rag_similarity_threshold,
        }
        search_data = await self._invoke_json_tool(
            search,
            {
                "query": rewritten_query,
                "knowledge_base_ids": scope,
                "top_k": retrieval_parameters["top_k"],
            },
        )
        raw_chunks = list(search_data.get("results") or [])
        retrieval_time_ms = float(search_data.get("retrieval_time_ms", 0.0) or 0.0)
        steps.append(
            self._step(
                2,
                "retrieval",
                search.name,
                {
                    "query": rewritten_query,
                    "knowledge_base_ids": scope,
                    "top_k": retrieval_parameters["top_k"],
                },
                {
                    "knowledge_base_scope": scope,
                    "retrieval_parameters": retrieval_parameters,
                    "raw_chunks": raw_chunks,
                    "retrieval_time_ms": retrieval_time_ms,
                },
            )
        )

        selection_data = await self._invoke_json_tool(
            selector, {"chunks": raw_chunks, "max_chars": self._CONTEXT_MAX_CHARS}
        )
        filtered_chunks = list(selection_data.get("selected_chunks") or [])
        final_context = self._render_context(filtered_chunks)
        steps.append(
            self._step(
                3,
                "context_selection",
                selector.name,
                {"chunk_count": len(raw_chunks), "max_chars": self._CONTEXT_MAX_CHARS},
                {
                    "raw_chunk_count": len(raw_chunks),
                    "filtered_chunks": filtered_chunks,
                    "final_context": final_context,
                    "context_char_count": len(final_context),
                },
            )
        )

        answer_data = await self._generate_answer(task, rewritten_query, final_context)
        answer = str(answer_data.get("answer", ""))
        citation_validation = await self._invoke_json_tool(
            validator, {"answer": answer, "chunks": filtered_chunks}
        )
        generation_time_ms = float(answer_data.get("generation_time_ms", 0.0) or 0.0)
        total_time_ms = round((time.perf_counter() - started) * 1000, 2)
        metrics = {
            "retrieval_time_ms": retrieval_time_ms,
            "generation_time_ms": generation_time_ms,
            "total_time_ms": total_time_ms,
        }
        steps.append(
            self._step(
                4,
                "answer_and_citation_validation",
                validator.name,
                {"answer": answer, "chunk_count": len(filtered_chunks)},
                {
                    "answer": answer,
                    "citation_validation": citation_validation,
                    "tokens_used": int(answer_data.get("tokens_used", 0) or 0),
                    **metrics,
                },
            )
        )
        return {
            "result": answer,
            "steps": steps,
            "status": "completed",
            "error": None,
            "metrics": metrics,
        }

    async def execute_task(
        self,
        task: str,
        knowledge_base_ids: Optional[List[int]] = None,
        max_iterations: int = 10,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """Execute the fixed workflow; iteration and verbosity remain API-compatible."""
        del max_iterations, verbose
        try:
            self.builtin_tools = self._load_builtin_tools(knowledge_base_ids or [])
            return await self._run_workflow(task, knowledge_base_ids)
        except Exception as exc:
            logger.error("Constrained RAG Agent failed: %s", exc, exc_info=True)
            return {
                "result": None,
                "steps": [],
                "status": "failed",
                "error": str(exc),
                "metrics": {},
            }

    async def stream_execute_task(
        self,
        task: str,
        knowledge_base_ids: Optional[List[int]] = None,
        max_iterations: int = 10,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Emit the persisted structured steps followed by one final result event."""
        result = await self.execute_task(
            task=task,
            knowledge_base_ids=knowledge_base_ids,
            max_iterations=max_iterations,
            verbose=False,
        )
        if result["status"] != "completed":
            yield {
                "type": "error",
                "data": {
                    "message": result.get("error", "Constrained RAG Agent failed"),
                    "steps": result.get("steps", []),
                    "metrics": result.get("metrics", {}),
                },
            }
            return
        for step in result["steps"]:
            yield {"type": "step", "data": step}
        yield {
            "type": "result",
            "data": {
                "result": result["result"],
                "steps": result["steps"],
                "status": result["status"],
                "metrics": result["metrics"],
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
