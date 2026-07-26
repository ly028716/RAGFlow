"""Context selection tool for the constrained local RAG workflow."""

import json
from typing import Any, Dict, List, Optional, Type

from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from app.services.rag.context_selector_service import ContextSelectorService


class ContextSelectorInput(BaseModel):
    """Input accepted by :class:`ContextSelectorTool`."""

    chunks: List[Dict[str, Any]] = Field(default_factory=list, description="Retrieved chunks")
    max_chars: int = Field(default=6000, ge=1, description="Maximum context characters")


class ContextSelectorTool(BaseTool):
    """Select citation-ready chunks that fit the final prompt budget."""

    name: str = "context_selector"
    description: str = "Select the highest-scoring local chunks within a character budget."
    args_schema: Type[BaseModel] = ContextSelectorInput

    def _run(
        self,
        chunks: List[Dict[str, Any]],
        max_chars: int = 6000,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        selected = ContextSelectorService().select(chunks, max_chars)
        return json.dumps(
            {
                "selected_chunks": selected,
                "selected_count": len(selected),
                "max_chars": max_chars,
            },
            ensure_ascii=False,
        )

    async def _arun(
        self,
        chunks: List[Dict[str, Any]],
        max_chars: int = 6000,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        return self._run(chunks, max_chars, run_manager)


__all__ = ["ContextSelectorInput", "ContextSelectorTool"]
