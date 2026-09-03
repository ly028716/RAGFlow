#!/usr/bin/env python3
"""Upload the versioned RAG evaluation corpus and write a runtime ID mapping.

The corpus uses stable logical IDs (filenames) in source control.  The database
assigns numeric document IDs, so this script writes an environment-specific
mapping that lets evaluation results compare retrieved document IDs correctly.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS_ROOT = REPOSITORY_ROOT / "docs" / "evaluation-corpus" / "rag-agent-demo"


def load_manifest(corpus_root: Path = DEFAULT_CORPUS_ROOT) -> dict[str, Any]:
    """Load the checked-in corpus manifest."""
    return json.loads((corpus_root / "manifest.json").read_text(encoding="utf-8"))


def upload_document(
    client: httpx.Client, api_base_url: str, knowledge_base_id: int, path: Path
) -> dict[str, Any]:
    """Upload one corpus document and return the API response."""
    with path.open("rb") as handle:
        response = client.post(
            f"{api_base_url.rstrip('/')}/documents/upload",
            params={"knowledge_base_id": knowledge_base_id},
            files={"file": (path.name, handle, "text/markdown")},
        )
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knowledge-base-id", type=int, required=True)
    parser.add_argument(
        "--api-base-url", default="http://localhost:8000/api/v1", help="API v1 base URL"
    )
    parser.add_argument(
        "--access-token",
        default=os.getenv("RAG_EVAL_ACCESS_TOKEN"),
        help="Bearer access token (or set RAG_EVAL_ACCESS_TOKEN)",
    )
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=DEFAULT_CORPUS_ROOT,
        help="Directory containing manifest.json and its Markdown corpus",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path for the environment-specific runtime ID mapping",
    )
    args = parser.parse_args()
    if not args.access_token:
        parser.error("--access-token or RAG_EVAL_ACCESS_TOKEN is required")

    corpus_root = args.corpus_root.resolve()
    manifest = load_manifest(corpus_root)
    output_path = args.output or corpus_root / "runtime-document-map.local.json"
    headers = {"Authorization": f"Bearer {args.access_token}"}
    runtime_documents: list[dict[str, Any]] = []
    with httpx.Client(headers=headers, timeout=60.0) as client:
        for item in manifest["documents"]:
            result = upload_document(
                client,
                args.api_base_url,
                args.knowledge_base_id,
                corpus_root / item["corpus_path"],
            )
            runtime_documents.append(
                {
                    "logical_document_id": item["logical_document_id"],
                    "expected_source_identifier": item["expected_source_identifier"],
                    "runtime_document_id": result["id"],
                    "runtime_filename": result["filename"],
                }
            )

    output_data = {
        "corpus_id": manifest["corpus_id"],
        "knowledge_base_id": args.knowledge_base_id,
        "documents": runtime_documents,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Uploaded {len(runtime_documents)} documents; runtime mapping: {output_path}")
    print("Wait for all document statuses to become completed before running evaluation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
