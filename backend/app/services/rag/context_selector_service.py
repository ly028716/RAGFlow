"""Context-budget selection for retrieved RAG chunks."""

from typing import Any, Dict, List


class ContextSelectorService:
    """Keep the most relevant complete chunks that fit the prompt budget."""

    @staticmethod
    def _score(chunk: Dict[str, Any]) -> float:
        """Read a normalized score from either supported result field."""
        try:
            return float(chunk.get("similarity", chunk.get("score", 0.0)))
        except (TypeError, ValueError):
            return 0.0

    def select(self, chunks: List[dict], max_chars: int) -> List[dict]:
        """Return high-score chunks without splitting any chunk or mutating input.

        A chunk that would exhaust the remaining character budget is skipped so
        a later, smaller source can still contribute evidence to the answer.
        """
        if max_chars <= 0:
            return []

        ordered = sorted(
            enumerate(chunks), key=lambda item: (-self._score(item[1]), item[0])
        )
        selected: List[dict] = []
        used_chars = 0
        for _, chunk in ordered:
            content = str(chunk.get("content", ""))
            if not content:
                continue
            if used_chars + len(content) > max_chars:
                continue
            selected.append(dict(chunk))
            used_chars += len(content)
        return selected


__all__ = ["ContextSelectorService"]
