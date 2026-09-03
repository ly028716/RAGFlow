#!/usr/bin/env python3
"""Run reproducible, API-first RAG/Agent evaluations and archive evidence.

The runner intentionally calls the public RAGFlow SSE endpoints.  It does not
invoke internal retrieval classes, so permissions, Chroma, LLM generation and
stream timing are exercised exactly as they are in the demo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Optional

import httpx


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS_ROOT = REPOSITORY_ROOT / "docs" / "evaluation-corpus" / "vehicle-agent-demo"
DEFAULT_DATASET = REPOSITORY_ROOT / "docs" / "vehicle-rag-evaluation-dataset.jsonl"
DEFAULT_RESULTS_ROOT = REPOSITORY_ROOT / "docs" / "evaluation-results" / "vehicle-agent-demo-v1"
REFUSAL_CITATION_MARKER = "[citation:"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a non-empty JSONL dataset with contextual validation errors."""
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_number}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"Dataset row {line_number} must be a JSON object")
        rows.append(item)
    if not rows:
        raise ValueError(f"Dataset is empty: {path}")
    return rows


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON object expected: {path}")
    return data


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def runtime_document_ids(
    expected_logical_ids: list[str], runtime_map: dict[str, Any]
) -> list[int]:
    mapping = {
        item["logical_document_id"]: item["runtime_document_id"]
        for item in runtime_map.get("documents", [])
        if isinstance(item, dict)
        and isinstance(item.get("logical_document_id"), str)
        and isinstance(item.get("runtime_document_id"), int)
    }
    missing = [document_id for document_id in expected_logical_ids if document_id not in mapping]
    if missing:
        raise ValueError(f"Runtime document mapping missing logical IDs: {', '.join(missing)}")
    return [mapping[document_id] for document_id in expected_logical_ids]


def score_retrieval(
    expected_document_ids: list[int], retrieved_document_ids: list[int]
) -> dict[str, Any]:
    """Score one answerable case without inventing a score for unknown-answer cases."""
    if not expected_document_ids:
        return {
            "recall_at_k": None,
            "hit": None,
            "reciprocal_rank": None,
            "matched_document_ids": [],
        }
    expected_set = set(expected_document_ids)
    matched = [document_id for document_id in expected_document_ids if document_id in retrieved_document_ids]
    first_rank = next(
        (index for index, document_id in enumerate(retrieved_document_ids, start=1) if document_id in expected_set),
        None,
    )
    return {
        "recall_at_k": len(matched) / len(expected_document_ids),
        "hit": bool(matched),
        "reciprocal_rank": 1.0 / first_rank if first_rank else 0.0,
        "matched_document_ids": matched,
    }


def is_refusal(answer: str, expected_patterns: list[str]) -> bool:
    """A refusal must use a declared phrase and must not pretend to cite evidence."""
    normalized_answer = answer.strip()
    return (
        bool(normalized_answer)
        and REFUSAL_CITATION_MARKER not in normalized_answer.lower()
        and any(pattern in normalized_answer for pattern in expected_patterns)
    )


