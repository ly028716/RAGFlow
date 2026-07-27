# RAG Agent 评估报告

## 目的和固定数据集

本报告评估受限本地知识库 RAG Agent 的检索质量、答案忠实度与端到端延迟。数据集为 [rag-evaluation-dataset.jsonl](./rag-evaluation-dataset.jsonl)，共 **24** 个固定问题；每行均包含 `id`、`knowledge_base`、`question`、`expected_document_ids` 和 `expected_answer_points`。

版本化演示语料和稳定逻辑 ID 位于 [evaluation-corpus/rag-agent-demo](./evaluation-corpus/rag-agent-demo)。数据集中的 `expected_document_ids` 是逻辑文件名，不是数据库自增 ID；`manifest.json` 将每个逻辑 ID 映射到稳定的 `expected_source_identifier`。运行导入脚本后，会生成该次环境的 `runtime-document-map.local.json`，其中保存逻辑 ID 到真实 `Document.id` 的映射。该映射和模型版本必须与结果一并归档，避免把不同语料、模型或索引参数的结果直接比较。

### 导入固定语料

1. 使用界面或 `POST /api/v1/knowledge-bases` 创建名为 `rag-agent-demo` 的知识库，并记录其数字 ID。
2. 登录获得访问令牌，将令牌放入 `RAG_EVAL_ACCESS_TOKEN`。
3. 在仓库根目录运行以下命令；脚本按 `manifest.json` 上传全部 16 个 Markdown 文档，并写出本次评测的真实 ID 映射。

```bash
python backend/scripts/import_rag_evaluation_corpus.py --knowledge-base-id <知识库ID>
```

4. 等待所有文档状态为 `completed`，再用生成的 `runtime-document-map.local.json` 将每题逻辑期望 ID 转换为实际 `document_id` 评分。

## 采集过程

1. 固定 `LLM_PROVIDER=dashscope`、`LLM_MODEL=qwen-plus`、`EMBEDDING_PROVIDER=dashscope`、`EMBEDDING_MODEL=text-embedding-v3`。
2. 固定分块、Top-K、阈值和提示词；记录 Git commit、语料版本、运行时 ID 映射和 DashScope 模型版本。
3. 每题保存检索到的真实文档 ID、原始与最终上下文、流式事件、最终答案和引用校验结果。
4. 由两位评审独立标注 Faithfulness 与 Answer Relevancy；存在分歧时复核并记录结论。

## 指标定义

| 指标 | 定义 | 方向 |
| --- | --- | --- |
| Recall@K | `Top-K 检索结果中命中的期望文档数 / 期望文档数`，再对题目求平均。 | 越高越好 |
| Hit Rate | 至少命中一个 `expected_document_ids` 的题目占比。 | 越高越好 |
| Faithfulness | 答案中的可验证断言被最终上下文或有效引用支持的比例。 | 越高越好 |
| Answer Relevancy | 回答覆盖 `expected_answer_points` 且未偏离问题的人工评分，按 0–1 归一化。 | 越高越好 |
| 平均检索耗时 | 全部题目的 `retrieval_time_ms` 平均值。 | 越低越好 |
| 首 Token 延迟 | 从服务收到请求到首个 `token` SSE 事件的毫秒数平均值。 | 越低越好 |

`citation_validation.valid=false` 的样本必须单列，不得只用表面可读性掩盖无效来源。

## 结果模板

| 运行日期 | Commit | 语料版本 | Top-K / 阈值 | LLM / Embedding | Recall@K | Hit Rate | Faithfulness | Answer Relevancy | 平均检索耗时 | 平均首 Token 延迟 | 无效引用数 |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 待执行 | 待填写 | rag-agent-demo-v1 | 待填写 | qwen-plus / text-embedding-v3 | — | — | — | — | — | — | — |

## 逐题记录模板

| ID | 实际检索文档 | 命中期望文档 | 引用校验 | Faithfulness | Relevancy | 检索 ms | 首 Token ms | 问题与处理结论 |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| rag-001 | 待填写 | 待填写 | 待填写 | — | — | — | — | 待填写 |

## 回归判定

- 若 Recall@K、Hit Rate、Faithfulness 或 Answer Relevancy 下降，先检查语料版本和标注映射，再检查改写、阈值和上下文选择。
- 若延迟上升，分开检查 DashScope 首 Token 时间、向量检索和后端排队时间。
- 若无效引用出现，视为阻断发布的问题：检查引用 ID 生成、上下文截断和输出提示词。
- 不编造基准数值；没有实际执行的指标保留为空或标记“待执行”。
