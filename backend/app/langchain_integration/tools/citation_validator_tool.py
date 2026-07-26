"""Citation validator tool for the constrained local RAG workflow."""

import json
from typing import Any, Dict, List, Optional, Type

from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from app.services.rag.citation_service import CitationService


class CitationValidatorInput(BaseModel):
    """Input accepted by :class:`CitationValidatorTool`."""

    answer: str = Field(..., description="Generated answer to validate")
    chunks: List[Dict[str, Any]] = Field(default_factory=list, description="Selected chunks")


class CitationValidatorTool(BaseTool):
    """Check that answer citations reference selected local chunks only."""

    name: str = "citation_validator"
    description: str = "Validate answer citations against selected local knowledge-base chunks."
    args_schema: Type[BaseModel] = CitationValidatorInput

    def _run(
        self,
        answer: str,
        chunks: List[Dict[str, Any]],
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        return json.dumps(CitationService().validate(answer, chunks), ensure_ascii=False)

    async def _arun(
        self,
        answer: str,
        chunks: List[Dict[str, Any]],
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        return self._run(answer, chunks, run_manager)


__all__ = ["CitationValidatorInput", "CitationValidatorTool"]
