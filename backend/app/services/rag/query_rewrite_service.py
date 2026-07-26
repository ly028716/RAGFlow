"""Deterministic, local query normalization for the constrained RAG Agent."""

import re


class QueryRewriteService:
    """Rewrite only unambiguous conversational prefixes without changing intent."""

    _POLITE_PREFIX = re.compile(
        r"^(?:请问|请帮我(?:查询|查找|了解)?|帮我(?:查询|查找|了解)?|麻烦你(?:查询|查找|了解)?)[，,：:\s]*"
    )

    def rewrite(self, question: str) -> str:
        """Return a retrieval-ready query while preserving an already clear question.

        This deliberately does not call an external LLM.  The agent's rewrite
        step must be deterministic and inspectable before retrieval; a concise
        question is therefore returned unchanged.
        """
        normalized = " ".join((question or "").split())
        if not normalized:
            return ""
        rewritten = self._POLITE_PREFIX.sub("", normalized).strip()
        return rewritten or normalized


__all__ = ["QueryRewriteService"]