def _step_data(step: dict[str, Any]) -> dict[str, Any]:
    data = step.get("data")
    if isinstance(data, dict):
        nested_data = data.get("data")
        if isinstance(nested_data, dict):
            return nested_data
        return data
    observation = step.get("observation")
    if isinstance(observation, dict):
        return observation
    if isinstance(observation, str):
        try:
            parsed = json.loads(observation)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def extract_agent_result(events: list[dict[str, Any]], first_token_latency_ms: Optional[float]) -> dict[str, Any]:
    """Extract public Agent trace evidence from the streamed event contract."""
    steps: list[dict[str, Any]] = []
    final_payload: dict[str, Any] = {}
    answer_fragments: list[str] = []
    for event in events:
        payload = event.get("data") if isinstance(event.get("data"), dict) else {}
        if event.get("type") == "step" and isinstance(payload, dict):
            steps.append(payload)
        elif event.get("type") == "token" and isinstance(payload, dict):
            answer_fragments.append(str(payload.get("content", "")))
        elif event.get("type") == "result" and isinstance(payload, dict):
            final_payload = payload
            result_steps = payload.get("steps")
            if isinstance(result_steps, list):
                steps_by_number = {
                    step.get("step_number"): step
                    for step in steps
                    if isinstance(step, dict) and step.get("step_number") is not None
                }
                steps_by_number.update(
                    {
                        step.get("step_number"): step
                        for step in result_steps
                        if isinstance(step, dict) and step.get("step_number") is not None
                    }
                )
                steps = list(steps_by_number.values())

    retrieval_step = next((step for step in steps if step.get("step_number") == 2), {})
    completion_step = next((step for step in steps if step.get("step_number") == 4), {})
    retrieval_data = _step_data(retrieval_step)
    completion_data = _step_data(completion_step)
    chunks = retrieval_data.get("raw_chunks", [])
    chunks = chunks if isinstance(chunks, list) else []
    metrics = final_payload.get("metrics", {})
    metrics = metrics if isinstance(metrics, dict) else {}
    citation_validation = completion_data.get("citation_validation", {})
    citation_validation = citation_validation if isinstance(citation_validation, dict) else {}
    answer = str(final_payload.get("result") or "".join(answer_fragments))
    return {
        "answer": answer,
        "retrieved_chunks": chunks,
        "retrieved_document_ids": [
            item["document_id"] for item in chunks if isinstance(item, dict) and isinstance(item.get("document_id"), int)
        ],
        "citation_valid": citation_validation.get("valid") if "valid" in citation_validation else None,
        "retrieval_time_ms": metrics.get("retrieval_time_ms", retrieval_data.get("retrieval_time_ms")),
        "generation_time_ms": metrics.get("generation_time_ms"),
        "total_time_ms": metrics.get("total_time_ms"),
        "first_token_latency_ms": first_token_latency_ms,
    }


def extract_rag_result(events: list[dict[str, Any]], first_token_latency_ms: Optional[float]) -> dict[str, Any]:
    """Extract public plain-RAG SSE evidence; plain RAG has no citation validator."""
    sources: list[dict[str, Any]] = []
    done: dict[str, Any] = {}
    fragments: list[str] = []
    for event in events:
        if event.get("type") == "sources":
            candidate = event.get("sources", [])
            sources = candidate if isinstance(candidate, list) else []
        elif event.get("type") == "token":
            fragments.append(str(event.get("content", "")))
        elif event.get("type") == "done":
            done = event
    return {
        "answer": str(done.get("content") or "".join(fragments)),
        "retrieved_chunks": sources,
        "retrieved_document_ids": [
            item["document_id"] for item in sources if isinstance(item, dict) and isinstance(item.get("document_id"), int)
        ],
        "citation_valid": None,
        "retrieval_time_ms": done.get("retrieval_time_ms"),
        "generation_time_ms": done.get("generation_time_ms"),
        "total_time_ms": None,
        "first_token_latency_ms": first_token_latency_ms,
    }


def stream_sse(
    client: httpx.Client, url: str, payload: dict[str, Any]
) -> tuple[list[dict[str, Any]], Optional[float]]:
    """Call an existing SSE endpoint and retain every JSON event verbatim."""
    events: list[dict[str, Any]] = []
    first_token_latency_ms: Optional[float] = None
    started = time.perf_counter()
    with client.stream("POST", url, json=payload) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            event = json.loads(line[6:])
            if not isinstance(event, dict):
                continue
            if event.get("type") == "token" and first_token_latency_ms is None:
                first_token_latency_ms = round((time.perf_counter() - started) * 1000, 2)
            events.append(event)
    return events, first_token_latency_ms


