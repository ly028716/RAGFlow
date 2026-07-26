"""Query rewrite tool for the constrained local RAG workflow."""

import json
from typing import Optional, Type

from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from app.services.rag.query_rewrite_service import QueryRewriteService


class QueryRewriterInput(BaseModel):
    """Input accepted by :class:`QueryRewriterTool`."""

    question: str = Field(..., min_length=1, description="User's original question")


class QueryRewriterTool(BaseTool):
    """Normalize a user question before local knowledge-base retrieval."""

    name: str = "query_rewriter"
    description: str = "Normalize the question for local knowledge-base retrieval."
    args_schema: Type[BaseModel] = QueryRewriterInput

    def _run(
        self, question: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        rewritten = QueryRewriteService().rewrite(question)
        return json.dumps(
            {"original_question": question, "rewritten_query": rewritten},
            ensure_ascii=False,
        )

    async def _arun(
        self, question: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        return self._run(question, run_manager)


__all__ = ["QueryRewriterInput", "QueryRewriterTool"]
