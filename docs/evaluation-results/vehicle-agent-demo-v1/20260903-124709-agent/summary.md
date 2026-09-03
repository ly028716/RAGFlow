# 车载 RAG 评测结果

本报告由 `run_rag_evaluation.py` 真实调用 RAGFlow API 生成。人工指标未复核时保留为空。

## 运行元数据

- 运行时间：2026-09-03T04:47:11+00:00
- Git commit：a21a671a84899c01e7549f156209cbd18982134e
- 语料：vehicle-agent-demo-v1
- 模式：agent
- LLM / Embedding：qwen-plus / text-embedding-v3
- Top-K / 阈值：5 / 0.7
- 分块：1000 / 200

## 自动指标

### agent

| Recall@K | Hit Rate | MRR | 引用有效率 | 平均检索 ms | 平均生成 ms | 平均首 Token ms | 拒答率 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.5100 | 0.7400 | 0.7400 | 1.0000 | 2383.35 | 1470.21 | 3394.63 | 0.0000 |

## 逐题结果

| ID | 类型 | 命中文档 | Recall@K | MRR | 引用 | 拒答 | 错误 |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| vehicle-001 | single_fact | 1 | 1.0000 | 1.0000 | True | — | — |
| vehicle-002 | single_fact | 2 | 1.0000 | 1.0000 | True | — | — |
| vehicle-003 | single_fact | — | 0.0000 | 0.0000 | True | — | — |
| vehicle-004 | single_fact | — | 0.0000 | 0.0000 | True | — | — |
| vehicle-005 | single_fact | 5 | 1.0000 | 1.0000 | True | — | — |
| vehicle-006 | single_fact | 6 | 1.0000 | 1.0000 | True | — | — |
| vehicle-007 | single_fact | 7 | 1.0000 | 1.0000 | True | — | — |
| vehicle-008 | single_fact | 8 | 1.0000 | 1.0000 | True | — | — |
| vehicle-009 | log_diagnosis | 9 | 0.5000 | 1.0000 | True | — | — |
| vehicle-010 | log_diagnosis | 10 | 0.5000 | 1.0000 | True | — | — |
| vehicle-011 | version_difference | 11 | 0.5000 | 1.0000 | True | — | — |
| vehicle-012 | version_difference | 11 | 0.5000 | 1.0000 | True | — | — |
| vehicle-013 | multi_document | — | 0.0000 | 0.0000 | True | — | — |
| vehicle-014 | multi_document | 4 | 0.3333 | 1.0000 | True | — | — |
| vehicle-015 | log_diagnosis | 5 | 0.3333 | 1.0000 | True | — | — |
| vehicle-016 | log_diagnosis | 6 | 0.5000 | 1.0000 | True | — | — |
| vehicle-017 | security | 3 | 0.5000 | 1.0000 | True | — | — |
| vehicle-018 | security | — | 0.0000 | 0.0000 | True | — | — |
| vehicle-019 | citation | — | 0.0000 | 0.0000 | True | — | — |
| vehicle-020 | unanswerable | — | — | — | True | False | — |
| vehicle-021 | unanswerable | — | — | — | True | False | — |
| vehicle-022 | unanswerable | — | — | — | True | False | — |
| vehicle-023 | unanswerable | — | — | — | True | False | — |
| vehicle-024 | unanswerable | — | — | — | True | False | — |

## 人工复核

Faithfulness 与 Answer Relevancy 请以 `manual-review.jsonl` 的双人独立复核记录为准。