def summarize(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate only observed numeric values; unavailable metrics remain null."""
    answerable = [item for item in case_results if item.get("answerability") == "answerable" and not item.get("error")]
    unanswerable = [item for item in case_results if item.get("answerability") == "unanswerable" and not item.get("error")]

    def average(field: str, rows: Iterable[dict[str, Any]]) -> Optional[float]:
        values = [float(row[field]) for row in rows if isinstance(row.get(field), (int, float))]
        return round(mean(values), 2) if values else None

    citation_rows = [row for row in answerable if isinstance(row.get("citation_valid"), bool)]
    refusal_rows = [row for row in unanswerable if isinstance(row.get("refusal"), bool)]
    return {
        "total_cases": len(case_results),
        "completed_cases": len([row for row in case_results if not row.get("error")]),
        "failed_cases": len([row for row in case_results if row.get("error")]),
        "answerable_cases": len(answerable),
        "unanswerable_cases": len(unanswerable),
        "recall_at_k": average("recall_at_k", answerable),
        "hit_rate": average("hit_numeric", answerable),
        "mrr": average("reciprocal_rank", answerable),
        "citation_validity_rate": (
            round(mean(1.0 if row["citation_valid"] else 0.0 for row in citation_rows), 4)
            if citation_rows
            else None
        ),
        "average_retrieval_time_ms": average("retrieval_time_ms", case_results),
        "average_generation_time_ms": average("generation_time_ms", case_results),
        "average_first_token_latency_ms": average("first_token_latency_ms", case_results),
        "refusal_rate": (
            round(mean(1.0 if row["refusal"] else 0.0 for row in refusal_rows), 4) if refusal_rows else None
        ),
    }


def markdown_report(metadata: dict[str, Any], summary: dict[str, Any], results: list[dict[str, Any]]) -> str:
    def display(value: Any) -> str:
        if value is None:
            return "—"
        if isinstance(value, float):
            return f"{value:.4f}" if 0 <= value <= 1 else f"{value:.2f}"
        return str(value)

    lines = [
        "# 车载 RAG 评测结果",
        "",
        "本报告由 `run_rag_evaluation.py` 真实调用 RAGFlow API 生成。人工指标未复核时保留为空。",
        "",
        "## 运行元数据",
        "",
        f"- 运行时间：{metadata['run_at_utc']}",
        f"- Git commit：{metadata['git_commit']}",
        f"- 语料：{metadata['corpus_id']}",
        f"- 模式：{metadata['mode']}",
        f"- LLM / Embedding：{metadata['llm_model']} / {metadata['embedding_model']}",
        f"- Top-K / 阈值：{metadata['top_k']} / {metadata['similarity_threshold']}",
        f"- 分块：{metadata['chunk_size']} / {metadata['chunk_overlap']}",
        "",
        "## 自动指标",
        "",
    ]
    metric_fields = (
        "recall_at_k", "hit_rate", "mrr", "citation_validity_rate",
        "average_retrieval_time_ms", "average_generation_time_ms",
        "average_first_token_latency_ms", "refusal_rate",
    )
    summaries = summary.get("by_mode", {metadata["mode"]: summary})
    for mode, mode_summary in summaries.items():
        lines.extend([
            f"### {mode}",
            "",
            "| Recall@K | Hit Rate | MRR | 引用有效率 | 平均检索 ms | 平均生成 ms | 平均首 Token ms | 拒答率 |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            "| " + " | ".join(display(mode_summary[field]) for field in metric_fields) + " |",
            "",
        ])
    lines.extend([
        "## 逐题结果",
        "",
        "| ID | 类型 | 命中文档 | Recall@K | MRR | 引用 | 拒答 | 错误 |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- |",
    ])
    for row in results:
        lines.append(
            "| {id} | {category} | {matched} | {recall} | {mrr} | {citation} | {refusal} | {error} |".format(
                id=row["id"], category=row.get("category", "—"),
                matched=", ".join(map(str, row.get("matched_document_ids", []))) or "—",
                recall=display(row.get("recall_at_k")), mrr=display(row.get("reciprocal_rank")),
                citation=display(row.get("citation_valid")), refusal=display(row.get("refusal")),
                error=str(row.get("error") or "—").replace("|", "/"),
            )
        )
    lines.extend(["", "## 人工复核", "", "Faithfulness 与 Answer Relevancy 请以 `manual-review.jsonl` 的双人独立复核记录为准。", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knowledge-base-id", type=int, required=True)
    parser.add_argument("--access-token", default=os.getenv("RAG_EVAL_ACCESS_TOKEN"))
    parser.add_argument("--api-base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--mode", choices=("agent", "rag", "both"), default="agent")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT)
    parser.add_argument("--runtime-map", type=Path, required=True)
    parser.add_argument("--llm-model", required=True)
    parser.add_argument("--embedding-model", required=True)
    parser.add_argument("--top-k", type=int, required=True)
    parser.add_argument("--similarity-threshold", type=float, required=True)
    parser.add_argument("--chunk-size", type=int, required=True)
    parser.add_argument("--chunk-overlap", type=int, required=True)
    parser.add_argument("--request-timeout", type=float, default=180.0)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if not args.access_token:
        parser.error("--access-token or RAG_EVAL_ACCESS_TOKEN is required")

    manifest_path = args.corpus_root / "manifest.json"
    manifest = read_json(manifest_path)
    dataset = read_jsonl(args.dataset)
    runtime_map = read_json(args.runtime_map)
    run_at = datetime.now(timezone.utc).replace(microsecond=0)
    output_dir = args.output_dir or DEFAULT_RESULTS_ROOT / f"{run_at.strftime('%Y%m%dT%H%M%SZ')}-{args.mode}"
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing evaluation output: {output_dir}")
    output_dir.mkdir(parents=True)

    metadata = {
        "run_at_utc": run_at.isoformat(), "git_commit": git_commit(),
        "corpus_id": manifest.get("corpus_id", "unknown"), "mode": args.mode,
        "knowledge_base_id": args.knowledge_base_id, "llm_model": args.llm_model,
        "embedding_model": args.embedding_model, "top_k": args.top_k,
        "similarity_threshold": args.similarity_threshold, "chunk_size": args.chunk_size,
        "chunk_overlap": args.chunk_overlap, "api_base_url": args.api_base_url,
        "dataset_sha256": sha256_file(args.dataset), "manifest_sha256": sha256_file(manifest_path),
    }
    headers = {"Authorization": f"Bearer {args.access_token}"}
    modes = ("agent", "rag") if args.mode == "both" else (args.mode,)
    results: list[dict[str, Any]] = []
    # Evaluation targets are local RAGFlow endpoints.  Ignore machine-level
    # proxy settings so localhost traffic cannot be routed to an external
    # gateway and reported as a false API failure.
    with httpx.Client(
        headers=headers, timeout=args.request_timeout, trust_env=False
    ) as client:
        for mode in modes:
            endpoint = "/agent/execute/stream" if mode == "agent" else "/rag/query/stream"
            for case in dataset:
                expected_logical_ids = list(case.get("expected_document_ids", []))
                expected_runtime_ids = runtime_document_ids(expected_logical_ids, runtime_map)
                payload: dict[str, Any] = {
                    "knowledge_base_ids": [args.knowledge_base_id],
                    ("task" if mode == "agent" else "question"): case["question"],
                }
                if mode == "rag":
                    payload["top_k"] = args.top_k
                row: dict[str, Any] = {
                    "id": case["id"], "mode": mode, "category": case.get("category"),
                    "answerability": case.get("answerability", "answerable"), "question": case["question"],
                    "expected_document_ids": expected_logical_ids,
                    "expected_runtime_document_ids": expected_runtime_ids,
                }
                try:
                    events, first_token = stream_sse(client, f"{args.api_base_url.rstrip('/')}{endpoint}", payload)
                    extracted = extract_agent_result(events, first_token) if mode == "agent" else extract_rag_result(events, first_token)
                    retrieval = score_retrieval(expected_runtime_ids, extracted["retrieved_document_ids"])
                    row.update(extracted)
                    row.update(retrieval)
                    row["hit_numeric"] = 1.0 if retrieval["hit"] else 0.0 if retrieval["hit"] is not None else None
                    row["refusal"] = is_refusal(extracted["answer"], list(case.get("expected_refusal_patterns", []))) if row["answerability"] == "unanswerable" else None
                    row["raw_events"] = events
                except (httpx.HTTPError, ValueError, KeyError) as exc:
                    row["error"] = str(exc)
                results.append(row)

    summary = summarize(results)
    if args.mode == "both":
        summary["by_mode"] = {
            mode: summarize([row for row in results if row["mode"] == mode]) for mode in modes
        }
    manual_review = [
        {
            "id": row["id"], "mode": row["mode"], "question": row["question"],
            "expected_answer_points": next(case.get("expected_answer_points", []) for case in dataset if case["id"] == row["id"]),
            "answer": row.get("answer", ""), "retrieved_chunks": row.get("retrieved_chunks", []),
            "citation_valid": row.get("citation_valid"), "faithfulness_reviewer_a": None,
            "faithfulness_reviewer_b": None, "answer_relevancy_reviewer_a": None,
            "answer_relevancy_reviewer_b": None,
        }
        for row in results if row.get("answerability") == "answerable"
    ]
    (output_dir / "run-metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "case-results.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in results), encoding="utf-8")
    (output_dir / "sse-events.jsonl").write_text(
        "".join(
            json.dumps({"id": row["id"], "mode": row["mode"], "events": row.get("raw_events", [])}, ensure_ascii=False) + "\n"
            for row in results
        ),
        encoding="utf-8",
    )
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "summary.md").write_text(markdown_report(metadata, summary, results), encoding="utf-8")
    (output_dir / "manual-review.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in manual_review), encoding="utf-8")
    (output_dir / "runtime-document-map.json").write_text(json.dumps(runtime_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Evaluation completed: {output_dir}")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["failed_cases"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
