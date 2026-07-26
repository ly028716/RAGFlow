"""Citation parsing and validation for local-knowledge-base answers."""

import re
from typing import Any, Dict, List, Set


class CitationService:
    """Validate ``[citation:<document_id>:<chunk_index>]`` references."""

    _CITATION_PATTERN = re.compile(r"\[citation:([^\]]+)\]")

    @staticmethod
    def citation_id(chunk: Dict[str, Any]) -> str:
        """Build the stable identifier used in model-visible citations."""
        explicit_id = chunk.get("citation_id")
        if explicit_id is not None:
            return str(explicit_id)
        document_id = chunk.get("document_id")
        chunk_index = chunk.get("chunk_index")
        if document_id is None:
            return ""
        if chunk_index is None:
            return str(document_id)
        return f"{document_id}:{chunk_index}"

    def validate(self, answer: str, chunks: List[dict]) -> dict:
        """Return citation validity, unknown ids and the ids checked.

        A response grounded in selected chunks must carry at least one explicit
        citation.  With no selected chunks, a citation-free answer is valid.
        """
        available_ids: Set[str] = {
            citation_id
            for chunk in chunks
            if (citation_id := self.citation_id(chunk))
        }
        referenced_ids = list(dict.fromkeys(self._CITATION_PATTERN.findall(answer or "")))
        missing_ids = sorted(
            citation_id for citation_id in referenced_ids if citation_id not in available_ids
        )
        valid = not missing_ids and (not available_ids or bool(referenced_ids))
        return {
            "valid": valid,
            "missing_citation_ids": missing_ids,
            "referenced_citation_ids": referenced_ids,
            "available_citation_ids": sorted(available_ids),
        }


__all__ = ["CitationService"]
